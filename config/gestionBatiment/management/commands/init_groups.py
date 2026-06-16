from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from gestionBatiment.models import (
    Client, Batiment, Niveau, TypeBureau, Bureau, 
    Reservation, Contrat, Location, Paiement
)


class Command(BaseCommand):
    help = 'Initialise les groupes et permissions pour l\'application'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Initialisation des groupes et permissions...'))

        # Créer les groupes
        admin_group, _ = Group.objects.get_or_create(name='ADMIN')
        travailleur_group, _ = Group.objects.get_or_create(name='TRAVAILLEUR')
        manager_group, _ = Group.objects.get_or_create(name='MANAGER')
        agent_group, _ = Group.objects.get_or_create(name='AGENT')
        client_group, _ = Group.objects.get_or_create(name='CLIENT')

        # Réinitialiser les permissions pour chaque groupe
        admin_group.permissions.clear()
        travailleur_group.permissions.clear()
        manager_group.permissions.clear()
        agent_group.permissions.clear()
        client_group.permissions.clear()

        # Récupérer tous les content types et permissions
        models = [Client, Batiment, Niveau, TypeBureau, Bureau, Reservation, Contrat, Location, Paiement]
        
        # ADMIN: Accès complet à tout
        for model in models:
            content_type = ContentType.objects.get_for_model(model)
            permissions = Permission.objects.filter(content_type=content_type)
            admin_group.permissions.add(*permissions)

        self.stdout.write(self.style.SUCCESS('✓ ADMIN: Accès complet'))

        # TRAVAILLEUR/MANAGER/AGENT: Permissions limitées
        worker_permissions = self._get_worker_permissions(models)
        for group in [travailleur_group, manager_group, agent_group]:
            group.permissions.add(*worker_permissions)
        self.stdout.write(self.style.SUCCESS('✓ TRAVAILLEUR/MANAGER/AGENT: Permissions configurées'))

        # CLIENT: Permissions minimales
        client_permissions = self._get_client_permissions(models)
        client_group.permissions.add(*client_permissions)
        self.stdout.write(self.style.SUCCESS('✓ CLIENT: Permissions configurées'))

        self.stdout.write(self.style.SUCCESS('\n✓ Initialisation terminée avec succès!'))
        self.stdout.write(self.style.WARNING(
            '\nNote: Les permissions d\'accès sont contrôlées par les classes '
            'de permissions personnalisées (ClientPermission, BatimentPermission, etc.) '
            'dans permissions.py, pas seulement par Django Permissions.'
        ))

    def _get_worker_permissions(self, models):
        """Retourne les permissions pour les travailleurs/managers"""
        permissions = []
        for model in models:
            content_type = ContentType.objects.get_for_model(model)
            # Les travailleurs peuvent voir (view) et créer (add)
            perms = Permission.objects.filter(
                content_type=content_type,
                codename__in=['view_' + model.__name__.lower(), 'add_' + model.__name__.lower()]
            )
            permissions.extend(perms)
        return permissions

    def _get_client_permissions(self, models):
        """Retourne les permissions pour les clients"""
        permissions = []
        # Les clients peuvent seulement voir les modèles pertinents
        relevant_models = [Bureau, Reservation, Contrat, Paiement, Client]
        for model in relevant_models:
            content_type = ContentType.objects.get_for_model(model)
            perms = Permission.objects.filter(
                content_type=content_type,
                codename='view_' + model.__name__.lower()
            )
            permissions.extend(perms)
        return permissions