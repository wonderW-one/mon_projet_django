# gestionBatiment/signals.py
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Reservation, Contrat, Paiement, Bureau

# Configuration du logger pour afficher les messages dans le terminal
logger = logging.getLogger(__name__)

def envoyer_sms_local_test(telephone, message):
    """Simulateur local de SMS pour l'environnement de développement."""
    print("\n" + "="*40)
    print(f"📱 [TEST LOCAL - SMS ENVOYÉ]")
    print(f"À      : {telephone}")
    print(f"Texte  : {message}")
    print("="*40 + "\n")

def envoyer_push_local_test(user_id, titre, message):
    """Simulateur local de Notification Push."""
    print("\n" + "="*40)
    print(f"🔔 [TEST LOCAL - NOTIFICATION PUSH]")
    print(f"User ID: {user_id}")
    print(f"Titre  : {titre}")
    print(f"Message: {message}")
    print("="*40 + "\n")


# --- Vos récepteurs de signaux restent inchangés ---

@receiver(post_save, sender=Reservation)
def notification_reservation(sender, instance, created, **kwargs):
    if created:
        client_user = instance.client.user
        telephone = instance.client.telephone
        bureau_num = instance.bureau.numero
        
        message = f"Bonjour {client_user.first_name}, votre réservation pour le Bureau {bureau_num} a été enregistrée."
        
        # Appels des simulateurs locaux
        envoyer_sms_local_test(telephone, message)
        envoyer_push_local_test(client_user.id, "Réservation Confirmée", message)


@receiver(post_save, sender=Paiement)
def notification_paiement(sender, instance, created, **kwargs):
    client_user = instance.client.user
    telephone = instance.client.telephone
    mois_str = instance.get_mois_paye_display()

    if created:
        if instance.statut == 'PAID':
            message = f"Paiement reçu ! Montant : {instance.montant} FBU pour le mois de {mois_str}."
            envoyer_sms_local_test(telephone, message)
            envoyer_push_local_test(client_user.id, "Paiement Validé", message)