from __future__ import annotations

import math
import os
from collections import Counter
from statistics import median

import bcrypt
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import inspect, text

from feedback_engine import process_feedback
from models import AdminUser, Feedback, Location, Route, db
from route_intelligence import RouteGraph

app = Flask(__name__)
app.config.from_object('config.Config')
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=False,
    PERMANENT_SESSION_LIFETIME=3600,
)
db.init_app(app)


def normalize_location_name(value):
    if value is None:
        return ''
    return ' '.join(value.strip().split())


def create_csrf_token():
    token = session.get('csrf_token') or os.urandom(16).hex()
    session['csrf_token'] = token
    return token


def validate_csrf(form_token=None):
    if request.method in {'GET', 'HEAD', 'OPTIONS'}:
        return True
    expected = session.get('csrf_token')
    submitted = form_token or request.form.get('csrf_token') or request.headers.get('X-CSRFToken')
    if expected and submitted != expected:
        return False
    return True


def ensure_schema():
    with app.app_context():
        db.create_all()
        inspector = inspect(db.engine)
        tables = set(inspector.get_table_names())

        if 'location' in tables:
            location_columns = {column['name'] for column in inspector.get_columns('location')}
            with db.engine.begin() as connection:
                if 'lat' not in location_columns:
                    connection.execute(text('ALTER TABLE location ADD COLUMN lat FLOAT'))
                if 'lng' not in location_columns:
                    connection.execute(text('ALTER TABLE location ADD COLUMN lng FLOAT'))
                if 'created_at' not in location_columns:
                    connection.execute(text('ALTER TABLE location ADD COLUMN created_at DATETIME'))
                if 'updated_at' not in location_columns:
                    connection.execute(text('ALTER TABLE location ADD COLUMN updated_at DATETIME'))

        if 'route' in tables:
            route_columns = {column['name'] for column in inspector.get_columns('route')}
            with db.engine.begin() as connection:
                if 'notes' not in route_columns:
                    connection.execute(text('ALTER TABLE route ADD COLUMN notes TEXT'))
                if 'created_at' not in route_columns:
                    connection.execute(text('ALTER TABLE route ADD COLUMN created_at DATETIME'))
                if 'updated_at' not in route_columns:
                    connection.execute(text('ALTER TABLE route ADD COLUMN updated_at DATETIME'))

        if 'feedback' in tables:
            feedback_columns = {column['name'] for column in inspector.get_columns('feedback')}
            with db.engine.begin() as connection:
                if 'approved' not in feedback_columns:
                    connection.execute(text('ALTER TABLE feedback ADD COLUMN approved BOOLEAN'))
                if 'suspicious' not in feedback_columns:
                    connection.execute(text('ALTER TABLE feedback ADD COLUMN suspicious BOOLEAN'))
                if 'notes' not in feedback_columns:
                    connection.execute(text('ALTER TABLE feedback ADD COLUMN notes TEXT'))
                if 'source' not in feedback_columns:
                    connection.execute(text('ALTER TABLE feedback ADD COLUMN source VARCHAR(50)'))
                if 'created_at' not in feedback_columns:
                    connection.execute(text('ALTER TABLE feedback ADD COLUMN created_at DATETIME'))
                if 'updated_at' not in feedback_columns:
                    connection.execute(text('ALTER TABLE feedback ADD COLUMN updated_at DATETIME'))

        if 'admin_user' in tables:
            admin_columns = {column['name'] for column in inspector.get_columns('admin_user')}
            with db.engine.begin() as connection:
                if 'created_at' not in admin_columns:
                    connection.execute(text('ALTER TABLE admin_user ADD COLUMN created_at DATETIME'))

        with db.engine.begin() as connection:
            connection.execute(text('CREATE INDEX IF NOT EXISTS idx_location_name ON location (name)'))
            connection.execute(text('CREATE INDEX IF NOT EXISTS idx_route_status ON route (status)'))
            connection.execute(text('CREATE INDEX IF NOT EXISTS idx_feedback_approved ON feedback (approved)'))

        admin_username = os.environ.get('ADMIN_USERNAME', 'admin').strip() or 'admin'
        existing_admin = AdminUser.query.filter_by(username=admin_username).first()
        if not existing_admin:
            admin_password = os.environ.get('ADMIN_PASSWORD')
            if admin_password:
                password_hash = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                db.session.add(AdminUser(username=admin_username, password_hash=password_hash))
                db.session.commit()
            else:
                app.logger.warning(
                    'No admin account was created; set ADMIN_PASSWORD before initializing a new database.'
                )


