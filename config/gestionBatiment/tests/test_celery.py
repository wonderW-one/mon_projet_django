# gestionBatiment/tests/test_celery.py
"""
Tests de la configuration Celery elle-même (app, enregistrement des tâches,
exécution asynchrone). À la différence de test_tasks.py, on vérifie ici le
câblage Celery, pas la logique métier.

Pré-requis settings.py (settings de test) :
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True

`ALWAYS_EAGER` fait que `.delay()` / `.apply_async()` exécutent la tâche
immédiatement dans le process de test, sans passer par Redis ni un worker
séparé.
"""
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from freezegun import freeze_time

from config.celery import app as celery_app
from gestionBatiment.models import Batiment, Bureau, Client, Contrat
from gestionBatiment.tasks import JOURS_AVANT_RAPPEL, envoyer_rappels_paiement


class CeleryAppConfigTestCase(TestCase):
    """Vérifie que l'app Celery est bien configurée et que la tâche est connue."""

    def test_app_utilise_bien_la_config_django(self):
        # namespace='CELERY' -> les clés CELERY_BROKER_URL etc. sont bien lues
        self.assertEqual(celery_app.conf.timezone, "UTC")

    def test_tache_rappel_est_enregistree(self):
        self.assertIn(
            "gestionBatiment.tasks.envoyer_rappels_paiement",
            celery_app.tasks,
        )

    def test_broker_url_est_configure(self):
        self.assertTrue(celery_app.conf.broker_url)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class CeleryExecutionAsyncTestCase(TestCase):
    """Vérifie que l'appel asynchrone (.delay) fonctionne réellement."""

    def setUp(self):
        user = User.objects.create_user(
            username="jdupont", email="jdupont@example.com", first_name="Jean"
        )
        self.client_profile = Client.objects.create(user=user)
        admin_user = User.objects.create_user(username="admin_bat")
        batiment = Batiment.objects.create(user=admin_user, nom="Tour A", adresse="Rue X")
        self.bureau = Bureau.objects.create(
            numero="101", batiment=batiment, unite=10, espace=100
        )

    @freeze_time("2026-07-08")
    def test_delay_execute_la_tache_et_renvoie_un_resultat_reussi(self):
        date_cible = date(2026, 7, 8) + timedelta(days=JOURS_AVANT_RAPPEL)
        Contrat.objects.create(
            client=self.client_profile,
            bureau=self.bureau,
            periodicite="MENSUEL",
            statut=Contrat.ContratStatus.VALIDE,
            date_debut=date_cible - timedelta(days=30),
            date_fin=date_cible,
            is_active=True,
        )

        async_result = envoyer_rappels_paiement.delay()

        self.assertTrue(async_result.successful())
        self.assertIn("1 rappel(s) envoyé(s)", async_result.result)
        self.assertEqual(len(mail.outbox), 1)

    def test_delay_sans_contrat_ne_leve_pas_d_erreur(self):
        async_result = envoyer_rappels_paiement.delay()
        self.assertTrue(async_result.successful())
        self.assertIn("0 rappel(s) envoyé(s)", async_result.result)
