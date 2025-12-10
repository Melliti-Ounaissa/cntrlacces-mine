"""
policies/business_rules.py - Règles métier (validations)

Contraintes business pour les opérations CRUD
"""

from datetime import datetime, timedelta


class BookingRules:
    """Règles métier pour les réservations"""
    
    MIN_AMOUNT = 5000.0  # DZD
    MAX_AMOUNT_EMPLOYEE = 500000.0  # DZD
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
        amount = float(booking_data.get('total_amount_dzd', 0))
        if amount < BookingRules.MIN_AMOUNT:
            errors.append(f"Montant minimum : {BookingRules.MIN_AMOUNT:,.0f} DZD")
        
        # 2. Montant maximum pour EMPLOYEE
        highest_role = creator.get_highest_role()
        if highest_role and highest_role.code == "EMPLOYEE":
            if amount > BookingRules.MAX_AMOUNT_EMPLOYEE:
                errors.append(
                    f"En tant qu'employé, vous ne pouvez pas créer "
                    f"de réservation > {BookingRules.MAX_AMOUNT_EMPLOYEE:,.0f} DZD. "
                    f"Contactez votre manager."
                )
        
        # 3. Date dans le futur
        travel_date = booking_data.get('travel_date')
        if travel_date:
            if isinstance(travel_date, str):
                travel_date = datetime.strptime(travel_date, '%Y-%m-%d').date()
            
            if travel_date <= datetime.now().date():
                errors.append("La date de voyage doit être dans le futur")
            
            # 4. Délai minimum
            min_date = datetime.now().date() + timedelta(days=BookingRules.MIN_ADVANCE_DAYS)
            if travel_date < min_date:
                errors.append(
                    f"La réservation doit être faite au moins "
                    f"{BookingRules.MIN_ADVANCE_DAYS} jours à l'avance"
                )
        
        # 5. Nombre de voyageurs
        travelers = int(booking_data.get('number_of_travelers', 1))
        if not (BookingRules.MIN_TRAVELERS <= travelers <= BookingRules.MAX_TRAVELERS):
            errors.append(
                f"Nombre de voyageurs : entre {BookingRules.MIN_TRAVELERS} "
                f"et {BookingRules.MAX_TRAVELERS}"
            )
        
        return len(errors) == 0, errors
    
    @staticmethod
    def can_modify(booking):
        """
        Vérifie si une réservation peut être modifiée
        """
        # Pas de modification si confirmée et < 48h avant voyage
        if booking.status == 'confirmed':
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
            return 0.0
        
        time_until_travel = booking.travel_date - datetime.now().date()
        
        if time_until_travel.days < BookingRules.CANCELLATION_DEADLINE_DAYS:
            # Frais 50% si annulation tardive
            fee = float(booking.total_amount_dzd) * BookingRules.CANCELLATION_FEE_PERCENT
            return fee
        
        # Pas de frais si annulation ≥ 7 jours avant
        return 0.0


class ClientRules:
    """Règles métier pour les clients"""
    
    MIN_AGE = 18
    PASSPORT_VALIDITY_MONTHS = 6
    
    @staticmethod
    def validate_create(client_data):
        """
        Valide la création d'un client
        """
        errors = []
        
        # 1. Consentement RGPD obligatoire
        if not client_data.get('is_personal_data_consented'):
            errors.append(
                "Le client doit donner son consentement pour le traitement "
                "de ses données personnelles (Loi 18-07)"
            )
        
        # 2. Âge minimum
        dob = client_data.get('date_of_birth')
        if dob:
            if isinstance(dob, str):
                dob = datetime.strptime(dob, '%Y-%m-%d').date()
            
            age = (datetime.now().date() - dob).days // 365
            if age < ClientRules.MIN_AGE:
                errors.append(f"Le client doit avoir au moins {ClientRules.MIN_AGE} ans")
        
        # 3. Téléphone algérien
        phone = client_data.get('phone', '')
        if phone and not phone.startswith('+213'):
            errors.append("Le téléphone doit commencer par +213 (Algérie)")
        
        return len(errors) == 0, errors


class PaymentRules:
    """Règles métier pour les paiements"""
    
    MAX_AMOUNT_FINANCE_MANAGER = 100000.0  # DZD
    PAYMENT_DEADLINE_HOURS = 48
    
    @staticmethod
    def validate_create(payment_data, booking, processor):
        """
        Valide la création d'un paiement
        """
        errors = []
        
        # 1. Montant = montant de la réservation
        payment_amount = float(payment_data.get('amount_dzd', 0))
        if abs(payment_amount - float(booking.total_amount_dzd)) > 0.01:
            errors.append(
                f"Le montant du paiement ({payment_amount:,.2f} DZD) doit "
                f"correspondre au montant de la réservation "
                f"({booking.total_amount_dzd:,.2f} DZD)"
            )
        
        # 2. Montant max pour Manager Finance
        highest_role = processor.get_highest_role()
        if highest_role and highest_role.code == "MANAGER_DEPT":
            if processor.department and processor.department.code.startswith("FIN"):
                if payment_amount > PaymentRules.MAX_AMOUNT_FINANCE_MANAGER:
                    errors.append(
                        f"En tant que Manager Finance, vous ne pouvez traiter "
                        f"un paiement > {PaymentRules.MAX_AMOUNT_FINANCE_MANAGER:,.0f} DZD. "
                        f"Contactez le directeur."
                    )
        
        # 3. Vérifier qu'il n'y a pas déjà un paiement réussi
        from models import Payment
        existing = Payment.query.filter(
            Payment.booking_id == booking.id,
            Payment.status == 'completed'
        ).first()
        
        if existing:
            errors.append("Cette réservation a déjà été payée")
        
        return len(errors) == 0, errors