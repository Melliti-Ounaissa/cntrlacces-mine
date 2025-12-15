"""
models.py - Modèles SQLAlchemy CORRIGÉS pour correspondre au schéma SQL

CORRECTIONS:
- Client utilise maintenant full_name (comme dans le schéma SQL)
- Cohérence totale avec message.txt
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import uuid

db = SQLAlchemy()


# ==================== TABLES DE BASE ====================

class Site(db.Model):
    __tablename__ = 'sites'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    code = db.Column(db.String(10), unique=True, nullable=False)
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    
    # Relations
    departments = db.relationship('Department', backref='site', lazy=True)
    


class Department(db.Model):
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    code = db.Column(db.String(10), nullable=False)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=False)
    
    # Relations
    users = db.relationship('User', backref='department', lazy=True)
    bookings = db.relationship('Booking', foreign_keys='Booking.created_by_department_id', 
                              backref='created_department', lazy=True)


# ==================== SYSTÈME RBAC ====================

class Role(db.Model):
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)
    hierarchy_level = db.Column(db.Integer, nullable=False)


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    phone = db.Column(db.String(50))
    password_hash = db.Column(db.String(255), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relations many-to-many via user_roles
    roles = db.relationship('Role', secondary='user_roles', backref='users', lazy='dynamic')
    
    # Relations one-to-many
    created_bookings = db.relationship('Booking', foreign_keys='Booking.created_by_user_id', 
                                      backref='creator', lazy=True)
    
    # Propriété site_id via department
    @property
    def site_id(self):
        return self.department.site_id if self.department else None
    
    @property
    def site(self):
        return self.department.site if self.department else None
    
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
        # Simplification: basé sur les rôles
        return True


class UserRole(db.Model):
    __tablename__ = 'user_roles'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True, nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), primary_key=True, nullable=False)


# ==================== DONNÉES MÉTIER ====================

class Client(db.Model):
    __tablename__ = 'clients'
    
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    phone = db.Column(db.String(50))
    city = db.Column(db.String(100))
    rgpd_consent = db.Column(db.Boolean, default=False, nullable=False)
    consent_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relations
    bookings = db.relationship('Booking', backref='client', lazy=True)


class Flight(db.Model):
    __tablename__ = 'flights'
    
    id = db.Column(db.Integer, primary_key=True)
    flight_number = db.Column(db.String(50), nullable=False)
    airline = db.Column(db.String(100), nullable=False)
    departure_airport = db.Column(db.String(10), nullable=False)
    arrival_airport = db.Column(db.String(10), nullable=False)
    departure_date = db.Column(db.DateTime, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    
    # Relations
    bookings = db.relationship('Booking', backref='flight', lazy=True)


class Booking(db.Model):
    __tablename__ = 'bookings'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    flight_id = db.Column(db.Integer, db.ForeignKey('flights.id'), nullable=False)
    total_price = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='PENDING')
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Pour RBAC
    created_by_department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    created_at_site_id = db.Column(db.Integer, db.ForeignKey('sites.id'))
    
    # Relations
    payments = db.relationship('Payment', backref='booking', lazy=True)
    
    # Propriétés pour compatibilité avec les templates
    @property
    def booking_reference(self):
        return f"BK{self.id:06d}"
    
    @property
    def booking_type(self):
        return "flight"
    
    @property
    def travel_date(self):
        return self.flight.departure_date.date() if self.flight else None
    
    @property
    def number_of_travelers(self):
        return 1
    
    @property
    def total_amount_dzd(self):
        return self.total_price


class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Propriétés pour compatibilité
    @property
    def amount_dzd(self):
        return self.amount
    
    @property
    def transaction_reference(self):
        return f"TRX{self.id:08d}"