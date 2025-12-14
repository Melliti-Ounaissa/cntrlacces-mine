
"""
scripts/generate_data_standalone.py - Version STANDALONE sans dépendance Flask

USAGE:
    python generate_data_standalone.py --db-url "postgresql://..."

Ce script ne dépend PAS de app.py, uniquement de SQLAlchemy direct.
"""

import argparse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from faker import Faker
from datetime import datetime, timedelta
import random
from werkzeug.security import generate_password_hash
import sys

# Configuration
fake = Faker('fr_FR')

# ==================== DONNÉES ALGÉRIENNES ====================

VILLES_ALGERIE = [
    'Alger', 'Oran', 'Constantine', 'Annaba', 'Blida',
    'Sétif', 'Tlemcen', 'Batna', 'Béjaïa', 'Tizi Ouzou'
]

AEROPORTS = {
    'Algérie': ['ALG', 'ORN', 'CZL', 'AAE'],
    'International': ['CDG', 'ORY', 'LHR', 'IST', 'DXB', 'JED', 'CAI', 'TUN']
}

COMPAGNIES = ['Air Algérie', 'Tassili Airlines', 'Air France', 'Turkish Airlines', 'Emirates']

DEPARTEMENTS_INFO = [
    {'name': 'Réservations', 'code': 'RES'},
    {'name': 'Finance', 'code': 'FIN'},
    {'name': 'Service Client', 'code': 'SUP'},
    {'name': 'Marketing', 'code': 'MKT'},
    {'name': 'Comptabilité', 'code': 'ACC'},
    {'name': 'Ressources Humaines', 'code': 'RH'},
    {'name': 'IT', 'code': 'IT'},
    {'name': 'Commercial', 'code': 'COM'},
    {'name': 'Logistique', 'code': 'LOG'},
    {'name': 'Direction', 'code': 'DIR'},
]

SITES_INFO = [
    {'name': 'Alger', 'code': 'ALG', 'address': 'Avenue Didouche Mourad, Alger', 'city': 'Alger'},
    {'name': 'Oran', 'code': 'ORN', 'address': 'Boulevard de la Révolution, Oran', 'city': 'Oran'},
]

ROLES_INFO = [
    {'name': 'Employé', 'code': 'EMPLOYEE', 'hierarchy_level': 1},
    {'name': 'Manager Département', 'code': 'MANAGER_DEPT', 'hierarchy_level': 2},
    {'name': 'Manager Multi-Départements', 'code': 'MANAGER_MULTI_DEPT', 'hierarchy_level': 3},
    {'name': 'Directeur de Site', 'code': 'DIRECTOR_SITE', 'hierarchy_level': 4},
    {'name': 'Directeur Général', 'code': 'GENERAL_DIRECTOR', 'hierarchy_level': 5},
    {'name': 'DPO (Data Protection Officer)', 'code': 'DPO', 'hierarchy_level': 5},
    {'name': 'Administrateur IT', 'code': 'ADMIN_IT', 'hierarchy_level': 5},
]


def generate_algerian_phone():
    """Génère un numéro de téléphone algérien"""
    prefixes = ['05', '06', '07']
    return f"+213{random.choice(prefixes)}{fake.random_number(digits=8, fix_len=True)}"


def parse_arguments():
    parser = argparse.ArgumentParser(description='Génération de données pour VoyagesDZ')
    parser.add_argument('--db-url', required=True, help='URL de connexion PostgreSQL')
    parser.add_argument('--volume', choices=['small', 'medium', 'large'], default='small',
                        help='Volume de données: small (1K), medium (100K), large (1M)')
    return parser.parse_args()


def get_volume_counts(volume):
    """Retourne le nombre d'enregistrements selon le volume"""
    volumes = {
        'small': {'users': 50, 'clients': 1000, 'bookings': 5000, 'payments': 2500},
        'medium': {'users': 100, 'clients': 50000, 'bookings': 200000, 'payments': 100000},
        'large': {'users': 200, 'clients': 100000, 'bookings': 1000000, 'payments': 500000}
    }
    return volumes[volume]


