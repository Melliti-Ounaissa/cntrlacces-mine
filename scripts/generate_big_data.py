"""
scripts/generate_big_data.py - Génération de 3M lignes de données

ADAPTÉ AU SCHÉMA RÉEL avec :
- full_name au lieu de first_name + last_name
- user_roles (many-to-many)
- Données 100% algériennes
"""

import os
import sys

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from faker import Faker
from datetime import datetime, timedelta
import random
import uuid
from werkzeug.security import generate_password_hash

# Configuration
# Note : ar_DZ n'existe pas dans Faker, on utilise fr_FR pour les noms algériens
fake = Faker('fr_FR')  # Locale française (noms compatibles Algérie)

# Importer les modèles
from app import app, db
from models import (
    Site, Department, Role, User, UserRole, Client,
    Flight, Hotel, Package, Booking, Payment, Invoice,
    TemporalConstraint
)

# ==================== DONNÉES ALGÉRIENNES ====================

VILLES_ALGERIE = [
    'Alger', 'Oran', 'Constantine', 'Annaba', 'Blida',
    'Sétif', 'Tlemcen', 'Batna', 'Béjaïa', 'Tizi Ouzou'
]

AEROPORTS = {
    'Algérie': ['ALG', 'ORN', 'CZL', 'AAE'],  # Alger, Oran, Constantine, Annaba
    'International': ['CDG', 'ORY', 'LHR', 'IST', 'DXB', 'JED', 'CAI', 'TUN']
}

COMPAGNIES = ['Air Algérie', 'Tassili Airlines', 'Air France', 'Turkish Airlines', 'Emirates']

DEPARTEMENTS_INFO = [
    {'name': 'Réservations', 'code': 'RES'},
    {'name': 'Finance', 'code': 'FIN'},
    {'name': 'Service Client', 'code': 'SUP'},
    {'name': 'Marketing', 'code': 'MKT'},
    {'name': 'IT', 'code': 'IT'}
]

ROLES_INFO = [
    {'name': 'Employé', 'code': 'EMPLOYEE', 'level': 3},
    {'name': 'Manager Département', 'code': 'MANAGER_DEPT', 'level': 4},
    {'name': 'Manager Multi-Depts', 'code': 'MANAGER_MULTI_DEPT', 'level': 5},
    {'name': 'Directeur Site', 'code': 'DIRECTOR_SITE', 'level': 6},
    {'name': 'Directeur Général', 'code': 'GENERAL_DIRECTOR', 'level': 7},
    {'name': 'DPO', 'code': 'DPO', 'level': 2},
    {'name': 'Admin IT', 'code': 'ADMIN_IT', 'level': 1}
]


def create_base_data():
    """Créer les données de base (sites, départements, rôles)"""
    print("🏗️  Création des données de base...")
    
    # 1. SITES
    sites_data = [
        {'name': 'VoyagesDZ Alger', 'code': 'ALG', 'city': 'Alger'},
        {'name': 'VoyagesDZ Oran', 'code': 'ORN', 'city': 'Oran'}
    ]
    
    sites = []
    for s in sites_data:
        site = Site(
            id=str(uuid.uuid4()),
            name=s['name'],
            code=s['code'],
            city=s['city'],
            address=fake.address()
        )
        db.session.add(site)
        sites.append(site)
    
    db.session.commit()
    print(f"✅ {len(sites)} sites créés")
    
    # 2. DÉPARTEMENTS (5 par site = 10 total)
    departments = []
    for site in sites:
        for dept_info in DEPARTEMENTS_INFO:
            dept = Department(
                id=str(uuid.uuid4()),
                name=dept_info['name'],
                code=f"{dept_info['code']}_{site.code}",
                site_id=site.id,
                description=f"Département {dept_info['name']} - {site.name}"
            )
            db.session.add(dept)
            departments.append(dept)
    
    db.session.commit()
    print(f"✅ {len(departments)} départements créés")
    
    # 3. RÔLES
    roles = []
    for role_info in ROLES_INFO:
        role = Role(
            id=str(uuid.uuid4()),
            name=role_info['name'],
            code=role_info['code'],
            hierarchy_level=role_info['level'],
            is_multi_site=(role_info['code'] in ['GENERAL_DIRECTOR', 'ADMIN_IT', 'DPO'])
        )
        db.session.add(role)
        roles.append(role)
    
    db.session.commit()
    print(f"✅ {len(roles)} rôles créés")
    
    return sites, departments, roles


def create_users(sites, departments, roles, count=200):
    """Créer les utilisateurs avec user_roles"""
    print(f"\n👥 Création de {count} utilisateurs...")
    
    users = []
    
    # Répartition des rôles
    role_distribution = {
        'EMPLOYEE': int(count * 0.85),  # 85% employés
        'MANAGER_DEPT': 10,
        'MANAGER_MULTI_DEPT': 4,
        'DIRECTOR_SITE': 2,
        'GENERAL_DIRECTOR': 1,
        'DPO': 2,
        'ADMIN_IT': 3
    }
    
    user_list = []
    
    for role_code, role_count in role_distribution.items():
        role = next(r for r in roles if r.code == role_code)
        
        for _ in range(role_count):
            # Choisir un site aléatoire (sauf pour DG, Admin IT, DPO qui sont multi-sites)
            if role.is_multi_site:
                site = random.choice(sites)
            else:
                site = random.choice(sites)
            
            # Choisir un département du site
            site_departments = [d for d in departments if d.site_id == site.id]
            department = random.choice(site_departments) if site_departments else None
            
            # Créer l'utilisateur
            user = User(
                id=str(uuid.uuid4()),
                email=fake.email(),
                full_name=fake.name(),  # ← ADAPTÉ : full_name au lieu de first_name + last_name
                password_hash=generate_password_hash('password123'),
                site_id=site.id,
                department_id=department.id if department else None,
                is_active=True
            )
            
            db.session.add(user)
            user_list.append((user, role))
    
    db.session.commit()
    
    # Créer les user_roles
    print("🔗 Création des user_roles...")
    for user, role in user_list:
        user_role = UserRole(
            id=str(uuid.uuid4()),
            user_id=user.id,
            role_id=role.id,
            assigned_at=datetime.now()
        )
        db.session.add(user_role)
        users.append(user)
    
    db.session.commit()
    print(f"✅ {len(users)} utilisateurs créés")
    
    return users


def create_temporal_constraints(users, roles):
    """Créer des contraintes temporelles pour les employés"""
    print("\n⏰ Création des contraintes temporelles...")
    
    constraints = []
    
    # Contraintes pour les employés : Lun-Ven 9h-17h
    employee_role = next(r for r in roles if r.code == 'EMPLOYEE')
    
    for user in users[:50]:  # Appliquer à 50 employés
        constraint = TemporalConstraint(
            id=str(uuid.uuid4()),
            name=f"Horaires de travail - {user.full_name}",
            user_id=user.id,
            constraint_type='allowed',
            days_of_week=[0, 1, 2, 3, 4],  # Lun-Ven
            start_time=datetime.strptime('09:00', '%H:%M').time(),
            end_time=datetime.strptime('17:00', '%H:%M').time(),
            resource_type='bookings',
            is_active=True
        )
        db.session.add(constraint)
        constraints.append(constraint)
    
    db.session.commit()
    print(f"✅ {len(constraints)} contraintes créées")
    
    return constraints


def create_clients(sites, count=100000):
    """Créer 100K clients"""
    print(f"\n👤 Création de {count} clients...")
    
    clients = []
    batch_size = 1000
    
    for i in range(0, count, batch_size):
        batch = []
        for _ in range(min(batch_size, count - i)):
            client = Client(
                id=str(uuid.uuid4()),
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                email=fake.email(),
                phone=f"+213{random.randint(500000000, 799999999)}",
                passport_number=f"DZ{random.randint(100000000, 999999999)}",
                date_of_birth=fake.date_of_birth(minimum_age=18, maximum_age=80),
                address=fake.address(),
                city=random.choice(VILLES_ALGERIE),
                country='Algérie',
                registered_at_site_id=random.choice(sites).id,
                is_personal_data_consented=random.random() < 0.75,  # 75% ont consenti
                consent_date=datetime.now() if random.random() < 0.75 else None
            )
            batch.append(client)
            clients.append(client)
        
        db.session.bulk_save_objects(batch)
        db.session.commit()
        
        if (i + batch_size) % 10000 == 0:
            print(f"  ➤ {i + batch_size}/{count} clients créés...")
    
    print(f"✅ {len(clients)} clients créés")
    return clients


def create_flights(count=10000):
    """Créer 10K vols"""
    print(f"\n✈️  Création de {count} vols...")
    
    flights = []
    for _ in range(count):
        departure = random.choice(AEROPORTS['Algérie'])
        arrival = random.choice(AEROPORTS['International'])
        
        departure_time = datetime.now() + timedelta(days=random.randint(1, 365))
        arrival_time = departure_time + timedelta(hours=random.randint(2, 12))
        
        flight = Flight(
            id=str(uuid.uuid4()),
            flight_number=f"{random.choice(['AH', 'DT', 'AF', 'TK'])}{random.randint(1000, 9999)}",
            airline=random.choice(COMPAGNIES),
            departure_airport=departure,
            arrival_airport=arrival,
            departure_time=departure_time,
            arrival_time=arrival_time,
            price_dzd=random.uniform(15000, 150000),
            available_seats=random.randint(50, 300)
        )
        db.session.add(flight)
        flights.append(flight)
    
    db.session.commit()
    print(f"✅ {len(flights)} vols créés")
    return flights


