"""
models.py - Modèles SQLAlchemy adaptés au schéma réel

Adapté au schéma de ton camarade avec :
- full_name au lieu de first_name + last_name
- user_roles (many-to-many)
- Système de permissions
- Contraintes temporelles
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import uuid

db = SQLAlchemy()


# ==================== TABLES DE BASE ====================

class Site(db.Model):
    __tablename__ = 'sites'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.Text, nullable=False)
    code = db.Column(db.Text, unique=True, nullable=False)
    city = db.Column(db.Text)
    address = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    
    # Relations
    departments = db.relationship('Department', backref='site', lazy=True)
    users = db.relationship('User', backref='site', lazy=True)
    clients = db.relationship('Client', backref='registered_site', lazy=True)
    bookings = db.relationship('Booking', backref='created_site', lazy=True)


class Department(db.Model):
    __tablename__ = 'departments'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.Text, nullable=False)
    code = db.Column(db.Text, unique=True, nullable=False)
    site_id = db.Column(db.String(36), db.ForeignKey('sites.id'), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    
    # Relations
    users = db.relationship('User', backref='department', lazy=True)
    bookings = db.relationship('Booking', backref='created_department', lazy=True)


# ==================== SYSTÈME RBAC ====================

class Role(db.Model):
    __tablename__ = 'roles'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.Text, nullable=False)
    code = db.Column(db.Text, unique=True, nullable=False)
    description = db.Column(db.Text)
    hierarchy_level = db.Column(db.Integer, default=0)
    is_multi_site = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    
    # Relations
    permissions = db.relationship('Permission', secondary='role_permissions', 
                                 backref='roles', lazy='dynamic')


class Permission(db.Model):
    __tablename__ = 'permissions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.Text, nullable=False)
    code = db.Column(db.Text, unique=True, nullable=False)
    resource_type = db.Column(db.Text)
    action = db.Column(db.Text)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)


class RolePermission(db.Model):
    __tablename__ = 'role_permissions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    role_id = db.Column(db.String(36), db.ForeignKey('roles.id'), nullable=False)
    permission_id = db.Column(db.String(36), db.ForeignKey('permissions.id'), nullable=False)
    granted_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.Text, unique=True, nullable=False)
    full_name = db.Column(db.Text, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    
    site_id = db.Column(db.String(36), db.ForeignKey('sites.id'), nullable=False)
    department_id = db.Column(db.String(36), db.ForeignKey('departments.id'))
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations many-to-many via user_roles
    roles = db.relationship('Role', secondary='user_roles', backref='users', lazy='dynamic')
    
    # Relations one-to-many
    created_bookings = db.relationship('Booking', foreign_keys='Booking.created_by_user_id', 
                                      backref='creator', lazy=True)
    processed_payments = db.relationship('Payment', backref='processor', lazy=True)
    
    # ===== MÉTHODES UTILITAIRES =====
    
    def has_role(self, role_code):
        """Vérifie si l'utilisateur a un rôle donné"""
        return self.roles.filter_by(code=role_code).first() is not None
    
    def get_highest_role(self):
        """Retourne le rôle avec le niveau hiérarchique le plus élevé"""
        if not self.roles.count():
            return None
        return max(self.roles, key=lambda r: r.hierarchy_level)
    
    def has_permission(self, permission_code):
        """Vérifie si l'utilisateur a une permission donnée"""
        for role in self.roles:
            if role.permissions.filter_by(code=permission_code).first():
                return True
        return False
    
    def can_access_resource(self, resource_type, action):
        """Vérifie si l'utilisateur peut effectuer une action sur une ressource"""
        permission_code = f"{resource_type}.{action}"
        return self.has_permission(permission_code)


class UserRole(db.Model):
    __tablename__ = 'user_roles'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    role_id = db.Column(db.String(36), db.ForeignKey('roles.id'), nullable=False)
    assigned_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    assigned_by = db.Column(db.String(36), db.ForeignKey('users.id'))


# ==================== CONTRAINTES TEMPORELLES ====================

class TemporalConstraint(db.Model):
    __tablename__ = 'temporal_constraints'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.Text)
    description = db.Column(db.Text)
    
    role_id = db.Column(db.String(36), db.ForeignKey('roles.id'))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'))
    department_id = db.Column(db.String(36), db.ForeignKey('departments.id'))
    
    constraint_type = db.Column(db.Text)
    days_of_week = db.Column(db.ARRAY(db.Integer))
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    resource_type = db.Column(db.Text)
    location = db.Column(db.Text)
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)


# ==================== DONNÉES MÉTIER ====================

class Client(db.Model):
    __tablename__ = 'clients'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    first_name = db.Column(db.Text, nullable=False)
    last_name = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, unique=True)
    phone = db.Column(db.Text)
    passport_number = db.Column(db.Text)
    date_of_birth = db.Column(db.Date)
    address = db.Column(db.Text)
    city = db.Column(db.Text)
    country = db.Column(db.Text)
    
    registered_at_site_id = db.Column(db.String(36), db.ForeignKey('sites.id'))
    
    is_personal_data_consented = db.Column(db.Boolean, default=False)
    consent_date = db.Column(db.DateTime(timezone=True))
    
    # Attributs pour le droit à l'oubli (à ajouter par ton camarade)
    is_anonymized = db.Column(db.Boolean, default=False)
    anonymized_at = db.Column(db.DateTime(timezone=True))
    anonymized_by = db.Column(db.String(36), db.ForeignKey('users.id'))
    
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    bookings = db.relationship('Booking', backref='client', lazy=True)