def main():
    args = parse_arguments()
    counts = get_volume_counts(args.volume)
    
    print(f"\n{'='*60}")
    print(f"GÉNÉRATION DE DONNÉES - VOLUME: {args.volume.upper()}")
    print(f"{'='*60}\n")
    
    # Connexion à la base de données
    print(f"📡 Connexion à la base de données...")
    try:
        engine = create_engine(args.db_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Test de connexion
        session.execute(text("SELECT 1"))
        print("✅ Connexion établie avec succès!\n")
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
        sys.exit(1)
    
    try:
        # ==================== 1. SITES ====================
        print("📍 Création des sites...")
        for site_info in SITES_INFO:
            session.execute(text("""
                INSERT INTO sites (name, code, address, city)
                VALUES (:name, :code, :address, :city)
                ON CONFLICT (code) DO NOTHING
            """), site_info)
        session.commit()
        print(f"   ✅ {len(SITES_INFO)} sites créés\n")
        
        # ==================== 2. DÉPARTEMENTS ====================
        print("🏢 Création des départements...")
        
        # Récupérer les IDs des sites
        result = session.execute(text("SELECT id, code FROM sites"))
        sites = {row[1]: row[0] for row in result}
        
        for site_code, site_id in sites.items():
            for dept_info in DEPARTEMENTS_INFO:
                session.execute(text("""
                    INSERT INTO departments (name, code, site_id)
                    VALUES (:name, :code, :site_id)
                    ON CONFLICT (code, site_id) DO NOTHING
                """), {
                    'name': dept_info['name'],
                    'code': dept_info['code'],
                    'site_id': site_id
                })
        session.commit()
        print(f"   ✅ {len(DEPARTEMENTS_INFO) * len(sites)} départements créés\n")
        
        # ==================== 3. ROLES ====================
        print("👥 Création des rôles...")
        for role_info in ROLES_INFO:
            session.execute(text("""
                INSERT INTO roles (name, code, hierarchy_level)
                VALUES (:name, :code, :hierarchy_level)
                ON CONFLICT (code) DO NOTHING
            """), role_info)
        session.commit()
        print(f"   ✅ {len(ROLES_INFO)} rôles créés\n")
        
        # ==================== 4. USERS ====================
        print(f"👤 Création de {counts['users']} utilisateurs...")
        
        # Récupérer les départements et rôles
        result = session.execute(text("SELECT id FROM departments"))
        department_ids = [row[0] for row in result]
        
        result = session.execute(text("SELECT id, code FROM roles"))
        roles = {row[1]: row[0] for row in result}
        
        user_ids = []
        for i in range(counts['users']):
            full_name = fake.name()
            email = fake.email()
            phone = generate_algerian_phone()
            password_hash = generate_password_hash('password123')
            department_id = random.choice(department_ids)
            
            result = session.execute(text("""
                INSERT INTO users (full_name, email, phone, password_hash, department_id, is_active, created_at)
                VALUES (:full_name, :email, :phone, :password_hash, :department_id, true, :created_at)
                RETURNING id
            """), {
                'full_name': full_name,
                'email': email,
                'phone': phone,
                'password_hash': password_hash,
                'department_id': department_id,
                'created_at': datetime.now()
            })
            user_id = result.fetchone()[0]
            user_ids.append(user_id)
            
            # Assigner un rôle (80% EMPLOYEE, 15% MANAGER_DEPT, 5% autres)
            rand = random.random()
            if rand < 0.80:
                role_code = 'EMPLOYEE'
            elif rand < 0.95:
                role_code = 'MANAGER_DEPT'
            else:
                role_code = random.choice(['DIRECTOR_SITE', 'GENERAL_DIRECTOR', 'DPO', 'ADMIN_IT'])
            
            session.execute(text("""
                INSERT INTO user_roles (user_id, role_id)
                VALUES (:user_id, :role_id)
            """), {'user_id': user_id, 'role_id': roles[role_code]})
            
            if (i + 1) % 100 == 0:
                session.commit()
                print(f"   ⏳ {i + 1}/{counts['users']} utilisateurs créés...")
        
        session.commit()
        print(f"   ✅ {counts['users']} utilisateurs créés\n")
        
        # ==================== 5. CLIENTS ====================
        print(f"👥 Création de {counts['clients']} clients...")
        
        # AJOUTER CETTE LIGNE POUR RÉINITIALISER L'UNICITÉ DE FAKER
        fake.unique.clear() 
        
        client_ids = []
        for i in range(counts['clients']):
            full_name = fake.name()
            # MODIFIER ICI: Utiliser fake.unique.email() pour garantir l'unicité
            email = fake.unique.email() 
            phone = generate_algerian_phone()
            city = random.choice(VILLES_ALGERIE)
            rgpd_consent = random.random() < 0.75  # 75% consent
            
            result = session.execute(text("""
                INSERT INTO clients (full_name, email, phone, city, rgpd_consent, consent_date, created_at)
                VALUES (:full_name, :email, :phone, :city, :rgpd_consent, :consent_date, :created_at)
                RETURNING id
            """), {
                'full_name': full_name,
                'email': email,
                'phone': phone,
                'city': city,
                'rgpd_consent': rgpd_consent,
                'consent_date': datetime.now() if rgpd_consent else None,
                'created_at': datetime.now() - timedelta(days=random.randint(0, 365))
            })
            client_id = result.fetchone()[0]
            client_ids.append(client_id)
            
            if (i + 1) % 1000 == 0:
                session.commit()
                print(f"   ⏳ {i + 1}/{counts['clients']} clients créés...")
        
        session.commit()
        print(f"   ✅ {counts['clients']} clients créés\n")
        
        # ==================== 6. VOLS ====================
        print("✈️ Création de vols...")
        
        flight_ids = []
        num_flights = min(10000, counts['bookings'] // 10)
        
        for i in range(num_flights):
            departure = random.choice(AEROPORTS['Algérie'])
            arrival = random.choice(AEROPORTS['International'])
            airline = random.choice(COMPAGNIES)
            flight_number = f"{airline[:2].upper()}{random.randint(100, 999)}"
            departure_date = datetime.now() + timedelta(days=random.randint(1, 180))
            price = random.randint(15000, 150000)  # Prix en DZD
            
            result = session.execute(text("""
                INSERT INTO flights (flight_number, airline, departure_airport, arrival_airport, 
                                     departure_date, price)
                VALUES (:flight_number, :airline, :departure, :arrival, :departure_date, :price)
                RETURNING id
            """), {
                'flight_number': flight_number,
                'airline': airline,
                'departure': departure,
                'arrival': arrival,
                'departure_date': departure_date,
                'price': price
            })
            flight_id = result.fetchone()[0]
            flight_ids.append(flight_id)
        
        session.commit()
        print(f"   ✅ {num_flights} vols créés\n")
        
        # ==================== 7. RÉSERVATIONS ====================
        print(f"📋 Création de {counts['bookings']} réservations...")
        
        # --- NOUVEAU CODE POUR PRÉPARER LES PAIRES UNIQUES ---
        # Calculer le nombre maximum de réservations uniques possibles
        max_bookings = len(client_ids) * len(flight_ids)
        num_bookings_to_create = min(counts['bookings'], max_bookings)
        
        print(f"   (Max. uniques possibles: {max_bookings:,}. Création de {num_bookings_to_create:,} uniques)")
        
        # Créer toutes les paires (client_id, flight_id) uniques
        all_unique_pairs = [(c, f) for c in client_ids for f in flight_ids]
        
        # Mélanger et sélectionner le nombre exact de réservations souhaitées
        random.shuffle(all_unique_pairs)
        selected_pairs = all_unique_pairs[:num_bookings_to_create]
        
        booking_ids = []
        # MODIFIER LA BOUCLE POUR PARCOURIR LES PAIRES PRÉSÉLECTIONNÉES
        for i, (client_id, flight_id) in enumerate(selected_pairs):
            # client_id et flight_id sont déjà uniques par définition de la boucle
            
            # --- Code inchangé (sauf la source de client_id et flight_id) ---
            user_id = random.choice(user_ids)
            total_price = random.randint(10000, 500000)
            status = random.choices(
                ['CONFIRMED', 'PENDING', 'CANCELLED'],
                weights=[0.70, 0.20, 0.10]
            )[0]
            created_at = datetime.now() - timedelta(days=random.randint(0, 365))
            
            result = session.execute(text("""
                INSERT INTO bookings (client_id, flight_id, total_price, status, 
                                      created_by_user_id, created_at)
                VALUES (:client_id, :flight_id, :total_price, :status, :user_id, :created_at)
                RETURNING id
            """), {
                'client_id': client_id,
                'flight_id': flight_id,
                'total_price': total_price,
                'status': status,
                'user_id': user_id,
                'created_at': created_at
            })
            booking_id = result.fetchone()[0]
            booking_ids.append(booking_id)
            
            if (i + 1) % 5000 == 0:
                session.commit()
                print(f"   ⏳ {i + 1}/{counts['bookings']} réservations créées...")
        
        session.commit()
        print(f"   ✅ {counts['bookings']} réservations créées\n")
        
        # ==================== 8. PAIEMENTS ====================
        print(f"💳 Création de {counts['payments']} paiements...")
        
        for i in range(counts['payments']):
            booking_id = random.choice(booking_ids)
            payment_method = random.choice(['CARD', 'CASH', 'TRANSFER'])
            amount = random.randint(10000, 500000)
            status = random.choices(['COMPLETED', 'PENDING', 'FAILED'], weights=[0.85, 0.10, 0.05])[0]
            
            session.execute(text("""
                INSERT INTO payments (booking_id, amount, payment_method, status, payment_date)
                VALUES (:booking_id, :amount, :payment_method, :status, :payment_date)
            """), {
                'booking_id': booking_id,
                'amount': amount,
                'payment_method': payment_method,
                'status': status,
                'payment_date': datetime.now() - timedelta(days=random.randint(0, 365))
            })
            
            if (i + 1) % 5000 == 0:
                session.commit()
                print(f"   ⏳ {i + 1}/{counts['payments']} paiements créés...")
        
        session.commit()
        print(f"   ✅ {counts['payments']} paiements créés\n")
        
        print(f"\n{'='*60}")
        print("🎉 GÉNÉRATION TERMINÉE AVEC SUCCÈS!")
        print(f"{'='*60}\n")
        
        # Statistiques finales
        print("📊 STATISTIQUES:")
        stats_queries = [
            ("Sites", "SELECT COUNT(*) FROM sites"),
            ("Départements", "SELECT COUNT(*) FROM departments"),
            ("Rôles", "SELECT COUNT(*) FROM roles"),
            ("Utilisateurs", "SELECT COUNT(*) FROM users"),
            ("Clients", "SELECT COUNT(*) FROM clients"),
            ("Vols", "SELECT COUNT(*) FROM flights"),
            ("Réservations", "SELECT COUNT(*) FROM bookings"),
            ("Paiements", "SELECT COUNT(*) FROM payments"),
        ]
        
        for label, query in stats_queries:
            result = session.execute(text(query))
            count = result.fetchone()[0]
            print(f"   • {label}: {count:,}")
        
        print()
        
    except Exception as e:
        print(f"\n❌ ERREUR lors de la génération: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == '__main__':
    main()