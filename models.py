from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


db = SQLAlchemy()


class Location(db.Model):
    __tablename__ = 'location'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    city = db.Column(db.String(100), nullable=False)
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<Location {self.name}, {self.city}>'


class Route(db.Model):
    __tablename__ = 'route'

    id = db.Column(db.Integer, primary_key=True)
    from_location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=False)
    to_location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=False)
    fare = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(20), nullable=False)
    via_location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='verified', index=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    from_location = db.relationship('Location', foreign_keys=[from_location_id])
    to_location = db.relationship('Location', foreign_keys=[to_location_id])
    via_location = db.relationship('Location', foreign_keys=[via_location_id])

    def __repr__(self):
        return f'<Route {self.from_location.name} to {self.to_location.name} - {self.fare}>'


class Feedback(db.Model):
    __tablename__ = 'feedback'

    id = db.Column(db.Integer, primary_key=True)
    from_location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=False)
    to_location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=False)
    fare = db.Column(db.Float, nullable=False)
    user_identifier = db.Column(db.String(100), nullable=True)
    approved = db.Column(db.Boolean, default=False, nullable=False, index=True)
    suspicious = db.Column(db.Boolean, default=False, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    source = db.Column(db.String(50), default='community', nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    from_location = db.relationship('Location', foreign_keys=[from_location_id])
    to_location = db.relationship('Location', foreign_keys=[to_location_id])

    def __repr__(self):
        return f'<Feedback {self.from_location.name} to {self.to_location.name} - {self.fare}>'


class AdminUser(db.Model):
    __tablename__ = 'admin_user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<AdminUser {self.username}>'