if os.environ.get('TRUEFARE_WORKER') != '1':
    ensure_schema()


@app.context_processor
def inject_csrf_token():
    return {'csrf_token': create_csrf_token()}


@app.route('/')
def index():
    verified_routes = Route.query.filter_by(status='verified').count()
    total_feedback = Feedback.query.count()
    total_locations = Location.query.count()
    return render_template(
        'index.html',
        verified_routes=verified_routes,
        total_feedback=total_feedback,
        total_locations=total_locations,
    )


@app.route('/about')
def about():
    return render_template('about.html')


def get_or_create_location(name, lat=None, lng=None, city='Unknown'):
    cleaned_name = normalize_location_name(name)
    if not cleaned_name:
        return None

    location = Location.query.filter(Location.name.ilike(cleaned_name)).first()
    if location:
        return location

    try:
        value_lat = float(lat) if lat not in (None, '', 'None') else None
        value_lng = float(lng) if lng not in (None, '', 'None') else None
    except (TypeError, ValueError):
        value_lat = None
        value_lng = None

    location = Location(name=cleaned_name.title(), city=city or 'Unknown', lat=value_lat, lng=value_lng)
    db.session.add(location)
    db.session.commit()
    return location


def compute_driver_comparison(standard_fare, driver_fare):
    if driver_fare is None:
        return {
            'driver_fare': None,
            'difference': None,
            'overcharge': False,
            'fairness': 'No driver fare provided',
            'difference_text': '?',
        }

    standard = float(standard_fare)
    demand = float(driver_fare)
    difference = demand - standard
    overcharge = difference > 0
    fairness = 'Overcharge risk' if overcharge else 'Fair fare' if difference < 0 else 'Aligned fare'
    return {
        'driver_fare': demand,
        'difference': difference,
        'overcharge': overcharge,
        'fairness': fairness,
        'difference_text': f'{difference:+.2f}',
    }


@app.route('/search', methods=['POST'])
def search():
    from_loc = normalize_location_name(request.form.get('from'))
    to_loc = normalize_location_name(request.form.get('to'))
    from_lat = request.form.get('from_lat')
    from_lng = request.form.get('from_lng')
    to_lat = request.form.get('to_lat')
    to_lng = request.form.get('to_lng')
    driver_fare_value = request.form.get('driver_fare')

    if not from_loc or not to_loc:
        return jsonify({'error': 'Both pickup and destination are required.'}), 400

    if from_loc.lower() == to_loc.lower():
        return jsonify({'error': 'Pickup and destination cannot be the same place.'}), 400

    try:
        driver_fare = float(driver_fare_value) if driver_fare_value not in (None, '', 'None') else None
    except ValueError:
        return jsonify({'error': 'Driver-demanded fare must be a valid number.'}), 400

    from_location = get_or_create_location(from_loc, from_lat, from_lng)
    to_location = get_or_create_location(to_loc, to_lat, to_lng)

    routes = Route.query.filter_by(status='verified').all()
    graph = RouteGraph(routes)

    direct = graph.find_direct_route(from_location.id, to_location.id)
    if direct:
        comparison = compute_driver_comparison(direct.fare, driver_fare)
        response = {
            'fare': direct.fare,
            'type': 'verified',
            'source': 'admin_verified',
            'route': [from_location.name, to_location.name],
            'from_lat': from_location.lat,
            'from_lng': from_location.lng,
            'to_lat': to_location.lat,
            'to_lng': to_location.lng,
            'confidence': 1.0,
            'confidence_label': 'High',
            'message': 'Verified fare from the trusted route database.',
            'driver_fare': comparison['driver_fare'],
            'difference': comparison['difference'],
            'overcharge': comparison['overcharge'],
            'fairness': comparison['fairness'],
        }
        return jsonify(response)

    feedbacks = Feedback.query.filter_by(from_location_id=from_location.id, to_location_id=to_location.id).all()
    if feedbacks:
        processed = process_feedback(feedbacks)
        if processed:
            comparison = compute_driver_comparison(processed['mode'], driver_fare)
            return jsonify({
                'fare': processed['mode'],
                'type': 'estimated',
                'source': 'community_estimate',
                'route': [from_location.name, to_location.name],
                'from_lat': from_location.lat,
                'from_lng': from_location.lng,
                'to_lat': to_location.lat,
                'to_lng': to_location.lng,
                'confidence': processed['confidence_score'] * 100,
                'confidence_label': processed['confidence_label'],
                'contributors': processed['total'],
                'distribution': processed.get('distribution', []),
                'message': 'Community estimate only. This is unverified and should be treated as guidance.',
                'driver_fare': comparison['driver_fare'],
                'difference': comparison['difference'],
                'overcharge': comparison['overcharge'],
                'fairness': comparison['fairness'],
            })

    path, total_fare = graph.find_path(from_location.id, to_location.id)
    if path:
        route_names = [Location.query.get(node).name for node in path]
        comparison = compute_driver_comparison(total_fare, driver_fare)
        return jsonify({
            'fare': total_fare,
            'type': 'indirect',
            'source': 'indirect_route',
            'route': route_names,
            'from_lat': from_location.lat,
            'from_lng': from_location.lng,
            'to_lat': to_location.lat,
            'to_lng': to_location.lng,
            'confidence': 0.55,
            'confidence_label': 'Medium',
            'message': 'This route is calculated using connected verified segments.',
            'driver_fare': comparison['driver_fare'],
            'difference': comparison['difference'],
            'overcharge': comparison['overcharge'],
            'fairness': comparison['fairness'],
        })

    return jsonify({
        'fare': None,
        'type': 'none',
        'route': [from_location.name, to_location.name],
        'message': 'No verified or estimated route is available yet. Please submit feedback to help the community.',
    })


