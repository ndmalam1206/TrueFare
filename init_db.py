from app import app, db
from models import AdminUser
import bcrypt
import os

with app.app_context():
    db.create_all()

    username = os.environ.get('ADMIN_USERNAME', 'admin').strip() or 'admin'
    password = os.environ.get('ADMIN_PASSWORD')
    if not password:
        raise RuntimeError('Set ADMIN_PASSWORD before initializing the admin account.')

    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    admin = AdminUser(username=username, password_hash=hashed.decode('utf-8'))

    # Check if already exists
    existing = AdminUser.query.filter_by(username=username).first()
    if not existing:
        db.session.add(admin)
        db.session.commit()
        print("Admin user created.")
    else:
        # Update password
        existing.password_hash = hashed.decode('utf-8')
        db.session.commit()
        print("Admin user password updated.")