def create_bookings(clients, users, sites, departments, flights, count=1000000):
    """Créer 1M réservations"""
    print(f"\n📋 Création de {count} réservations...")
    
    bookings = []
    batch_size = 1000
    
    for i in range(0, count, batch_size):
        batch = []
        for _ in range(min(batch_size, count - i)):
            user = random.choice(users)
            
            booking = Booking(
                id=str(uuid.uuid4()),
                booking_reference=f"BK{datetime.now().strftime('%Y%m%d')}{random.randint(10000, 99999)}",
                client_id=random.choice(clients).id,
                booking_type=random.choice(['flight', 'hotel', 'package', 'custom']),
                flight_id=random.choice(flights).id if random.random() < 0.7 else None,
                booking_date=datetime.now() - timedelta(days=random.randint(0, 365)),
                travel_date=(datetime.now() + timedelta(days=random.randint(1, 180))).date(),
                return_date=(datetime.now() + timedelta(days=random.randint(5, 190))).date(),
                number_of_travelers=random.randint(1, 6),
                total_amount_dzd=random.uniform(10000, 500000),
                status=random.choice(['pending', 'confirmed', 'cancelled', 'completed']),
                created_by_user_id=user.id,
                created_at_site_id=user.site_id,
                created_by_department_id=user.department_id
            )
            batch.append(booking)
            bookings.append(booking)
        
        db.session.bulk_save_objects(batch)
        db.session.commit()
        
        if (i + batch_size) % 50000 == 0:
            print(f"  ➤ {i + batch_size}/{count} réservations créées...")
    
    print(f"✅ {len(bookings)} réservations créées")
    return bookings


def create_payments(bookings, users, count=500000):
    """Créer 500K paiements"""
    print(f"\n💰 Création de {count} paiements...")
    
    # Sélectionner des réservations confirmées
    confirmed_bookings = random.sample(bookings, min(count, len(bookings)))
    
    payments = []
    batch_size = 1000
    
    for i in range(0, len(confirmed_bookings), batch_size):
        batch = []
        for booking in confirmed_bookings[i:i+batch_size]:
            user = random.choice(users)
            
            payment = Payment(
                id=str(uuid.uuid4()),
                booking_id=booking.id,
                amount_dzd=booking.total_amount_dzd,
                payment_method=random.choice(['cash', 'card', 'transfer', 'check']),
                payment_date=datetime.now() - timedelta(days=random.randint(0, 365)),
                card_last_four=f"{random.randint(1000, 9999)}" if random.random() < 0.5 else None,
                transaction_reference=f"TRX{random.randint(100000000, 999999999)}",
                status=random.choice(['pending', 'completed', 'failed']),
                processed_by_user_id=user.id,
                processed_at_site_id=user.site_id
            )
            batch.append(payment)
            payments.append(payment)
        
        db.session.bulk_save_objects(batch)
        db.session.commit()
        
        if (i + batch_size) % 50000 == 0:
            print(f"  ➤ {i + batch_size}/{len(confirmed_bookings)} paiements créés...")
    
    print(f"✅ {len(payments)} paiements créés")
    return payments


def main():
    """Script principal"""
    print("=" * 60)
    print("🚀 GÉNÉRATION DE DONNÉES - VOYAGESDZ BIG DATA")
    print("=" * 60)
    
    with app.app_context():
        # Étape 1 : Données de base
        sites, departments, roles = create_base_data()
        
        # Étape 2 : Utilisateurs
        users = create_users(sites, departments, roles, count=200)
        
        # Étape 3 : Contraintes temporelles
        create_temporal_constraints(users, roles)
        
        # Étape 4 : Clients (100K)
        clients = create_clients(sites, count=100000)
        
        # Étape 5 : Vols (10K)
        flights = create_flights(count=10000)
        
        # Étape 6 : Réservations (1M)
        bookings = create_bookings(clients, users, sites, departments, flights, count=1000000)
        
        # Étape 7 : Paiements (500K)
        create_payments(bookings, users, count=500000)
        
        print("\n" + "=" * 60)
        print("✅ GÉNÉRATION TERMINÉE AVEC SUCCÈS !")
        print("=" * 60)
        print(f"📊 Total généré:")
        print(f"   - Sites: {len(sites)}")
        print(f"   - Départements: {len(departments)}")
        print(f"   - Rôles: {len(roles)}")
        print(f"   - Utilisateurs: {len(users)}")
        print(f"   - Clients: 100,000")
        print(f"   - Vols: 10,000")
        print(f"   - Réservations: 1,000,000")
        print(f"   - Paiements: 500,000")


if __name__ == '__main__':
    main()