@app.route('/feedback', methods=['POST'])
def submit_feedback():
    from_loc = normalize_location_name(request.form.get('from'))
    to_loc = normalize_location_name(request.form.get('to'))
    fare_str = request.form.get('fare')
    from_lat = request.form.get('from_lat')
    from_lng = request.form.get('from_lng')
    to_lat = request.form.get('to_lat')
    to_lng = request.form.get('to_lng')
    notes = request.form.get('notes', '').strip()

    if not from_loc or not to_loc or not fare_str:
        return jsonify({'error': 'All fields are required.'}), 400

    if from_loc.lower() == to_loc.lower():
        return jsonify({'error': 'Pickup and destination cannot be the same place.'}), 400

    try:
        fare = float(fare_str)
        if fare <= 0:
            raise ValueError
    except ValueError:
        return jsonify({'error': 'Please enter a valid positive fare.'}), 400

    from_location = get_or_create_location(from_loc, from_lat, from_lng)
    to_location = get_or_create_location(to_loc, to_lat, to_lng)

    existing = Feedback.query.filter_by(from_location_id=from_location.id, to_location_id=to_location.id, fare=fare).first()
    if existing:
        return jsonify({'success': 'A matching fare has already been submitted for this route. Thank you for helping improve TrueFare.'})

    suspicious = fare < 2 or fare > 1000
    feedback = Feedback(
        from_location_id=from_location.id,
        to_location_id=to_location.id,
        fare=fare,
        suspicious=suspicious,
        notes=notes,
        source='community',
        approved=False,
    )
    db.session.add(feedback)
    db.session.commit()

    return jsonify({'success': 'Feedback submitted successfully. It is now pending admin review.'})


@app.route('/autocomplete', methods=['GET'])
def autocomplete():
    query = normalize_location_name(request.args.get('q', ''))
    if not query:
        return jsonify([])

    locations = Location.query.filter(Location.name.ilike(f'%{query}%')).order_by(Location.name.asc()).limit(10).all()
    suggestions = [location.name for location in locations]
    return jsonify(suggestions)


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if 'admin' in session:
        return redirect(url_for('admin_dashboard'))

    error = None
    if request.method == 'POST':
        if not validate_csrf():
            return jsonify({'success': False, 'error': 'Invalid request token.'}), 400

        username = normalize_location_name(request.form.get('username'))
        password = request.form.get('password') or ''

        user = AdminUser.query.filter(AdminUser.username.ilike(username)).first()
        if user and bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
            session['admin'] = user.username
            session.permanent = True
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True, 'redirect': url_for('admin_dashboard')})
            flash('Welcome back. You are now signed in.', 'success')
            return redirect(url_for('admin_dashboard'))

        error = 'Invalid username or password.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': error}), 401

    return render_template('admin/login.html', error=error)


@app.route('/admin/logout', methods=['GET', 'POST'])
def admin_logout():
    if request.method == 'POST' and not validate_csrf():
        return jsonify({'error': 'Invalid request token.'}), 400
    session.pop('admin', None)
    session.pop('csrf_token', None)
    flash('You have been signed out.', 'info')
    return redirect(url_for('index'))


def require_admin():
    if 'admin' not in session:
        return False
    return True


