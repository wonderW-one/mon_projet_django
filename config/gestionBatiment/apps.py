from django.apps import AppConfig


class GestionbatimentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "gestionBatiment"

    def ready(self):
        # Importation obligatoire des signaux pour exécution au démarrage
        import gestionBatiment.signals  # noqa: F401
