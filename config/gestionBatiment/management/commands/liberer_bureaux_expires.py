from django.core.management.base import BaseCommand
from gestion.models import synchroniser_bureaux_expires  # adapte le nom de l'app

class Command(BaseCommand):
    help = "Libère manuellement les bureaux dont le contrat/réservation est expiré."

    def handle(self, *args, **options):
        synchroniser_bureaux_expires()
        self.stdout.write(self.style.SUCCESS("Synchronisation terminée."))