@app.route('/admin/dashboard')
def admin_dashboard():
    if not require_admin():
        return redirect(url_for('admin_login'))

    routes = Route.query.order_by(Route.updated_at.desc()).all()
    feedbacks = Feedback.query.order_by(Feedback.timestamp.desc()).limit(8).all()
    total_locations = Location.query.count()
    total_routes = Route.query.count()
    verified_routes = Route.query.filter_by(status='verified').count()
    pending_feedback = Feedback.query.filter_by(approved=False).count()
    approved_feedback = Feedback.query.filter_by(approved=True).count()
    total_submissions = Feedback.query.count()

    route_summary = []
    for route in routes[:8]:
        route_summary.append({
            'label': f"{route.from_location.name} → {route.to_location.name}",
            'value': route.fare,
        })

    recent_activity = []
    for entry in feedbacks:
        recent_activity.append({
            'route': f"{entry.from_location.name} → {entry.to_location.name}",
            'fare': entry.fare,
            'time': entry.timestamp.strftime('%b %d, %Y') if entry.timestamp else 'Recently',
            'status': 'Approved' if entry.approved else 'Pending',
        })

    return render_template(
        'admin/dashboard.html',
        routes=routes,
        feedbacks=feedbacks,
        total_locations=total_locations,
        total_routes=total_routes,
        verified_routes=verified_routes,
        pending_feedback=pending_feedback,
        approved_feedback=approved_feedback,
        total_submissions=total_submissions,
        route_summary=route_summary,
        recent_activity=recent_activity,
    )


@app.route('/admin/view_feedback')
def view_feedback():
    if not require_admin():
        return redirect(url_for('admin_login'))

    feedback_groups = build_feedback_groups()
    return render_template('admin/view_feedback.html', feedback_groups=feedback_groups)


