from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group

class Command(BaseCommand):
    help = "Crée les groupes d'utilisateurs nécessaires pour les permissions de l'API"


    def handle(self, *args, **options):
        # Liste des rôles que vous avez définis dans vos permissions
        groupes_a_creer = ['ADMIN', 'TRAVAILLEUR', 'MANAGER', 'CLIENT']

        for nom_groupe in groupes_a_creer:
            # get_or_create évite de lever une erreur si le groupe existe déjà
            groupe, cree = Group.objects.get_or_create(name=nom_groupe)
            
            if cree:
                self.stdout.write(self.style.SUCCESS(f"🟢 Le groupe '{nom_groupe}' a été créé avec succès."))
            else:
                self.stdout.write(self.style.WARNING(f"🟡 Le groupe '{nom_groupe}' existe déjà."))