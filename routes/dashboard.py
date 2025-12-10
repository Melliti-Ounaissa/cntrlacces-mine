"""
routes/dashboard.py - 7 Dashboards selon les rôles
"""

from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
from models import Booking, Client, Payment, User, DataProcessingLog, TemporalConstraint
from policies.rbac import get_bookings_query, get_clients_query, get_payments_query
from sqlalchemy import func
from datetime import datetime, timedelta

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/employee')
@login_required
def employee():
    """
    Dashboard EMPLOYÉ
    
    Voit : Ses statistiques personnelles uniquement
    """
    if not current_user.has_role('EMPLOYEE'):
        abort(403)
    
    # Statistiques personnelles
    my_bookings = Booking.query.filter_by(created_by_user_id=current_user.id)
    
    stats = {
        'total_bookings': my_bookings.count(),
        'this_month': my_bookings.filter(
            Booking.created_at >= datetime.now().replace(day=1)
        ).count(),
        'pending': my_bookings.filter_by(status='pending').count(),
        'confirmed': my_bookings.filter_by(status='confirmed').count()
    }
    
    # Dernières réservations
    recent_bookings = my_bookings.order_by(Booking.created_at.desc()).limit(10).all()
    
    return render_template(
        'dashboards/employee.html',
        stats=stats,
        recent_bookings=recent_bookings
    )


@dashboard_bp.route('/manager-dept')
@login_required
def manager_dept():
    """
    Dashboard MANAGER DÉPARTEMENT
    
    Voit : Tout son département
    """
    if not current_user.has_role('MANAGER_DEPT'):
        abort(403)
    
    # Statistiques du département
    dept_bookings = Booking.query.filter_by(
        created_by_department_id=current_user.department_id,
        created_at_site_id=current_user.site_id
    )
    
    stats = {
        'total_bookings': dept_bookings.count(),
        'this_month': dept_bookings.filter(
            Booking.created_at >= datetime.now().replace(day=1)
        ).count(),
        'total_amount': sum([float(b.total_amount_dzd) for b in dept_bookings.all()]),
        'pending': dept_bookings.filter_by(status='pending').count(),
        'confirmed': dept_bookings.filter_by(status='confirmed').count()
    }
    
    # Employés du département
    employees = User.query.filter_by(department_id=current_user.department_id).all()
    
    # Dernières réservations
    recent_bookings = dept_bookings.order_by(Booking.created_at.desc()).limit(20).all()
    
    # Si Finance : Stats paiements
    payment_stats = None
    if current_user.department.code.startswith('FIN'):
        dept_payments = Payment.query.filter_by(processed_at_site_id=current_user.site_id)
        payment_stats = {
            'total_payments': dept_payments.count(),
            'completed': dept_payments.filter_by(status='completed').count(),
            'pending': dept_payments.filter_by(status='pending').count(),
            'total_amount': sum([float(p.amount_dzd) for p in dept_payments.all()])
        }
    
    return render_template(
        'dashboards/manager_dept.html',
        stats=stats,
        employees=employees,
        recent_bookings=recent_bookings,
        payment_stats=payment_stats
    )


@dashboard_bp.route('/manager-multi')
@login_required
def manager_multi():
    """
    Dashboard MANAGER MULTI-DÉPARTEMENTS
    
    Voit : 2-3 départements sur son site
    """
    if not current_user.has_role('MANAGER_MULTI_DEPT'):
        abort(403)
    
    # Stats du site
    site_bookings = Booking.query.filter_by(created_at_site_id=current_user.site_id)
    
    stats = {
        'total_bookings': site_bookings.count(),
        'this_month': site_bookings.filter(
            Booking.created_at >= datetime.now().replace(day=1)
        ).count(),
        'total_amount': sum([float(b.total_amount_dzd) for b in site_bookings.all()])
    }
    
    # Stats par département
    from models import Department
    departments = Department.query.filter_by(site_id=current_user.site_id).all()
    dept_stats = []
    
    for dept in departments:
        dept_bookings = site_bookings.filter_by(created_by_department_id=dept.id)
        dept_stats.append({
            'name': dept.name,
            'bookings': dept_bookings.count(),
            'amount': sum([float(b.total_amount_dzd) for b in dept_bookings.all()])
        })
    
    return render_template(
        'dashboards/manager_multi.html',
        stats=stats,
        dept_stats=dept_stats
    )


