"""
Routes package - Initialisation des blueprints
"""

from routes.auth import auth_bp
from routes.public import public_bp
from routes.dashboard import dashboard_bp
from routes.bookings import bookings_bp
from routes.clients import clients_bp
from routes.payments import payments_bp
from routes.api import api_bp

__all__ = [
    'auth_bp',
    'public_bp', 
    'dashboard_bp',
    'bookings_bp',
    'clients_bp',
    'payments_bp',
    'api_bp'
]