@app.route('/admin/add_route', methods=['GET', 'POST'])
def add_route():
    if not require_admin():
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        if not validate_csrf():
            flash('Invalid request token.', 'error')
            return redirect(url_for('add_route'))

        from_loc = normalize_location_name(request.form.get('from'))
        to_loc = normalize_location_name(request.form.get('to'))
        fare_str = request.form.get('fare')
        route_type = request.form.get('type')
        via_loc = normalize_location_name(request.form.get('via'))
        notes = request.form.get('notes', '').strip()

        if not from_loc or not to_loc or not fare_str or not route_type:
            flash('All required route details must be filled.', 'error')
            return redirect(url_for('add_route'))

        try:
            fare = float(fare_str)
            if fare <= 0:
                raise ValueError
        except ValueError:
            flash('Please enter a valid fare value.', 'error')
            return redirect(url_for('add_route'))

        if route_type not in {'direct', 'indirect'}:
            flash('Invalid route type selected.', 'error')
            return redirect(url_for('add_route'))

        if route_type == 'indirect' and not via_loc:
            flash('Indirect routes require a via location.', 'error')
            return redirect(url_for('add_route'))

        from_location = get_or_create_location(from_loc, request.form.get('from_lat'), request.form.get('from_lng'))
        to_location = get_or_create_location(to_loc, request.form.get('to_lat'), request.form.get('to_lng'))

        via_location = None
        if via_loc:
            via_location = get_or_create_location(via_loc, request.form.get('via_lat'), request.form.get('via_lng'))

        route = Route(
            from_location=from_location,
            to_location=to_location,
            fare=fare,
            type=route_type,
            via_location=via_location,
            status='verified',
            notes=notes,
        )
        db.session.add(route)
        db.session.commit()
        flash('Route created successfully.', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('admin/add_route.html')


@app.route('/admin/edit_route/<int:route_id>', methods=['GET', 'POST'])
def edit_route(route_id):
    if not require_admin():
        return redirect(url_for('admin_login'))

    route = Route.query.get_or_404(route_id)
    if request.method == 'POST':
        if not validate_csrf():
            flash('Invalid request token.', 'error')
            return redirect(url_for('edit_route', route_id=route_id))

        from_loc = normalize_location_name(request.form.get('from'))
        to_loc = normalize_location_name(request.form.get('to'))
        fare_str = request.form.get('fare')
        route_type = request.form.get('type')
        via_loc = normalize_location_name(request.form.get('via'))
        notes = request.form.get('notes', '').strip()

        if not from_loc or not to_loc or not fare_str or not route_type:
            flash('Route edits require all required details.', 'error')
            return redirect(url_for('edit_route', route_id=route_id))

        try:
            fare = float(fare_str)
            if fare <= 0:
                raise ValueError
        except ValueError:
            flash('Please enter a valid fare value.', 'error')
            return redirect(url_for('edit_route', route_id=route_id))

        route.from_location = get_or_create_location(from_loc, request.form.get('from_lat'), request.form.get('from_lng'))
        route.to_location = get_or_create_location(to_loc, request.form.get('to_lat'), request.form.get('to_lng'))
        route.fare = fare
        route.type = route_type
        route.status = 'verified'
        route.notes = notes

        if via_loc:
            route.via_location = get_or_create_location(via_loc, request.form.get('via_lat'), request.form.get('via_lng'))
        else:
            route.via_location = None

        db.session.commit()
        flash('Route updated successfully.', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('admin/edit_route.html', route=route)


@app.route('/admin/delete_route/<int:route_id>', methods=['POST'])
def delete_route(route_id):
    if not require_admin():
        return redirect(url_for('admin_login'))
    if not validate_csrf():
        return jsonify({'error': 'Invalid request token.'}), 400

    route = Route.query.get_or_404(route_id)
    db.session.delete(route)
    db.session.commit()
    flash('Route deleted successfully.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/approve_route', methods=['POST'])
def approve_route():
    if not require_admin():
        return redirect(url_for('admin_login'))
    if not validate_csrf():
        flash('Invalid request token.', 'error')
        return redirect(url_for('view_feedback'))

    from_loc = normalize_location_name(request.form.get('from'))
    to_loc = normalize_location_name(request.form.get('to'))
    fare_str = request.form.get('fare')

    if not from_loc or not to_loc or not fare_str:
        flash('All route details are required before approval.', 'error')
        return redirect(url_for('view_feedback'))

    try:
        fare = float(fare_str)
        if fare <= 0:
            raise ValueError
    except ValueError:
        flash('Please enter a valid positive fare.', 'error')
        return redirect(url_for('view_feedback'))

    from_location = get_or_create_location(from_loc)
    to_location = get_or_create_location(to_loc)

    route = Route(from_location=from_location, to_location=to_location, fare=fare, type='direct', status='verified')
    db.session.add(route)

    Feedback.query.filter_by(from_location_id=from_location.id, to_location_id=to_location.id).update({'approved': True})
    db.session.commit()
    flash('Community route approved and added to the verified database.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/feedback/<int:feedback_id>/approve', methods=['POST'])
def approve_feedback(feedback_id):
    if not require_admin():
        return redirect(url_for('admin_login'))
    if not validate_csrf():
        return jsonify({'error': 'Invalid request token.'}), 400

    feedback = Feedback.query.get_or_404(feedback_id)
    feedback.approved = True
    db.session.commit()
    flash('Feedback approved.', 'success')
    return redirect(url_for('view_feedback'))


@app.route('/admin/feedback/<int:feedback_id>/reject', methods=['POST'])
def reject_feedback(feedback_id):
    if not require_admin():
        return redirect(url_for('admin_login'))
    if not validate_csrf():
        return jsonify({'error': 'Invalid request token.'}), 400

    feedback = Feedback.query.get_or_404(feedback_id)
    feedback.approved = False
    feedback.suspicious = True
    db.session.commit()
    flash('Feedback marked as suspicious and rejected.', 'warning')
    return redirect(url_for('view_feedback'))


def build_feedback_groups():
    feedback_groups = {}
    feedbacks = Feedback.query.order_by(Feedback.timestamp.desc()).all()

    for feedback in feedbacks:
        key = (feedback.from_location.name, feedback.to_location.name)
        feedback_groups.setdefault(key, []).append(feedback)

    processed_groups = []
    for (source_name, target_name), entries in feedback_groups.items():
        fares = [float(entry.fare) for entry in entries]
        metric = process_feedback(entries)
        processed_groups.append({
            'from': source_name,
            'to': target_name,
            'mode': metric['mode'] if metric else round(sum(fares) / len(fares), 2),
            'median': metric['median'] if metric else round(median(fares), 2),
            'total': len(entries),
            'confidence': metric['confidence_score'] if metric else 0.0,
            'confidence_label': metric['confidence_label'] if metric else 'Low',
            'suspicious': any(entry.suspicious for entry in entries),
        })

    return processed_groups


@app.route('/api/admin/routes', methods=['GET'])
def api_admin_routes():
    if not require_admin():
        return jsonify({'error': 'Unauthorized'}), 401

    routes = Route.query.order_by(Route.updated_at.desc()).all()
    payload = []
    for route in routes:
        payload.append({
            'id': route.id,
            'from': route.from_location.name,
            'to': route.to_location.name,
            'fare': route.fare,
            'type': route.type,
            'status': route.status,
            'via': route.via_location.name if route.via_location else None,
            'notes': route.notes,
        })
    return jsonify(payload)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
