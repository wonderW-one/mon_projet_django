# gestionBatiment/management/commands/envoyer_rappels_paiement.py
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from gestionBatiment.models import Contrat

# Nombre de jours avant l'échéance pour envoyer le rappel
JOURS_AVANT_RAPPEL = 5

class Command(BaseCommand):
    help = "Envoie un email de rappel aux clients dont l'échéance de paiement approche."

    def handle(self, *args, **options):
        aujourdhui = timezone.now().date()
        date_cible = aujourdhui + timedelta(days=JOURS_AVANT_RAPPEL)

        # Contrats actifs et validés dont la date de fin tombe exactement dans JOURS_AVANT_RAPPEL jours
        contrats = Contrat.objects.filter(
            statut=Contrat.ContratStatus.VALIDE,
            is_active=True,
            date_fin=date_cible,
        ).select_related('client__user')

        envoyes = 0
        for contrat in contrats:
            client = contrat.client
            email = client.user.email
            if not email:
                continue

            nom = client.user.first_name or client.user.username
            periodicite_label = contrat.get_periodicite_display()
            bureau = contrat.bureau_effectif
            bureau_nom = f"Bureau {bureau.numero}" if bureau else "votre espace"

            sujet = f"Rappel : renouvellement de votre {periodicite_label.lower()} - {bureau_nom}"
            corps = (
                f"Bonjour {nom},\n\n"
                f"Votre contrat de location ({periodicite_label}) pour {bureau_nom} "
                f"arrive à échéance le {contrat.date_fin.strftime('%d/%m/%Y')}.\n\n"
                f"Montant à régler : {contrat.montant} FBU.\n\n"
                f"Merci de procéder au renouvellement avant cette date pour éviter "
                f"toute interruption de votre location.\n\n"
                f"L'équipe de gestion."
            )


            try:
                send_mail(
                    sujet, corps,
                    settings.EMAIL_HOST_USER,
                    [email],
                    fail_silently=False,   # pour voir les erreurs pendant les tests
                )
                envoyes += 1
            except Exception as e:
                self.stderr.write(f"Échec envoi à {email} (contrat #{contrat.id}) : {e}")

        self.stdout.write(self.style.SUCCESS(f"{envoyes} rappel(s) envoyé(s)."))