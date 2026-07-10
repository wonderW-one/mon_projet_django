# gestionBatiment/tests/test_tasks.py
"""
Tests de la tâche Celery `envoyer_rappels_paiement`.

Ces tests appellent la fonction directement (pas via .delay()), donc ils
n'ont besoin d'aucune configuration Celery particulière : ils testent la
logique métier (filtrage des contrats, contenu de l'email, cas limites).

Pré-requis settings.py (settings de test) :
    EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
"""

from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from freezegun import freeze_time
from gestionBatiment.models import Batiment, Bureau, Client, Contrat, TypeBureau
from gestionBatiment.tasks import JOURS_AVANT_RAPPEL, envoyer_rappels_paiement

DATE_DU_JOUR = "2026-07-08"


class EnvoyerRappelsPaiementTestCase(TestCase):
    def setUp(self):
        user = User.objects.create_user(
            username="jdupont",
            email="jdupont@example.com",
            first_name="Jean",
        )
        self.client_profile = Client.objects.create(user=user)

        admin_user = User.objects.create_user(username="admin_bat")
        batiment = Batiment.objects.create(
            user=admin_user, nom="Tour A", adresse="Rue X"
        )
        type_bureau = TypeBureau.objects.create(nom="Open space")
        self.bureau = Bureau.objects.create(
            numero="101", type=type_bureau, unite=10, espace=100, batiment=batiment
        )

    def _creer_contrat(
        self,
        date_fin,
        statut=Contrat.ContratStatus.VALIDE,
        actif=True,
        periodicite="MENSUEL",
    ):
        """
        Crée un contrat direct (sans réservation) rattaché au bureau de test.
        Comme aucun `user=` n'est passé à .save(), la logique de rétrogradation
        automatique du statut (réservée aux CLIENT créant leur propre demande)
        ne s'applique pas : le statut demandé est bien conservé.
        """
        contrat = Contrat(
            client=self.client_profile,
            bureau=self.bureau,
            periodicite=periodicite,
            statut=statut,
            date_debut=date_fin - timedelta(days=30),
            date_fin=date_fin,
            is_active=actif,
        )
        contrat.save()
        return contrat

    @freeze_time(DATE_DU_JOUR)
    def test_envoie_un_email_pour_contrat_a_echeance_dans_5_jours(self):
        date_cible = date.fromisoformat(DATE_DU_JOUR) + timedelta(
            days=JOURS_AVANT_RAPPEL
        )
        self._creer_contrat(date_fin=date_cible)

        resultat = envoyer_rappels_paiement()

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ["jdupont@example.com"])
        self.assertIn("Bureau 101", email.body)
        self.assertIn("Jean", email.body)
        self.assertIn("1 rappel(s) envoyé(s)", resultat)

    @freeze_time(DATE_DU_JOUR)
    def test_ignore_contrat_non_valide(self):
        date_cible = date.fromisoformat(DATE_DU_JOUR) + timedelta(
            days=JOURS_AVANT_RAPPEL
        )
        self._creer_contrat(
            date_fin=date_cible, statut=Contrat.ContratStatus.EN_ATTENTE
        )

        resultat = envoyer_rappels_paiement()

        self.assertEqual(len(mail.outbox), 0)
        self.assertIn("0 rappel(s) envoyé(s)", resultat)

    @freeze_time(DATE_DU_JOUR)
    def test_ignore_contrat_inactif(self):
        date_cible = date.fromisoformat(DATE_DU_JOUR) + timedelta(
            days=JOURS_AVANT_RAPPEL
        )
        self._creer_contrat(date_fin=date_cible, actif=False)

        envoyer_rappels_paiement()

        self.assertEqual(len(mail.outbox), 0)

    @freeze_time(DATE_DU_JOUR)
    def test_ignore_contrat_hors_fenetre_de_rappel(self):
        # échéance dans 10 jours au lieu de 5 : ne doit pas être sélectionné
        date_cible = date.fromisoformat(DATE_DU_JOUR) + timedelta(days=10)
        self._creer_contrat(date_fin=date_cible)

        envoyer_rappels_paiement()

        self.assertEqual(len(mail.outbox), 0)

    @freeze_time(DATE_DU_JOUR)
    def test_ignore_client_sans_email(self):
        self.client_profile.user.email = ""
        self.client_profile.user.save()
        date_cible = date.fromisoformat(DATE_DU_JOUR) + timedelta(
            days=JOURS_AVANT_RAPPEL
        )
        self._creer_contrat(date_fin=date_cible)

        resultat = envoyer_rappels_paiement()

        self.assertEqual(len(mail.outbox), 0)
        self.assertIn("0 rappel(s) envoyé(s)", resultat)

    @freeze_time(DATE_DU_JOUR)
    def test_sujet_email_mentionne_la_periodicite(self):
        date_cible = date.fromisoformat(DATE_DU_JOUR) + timedelta(
            days=JOURS_AVANT_RAPPEL
        )
        self._creer_contrat(date_fin=date_cible, periodicite="TRIMESTRIEL")

        envoyer_rappels_paiement()

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("trimestriel", mail.outbox[0].subject.lower())

    @freeze_time(DATE_DU_JOUR)
    def test_plusieurs_contrats_generent_plusieurs_emails(self):
        date_cible = date.fromisoformat(DATE_DU_JOUR) + timedelta(
            days=JOURS_AVANT_RAPPEL
        )

        # deuxième client + bureau pour ne pas violer la contrainte d'unicité
        user2 = User.objects.create_user(
            username="marie", email="marie@example.com", first_name="Marie"
        )
        client2 = Client.objects.create(user=user2)
        bureau2 = Bureau.objects.create(
            numero="202", batiment=self.bureau.batiment, unite=10, espace=50
        )

        self._creer_contrat(date_fin=date_cible)
        Contrat.objects.create(
            client=client2,
            bureau=bureau2,
            periodicite="MENSUEL",
            statut=Contrat.ContratStatus.VALIDE,
            date_debut=date_cible - timedelta(days=30),
            date_fin=date_cible,
            is_active=True,
        )

        resultat = envoyer_rappels_paiement()

        self.assertEqual(len(mail.outbox), 2)
        self.assertIn("2 rappel(s) envoyé(s)", resultat)


class CommandeEnvoyerRappelsPaiementTestCase(TestCase):
    """Teste la commande de gestion qui appelle la tâche hors worker Celery."""

    def setUp(self):
        user = User.objects.create_user(
            username="jdupont", email="jdupont@example.com", first_name="Jean"
        )
        self.client_profile = Client.objects.create(user=user)
        admin_user = User.objects.create_user(username="admin_bat")
        batiment = Batiment.objects.create(
            user=admin_user, nom="Tour A", adresse="Rue X"
        )
        self.bureau = Bureau.objects.create(
            numero="101", batiment=batiment, unite=10, espace=100
        )

    @freeze_time(DATE_DU_JOUR)
    def test_commande_affiche_le_resultat(self):
        from io import StringIO

        from django.core.management import call_command

        date_cible = date.fromisoformat(DATE_DU_JOUR) + timedelta(
            days=JOURS_AVANT_RAPPEL
        )
        Contrat.objects.create(
            client=self.client_profile,
            bureau=self.bureau,
            periodicite="MENSUEL",
            statut=Contrat.ContratStatus.VALIDE,
            date_debut=date_cible - timedelta(days=30),
            date_fin=date_cible,
            is_active=True,
        )

        out = StringIO()
        call_command("envoyer_rappels_paiement", stdout=out)

        self.assertIn("rappel(s) envoyé(s)", out.getvalue())
        self.assertEqual(len(mail.outbox), 1)
