from django.core.management.base import BaseCommand
from gestionBatiment.tasks import envoyer_rappels_paiement


class Command(BaseCommand):
    help = "Envoie les rappels de paiement pour les contrats arrivant à échéance."

    def handle(self, *args, **options):
        resultat = envoyer_rappels_paiement()
        self.stdout.write(self.style.SUCCESS(resultat))
