"""
policies/rbac.py - Logique RBAC complète

Filtres RBAC pour contrôler QUI VOIT QUOI
Adapté au schéma réel avec user_roles many-to-many
"""

from datetime import datetime, timedelta
from sqlalchemy import and_, or_
import pytz


# ==================== FILTRES RBAC (READ) ====================

def get_bookings_query(user, base_query):
    """
    Filtre les réservations selon le(s) rôle(s) de l'utilisateur
    
    Args:
        user: L'utilisateur connecté
        base_query: Query SQLAlchemy de base (Booking.query)
    
    Returns:
        Query filtrée selon les permissions RBAC
    """
    from models import Booking
    
    # Récupérer le rôle avec le niveau hiérarchique le plus élevé
    highest_role = user.get_highest_role()
    
    if not highest_role:
        # Pas de rôle = pas d'accès
        return base_query.filter(Booking.id == None)
    
    role_code = highest_role.code
    
    if role_code == "EMPLOYEE":
        # Employé : SEULEMENT ses propres réservations
        return base_query.filter(
            Booking.created_by_user_id == user.id
        )
    
    elif role_code == "MANAGER_DEPT":
        # Manager Département : TOUT son département
        return base_query.filter(
            Booking.created_by_department_id == user.department_id,
            Booking.created_at_site_id == user.site_id
        )
    
    elif role_code == "MANAGER_MULTI_DEPT":
        # Manager Multi-Depts : Tout son site
        return base_query.filter(
            Booking.created_at_site_id == user.site_id
        )
    
    elif role_code == "DIRECTOR_SITE":
        # Directeur Site : Tout son site
        return base_query.filter(
            Booking.created_at_site_id == user.site_id
        )
    
    elif role_code in ["GENERAL_DIRECTOR", "ADMIN_IT", "DPO"]:
        # Accès complet
        return base_query
    
    else:
        # Rôle inconnu = accès restreint par défaut
        return base_query.filter(
            Booking.created_by_user_id == user.id
        )


def get_clients_query(user, base_query):
    """Filtre les clients selon le rôle RBAC"""
    from models import Client
    
    highest_role = user.get_highest_role()
    if not highest_role:
        return base_query.filter(Client.id == None)
    
    role_code = highest_role.code
    
    if role_code == "EMPLOYEE":
        # Employé : Clients de son site uniquement
        return base_query.filter(
            Client.registered_at_site_id == user.site_id
        )
    
    elif role_code in ["MANAGER_DEPT", "MANAGER_MULTI_DEPT", "DIRECTOR_SITE"]:
        # Managers et Directeurs : Clients de leur site
        return base_query.filter(
            Client.registered_at_site_id == user.site_id
        )
    
    elif role_code in ["GENERAL_DIRECTOR", "ADMIN_IT", "DPO"]:
        # Accès complet
        return base_query
    
    else:
        return base_query.filter(
            Client.registered_at_site_id == user.site_id
        )


def get_payments_query(user, base_query):
    """Filtre les paiements selon le rôle RBAC"""
    from models import Payment
    
    highest_role = user.get_highest_role()
    if not highest_role:
        return base_query.filter(Payment.id == None)
    
    role_code = highest_role.code
    
    if role_code == "EMPLOYEE":
        # Employés ne voient PAS les paiements
        return base_query.filter(Payment.id == None)
    
    elif role_code == "MANAGER_DEPT":
        # Manager département Finance peut voir les paiements
        if user.department and user.department.code.startswith("FIN"):
            return base_query.filter(
                Payment.processed_at_site_id == user.site_id
            )
        else:
            # Autres départements : pas d'accès
            return base_query.filter(Payment.id == None)
    
    elif role_code in ["MANAGER_MULTI_DEPT", "DIRECTOR_SITE"]:
        # Managers et Directeurs : paiements de leur site
        return base_query.filter(
            Payment.processed_at_site_id == user.site_id
        )
    
    elif role_code in ["GENERAL_DIRECTOR", "ADMIN_IT"]:
        # Accès complet
        return base_query
    
    elif role_code == "DPO":
        # DPO : Metadata uniquement (pas les montants)
        # À gérer dans la vue
        return base_query
    
    else:
        return base_query.filter(Payment.id == None)


# ==================== PERMISSIONS CRUD ====================

def can_create_booking(user):
    """Vérifie si l'utilisateur peut créer une réservation"""
    # APPROCHE 1 : Permissions (recommandé)
    if user.has_permission('booking.create'):
        return True
    
    # APPROCHE 2 : Rôles (alternatif)
    allowed_roles = [
        "EMPLOYEE",
        "MANAGER_DEPT",
        "MANAGER_MULTI_DEPT",
        "DIRECTOR_SITE",
        "GENERAL_DIRECTOR"
    ]
    return any(user.has_role(code) for code in allowed_roles)


