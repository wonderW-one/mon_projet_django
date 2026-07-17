import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402

User = get_user_model()

username = "admin_prod"
email = "admin@monprojet.com"
password = os.environ.get("ADMIN_PASSWORD", "ChangeMoiTemporairement123!")

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"Superutilisateur {username} créé avec succès !")
else:
    print("Le superutilisateur existe déjà.")