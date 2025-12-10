"""
routes/api.py - Routes API JSON pour le frontend
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models import Booking, Client, Payment
from policies.rbac import get_bookings_query, get_clients_query, get_payments_query

api_bp = Blueprint('api', __name__)


@api_bp.route('/bookings')
@login_required
def api_bookings():
    """
    API JSON pour récupérer les réservations
    
    Paramètres query :
    - page: Numéro de page (défaut 1)
    - per_page: Items par page (défaut 50)
    - status: Filtrer par statut
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    status_filter = request.args.get('status')
    
    # Filtrage RBAC
    base_query = Booking.query.order_by(Booking.created_at.desc())
    filtered_query = get_bookings_query(current_user, base_query)
    
    # Filtre additionnel par statut
    if status_filter:
        filtered_query = filtered_query.filter_by(status=status_filter)
    
    # Pagination
    pagination = filtered_query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Formater en JSON
    bookings_json = []
    for booking in pagination.items:
        bookings_json.append({
            'id': booking.id,
            'booking_reference': booking.booking_reference,
            'client_name': f"{booking.client.first_name} {booking.client.last_name}" if booking.client else "N/A",
            'booking_type': booking.booking_type,
            'travel_date': booking.travel_date.isoformat() if booking.travel_date else None,
            'total_amount_dzd': float(booking.total_amount_dzd) if booking.total_amount_dzd else 0,
            'status': booking.status,
            'created_at': booking.created_at.isoformat() if booking.created_at else None
        })
    
    return jsonify({
        'bookings': bookings_json,
        'pagination': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages
        }
    })


@api_bp.route('/clients')
@login_required
def api_clients():
    """API JSON pour récupérer les clients"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    # Filtrage RBAC
    base_query = Client.query.order_by(Client.created_at.desc())
    filtered_query = get_clients_query(current_user, base_query)
    
    # Pagination
    pagination = filtered_query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Formater en JSON
    clients_json = []
    for client in pagination.items:
        clients_json.append({
            'id': client.id,
            'first_name': client.first_name,
            'last_name': client.last_name,
            'email': client.email,
            'phone': client.phone,
            'city': client.city,
            'is_consented': client.is_personal_data_consented,
            'created_at': client.created_at.isoformat() if client.created_at else None
        })
    
    return jsonify({
        'clients': clients_json,
        'pagination': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages
        }
    })


@api_bp.route('/payments')
@login_required
def api_payments():
    """API JSON pour récupérer les paiements"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    # Filtrage RBAC
    base_query = Payment.query.order_by(Payment.created_at.desc())
    filtered_query = get_payments_query(current_user, base_query)
    
    # Pagination
    pagination = filtered_query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Formater en JSON
    payments_json = []
    for payment in pagination.items:
        payments_json.append({
            'id': payment.id,
            'booking_reference': payment.booking.booking_reference if payment.booking else "N/A",
            'amount_dzd': float(payment.amount_dzd) if payment.amount_dzd else 0,
            'payment_method': payment.payment_method,
            'status': payment.status,
            'payment_date': payment.payment_date.isoformat() if payment.payment_date else None
        })
    
    return jsonify({
        'payments': payments_json,
        'pagination': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages
        }
    })


@api_bp.route('/stats')
@login_required
def api_stats():
    """
    API JSON pour récupérer des statistiques
    
    Retourne des stats selon le rôle de l'utilisateur
    """
    # Filtrage RBAC
    bookings_query = get_bookings_query(current_user, Booking.query)
    clients_query = get_clients_query(current_user, Client.query)
    payments_query = get_payments_query(current_user, Payment.query)
    
    stats = {
        'bookings': {
            'total': bookings_query.count(),
            'pending': bookings_query.filter_by(status='pending').count(),
            'confirmed': bookings_query.filter_by(status='confirmed').count(),
            'cancelled': bookings_query.filter_by(status='cancelled').count()
        },
        'clients': {
            'total': clients_query.count(),
            'consented': clients_query.filter_by(is_personal_data_consented=True).count()
        },
        'payments': {
            'total': payments_query.count(),
            'completed': payments_query.filter_by(status='completed').count(),
            'pending': payments_query.filter_by(status='pending').count()
        }
    }
    
    return jsonify(stats)


@api_bp.route('/booking/<booking_id>')
@login_required
def api_booking_detail(booking_id):
    """API JSON pour récupérer le détail d'une réservation"""
    booking = Booking.query.get_or_404(booking_id)
    
    # Vérifier l'accès RBAC
    base_query = Booking.query.filter_by(id=booking_id)
    filtered_query = get_bookings_query(current_user, base_query)
    
    if not filtered_query.first():
        return jsonify({'error': 'Accès refusé'}), 403
    
    # Formater en JSON
    booking_json = {
        'id': booking.id,
        'booking_reference': booking.booking_reference,
        'client': {
            'id': booking.client.id,
            'name': f"{booking.client.first_name} {booking.client.last_name}"
        } if booking.client else None,
        'booking_type': booking.booking_type,
        'booking_date': booking.booking_date.isoformat() if booking.booking_date else None,
        'travel_date': booking.travel_date.isoformat() if booking.travel_date else None,
        'return_date': booking.return_date.isoformat() if booking.return_date else None,
        'number_of_travelers': booking.number_of_travelers,
        'total_amount_dzd': float(booking.total_amount_dzd) if booking.total_amount_dzd else 0,
        'status': booking.status,
        'created_by': booking.creator.full_name if booking.creator else "N/A",
        'created_at': booking.created_at.isoformat() if booking.created_at else None
    }
    
    return jsonify(booking_json)