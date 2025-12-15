"""
app.py - Configuration Flask CORRIGÉE
"""

from flask import Flask, redirect, url_for, render_template, flash
from flask_login import LoginManager, current_user, login_required
from config import Config
from models import db, User
import logging
import os
from dotenv import load_dotenv

load_dotenv()

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
    return db.session.get(User, int(user_id))


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


# ... après l'enregistrement des Blueprints ...

# ===== FILTRES JINJA2 PERSONNALISÉS =====

def get_status_class(status):
    """Retourne une classe CSS Bootstrap basée sur le statut."""
    if not status:
        return 'secondary'
    status_lower = status.lower()
    
    if status_lower == 'confirmed' or status_lower == 'completed':
        return 'success'
    elif status_lower == 'pending' or status_lower == 'in_progress':
        return 'warning'
    elif status_lower == 'cancelled' or status_lower == 'failed':
        return 'danger'
    else:
        return 'secondary'

# Enregistrer le filtre sous le nom 'lower_status_class' (le nom utilisé dans le template)
# Le dictionnaire 'filters' de jinja_env doit être utilisé
app.jinja_env.filters['lower_status_class'] = get_status_class 
# ... le reste du fichier app.py (gestionnaires d'erreurs, context processors, logging, etc.)

# ===== REDIRECTION AUTOMATIQUE AU BON DASHBOARD (DÉFINITION UNIQUE) =====

# app.py (Ajoutez cette fonction après vos autres routes/blueprints)

@app.route('/dashboard_redirect')
@login_required
def dashboard_redirect():
    """
    Détermine la page de tableau de bord appropriée en fonction du rôle le plus élevé.
    """
    highest_role = current_user.get_highest_role()
    
    if highest_role:
        role_code = highest_role.code
        
        if role_code == "GENERAL_DIRECTOR":
            # Redirection vers le dashboard DG
            return redirect(url_for('dashboard.general_director'))
        elif role_code == "DPO":
            return redirect(url_for('dashboard.dpo'))
        elif role_code == "ADMIN_IT":
            return redirect(url_for('dashboard.admin_it'))
            
        elif role_code == "DIRECTOR_SITE":
            return redirect(url_for('dashboard.site_director'))
            
        elif role_code == "MANAGER_DEPT":
            return redirect(url_for('dashboard.manager'))
            
        elif role_code == "EMPLOYEE":
            return redirect(url_for('dashboard.employee'))
            
    # Si l'utilisateur n'a aucun rôle défini, le renvoyer à l'accueil
    flash("Vous n'avez pas de rôle défini pour accéder au tableau de bord.", 'error')
    return redirect(url_for('public.index'))

# NOTE: Assurez-vous que cette fonction est bien disponible sous le nom 'dashboard_redirect'
# Si vous utilisez un Blueprint pour 'dashboard', vous pouvez la mettre dedans
# avec l'URL '/' et la fonction serait dashboard.dashboard_redirect


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
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )