"""
Script d'exemple pour initialiser les utilisateurs de test avec leurs rôles.

Usage:
    python manage.py shell
    >>> exec(open('setup_test_users.py').read())

Ou créer une commande Django et l'exécuter:
    python manage.py init_test_users
"""

from django.contrib.auth.models import Group, User
from gestionBatiment.models import Client


def create_test_users():
    """Crée les utilisateurs de test avec leurs rôles"""

    # Récupérer les groupes
    admin_group = Group.objects.get(name="ADMIN")
    travailleur_group = Group.objects.get(name="TRAVAILLEUR")
    manager_group = Group.objects.get(name="MANAGER")
    client_group = Group.objects.get(name="CLIENT")

    # 1. ADMIN
    admin_user, created = User.objects.get_or_create(
        username="admin_user",
        defaults={
            "first_name": "Admin",
            "last_name": "User",
            "email": "admin@example.com",
            "is_staff": True,
            "is_superuser": True,
        },
    )
    if created:
        admin_user.set_password("admin123")
        admin_user.save()
        print("✓ Utilisateur ADMIN créé: admin_user / admin123")

    # 2. TRAVAILLEUR
    travailleur_user, created = User.objects.get_or_create(
        username="travailleur_user",
        defaults={
            "first_name": "Jean",
            "last_name": "Travailleur",
            "email": "travailleur@example.com",
        },
    )
    if created:
        travailleur_user.set_password("travailleur123")
        travailleur_user.save()
        travailleur_user.groups.add(travailleur_group)
        print("✓ Utilisateur TRAVAILLEUR créé: travailleur_user / travailleur123")

        # Créer le profil Client pour le travailleur
        Client.objects.get_or_create(
            user=travailleur_user,
            defaults={
                "role": "TRAVAILLEUR",
                "telephone": "+237600000000",
                "addresse": "Yaounde",
            },
        )

    # 3. MANAGER
    manager_user, created = User.objects.get_or_create(
        username="manager_user",
        defaults={
            "first_name": "Marie",
            "last_name": "Manager",
            "email": "manager@example.com",
        },
    )
    if created:
        manager_user.set_password("manager123")
        manager_user.save()
        manager_user.groups.add(manager_group)
        print("✓ Utilisateur MANAGER créé: manager_user / manager123")

        # Créer le profil Client pour le manager
        Client.objects.get_or_create(
            user=manager_user,
            defaults={
                "role": "MANAGER",
                "telephone": "+237600000001",
                "addresse": "Douala",
            },
        )

    # 4. CLIENT 1
    client_user1, created = User.objects.get_or_create(
        username="client_user1",
        defaults={
            "first_name": "Pierre",
            "last_name": "Client",
            "email": "client1@example.com",
        },
    )
    if created:
        client_user1.set_password("client123")
        client_user1.save()
        client_user1.groups.add(client_group)
        print("✓ Utilisateur CLIENT créé: client_user1 / client123")

        # Créer le profil Client
        Client.objects.get_or_create(
            user=client_user1,
            defaults={
                "role": "CLIENT",
                "telephone": "+237600000002",
                "addresse": "Bamenda",
                "date_naissance": "1990-01-15",
            },
        )

    # 5. CLIENT 2
    client_user2, created = User.objects.get_or_create(
        username="client_user2",
        defaults={
            "first_name": "Sophie",
            "last_name": "Entreprise",
            "email": "client2@example.com",
        },
    )
    if created:
        client_user2.set_password("client456")
        client_user2.save()
        client_user2.groups.add(client_group)
        print("✓ Utilisateur CLIENT créé: client_user2 / client456")

        # Créer le profil Client
        Client.objects.get_or_create(
            user=client_user2,
            defaults={
                "role": "CLIENT",
                "telephone": "+237600000003",
                "addresse": "Limbe",
                "date_naissance": "1985-05-20",
            },
        )

    print("\n" + "=" * 50)
    print("UTILISATEURS DE TEST CRÉÉS")
    print("=" * 50)
    print("\nIdentifiants de test:\n")
    print("  ADMIN:")
    print("    - Username: admin_user")
    print("    - Password: admin123")
    print("    - Accès: Complet à tous les endpoints\n")
    print("  TRAVAILLEUR:")
    print("    - Username: travailleur_user")
    print("    - Password: travailleur123")
    print("    - Accès: Lecture clients, création réservations/contrats\n")
    print("  MANAGER:")
    print("    - Username: manager_user")
    print("    - Password: manager123")
    print("    - Accès: Même que TRAVAILLEUR\n")
    print("  CLIENT 1:")
    print("    - Username: client_user1")
    print("    - Password: client123")
    print("    - Accès: Voir bureaux, créer réservations/contrats personnels\n")
    print("  CLIENT 2:")
    print("    - Username: client_user2")
    print("    - Password: client456")
    print("    - Accès: Voir bureaux, créer réservations/contrats personnels\n")
    print("=" * 50)


# Exécuter si appelé directement
if __name__ == "__main__":
    create_test_users()
