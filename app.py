"""
app.py - Configuration Flask principale
Projet Big Data VoyagesDZ

Adapté au schéma réel avec :
- user_roles (many-to-many)
- full_name au lieu de first_name + last_name
- Système de permissions
"""

from flask import Flask, redirect, url_for, render_template, flash
from flask_login import LoginManager, current_user
from config import Config
from models import db, User
import logging

# Initialiser Flask
app = Flask(__name__)
app.config.from_object(Config)

# Initialiser la base de données
db.init_app(app)

# Initialiser Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'


@login_manager.user_loader
def load_user(user_id):
    """Charge un utilisateur depuis la BD"""
    return User.query.get(user_id)


# ===== ENREGISTREMENT DES BLUEPRINTS =====

# Routes publiques
from routes.public import public_bp
app.register_blueprint(public_bp)

# Routes authentification
from routes.auth import auth_bp
app.register_blueprint(auth_bp, url_prefix='/auth')

# Routes dashboards
from routes.dashboard import dashboard_bp
app.register_blueprint(dashboard_bp, url_prefix='/dashboard')

# Routes réservations
from routes.bookings import bookings_bp
app.register_blueprint(bookings_bp, url_prefix='/bookings')

# Routes clients
from routes.clients import clients_bp
app.register_blueprint(clients_bp, url_prefix='/clients')

# Routes paiements
from routes.payments import payments_bp
app.register_blueprint(payments_bp, url_prefix='/payments')

# Routes API JSON
from routes.api import api_bp
app.register_blueprint(api_bp, url_prefix='/api')


# ===== REDIRECTION AUTOMATIQUE AU BON DASHBOARD =====

@app.route('/dashboard')
def dashboard_redirect():
    """
    Redirige automatiquement l'utilisateur vers son dashboard
    selon son rôle (le plus élevé)
    """
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    
    # Récupérer le rôle le plus élevé
    highest_role = current_user.get_highest_role()
    
    if not highest_role:
        flash("Vous n'avez pas de rôle assigné. Contactez l'administrateur.", 'error')
        return redirect(url_for('public.index'))
    
    role_code = highest_role.code
    
    # Redirection selon le rôle
    dashboard_routes = {
        'EMPLOYEE': 'dashboard.employee',
        'MANAGER_DEPT': 'dashboard.manager_dept',
        'MANAGER_MULTI_DEPT': 'dashboard.manager_multi',
        'DIRECTOR_SITE': 'dashboard.director_site',
        'GENERAL_DIRECTOR': 'dashboard.general_director',
        'DPO': 'dashboard.dpo',
        'ADMIN_IT': 'dashboard.admin_it'
    }
    
    route = dashboard_routes.get(role_code)
    
    if route:
        return redirect(url_for(route))
    else:
        flash(f"Dashboard non trouvé pour le rôle : {role_code}", 'error')
        return redirect(url_for('public.index'))


# ===== GESTION DES ERREURS =====

@app.errorhandler(403)
def forbidden(e):
    """Gestion de l'erreur 403 Forbidden"""
    return render_template('errors/403.html'), 403


@app.errorhandler(404)
def not_found(e):
    """Gestion de l'erreur 404 Not Found"""
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def internal_error(e):
    """Gestion de l'erreur 500 Internal Server Error"""
    db.session.rollback()
    return render_template('errors/500.html'), 500


# ===== CONTEXT PROCESSOR (Variables globales dans templates) =====

@app.context_processor
def inject_user():
    """
    Rend l'utilisateur et ses infos disponibles dans tous les templates
    """
    if current_user.is_authenticated:
        highest_role = current_user.get_highest_role()
        return {
            'current_user': current_user,
            'user_role': highest_role.name if highest_role else 'Aucun rôle',
            'user_role_code': highest_role.code if highest_role else None,
            'user_site': current_user.site.name if current_user.site else 'N/A',
            'user_department': current_user.department.name if current_user.department else 'N/A'
        }
    return {}


# ===== LOGGING =====

if not app.debug:
    # Configuration du logging en production
    import logging
    from logging.handlers import RotatingFileHandler
    
    if not os.path.exists('logs'):
        os.mkdir('logs')
    
    file_handler = RotatingFileHandler('logs/voyagesdz.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    
    app.logger.setLevel(logging.INFO)
    app.logger.info('VoyagesDZ startup')


# ===== DÉMARRAGE DE L'APPLICATION =====

if __name__ == '__main__':
    # Mode développement
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )