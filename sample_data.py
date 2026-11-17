from app import app, db
from models import Location, Route

with app.app_context():
    # Sample locations
    locations = [
        Location(name='Downtown', city='Sample City'),
        Location(name='Airport', city='Sample City'),
        Location(name='Mall', city='Sample City'),
        Location(name='University', city='Sample City'),
        Location(name='Hospital', city='Sample City')
    ]

    for loc in locations:
        existing = Location.query.filter_by(name=loc.name).first()
        if not existing:
            db.session.add(loc)

    db.session.commit()

    # Get IDs
    downtown = Location.query.filter_by(name='Downtown').first()
    airport = Location.query.filter_by(name='Airport').first()
    mall = Location.query.filter_by(name='Mall').first()
    uni = Location.query.filter_by(name='University').first()
    hosp = Location.query.filter_by(name='Hospital').first()

    # Sample routes
    routes = [
        Route(from_location_id=downtown.id, to_location_id=airport.id, fare=25.0, type='direct', status='verified'),
        Route(from_location_id=downtown.id, to_location_id=mall.id, fare=10.0, type='direct', status='verified'),
        Route(from_location_id=mall.id, to_location_id=uni.id, fare=8.0, type='direct', status='verified'),
        Route(from_location_id=uni.id, to_location_id=hosp.id, fare=12.0, type='direct', status='verified')
    ]

    for route in routes:
        existing = Route.query.filter_by(from_location_id=route.from_location_id, to_location_id=route.to_location_id).first()
        if not existing:
            db.session.add(route)

    db.session.commit()
    print("Sample data added.")