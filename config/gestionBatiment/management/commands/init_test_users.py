from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from gestionBatiment.models import Client


class Command(BaseCommand):
    help = 'Crée les utilisateurs de test avec leurs rôles pour les tests d\'API'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Création des utilisateurs de test...'))

        # Récupérer les groupes (doivent être créés avec init_groups)
        try:
            admin_group = Group.objects.get(name='ADMIN')
            travailleur_group = Group.objects.get(name='TRAVAILLEUR')
            manager_group = Group.objects.get(name='MANAGER')
            client_group = Group.objects.get(name='CLIENT')
        except Group.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                '✗ Les groupes n\'existent pas. Exécutez d\'abord: python manage.py init_groups'
            ))
            return

        # 1. ADMIN
        admin_user, created = User.objects.get_or_create(
            username='admin_user',
            defaults={
                'first_name': 'Admin',
                'last_name': 'User',
                'email': 'admin@example.com',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('✓ ADMIN créé: admin_user / admin123'))
        else:
            self.stdout.write(self.style.WARNING('⚠ ADMIN existe déjà: admin_user'))

        # 2. TRAVAILLEUR
        travailleur_user, created = User.objects.get_or_create(
            username='travailleur_user',
            defaults={
                'first_name': 'Jean',
                'last_name': 'Travailleur',
                'email': 'travailleur@example.com'
            }
        )
        if created:
            travailleur_user.set_password('travailleur123')
            travailleur_user.save()
            travailleur_user.groups.add(travailleur_group)
            Client.objects.get_or_create(
                user=travailleur_user,
                defaults={
                    'role': 'TRAVAILLEUR',
                    'telephone': '+237600000000',
                    'addresse': 'Yaounde'
                }
            )
            self.stdout.write(self.style.SUCCESS('✓ TRAVAILLEUR créé: travailleur_user / travailleur123'))
        else:
            self.stdout.write(self.style.WARNING('⚠ TRAVAILLEUR existe déjà: travailleur_user'))

        # 3. MANAGER
        manager_user, created = User.objects.get_or_create(
            username='manager_user',
            defaults={
                'first_name': 'Marie',
                'last_name': 'Manager',
                'email': 'manager@example.com'
            }
        )
        if created:
            manager_user.set_password('manager123')
            manager_user.save()
            manager_user.groups.add(manager_group)
            Client.objects.get_or_create(
                user=manager_user,
                defaults={
                    'role': 'MANAGER',
                    'telephone': '+237600000001',
                    'addresse': 'Douala'
                }
            )
            self.stdout.write(self.style.SUCCESS('✓ MANAGER créé: manager_user / manager123'))
        else:
            self.stdout.write(self.style.WARNING('⚠ MANAGER existe déjà: manager_user'))

        # 4. CLIENT 1
        client_user1, created = User.objects.get_or_create(
            username='client_user1',
            defaults={
                'first_name': 'Pierre',
                'last_name': 'Client',
                'email': 'client1@example.com'
            }
        )
        if created:
            client_user1.set_password('client123')
            client_user1.save()
            client_user1.groups.add(client_group)
            Client.objects.get_or_create(
                user=client_user1,
                defaults={
                    'role': 'CLIENT',
                    'telephone': '+237600000002',
                    'addresse': 'Bamenda',
                    'date_naissance': '1990-01-15'
                }
            )
            self.stdout.write(self.style.SUCCESS('✓ CLIENT 1 créé: client_user1 / client123'))
        else:
            self.stdout.write(self.style.WARNING('⚠ CLIENT 1 existe déjà: client_user1'))

        # 5. CLIENT 2
        client_user2, created = User.objects.get_or_create(
            username='client_user2',
            defaults={
                'first_name': 'Sophie',
                'last_name': 'Entreprise',
                'email': 'client2@example.com'
            }
        )
        if created:
            client_user2.set_password('client456')
            client_user2.save()
            client_user2.groups.add(client_group)
            Client.objects.get_or_create(
                user=client_user2,
                defaults={
                    'role': 'CLIENT',
                    'telephone': '+237600000003',
                    'addresse': 'Limbe',
                    'date_naissance': '1985-05-20'
                }
            )
            self.stdout.write(self.style.SUCCESS('✓ CLIENT 2 créé: client_user2 / client456'))
        else:
            self.stdout.write(self.style.WARNING('⚠ CLIENT 2 existe déjà: client_user2'))

        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('✓ INITIALISATION UTILISATEURS TERMINÉE'))
        self.stdout.write(self.style.SUCCESS('='*60))
        self._print_credentials()

    def _print_credentials(self):
        """Affiche les identifiants de test"""
        credentials = [
            {
                'role': 'ADMIN',
                'username': 'admin_user',
                'password': 'admin123',
                'access': 'Accès complet à tous les endpoints'
            },
            {
                'role': 'TRAVAILLEUR',
                'username': 'travailleur_user',
                'password': 'travailleur123',
                'access': 'Lecture clients, création réservations/contrats'
            },
            {
                'role': 'MANAGER',
                'username': 'manager_user',
                'password': 'manager123',
                'access': 'Même que TRAVAILLEUR'
            },
            {
                'role': 'CLIENT 1',
                'username': 'client_user1',
                'password': 'client123',
                'access': 'Bureaux disponibles, réservations/contrats personnels'
            },
            {
                'role': 'CLIENT 2',
                'username': 'client_user2',
                'password': 'client456',
                'access': 'Bureaux disponibles, réservations/contrats personnels'
            }
        ]


        self.stdout.write('\nIDENTIFIANTS DE TEST:\n')
        for cred in credentials:
            self.stdout.write(f"\n{cred['role']}:")
            self.stdout.write(f"  • Username: {cred['username']}")
            self.stdout.write(f"  • Password: {cred['password']}")
            self.stdout.write(f"  • Accès: {cred['access']}")

        self.stdout.write('\n' + '='*60)
