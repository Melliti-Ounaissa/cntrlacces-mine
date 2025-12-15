"""
routes/bookings.py - CRUD Réservations avec RBAC
VERSION CORRIGÉE - Compatible avec le schéma SQL
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from models import db, Booking, Client, Flight
from policies.rbac import get_bookings_query, can_create_booking, can_update_booking, can_delete_booking
from policies.business_rules import BookingRules
from datetime import datetime

bookings_bp = Blueprint('bookings', __name__)


@bookings_bp.route('/')
@login_required
def list():
    """Liste des réservations (avec filtrage RBAC)"""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    # Filtrage RBAC
    base_query = Booking.query.order_by(Booking.created_at.desc())
    filtered_query = get_bookings_query(current_user, base_query)
    
    # Pagination
    pagination = filtered_query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Statistiques
    stats = {
        'total': filtered_query.count(),
        'pending': filtered_query.filter_by(status='PENDING').count(),
        'confirmed': filtered_query.filter_by(status='CONFIRMED').count(),
        'cancelled': filtered_query.filter_by(status='CANCELLED').count()
    }
    
    return render_template(
        'bookings/list.html',
        bookings=pagination.items,
        pagination=pagination,
        stats=stats,
        can_create=can_create_booking(current_user)
    )


@bookings_bp.route('/<int:booking_id>')
@login_required
def detail(booking_id):
    """Détail d'une réservation"""
    booking = Booking.query.get_or_404(booking_id)
    
    # Vérifier l'accès RBAC
    base_query = Booking.query.filter_by(id=booking_id)
    filtered_query = get_bookings_query(current_user, base_query)
    
    if not filtered_query.first():
        flash("Vous n'avez pas accès à cette réservation", 'error')
        abort(403)
    
    # Vérifier les permissions
    can_update, update_msg = can_update_booking(current_user, booking)
    can_delete, delete_msg = can_delete_booking(current_user, booking)
    
    return render_template(
        'bookings/detail.html',
        booking=booking,
        can_update=can_update,
        can_delete=can_delete,
        update_msg=update_msg,
        delete_msg=delete_msg
    )


@bookings_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Créer une nouvelle réservation"""
    if not can_create_booking(current_user):
        flash("Vous n'avez pas la permission de créer des réservations", 'error')
        return redirect(url_for('bookings.list'))
    
    if request.method == 'POST':
        # Récupérer les données du formulaire
        booking_data = {
            'client_id': request.form.get('client_id'),
            'flight_id': request.form.get('flight_id'),
            'total_price': request.form.get('total_price', type=int),
            'travel_date': request.form.get('travel_date')
        }
        
        # Vérifier que les IDs sont valides
        if not booking_data['client_id'] or not booking_data['flight_id']:
            flash("Client et vol sont requis", 'error')
            clients = Client.query.all()
            flights = Flight.query.limit(100).all()
            return render_template('bookings/create.html', clients=clients, flights=flights)
        
        # Valider les règles métier
        is_valid, errors = BookingRules.validate_create(booking_data, current_user)
        
        if not is_valid:
            for error in errors:
                flash(error, 'error')
            clients = Client.query.all()
            flights = Flight.query.limit(100).all()
            return render_template('bookings/create.html', clients=clients, flights=flights)
        
        # Créer la réservation
        booking = Booking(
            client_id=int(booking_data['client_id']),
            flight_id=int(booking_data['flight_id']),
            total_price=booking_data['total_price'],
            status='PENDING',
            created_by_user_id=current_user.id,
            created_by_department_id=current_user.department_id,
            created_at_site_id=current_user.site_id
        )
        
        try:
            db.session.add(booking)
            db.session.commit()
            
            flash(f'Réservation {booking.booking_reference} créée avec succès !', 'success')
            return redirect(url_for('bookings.detail', booking_id=booking.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la création : {str(e)}', 'error')
    
    # GET : Afficher le formulaire
    clients = Client.query.all()
    flights = Flight.query.limit(100).all()
    
    return render_template(
        'bookings/create.html',
        clients=clients,
        flights=flights
    )


@bookings_bp.route('/<int:booking_id>/update', methods=['GET', 'POST'])
@login_required
def update(booking_id):
    """Modifier une réservation"""
    booking = Booking.query.get_or_404(booking_id)
    
    # Vérifier la permission
    can_update_perm, error_msg = can_update_booking(current_user, booking)
    if not can_update_perm:
        flash(error_msg, 'error')
        return redirect(url_for('bookings.detail', booking_id=booking_id))
    
    # Vérifier si modification possible
    can_modify, modify_msg = BookingRules.can_modify(booking)
    if not can_modify:
        flash(modify_msg, 'error')
        return redirect(url_for('bookings.detail', booking_id=booking_id))
    
    if request.method == 'POST':
        # Mettre à jour
        new_price = request.form.get('total_price', type=int)
        new_status = request.form.get('status', 'PENDING')
        
        if new_price:
            booking.total_price = new_price
        
        booking.status = new_status
        
        try:
            db.session.commit()
            flash('Réservation modifiée avec succès !', 'success')
            return redirect(url_for('bookings.detail', booking_id=booking_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la modification : {str(e)}', 'error')
    
    # GET : Afficher le formulaire
    return render_template('bookings/update.html', booking=booking)


@bookings_bp.route('/<int:booking_id>/delete', methods=['POST'])
@login_required
def delete(booking_id):
    """Supprimer (annuler) une réservation"""
    booking = Booking.query.get_or_404(booking_id)
    
    # Vérifier la permission
    can_delete_perm, error_msg = can_delete_booking(current_user, booking)
    if not can_delete_perm:
        flash(error_msg, 'error')
        return redirect(url_for('bookings.detail', booking_id=booking_id))
    
    # Calculer les frais d'annulation
    cancellation_fee = BookingRules.calculate_cancellation_fee(booking)
    
    # Marquer comme annulée
    booking.status = 'CANCELLED'
    
    try:
        db.session.commit()
        
        if cancellation_fee > 0:
            flash(f'Réservation annulée. Frais d\'annulation : {cancellation_fee:,.2f} DZD', 'warning')
        else:
            flash('Réservation annulée avec succès', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de l\'annulation : {str(e)}', 'error')
    
    return redirect(url_for('bookings.list'))