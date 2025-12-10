"""
config.py - Configuration de l'application Flask

Gère les configurations pour différents environnements (dev, prod)
"""

import os
from datetime import timedelta


class Config:
    """Configuration de base"""
    
    # ===== CONFIGURATION FLASK =====
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # ===== CONFIGURATION BASE DE DONNÉES =====
    # URL Supabase PostgreSQL
    # Format: postgresql://user:password@host:port/database
    
    # DÉVELOPPEMENT (remplace par ton URL Supabase)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://postgres.xxxxx:password@aws-0-eu-central-1.pooler.supabase.com:6543/postgres'
    
    # Options SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False  # True pour voir les requêtes SQL (debug)
    SQLALCHEMY_POOL_SIZE = 10
    SQLALCHEMY_MAX_OVERFLOW = 20
    SQLALCHEMY_POOL_RECYCLE = 3600
    
    # ===== CONFIGURATION PAGINATION =====
    ITEMS_PER_PAGE = 50  # Nombre d'items par page
    
    # ===== CONFIGURATION FLASK-LOGIN =====
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    SESSION_COOKIE_SECURE = False  # True en production avec HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # ===== CONFIGURATION UPLOAD =====
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx'}
    
    # ===== TIMEZONE =====
    TIMEZONE = 'Africa/Algiers'


class DevelopmentConfig(Config):
    """Configuration pour le développement"""
    DEBUG = True
    TESTING = False
    SQLALCHEMY_ECHO = True  # Afficher les requêtes SQL


class ProductionConfig(Config):
    """Configuration pour la production"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True  # HTTPS uniquement
    
    # Utiliser des variables d'environnement pour les secrets
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY must be set in production")
    
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("DATABASE_URL must be set in production")


class TestingConfig(Config):
    """Configuration pour les tests"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


# Dictionnaire pour sélectionner la config
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


# ===== FONCTION UTILITAIRE =====

def get_config():
    """
    Retourne la configuration selon l'environnement
    
    Usage:
        from config import get_config
        app.config.from_object(get_config())
    """
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])