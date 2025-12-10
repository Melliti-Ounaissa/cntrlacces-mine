"""
routes/payments.py - CRUD Paiements avec RBAC
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from models import db, Payment, Booking
from policies.rbac import get_payments_query, can_view_sensitive_payment_data
from policies.business_rules import PaymentRules
from datetime import datetime
import uuid

payments_bp = Blueprint('payments', __name__)


@payments_bp.route('/')
@login_required
def list():
    """
    Liste des paiements (avec filtrage RBAC)
    
    Note : Seuls Finance, Directeurs, DG, et Admin IT peuvent voir
    """
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    # Filtrage RBAC
    base_query = Payment.query.order_by(Payment.created_at.desc())
    filtered_query = get_payments_query(current_user, base_query)
    
    # Vérifier si la requête retourne rien (pas d'accès)
    if filtered_query.count() == 0 and Payment.query.count() > 0:
        flash("Vous n'avez pas accès aux paiements", 'error')
        return redirect(url_for('dashboard_redirect'))
    
    # Pagination
    pagination = filtered_query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Statistiques
    stats = {
        'total': filtered_query.count(),
        'pending': filtered_query.filter_by(status='pending').count(),
        'completed': filtered_query.filter_by(status='completed').count(),
        'failed': filtered_query.filter_by(status='failed').count(),
        'total_amount': sum([float(p.amount_dzd) for p in filtered_query.all()])
    }
    
    # Vérifier si l'utilisateur peut voir les données sensibles
    can_view_sensitive = can_view_sensitive_payment_data(current_user)
    
    return render_template(
        'payments/list.html',
        payments=pagination.items,
        pagination=pagination,
        stats=stats,
        can_view_sensitive=can_view_sensitive
    )


@payments_bp.route('/<payment_id>')
@login_required
def detail(payment_id):
    """Détail d'un paiement"""
    payment = Payment.query.get_or_404(payment_id)
    
    # Vérifier l'accès RBAC
    base_query = Payment.query.filter_by(id=payment_id)
    filtered_query = get_payments_query(current_user, base_query)
    
    if not filtered_query.first():
        flash("Vous n'avez pas accès à ce paiement", 'error')
        abort(403)
    
    # Vérifier si l'utilisateur peut voir les données sensibles
    can_view_sensitive = can_view_sensitive_payment_data(current_user)
    
    return render_template(
        'payments/detail.html',
        payment=payment,
        can_view_sensitive=can_view_sensitive
    )


@payments_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """
    Créer un nouveau paiement
    
    Seuls Finance, Directeurs, et DG peuvent créer
    """
    highest_role = current_user.get_highest_role()
    allowed_roles = ['MANAGER_DEPT', 'MANAGER_MULTI_DEPT', 'DIRECTOR_SITE', 'GENERAL_DIRECTOR']
    
    if not highest_role or highest_role.code not in allowed_roles:
        flash("Vous n'avez pas la permission de créer des paiements", 'error')
        return redirect(url_for('dashboard_redirect'))
    
    # Si Manager, doit être Finance
    if highest_role.code == 'MANAGER_DEPT':
        if not current_user.department or not current_user.department.code.startswith('FIN'):
            flash("Seul le département Finance peut créer des paiements", 'error')
            return redirect(url_for('dashboard_redirect'))
    
    if request.method == 'POST':
        booking_id = request.form.get('booking_id')
        booking = Booking.query.get(booking_id)
        
        if not booking:
            flash("Réservation introuvable", 'error')
            return render_template('payments/create.html', bookings=Booking.query.limit(100).all())
        
        # Récupérer les données
        payment_data = {
            'amount_dzd': request.form.get('amount_dzd', type=float),
            'payment_method': request.form.get('payment_method'),
            'card_last_four': request.form.get('card_last_four')
        }
        
        # Valider les règles métier
        is_valid, errors = PaymentRules.validate_create(payment_data, booking, current_user)
        
        if not is_valid:
            for error in errors:
                flash(error, 'error')
            return render_template('payments/create.html', bookings=Booking.query.limit(100).all())
        
        # Créer le paiement
        payment = Payment(
            id=str(uuid.uuid4()),
            booking_id=booking.id,
            amount_dzd=payment_data['amount_dzd'],
            payment_method=payment_data['payment_method'],
            payment_date=datetime.now(),
            card_last_four=payment_data.get('card_last_four'),
            transaction_reference=f"TRX{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}",
            status='completed',
            processed_by_user_id=current_user.id,
            processed_at_site_id=current_user.site_id
        )
        
        # Mettre à jour le statut de la réservation
        booking.status = 'confirmed'
        
        db.session.add(payment)
        db.session.commit()
        
        flash(f'Paiement {payment.transaction_reference} créé avec succès !', 'success')
        return redirect(url_for('payments.detail', payment_id=payment.id))
    
    # GET : Afficher le formulaire
    bookings = Booking.query.filter_by(status='pending').limit(100).all()
    return render_template('payments/create.html', bookings=bookings)


@payments_bp.route('/<payment_id>/refund', methods=['POST'])
@login_required
def refund(payment_id):
    """
    Rembourser un paiement
    
    Seuls Directeurs et DG
    """
    payment = Payment.query.get_or_404(payment_id)
    
    highest_role = current_user.get_highest_role()
    allowed_roles = ['DIRECTOR_SITE', 'GENERAL_DIRECTOR', 'ADMIN_IT']
    
    if not highest_role or highest_role.code not in allowed_roles:
        flash("Vous n'avez pas la permission de rembourser", 'error')
        abort(403)
    
    if payment.status != 'completed':
        flash("Seuls les paiements complétés peuvent être remboursés", 'error')
        return redirect(url_for('payments.detail', payment_id=payment_id))
    
    # Rembourser
    payment.status = 'refunded'
    
    # Mettre à jour la réservation
    booking = payment.booking
    if booking:
        booking.status = 'cancelled'
    
    db.session.commit()
    
    flash('Paiement remboursé avec succès', 'success')
    return redirect(url_for('payments.detail', payment_id=payment_id))