@dashboard_bp.route('/director-site')
@login_required
def director_site():
    """
    Dashboard DIRECTEUR SITE
    
    Voit : Vue complète de son site
    """
    if not current_user.has_role('DIRECTOR_SITE'):
        abort(403)
    
    # Stats du site
    site_bookings = Booking.query.filter_by(created_at_site_id=current_user.site_id)
    site_clients = Client.query.filter_by(registered_at_site_id=current_user.site_id)
    site_payments = Payment.query.filter_by(processed_at_site_id=current_user.site_id)
    
    stats = {
        'total_bookings': site_bookings.count(),
        'total_clients': site_clients.count(),
        'total_payments': site_payments.count(),
        'ca_total': sum([float(b.total_amount_dzd) for b in site_bookings.all()]),
        'ca_this_month': sum([
            float(b.total_amount_dzd) for b in site_bookings.filter(
                Booking.created_at >= datetime.now().replace(day=1)
            ).all()
        ])
    }
    
    # Stats par département
    from models import Department
    departments = Department.query.filter_by(site_id=current_user.site_id).all()
    dept_stats = []
    
    for dept in departments:
        dept_bookings = site_bookings.filter_by(created_by_department_id=dept.id)
        dept_stats.append({
            'name': dept.name,
            'bookings': dept_bookings.count(),
            'amount': sum([float(b.total_amount_dzd) for b in dept_bookings.all()])
        })
    
    return render_template(
        'dashboards/director_site.html',
        stats=stats,
        dept_stats=dept_stats
    )


@dashboard_bp.route('/general-director')
@login_required
def general_director():
    """
    Dashboard DIRECTEUR GÉNÉRAL
    
    Voit : Vue consolidée de TOUTE l'entreprise
    """
    if not current_user.has_role('GENERAL_DIRECTOR'):
        abort(403)
    
    # Stats globales
    all_bookings = Booking.query
    all_clients = Client.query
    all_payments = Payment.query
    
    stats = {
        'total_bookings': all_bookings.count(),
        'total_clients': all_clients.count(),
        'total_payments': all_payments.count(),
        'ca_total': sum([float(b.total_amount_dzd) for b in all_bookings.all()]),
        'ca_this_month': sum([
            float(b.total_amount_dzd) for b in all_bookings.filter(
                Booking.created_at >= datetime.now().replace(day=1)
            ).all()
        ])
    }
    
    # Comparaison Alger vs Oran
    from models import Site
    sites = Site.query.all()
    site_comparison = []
    
    for site in sites:
        site_bookings = all_bookings.filter_by(created_at_site_id=site.id)
        site_comparison.append({
            'name': site.name,
            'code': site.code,
            'bookings': site_bookings.count(),
            'amount': sum([float(b.total_amount_dzd) for b in site_bookings.all()])
        })
    
    return render_template(
        'dashboards/general_director.html',
        stats=stats,
        site_comparison=site_comparison
    )


@dashboard_bp.route('/dpo')
@login_required
def dpo():
    """
    Dashboard DPO (Data Protection Officer)
    
    Voit : Conformité Loi 18-07
    """
    if not current_user.has_role('DPO'):
        abort(403)
    
    # Stats conformité
    total_clients = Client.query.count()
    consented_clients = Client.query.filter_by(is_personal_data_consented=True).count()
    anonymized_clients = Client.query.filter_by(is_anonymized=True).count()
    
    consent_rate = (consented_clients / total_clients * 100) if total_clients > 0 else 0
    
    stats = {
        'total_clients': total_clients,
        'consented_clients': consented_clients,
        'consent_rate': consent_rate,
        'no_consent': total_clients - consented_clients,
        'anonymized': anonymized_clients
    }
    
    # Clients sans consentement (PROBLÈME)
    no_consent_clients = Client.query.filter_by(
        is_personal_data_consented=False,
        is_anonymized=False
    ).limit(50).all()
    
    # Logs récents d'accès aux données sensibles
    recent_logs = DataProcessingLog.query.order_by(
        DataProcessingLog.created_at.desc()
    ).limit(50).all()
    
    # Contraintes temporelles actives
    active_constraints = TemporalConstraint.query.filter_by(is_active=True).all()
    
    return render_template(
        'dashboards/dpo.html',
        stats=stats,
        no_consent_clients=no_consent_clients,
        recent_logs=recent_logs,
        active_constraints=active_constraints
    )


@dashboard_bp.route('/admin-it')
@login_required
def admin_it():
    """
    Dashboard ADMIN IT
    
    Voit : Performance système, gestion utilisateurs
    """
    if not current_user.has_role('ADMIN_IT'):
        abort(403)
    
    # Stats système
    stats = {
        'total_users': User.query.count(),
        'active_users': User.query.filter_by(is_active=True).count(),
        'total_bookings': Booking.query.count(),
        'total_clients': Client.query.count(),
        'total_payments': Payment.query.count(),
        'db_size_mb': 'N/A'  # Nécessite une requête SQL spécifique
    }
    
    # Utilisateurs récents
    recent_users = User.query.order_by(User.created_at.desc()).limit(20).all()
    
    # Logs système
    recent_logs = DataProcessingLog.query.order_by(
        DataProcessingLog.created_at.desc()
    ).limit(50).all()
    
    return render_template(
        'dashboards/admin_it.html',
        stats=stats,
        recent_users=recent_users,
        recent_logs=recent_logs
    )