def can_update_booking(user, booking):
    """
    Vérifie si l'utilisateur peut modifier une réservation
    
    Règles :
    - EMPLOYEE : Seulement ses réservations, max 48h après création
    - MANAGER_DEPT : Réservations de son département, max 7 jours
    - DIRECTOR_SITE : Tout son site, max 30 jours
    - GENERAL_DIRECTOR : Tout, max 90 jours
    """
    # Vérifier la permission de base
    if not user.has_permission('booking.update'):
        return False, "Vous n'avez pas la permission de modifier les réservations"
    
    # Récupérer le rôle principal
    highest_role = user.get_highest_role()
    if not highest_role:
        return False, "Aucun rôle assigné"
    
    role_code = highest_role.code
    age = datetime.now() - booking.created_at.replace(tzinfo=None)
    
    if role_code == "EMPLOYEE":
        # EMPLOYEE : Ses réservations uniquement, max 48h
        if booking.created_by_user_id != user.id:
            return False, "Vous ne pouvez modifier que vos propres réservations"
        if age > timedelta(hours=48):
            return False, "Délai de modification dépassé (max 48h)"
        return True, None
    
    elif role_code == "MANAGER_DEPT":
        # MANAGER_DEPT : Son département, max 7 jours
        if booking.created_by_department_id != user.department_id:
            return False, "Vous ne pouvez modifier que les réservations de votre département"
        if booking.created_at_site_id != user.site_id:
            return False, "Réservation d'un autre site"
        if age > timedelta(days=7):
            return False, "Délai de modification dépassé (max 7 jours)"
        return True, None
    
    elif role_code == "MANAGER_MULTI_DEPT":
        # MANAGER_MULTI : Son site, max 7 jours
        if booking.created_at_site_id != user.site_id:
            return False, "Réservation d'un autre site"
        if age > timedelta(days=7):
            return False, "Délai de modification dépassé (max 7 jours)"
        return True, None
    
    elif role_code == "DIRECTOR_SITE":
        # DIRECTOR_SITE : Tout son site, max 30 jours
        if booking.created_at_site_id != user.site_id:
            return False, "Réservation d'un autre site"
        if age > timedelta(days=30):
            return False, "Délai de modification dépassé (max 30 jours)"
        return True, None
    
    elif role_code == "GENERAL_DIRECTOR":
        # GENERAL_DIRECTOR : Tout, max 90 jours
        if age > timedelta(days=90):
            return False, "Délai de modification dépassé (max 90 jours)"
        return True, None
    
    elif role_code == "ADMIN_IT":
        # ADMIN_IT : Urgences uniquement
        return True, None
    
    return False, "Rôle non autorisé à modifier les réservations"


def can_delete_booking(user, booking):
    """
    Vérifie si l'utilisateur peut supprimer une réservation
    
    Règles :
    - Seuls DIRECTOR_SITE et GENERAL_DIRECTOR peuvent supprimer
    """
    # Vérifier la permission
    if not user.has_permission('booking.delete'):
        return False, "Vous n'avez pas la permission de supprimer les réservations"
    
    highest_role = user.get_highest_role()
    if not highest_role:
        return False, "Aucun rôle assigné"
    
    role_code = highest_role.code
    
    allowed_roles = ["DIRECTOR_SITE", "GENERAL_DIRECTOR", "ADMIN_IT"]
    if role_code not in allowed_roles:
        return False, "Seuls les directeurs peuvent supprimer des réservations"
    
    # Vérifier la portée
    if role_code == "DIRECTOR_SITE":
        if booking.created_at_site_id != user.site_id:
            return False, "Vous ne pouvez supprimer que les réservations de votre site"
    
    return True, None


def can_view_sensitive_payment_data(user):
    """
    Vérifie si l'utilisateur peut voir les données sensibles de paiement
    (numéro de carte, etc.)
    """
    highest_role = user.get_highest_role()
    if not highest_role:
        return False
    
    role_code = highest_role.code
    
    if role_code == "MANAGER_DEPT":
        # Seulement si département Finance
        return user.department and user.department.code.startswith("FIN")
    
    allowed_roles = [
        "DIRECTOR_SITE",
        "GENERAL_DIRECTOR",
        "ADMIN_IT"
    ]
    
    return role_code in allowed_roles


# ==================== CONTRAINTES TEMPORELLES ====================

def check_temporal_access(user, resource_type):
    """
    Vérifie si l'utilisateur peut accéder maintenant (jour + heure)
    
    Args:
        user: L'utilisateur
        resource_type: Type de ressource ('bookings', 'payments', etc.)
    
    Returns:
        (bool, str): (Accès autorisé ?, Message d'erreur si refusé)
    """
    from models import TemporalConstraint
    
    # Récupérer les contraintes de l'utilisateur
    constraints = TemporalConstraint.query.filter(
        TemporalConstraint.user_id == user.id,
        TemporalConstraint.resource_type == resource_type,
        TemporalConstraint.is_active == True
    ).all()
    
    # Pas de contraintes = accès autorisé 24/7
    if not constraints:
        return True, None
    
    # Obtenir l'heure actuelle (timezone Algérie)
    tz = pytz.timezone('Africa/Algiers')
    now = datetime.now(tz)
    current_time = now.time()
    current_day = now.weekday()  # 0 = Lundi, 6 = Dimanche
    
    # Vérifier chaque contrainte
    for constraint in constraints:
        # Vérifier le jour
        if current_day not in constraint.days_of_week:
            days_map = {
                0: "Lundi", 1: "Mardi", 2: "Mercredi", 
                3: "Jeudi", 4: "Vendredi", 5: "Samedi", 6: "Dimanche"
            }
            allowed_days_str = ", ".join([days_map[d] for d in constraint.days_of_week])
            return False, f"Accès autorisé uniquement : {allowed_days_str}"
        
        # Vérifier l'heure
        if not (constraint.start_time <= current_time <= constraint.end_time):
            return False, f"Accès autorisé uniquement entre {constraint.start_time.strftime('%H:%M')} et {constraint.end_time.strftime('%H:%M')}"
    
    return True, None


def temporal_access_required(resource_type):
    """
    Décorateur pour vérifier l'accès temporel avant d'exécuter une route
    
    Usage:
        @app.route('/bookings')
        @login_required
        @temporal_access_required('bookings')
        def list_bookings():
            ...
    """
    from functools import wraps
    from flask import abort, flash
    from flask_login import current_user
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Vérifier l'accès temporel
            allowed, error_msg = check_temporal_access(current_user, resource_type)
            
            if not allowed:
                flash(error_msg, 'error')
                abort(403)  # Forbidden
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator