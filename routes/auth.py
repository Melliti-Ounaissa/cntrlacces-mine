"""
routes/auth.py - Authentification (Login, Logout, Register)
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User
from datetime import datetime

auth_bp = Blueprint('auth', __name__)


# routes/auth.py

# ... (les imports)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Page de connexion"""
    
    # Si déjà connecté, rediriger vers le dashboard
    if current_user.is_authenticated:
        return redirect(url_for('dashboard_redirect'))
    
    if request.method == 'POST':
        # FIX: Utiliser .strip() pour enlever les espaces inutiles qui causent des erreurs de hash
        email = request.form.get('email').strip()      # <--- MODIFICATION
        password = request.form.get('password').strip() # <--- MODIFICATION
        remember = request.form.get('remember', False)
        
        # Vérification
        if not email or not password:
            flash('Veuillez remplir tous les champs', 'error')
            return render_template('login.html')
        
        # AJOUT TEMPORAIRE POUR DEBUG
        print(f"DEBUG LOGIN: Email saisi: '{email}', Password saisi (non-hashed): '{password}'") 

        # Chercher l'utilisateur
        user = User.query.filter_by(email=email).first()
        
        if not user or not check_password_hash(user.password_hash, password):
            # Le mot de passe ne correspond pas ou l'utilisateur n'existe pas
            flash('Email ou mot de passe incorrect', 'error')
            return render_template('login.html')
        
        # Si la vérification a réussi, continuez...
        login_user(user, remember=remember)
        flash(f'Connexion réussie ! Bienvenue {user.full_name}.', 'success')
        return redirect(url_for('dashboard_redirect')) # Redirection vers la fonction dans app.py
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Déconnexion"""
    logout_user()
    flash('Vous avez été déconnecté avec succès', 'success')
    return redirect(url_for('public.index'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Page d'inscription
    
    Note : Dans un vrai système, l'inscription devrait être
    restreinte aux admins. Ceci est juste un exemple.
    """
    
    if request.method == 'POST':
        email = request.form.get('email')
        full_name = request.form.get('full_name')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        
        # Validations
        if not all([email, full_name, password, password_confirm]):
            flash('Veuillez remplir tous les champs', 'error')
            return render_template('register.html')
        
        if password != password_confirm:
            flash('Les mots de passe ne correspondent pas', 'error')
            return render_template('register.html')
        
        if len(password) < 8:
            flash('Le mot de passe doit contenir au moins 8 caractères', 'error')
            return render_template('register.html')
        
        # Vérifier si l'email existe déjà
        if User.query.filter_by(email=email).first():
            flash('Cet email est déjà utilisé', 'error')
            return render_template('register.html')
        
        # Créer l'utilisateur
        # Note : Dans un vrai système, il faudrait aussi assigner site_id, department_id, role
        new_user = User(
            email=email,
            full_name=full_name,
            password_hash=generate_password_hash(password), 
            is_active=True
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Compte créé avec succès ! Vous pouvez maintenant vous connecter.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html')


@auth_bp.route('/profile')
@login_required
def profile():
    """Page de profil utilisateur"""
    return render_template('profile.html', user=current_user)