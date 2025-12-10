"""
routes/clients.py - CRUD Clients avec RBAC
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from models import db, Client, DataProcessingLog
from policies.rbac import get_clients_query
from policies.business_rules import ClientRules
from datetime import datetime
import uuid

clients_bp = Blueprint('clients', __name__)


@clients_bp.route('/')
@login_required
def list():
    """Liste des clients (avec filtrage RBAC)"""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    # Filtrage RBAC
    base_query = Client.query.order_by(Client.created_at.desc())
    filtered_query = get_clients_query(current_user, base_query)
    
    # Pagination
    pagination = filtered_query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Statistiques
    stats = {
        'total': filtered_query.count(),
        'consented': filtered_query.filter_by(is_personal_data_consented=True).count(),
        'not_consented': filtered_query.filter_by(is_personal_data_consented=False).count()
    }
    
    return render_template(
        'clients/list.html',
        clients=pagination.items,
        pagination=pagination,
        stats=stats
    )


@clients_bp.route('/<client_id>')
@login_required
def detail(client_id):
    """Détail d'un client"""
    client = Client.query.get_or_404(client_id)
    
    # Vérifier l'accès RBAC
    base_query = Client.query.filter_by(id=client_id)
    filtered_query = get_clients_query(current_user, base_query)
    
    if not filtered_query.first():
        flash("Vous n'avez pas accès à ce client", 'error')
        abort(403)
    
    # Logger l'accès aux données personnelles
    log = DataProcessingLog(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        client_id=client.id,
        action='DATA_ACCESSED',
        resource_type='client',
        resource_id=client.id,
        details=f'Consultation du profil client par {current_user.full_name}',
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
    return render_template('clients/detail.html', client=client)


@clients_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Créer un nouveau client"""
    
    if request.method == 'POST':
        # Récupérer les données
        client_data = {
            'first_name': request.form.get('first_name'),
            'last_name': request.form.get('last_name'),
            'email': request.form.get('email'),
            'phone': request.form.get('phone'),
            'passport_number': request.form.get('passport_number'),
            'date_of_birth': request.form.get('date_of_birth'),
            'address': request.form.get('address'),
            'city': request.form.get('city'),
            'country': request.form.get('country', 'Algérie'),
            'is_personal_data_consented': request.form.get('consent_checkbox') == 'on'
        }
        
        # Valider les règles métier
        is_valid, errors = ClientRules.validate_create(client_data)
        
        if not is_valid:
            for error in errors:
                flash(error, 'error')
            return render_template('clients/create.html')
        
        # Créer le client
        client = Client(
            id=str(uuid.uuid4()),
            first_name=client_data['first_name'],
            last_name=client_data['last_name'],
            email=client_data['email'],
            phone=client_data['phone'],
            passport_number=client_data['passport_number'],
            date_of_birth=datetime.strptime(client_data['date_of_birth'], '%Y-%m-%d').date() if client_data['date_of_birth'] else None,
            address=client_data['address'],
            city=client_data['city'],
            country=client_data['country'],
            registered_at_site_id=current_user.site_id,
            is_personal_data_consented=client_data['is_personal_data_consented'],
            consent_date=datetime.now() if client_data['is_personal_data_consented'] else None
        )
        
        db.session.add(client)
        
        # Logger le consentement
        if client.is_personal_data_consented:
            log = DataProcessingLog(
                id=str(uuid.uuid4()),
                user_id=current_user.id,
                client_id=client.id,
                action='CONSENT_GIVEN',
                resource_type='client',
                resource_id=client.id,
                details='Client a donné son consentement lors de l\'inscription',
                ip_address=request.remote_addr
            )
            db.session.add(log)
        
        db.session.commit()
        
        flash(f'Client {client.first_name} {client.last_name} créé avec succès !', 'success')
        return redirect(url_for('clients.detail', client_id=client.id))
    
    return render_template('clients/create.html')


@clients_bp.route('/<client_id>/update', methods=['GET', 'POST'])
@login_required
def update(client_id):
    """Modifier un client"""
    client = Client.query.get_or_404(client_id)
    
    # Vérifier l'accès
    base_query = Client.query.filter_by(id=client_id)
    filtered_query = get_clients_query(current_user, base_query)
    
    if not filtered_query.first():
        flash("Vous n'avez pas accès à ce client", 'error')
        abort(403)
    
    if request.method == 'POST':
        # Mettre à jour
        client.first_name = request.form.get('first_name')
        client.last_name = request.form.get('last_name')
        client.email = request.form.get('email')
        client.phone = request.form.get('phone')
        client.address = request.form.get('address')
        client.city = request.form.get('city')
        client.updated_at = datetime.now()
        
        # Logger la modification
        log = DataProcessingLog(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            client_id=client.id,
            action='DATA_MODIFIED',
            resource_type='client',
            resource_id=client.id,
            details=f'Modification du profil client par {current_user.full_name}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        
        db.session.commit()
        
        flash('Client modifié avec succès !', 'success')
        return redirect(url_for('clients.detail', client_id=client_id))
    
    return render_template('clients/update.html', client=client)


@clients_bp.route('/<client_id>/anonymize', methods=['POST'])
@login_required
def anonymize(client_id):
    """
    Anonymiser un client (Droit à l'oubli - Loi 18-07)
    """
    client = Client.query.get_or_404(client_id)
    
    # Seuls DPO et directeurs peuvent anonymiser
    highest_role = current_user.get_highest_role()
    allowed_roles = ['DPO', 'GENERAL_DIRECTOR', 'DIRECTOR_SITE', 'ADMIN_IT']
    
    if not highest_role or highest_role.code not in allowed_roles:
        flash("Vous n'avez pas la permission d'anonymiser des clients", 'error')
        abort(403)
    
    # Anonymiser
    client.first_name = "ANONYMISÉ"
    client.last_name = "ANONYMISÉ"
    client.email = f"anonymized_{client.id}@deleted.local"
    client.phone = "+213000000000"
    client.passport_number = "DELETED"
    client.address = "ANONYMISÉ"
    client.is_personal_data_consented = False
    client.consent_date = None
    client.is_anonymized = True
    client.anonymized_at = datetime.now()
    client.anonymized_by = current_user.id
    
    # Logger l'anonymisation
    log = DataProcessingLog(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        client_id=client.id,
        action='DATA_ANONYMIZED',
        resource_type='client',
        resource_id=client.id,
        details=f'Client anonymisé par {current_user.full_name} (Loi 18-07)',
        ip_address=request.remote_addr
    )
    db.session.add(log)
    
    db.session.commit()
    
    flash('Client anonymisé conformément à la Loi 18-07', 'success')
    return redirect(url_for('clients.list'))