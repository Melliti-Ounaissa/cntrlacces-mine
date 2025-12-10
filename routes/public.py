"""
routes/public.py - Pages publiques (Home, About, Contact)
"""

from flask import Blueprint, render_template

public_bp = Blueprint('public', __name__)


@public_bp.route('/')
def index():
    """Page d'accueil"""
    return render_template('index.html')


@public_bp.route('/about')
def about():
    """Page À propos"""
    return render_template('about.html')


@public_bp.route('/contact')
def contact():
    """Page Contact"""
    return render_template('contact.html')