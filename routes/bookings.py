"""
routes/bookings.py - CRUD Réservations avec RBAC
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_required, current_user
from models import db, Booking, Client, Flight, Hotel, Package
from policies.rbac import (
    get_bookings_query, 
    can_create_booking, 
    can_update_booking, 
    can_delete_booking,
    temporal_access_required
)
from policies.business_rules import BookingRules
from datetime import datetime
import uuid

bookings_bp = Blueprint('bookings', __name__)


@bookings_bp.route('/')
@login_required
@temporal_access_required('bookings')
def list():
    """
    Liste des réservations (avec filtrage RBAC)
    """
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
        'pending': filtered_query.filter_by(status='pending').count(),
        'confirmed': filtered_query.filter_by(status='confirmed').count(),
        'cancelled': filtered_query.filter_by(status='cancelled').count()
    }
    
    return render_template(
        'bookings/list.html',
        bookings=pagination.items,
        pagination=pagination,
        stats=stats,
        can_create=can_create_booking(current_user)
    )


@bookings_bp.route('/<booking_id>')
@login_required
@temporal_access_required('bookings')
def detail(booking_id):
    """
    Détail d'une réservation
    """
    # Récupérer la réservation
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
@temporal_access_required('bookings')
def create():
    """
    Créer une nouvelle réservation
    """
    # Vérifier la permission
    if not can_create_booking(current_user):
        flash("Vous n'avez pas la permission de créer des réservations", 'error')
        return redirect(url_for('bookings.list'))
    
    if request.method == 'POST':
        # Récupérer les données du formulaire
        booking_data = {
            'client_id': request.form.get('client_id'),
            'booking_type': request.form.get('booking_type'),
            'travel_date': request.form.get('travel_date'),
            'return_date': request.form.get('return_date'),
            'number_of_travelers': request.form.get('number_of_travelers', type=int),
            'total_amount_dzd': request.form.get('total_amount_dzd', type=float)
        }
        
        # Valider les règles métier
        is_valid, errors = BookingRules.validate_create(booking_data, current_user)
        
        if not is_valid:
            for error in errors:
                flash(error, 'error')
            return render_template('bookings/create.html', 
                                 clients=Client.query.all())
        
        # Créer la réservation
        booking = Booking(
            id=str(uuid.uuid4()),
            booking_reference=f"BK{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}",
            client_id=booking_data['client_id'],
            booking_type=booking_data['booking_type'],
            booking_date=datetime.now(),
            travel_date=datetime.strptime(booking_data['travel_date'], '%Y-%m-%d').date() if booking_data['travel_date'] else None,
            return_date=datetime.strptime(booking_data['return_date'], '%Y-%m-%d').date() if booking_data.get('return_date') else None,
            number_of_travelers=booking_data['number_of_travelers'],
            total_amount_dzd=booking_data['total_amount_dzd'],
            status='pending',
            created_by_user_id=current_user.id,
            created_at_site_id=current_user.site_id,
            created_by_department_id=current_user.department_id
        )
        
        db.session.add(booking)
        db.session.commit()
        
        flash(f'Réservation {booking.booking_reference} créée avec succès !', 'success')
        return redirect(url_for('bookings.detail', booking_id=booking.id))
    
    # GET : Afficher le formulaire
    clients = Client.query.filter_by(registered_at_site_id=current_user.site_id).all()
    flights = Flight.query.limit(100).all()
    hotels = Hotel.query.limit(100).all()
    packages = Package.query.limit(100).all()
    
    return render_template(
        'bookings/create.html',
        clients=clients,
        flights=flights,
        hotels=hotels,
        packages=packages
    )


@bookings_bp.route('/<booking_id>/update', methods=['GET', 'POST'])
@login_required
@temporal_access_required('bookings')
def update(booking_id):
    """
    Modifier une réservation
    """
    booking = Booking.query.get_or_404(booking_id)
    
    # Vérifier la permission
    can_update, error_msg = can_update_booking(current_user, booking)
    if not can_update:
        flash(error_msg, 'error')
        return redirect(url_for('bookings.detail', booking_id=booking_id))
    
    # Vérifier si modification possible (règles métier)
    can_modify, modify_msg = BookingRules.can_modify(booking)
    if not can_modify:
        flash(modify_msg, 'error')
        return redirect(url_for('bookings.detail', booking_id=booking_id))
    
    if request.method == 'POST':
        # Mettre à jour
        booking.travel_date = datetime.strptime(request.form.get('travel_date'), '%Y-%m-%d').date() if request.form.get('travel_date') else None
        booking.return_date = datetime.strptime(request.form.get('return_date'), '%Y-%m-%d').date() if request.form.get('return_date') else None
        booking.number_of_travelers = request.form.get('number_of_travelers', type=int)
        booking.total_amount_dzd = request.form.get('total_amount_dzd', type=float)
        booking.status = request.form.get('status', 'pending')
        booking.updated_at = datetime.now()
        
        db.session.commit()
        
        flash('Réservation modifiée avec succès !', 'success')
        return redirect(url_for('bookings.detail', booking_id=booking_id))
    
    # GET : Afficher le formulaire
    return render_template('bookings/update.html', booking=booking)


@bookings_bp.route('/<booking_id>/delete', methods=['POST'])
@login_required
@temporal_access_required('bookings')
def delete(booking_id):
    """
    Supprimer (annuler) une réservation
    """
    booking = Booking.query.get_or_404(booking_id)
    
    # Vérifier la permission
    can_delete, error_msg = can_delete_booking(current_user, booking)
    if not can_delete:
        flash(error_msg, 'error')
        return redirect(url_for('bookings.detail', booking_id=booking_id))
    
    # Calculer les frais d'annulation
    cancellation_fee = BookingRules.calculate_cancellation_fee(booking)
    
    # Marquer comme annulée (pas supprimer physiquement)
    booking.status = 'cancelled'
    booking.updated_at = datetime.now()
    
    db.session.commit()
    
    if cancellation_fee > 0:
        flash(f'Réservation annulée. Frais d\'annulation : {cancellation_fee:,.2f} DZD', 'warning')
    else:
        flash('Réservation annulée avec succès', 'success')
    
    return redirect(url_for('bookings.list'))