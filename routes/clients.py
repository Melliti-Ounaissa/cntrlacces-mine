"""
routes/clients.py - CRUD Clients avec RBAC
VERSION CORRIGÉE - Compatible avec le schéma SQL
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from models import db, Client
from policies.rbac import get_clients_query
from policies.business_rules import ClientRules
from datetime import datetime

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
        'consented': filtered_query.filter_by(rgpd_consent=True).count(),
        'not_consented': filtered_query.filter_by(rgpd_consent=False).count()
    }
    
    return render_template(
        'clients/list.html',
        clients=pagination.items,
        pagination=pagination,
        stats=stats
    )


@clients_bp.route('/<int:client_id>')
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
    
    return render_template('clients/detail.html', client=client)


@clients_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Créer un nouveau client"""
    
    if request.method == 'POST':
        # Récupérer les données
        client_data = {
            'full_name': request.form.get('full_name', '').strip(),
            'email': request.form.get('email', '').strip(),
            'phone': request.form.get('phone', '').strip(),
            'city': request.form.get('city', '').strip(),
            'rgpd_consent': request.form.get('consent_checkbox') == 'on'
        }
        
        # Valider les règles métier
        is_valid, errors = ClientRules.validate_create(client_data)
        
        if not is_valid:
            for error in errors:
                flash(error, 'error')
            return render_template('clients/create.html')
        
        # Vérifier si l'email existe déjà
        existing = Client.query.filter_by(email=client_data['email']).first()
        if existing:
            flash("Un client avec cet email existe déjà", 'error')
            return render_template('clients/create.html')
        
        # Créer le client
        client = Client(
            full_name=client_data['full_name'],
            email=client_data['email'],
            phone=client_data['phone'] if client_data['phone'] else None,
            city=client_data['city'] if client_data['city'] else None,
            rgpd_consent=client_data['rgpd_consent'],
            consent_date=datetime.now() if client_data['rgpd_consent'] else None
        )
        
        try:
            db.session.add(client)
            db.session.commit()
            
            flash(f'Client {client.full_name} créé avec succès !', 'success')
            return redirect(url_for('clients.detail', client_id=client.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la création : {str(e)}', 'error')
            return render_template('clients/create.html')
    
    return render_template('clients/create.html')


@clients_bp.route('/<int:client_id>/update', methods=['GET', 'POST'])
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
        client.full_name = request.form.get('full_name', '').strip()
        client.email = request.form.get('email', '').strip()
        client.phone = request.form.get('phone', '').strip()
        client.city = request.form.get('city', '').strip()
        
        try:
            db.session.commit()
            flash('Client modifié avec succès !', 'success')
            return redirect(url_for('clients.detail', client_id=client_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la modification : {str(e)}', 'error')
    
    return render_template('clients/update.html', client=client)


@clients_bp.route('/<int:client_id>/anonymize', methods=['POST'])
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
    client.full_name = "ANONYMISÉ"
    client.email = f"anonymized_{client.id}@deleted.local"
    client.phone = "+213000000000"
    client.city = "ANONYMISÉ"
    client.rgpd_consent = False
    client.consent_date = None
    
    try:
        db.session.commit()
        flash('Client anonymisé conformément à la Loi 18-07', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de l\'anonymisation : {str(e)}', 'error')
    
    return redirect(url_for('clients.list'))