class Flight(db.Model):
    __tablename__ = 'flights'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    flight_number = db.Column(db.Text, nullable=False)
    airline = db.Column(db.Text)
    departure_airport = db.Column(db.Text)
    arrival_airport = db.Column(db.Text)
    departure_time = db.Column(db.DateTime(timezone=True))
    arrival_time = db.Column(db.DateTime(timezone=True))
    price_dzd = db.Column(db.Numeric(15, 2))
    available_seats = db.Column(db.Integer)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    
    # Relations
    bookings = db.relationship('Booking', backref='flight', lazy=True)


class Hotel(db.Model):
    __tablename__ = 'hotels'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.Text, nullable=False)
    city = db.Column(db.Text)
    country = db.Column(db.Text)
    address = db.Column(db.Text)
    stars = db.Column(db.Integer)
    price_per_night_dzd = db.Column(db.Numeric(15, 2))
    available_rooms = db.Column(db.Integer)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    
    # Relations
    bookings = db.relationship('Booking', backref='hotel', lazy=True)


class Package(db.Model):
    __tablename__ = 'packages'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    destination = db.Column(db.Text)
    duration_days = db.Column(db.Integer)
    price_dzd = db.Column(db.Numeric(15, 2))
    includes_flight = db.Column(db.Boolean, default=False)
    includes_hotel = db.Column(db.Boolean, default=False)
    max_participants = db.Column(db.Integer)
    available_slots = db.Column(db.Integer)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    
    # Relations
    bookings = db.relationship('Booking', backref='package', lazy=True)


class Booking(db.Model):
    __tablename__ = 'bookings'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    booking_reference = db.Column(db.Text, unique=True, nullable=False)
    
    client_id = db.Column(db.String(36), db.ForeignKey('clients.id'), nullable=False)
    booking_type = db.Column(db.Text)
    
    flight_id = db.Column(db.String(36), db.ForeignKey('flights.id'))
    hotel_id = db.Column(db.String(36), db.ForeignKey('hotels.id'))
    package_id = db.Column(db.String(36), db.ForeignKey('packages.id'))
    
    booking_date = db.Column(db.DateTime(timezone=True), nullable=False)
    travel_date = db.Column(db.Date)
    return_date = db.Column(db.Date)
    number_of_travelers = db.Column(db.Integer, default=1)
    total_amount_dzd = db.Column(db.Numeric(15, 2))
    status = db.Column(db.Text, default='pending')
    
    # Attributs RBAC
    created_at_site_id = db.Column(db.String(36), db.ForeignKey('sites.id'), nullable=False)
    created_by_user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    created_by_department_id = db.Column(db.String(36), db.ForeignKey('departments.id'))
    
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    payments = db.relationship('Payment', backref='booking', lazy=True)
    invoices = db.relationship('Invoice', backref='booking', lazy=True)


class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    booking_id = db.Column(db.String(36), db.ForeignKey('bookings.id'), nullable=False)
    
    amount_dzd = db.Column(db.Numeric(15, 2), nullable=False)
    payment_method = db.Column(db.Text)
    payment_date = db.Column(db.DateTime(timezone=True), nullable=False)
    card_last_four = db.Column(db.Text)
    transaction_reference = db.Column(db.Text)
    status = db.Column(db.Text, default='pending')
    
    # Attributs RBAC
    processed_by_user_id = db.Column(db.String(36), db.ForeignKey('users.id'))
    processed_at_site_id = db.Column(db.String(36), db.ForeignKey('sites.id'))
    
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)


class Invoice(db.Model):
    __tablename__ = 'invoices'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    invoice_number = db.Column(db.Text, unique=True, nullable=False)
    booking_id = db.Column(db.String(36), db.ForeignKey('bookings.id'), nullable=False)
    
    issue_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date)
    subtotal_dzd = db.Column(db.Numeric(15, 2))
    tax_amount_dzd = db.Column(db.Numeric(15, 2))
    total_amount_dzd = db.Column(db.Numeric(15, 2))
    status = db.Column(db.Text, default='unpaid')
    
    # Attributs RBAC
    generated_by_user_id = db.Column(db.String(36), db.ForeignKey('users.id'))
    generated_at_site_id = db.Column(db.String(36), db.ForeignKey('sites.id'))
    
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)


# ==================== LOGS RGPD ====================

class DataProcessingLog(db.Model):
    __tablename__ = 'data_processing_logs'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'))
    client_id = db.Column(db.String(36), db.ForeignKey('clients.id'))
    
    action = db.Column(db.Text)
    resource_type = db.Column(db.Text)
    resource_id = db.Column(db.String(36))
    
    details = db.Column(db.Text)
    ip_address = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)