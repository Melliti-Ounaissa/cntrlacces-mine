"""
policies/business_rules.py - Règles métier (validations)

Contraintes business pour les opérations CRUD
VERSION CORRIGÉE - Compatible avec le schéma SQL
"""

from datetime import datetime, timedelta


class BookingRules:
    """Règles métier pour les réservations"""
    
    MIN_AMOUNT = 5000  # DZD
    MAX_AMOUNT_EMPLOYEE = 500000  # DZD
    MIN_ADVANCE_DAYS = 3  # Jours minimum avant voyage
    MIN_TRAVELERS = 1
    MAX_TRAVELERS = 50
    CANCELLATION_DEADLINE_DAYS = 7
    CANCELLATION_FEE_PERCENT = 0.5  # 50%
    
    @staticmethod
    def validate_create(booking_data, creator):
        """
        Valide la création d'une réservation
        
        Returns:
            (bool, list): (Valide ?, Liste d'erreurs)
        """
        errors = []
        
        # 1. Montant minimum
        amount = int(booking_data.get('total_price', 0))
        if amount < BookingRules.MIN_AMOUNT:
            errors.append(f"Montant minimum : {BookingRules.MIN_AMOUNT:,} DZD")
        
        # 2. Montant maximum pour EMPLOYEE
        highest_role = creator.get_highest_role()
        if highest_role and highest_role.code == "EMPLOYEE":
            if amount > BookingRules.MAX_AMOUNT_EMPLOYEE:
                errors.append(
                    f"En tant qu'employé, vous ne pouvez pas créer "
                    f"de réservation > {BookingRules.MAX_AMOUNT_EMPLOYEE:,} DZD. "
                    f"Contactez votre manager."
                )
        
        # 3. Date dans le futur
        travel_date = booking_data.get('travel_date')
        if travel_date:
            if isinstance(travel_date, str):
                try:
                    travel_date = datetime.strptime(travel_date, '%Y-%m-%d').date()
                except ValueError:
                    errors.append("Format de date invalide (YYYY-MM-DD requis)")
                    return len(errors) == 0, errors
            
            if travel_date <= datetime.now().date():
                errors.append("La date de voyage doit être dans le futur")
            
            # 4. Délai minimum
            min_date = datetime.now().date() + timedelta(days=BookingRules.MIN_ADVANCE_DAYS)
            if travel_date < min_date:
                errors.append(
                    f"La réservation doit être faite au moins "
                    f"{BookingRules.MIN_ADVANCE_DAYS} jours à l'avance"
                )
        
        return len(errors) == 0, errors
    
    @staticmethod
    def can_modify(booking):
        """
        Vérifie si une réservation peut être modifiée
        """
        # Pas de modification si confirmée et < 48h avant voyage
        if booking.status in ['CONFIRMED', 'confirmed']:
            if booking.travel_date:
                time_until_travel = booking.travel_date - datetime.now().date()
                if time_until_travel.days < 2:
                    return False, "Impossible de modifier < 48h avant le voyage"
        
        return True, None
    
    @staticmethod
    def calculate_cancellation_fee(booking):
        """
        Calcule les frais d'annulation
        """
        if not booking.travel_date:
            return 0
        
        time_until_travel = booking.travel_date - datetime.now().date()
        
        if time_until_travel.days < BookingRules.CANCELLATION_DEADLINE_DAYS:
            # Frais 50% si annulation tardive
            fee = int(booking.total_price) * BookingRules.CANCELLATION_FEE_PERCENT
            return fee
        
        # Pas de frais si annulation ≥ 7 jours avant
        return 0


class ClientRules:
    """Règles métier pour les clients"""
    
    MIN_AGE = 18
    
    @staticmethod
    def validate_create(client_data):
        """
        Valide la création d'un client
        """
        errors = []
        
        # 1. Consentement RGPD obligatoire
        if not client_data.get('rgpd_consent'):
            errors.append(
                "Le client doit donner son consentement pour le traitement "
                "de ses données personnelles (Loi 18-07)"
            )
        
        # 2. Téléphone algérien (optionnel mais si fourni)
        phone = client_data.get('phone', '')
        if phone and not phone.startswith('+213'):
            errors.append("Le téléphone doit commencer par +213 (Algérie)")
        
        # 3. Email valide
        email = client_data.get('email', '')
        if not email or '@' not in email:
            errors.append("Email valide requis")
        
        # 4. Nom complet requis
        full_name = client_data.get('full_name', '').strip()
        if not full_name or len(full_name) < 3:
            errors.append("Nom complet requis (minimum 3 caractères)")
        
        return len(errors) == 0, errors


class PaymentRules:
    """Règles métier pour les paiements"""
    
    MAX_AMOUNT_FINANCE_MANAGER = 100000  # DZD
    PAYMENT_DEADLINE_HOURS = 48
    
    @staticmethod
    def validate_create(payment_data, booking, processor):
        """
        Valide la création d'un paiement
        """
        errors = []
        
        # 1. Montant = montant de la réservation
        payment_amount = int(payment_data.get('amount', 0))
        if abs(payment_amount - int(booking.total_price)) > 0:
            errors.append(
                f"Le montant du paiement ({payment_amount:,} DZD) doit "
                f"correspondre au montant de la réservation "
                f"({booking.total_price:,} DZD)"
            )
        
        # 2. Montant max pour Manager Finance
        highest_role = processor.get_highest_role()
        if highest_role and highest_role.code == "MANAGER_DEPT":
            if processor.department and processor.department.code.startswith("FIN"):
                if payment_amount > PaymentRules.MAX_AMOUNT_FINANCE_MANAGER:
                    errors.append(
                        f"En tant que Manager Finance, vous ne pouvez traiter "
                        f"un paiement > {PaymentRules.MAX_AMOUNT_FINANCE_MANAGER:,} DZD. "
                        f"Contactez le directeur."
                    )
        
        # 3. Vérifier qu'il n'y a pas déjà un paiement réussi
        from models import Payment
        existing = Payment.query.filter(
            Payment.booking_id == booking.id,
            Payment.status == 'COMPLETED'
        ).first()
        
        if existing:
            errors.append("Cette réservation a déjà été payée")
        
        return len(errors) == 0, errors