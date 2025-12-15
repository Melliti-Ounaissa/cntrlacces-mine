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


# routes/payments.py (à modifier)
# ...
# routes/payments.py

# ... (imports)
from models import db, Payment, Booking
from policies.rbac import get_payments_query, can_view_sensitive_payment_data
# ...

@payments_bp.route('/')
@login_required
def list():
    """
    Liste des paiements (avec filtrage RBAC)
    """
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    # 1. Filtrage RBAC
    base_query = Payment.query.order_by(Payment.created_at.desc())
    
    # Appliquer le filtre RBAC pour l'utilisateur courant
    filtered_query_for_stats_and_pagination = get_payments_query(current_user, base_query)
    
    # Vérifier si la requête retourne rien (pas d'accès)
    # Utilisez .limit(1) pour un count rapide ici
    if filtered_query_for_stats_and_pagination.limit(1).count() == 0 and Payment.query.count() > 0:
        flash("Vous n'avez pas accès aux paiements", 'error')
        return redirect(url_for('dashboard_redirect'))
    
    
    # 2. Calcul des Statistiques
    # IMPORTANT : Cloner la requête filtrée pour le calcul des statistiques.
    # Cela garantit que la pagination (étape 3) utilise une requête propre et non exécutée.
    stats_query = filtered_query_for_stats_and_pagination.options(db.Load(Payment)) # Pas strictement nécessaire, mais bonne pratique

    stats = {
        'total': stats_query.count(),
        # Les filtres status doivent être appliqués à la requête filtrée par RBAC
        'pending': stats_query.filter_by(status='PENDING').count(),
        'completed': stats_query.filter_by(status='COMPLETED').count(),
        'failed': stats_query.filter_by(status='FAILED').count(),
        'refunded': stats_query.filter_by(status='REFUNDED').count(),
    }
    
    # 3. Pagination
    # Utilisez la requête filtrée originale (qui n'a été qu'inspectée mais pas complètement exécutée si vous avez cloné)
    # ou une copie (si vous avez utilisé l'astuce du .count() rapide ci-dessus)
    pagination = filtered_query_for_stats_and_pagination.paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('payments/list.html', 
                           pagination=pagination, 
                           payments=pagination.items, # Assurez-vous que vous passez bien les éléments de la page
                           stats=stats) # Assurez-vous de passer les stats


# routes/payments.py (à ajouter/vérifier)

# ... après la route list()...

@payments_bp.route('/<int:payment_id>')
@login_required
def detail(payment_id): # La fonction detail() devrait accepter payment_id
    """Détail d'un paiement"""
    
    payment = Payment.query.get_or_404(payment_id)
    
    # Logique d'accès sensible: Ne pas afficher le détail si l'utilisateur n'a pas la permission
    # On utilise le filtre RBAC en mode "uniquement ce paiement"
    base_query = Payment.query.filter(Payment.id == payment_id)
    filtered_query = get_payments_query(current_user, base_query)
    
    if filtered_query.count() == 0:
        flash("Vous n'avez pas la permission de consulter ce paiement.", 'error')
        abort(403)

    # Assurez-vous que le nom du template est 'payments/detail.html'
    return render_template('payments/detail.html', 
                           payment=payment,
                           # Le filtre est déjà enregistré dans app.py, pas besoin de le passer
                           # mais on peut passer des variables utiles pour le template si besoin
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