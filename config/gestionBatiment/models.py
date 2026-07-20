from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models

# from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField


class BaseModel(models.Model):
    """Classe de base abstraite pour standardiser le soft-delete."""

    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class Client(BaseModel):  # Hérite désormais de BaseModel
    class UserRole(models.TextChoices):
        ADMIN = "ADMIN", _("Administrateur")
        TRAVAILLEUR = "TRAVAILLEUR", _("Travailleur")
        MANAGER = "MANAGER", _("Gestionnaire")
        CLIENT = "CLIENT", _("Client")

    id = models.AutoField(primary_key=True)
    # SÉCURITÉ : Passer en PROTECT pour préserver l'historique financier lié au profil
    user = models.OneToOneField(
        User, on_delete=models.PROTECT, related_name="client_profile"
    )
    role = models.CharField(
        max_length=15, choices=UserRole.choices, default=UserRole.CLIENT
    )

    telephone = PhoneNumberField(region="BI", blank=True, null=True)
    addresse = models.CharField(max_length=255, blank=True, null=True)
    date_naissance = models.DateField(blank=True, null=True)
    lieu_naissance = models.CharField(max_length=100, blank=True, null=True)
    nationalite = models.CharField(max_length=50, blank=True, null=True)
    profession = models.CharField(max_length=100, blank=True, null=True)

    TYPE_PIECE_CHOICES = [
        ("CNI", "Carte Nationale d'Identité"),
        ("PASSPORT", "Passeport"),
        ("PERMIS", "Permis de conduire"),
        ("ACTE_NAISSANCE", "Acte de naissance"),
        ("AUTRE", "Autre"),
    ]
    type_piece_identite = models.CharField(
        max_length=20, choices=TYPE_PIECE_CHOICES, blank=True, null=True
    )
    numero_piece_identite = models.CharField(max_length=50, blank=True, null=True)
    photo_profil = models.ImageField(upload_to="clients/photos/", blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Batiment(BaseModel):  # Hérite désormais de BaseModel
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    nom = models.CharField(max_length=100)
    adresse = models.CharField(max_length=50)
    nombre_etages = models.IntegerField(default=0)
    date_construction = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    proprietaire_nom = models.CharField(max_length=100, blank=True, null=True)
    proprietaire_prenom = models.CharField(max_length=100, blank=True, null=True)
    proprietaire_telephone = PhoneNumberField(region="BI", blank=True, null=True)
    proprietaire_email = models.EmailField(max_length=254, blank=True, null=True)
    proprietaire_adresse = models.CharField(max_length=255, blank=True, null=True)
    proprietaire_type_piece = models.CharField(
        max_length=20, choices=Client.TYPE_PIECE_CHOICES, blank=True, null=True
    )
    proprietaire_numero_piece = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.nom

    @property
    def taux_occupation(self):
        total_bureaux = self.bureaux.count()
        if total_bureaux == 0:
            return 0.0
        bureaux_occupes = (
            self.bureaux.filter(locations__is_active=True).distinct().count()
        )
        return round((bureaux_occupes / total_bureaux) * 100, 2)

    @property
    def revenues_totaux(self):
        return sum(
            p.montant
            for p in Paiement.objects.filter(statut="PAID").filter(
                models.Q(contrat__reservation__bureau__batiment=self)
                | models.Q(contrat__bureau__batiment=self)
            )
        )


class Niveau(BaseModel):  # Hérite désormais de BaseModel
    id = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=50)
    # SÉCURITÉ : Un bâtiment ne peut pas être supprimé s'il contient des niveaux configurés
    batiment = models.ForeignKey(
        Batiment, on_delete=models.PROTECT, related_name="niveaux"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.batiment.nom} - {self.nom}"

    @property
    def taux_occupation(self):
        total_bureaux = self.bureaux.count()
        if total_bureaux == 0:
            return 0.0
        bureaux_occupes = (
            self.bureaux.filter(locations__is_active=True).distinct().count()
        )
        return round((bureaux_occupes / total_bureaux) * 100)

    @property
    def revenues_totaux(self):
        return sum(
            p.montant
            for p in Paiement.objects.filter(statut="PAID").filter(
                models.Q(contrat__reservation__bureau__niveau=self)
                | models.Q(contrat__bureau__niveau=self)
            )
        )


class TypeBureau(BaseModel):  # Hérite désormais de BaseModel
    id = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nom


class Bureau(BaseModel):  # Hérite désormais de BaseModel
    class BureauStatus(models.TextChoices):
        DISPONIBLE = "DISPONIBLE", _("Disponible")
        OCCUPE = "OCCUPE", _("Occupé")

    id = models.AutoField(primary_key=True)
    numero = models.CharField(max_length=20)
    type = models.ForeignKey(
        TypeBureau,
        on_delete=models.SET_NULL,
        related_name="bureaux",
        null=True,
        blank=True,
    )
    unite = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    espace = models.FloatField(default=0.0)
    prix = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    # SÉCURITÉ : Un bâtiment ne peut pas être supprimé s'il possède des bureaux associés
    batiment = models.ForeignKey(
        Batiment, on_delete=models.PROTECT, related_name="bureaux"
    )
    niveau = models.ForeignKey(
        Niveau, on_delete=models.SET_NULL, related_name="bureaux", null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    statut = models.CharField(
        max_length=20, choices=BureauStatus.choices, default=BureauStatus.DISPONIBLE
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["batiment", "numero"], name="unique_numero_bureau_par_batiment"
            )
        ]

    def __str__(self):
        return f"Bureau {self.numero} ({self.type.nom if self.type else 'Sans type'})"

    def clean(self):
        super().clean()
        if self.unite is not None and self.unite < Decimal("0.00"):
            raise ValidationError(
                {
                    "unite": _(
                        "Le prix unitaire du bureau ne peut pas être inférieur à 0."
                    )
                }
            )
        if self.espace is not None and self.espace <= 0:
            raise ValidationError(
                {
                    "espace": _(
                        "L'espace du bureau doit être strictement supérieur à 0 m²."
                    )
                }
            )
        if self.niveau and self.batiment and self.niveau.batiment != self.batiment:
            raise ValidationError(
                {
                    "niveau": _(
                        f"Incohérence : Le niveau '{self.niveau.nom}' n'appartient pas au bâtiment '{self.batiment.nom}'."
                    )
                }
            )

    def save(self, *args, **kwargs):
        user_performing_action = kwargs.pop("user", None)
        if user_performing_action:
            self._history_user = user_performing_action
        self.prix = Decimal(str(self.espace)) * self.unite
        self.prix = self.prix.quantize(Decimal("0.01"))
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def date_disponibilite_prevue(self):
        """
        Calcule dynamiquement la date à laquelle le bureau sera libéré.
        Retourne None si le bureau est déjà DISPONIBLE.
        """
        if self.statut == self.BureauStatus.DISPONIBLE:
            return None

        aujourdhui = timezone.now().date()

        # On cherche la réservation active en cours sur ce bureau
        reservation_en_cours = (
            self.reservations.filter(
                is_active=True, date_debut__lte=aujourdhui, date_fin__gte=aujourdhui
            )
            .order_by("-date_fin")
            .first()
        )

        if reservation_en_cours and reservation_en_cours.date_fin:
            # Le lendemain de la fin de la réservation, le bureau est libre
            return reservation_en_cours.date_fin + timedelta(days=1)

        # Si pas de réservation mais statut occupé (ex: contrat direct)
        contrat_en_cours = (
            self.contrats_directs.filter(
                is_active=True, date_debut__lte=aujourdhui, date_fin__gte=aujourdhui
            )
            .order_by("-date_fin")
            .first()
        )

        if contrat_en_cours and contrat_en_cours.date_fin:
            return contrat_en_cours.date_fin + timedelta(days=1)

        return None


class Reservation(BaseModel):  # Hérite désormais de BaseModel
    class ReservationStatus(models.TextChoices):
        EN_ATTENTE = "EN_ATTENTE", _("En attente de validation")
        VALIDEE = "VALIDEE", _("Validée")
        REJETEE = "REJETEE", _("Rejetée")

    id = models.AutoField(primary_key=True)
    # ✅ AJOUT : workflow d'approbation. Par défaut VALIDEE (réservation créée par un
    # ADMIN/TRAVAILLEUR/MANAGER = confiance immédiate). Le save() ci-dessous force
    # EN_ATTENTE quand c'est un CLIENT qui crée la réservation.
    statut = models.CharField(
        max_length=20,
        choices=ReservationStatus.choices,
        default=ReservationStatus.VALIDEE,
    )
    date_debut = models.DateField(null=True, blank=True)
    date_fin = models.DateField(null=True, blank=True)
    # SÉCURITÉ : Bloquer la suppression d'un bureau s'il y a un historique de réservations
    bureau = models.ForeignKey(
        Bureau, on_delete=models.PROTECT, related_name="reservations"
    )
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # SÉCURITÉ : Bloquer la suppression du client pour préserver les réservations passées
    client = models.ForeignKey(
        Client, on_delete=models.PROTECT, related_name="reservations"
    )

    def __str__(self):
        return f"Réservation du {self.date_debut} au {self.date_fin} - {self.client.user.first_name} {self.client.user.last_name}"

    @property
    def statut_temporel(self):
        aujourdhui = timezone.now().date()
        if self.date_debut and aujourdhui < self.date_debut:
            return "À VENIR"
        elif (
            self.date_debut
            and self.date_fin
            and self.date_debut <= aujourdhui <= self.date_fin
        ):
            return "EN COURS"
        elif self.date_fin and aujourdhui > self.date_fin:
            return "EXPIRÉ"
        return "INCONNU"

    def clean(self):
        super().clean()
        if self.date_debut and self.date_fin and self.date_fin < self.date_debut:
            raise ValidationError(
                {
                    "date_fin": _(
                        "La date de fin doit être postérieure à la date de début."
                    )
                }
            )

        # ✅ CHANGEMENT DE RÈGLE MÉTIER : un bureau OCCUPE reste réservable pour une
        # période future, tant que les dates demandées ne chevauchent ni une
        # réservation VALIDEE existante, ni un contrat direct actif sur ce même
        # bureau (Contrat.bureau, location directe sans réservation). Le blocage
        # "bureau occupé" ne s'applique plus qu'à la LOCATION DIRECTE immédiate
        # (voir Contrat.clean()), jamais à une réservation pour plus tard.
        if self.date_debut and self.date_fin and self.bureau:
            chevauchements = Reservation.objects.filter(
                bureau=self.bureau,
                is_active=True,
                statut=self.ReservationStatus.VALIDEE,
                date_debut__lt=self.date_fin,
                date_fin__gt=self.date_debut,
            )
            if self.pk:
                chevauchements = chevauchements.exclude(pk=self.pk)
            if chevauchements.exists():
                raise ValidationError(
                    {
                        "date_debut": _(
                            "Ce bureau est déjà réservé pour tout ou partie de ces dates."
                        )
                    }
                )

            # 🔴 BUG CORRIGÉ : un bureau occupé via un CONTRAT DIRECT (location
            # directe, sans réservation liée) n'était jamais vérifié ici — seule
            # la table Reservation était consultée. Un client pouvait donc
            # réserver des dates qui chevauchaient une location directe en cours.
            chevauchements_contrat_direct = Contrat.objects.filter(
                bureau=self.bureau,
                is_active=True,
                statut=Contrat.ContratStatus.VALIDE,
                date_debut__lt=self.date_fin,
                date_fin__gt=self.date_debut,
            )
            if chevauchements_contrat_direct.exists():
                raise ValidationError(
                    {
                        "date_debut": _(
                            "Ce bureau est occupé par une location directe en cours sur "
                            "tout ou partie de ces dates."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        user_performing_action = kwargs.pop("user", None)
        if user_performing_action:
            self._history_user = user_performing_action

        # ✅ CHANGEMENT DE RÈGLE MÉTIER : les réservations ne passent plus par un
        # workflow d'approbation. Qu'elle soit créée par un CLIENT ou par un
        # ADMIN/TRAVAILLEUR/MANAGER, une réservation est désormais confirmée
        # immédiatement (statut par défaut VALIDEE). Elle reste annulable à tout
        # moment par le client (voir ReservationViewSet.annuler).
        #
        # ⚠️ En revanche, le CONTRAT qui découle d'une réservation (conversion en
        # location active) continue lui d'exiger une validation explicite d'un
        # ADMIN/TRAVAILLEUR/MANAGER — voir ReservationViewSet.convertir_contrat et
        # Contrat.save(). On ne "débloque" donc que la réservation, jamais le
        # contrat qui en découle.

        self.full_clean()
        super().save(*args, **kwargs)


class Contrat(BaseModel):
    class ContratStatus(models.TextChoices):
        EN_ATTENTE = "EN_ATTENTE", _("En attente de validation")
        VALIDE = "VALIDE", _("Validé")
        REJETE = "REJETE", _("Rejeté")

    id = models.AutoField(primary_key=True)
    reservation = models.OneToOneField(
        Reservation,
        on_delete=models.PROTECT,
        related_name="contrat",
        blank=True,
        null=True,
    )
    bureau = models.ForeignKey(
        "Bureau",
        on_delete=models.PROTECT,
        related_name="contrats_directs",
        blank=True,
        null=True,
    )
    client = models.ForeignKey(
        Client, on_delete=models.PROTECT, related_name="contrats"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contrats_crees",
    )
    statut = models.CharField(
        max_length=20, choices=ContratStatus.choices, default=ContratStatus.VALIDE
    )  # AJOUT
    date_debut = models.DateField(null=True, blank=True)
    date_fin = models.DateField(null=True, blank=True)
    date_paiement = models.DateField(null=True, blank=True)
    montant = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    description = models.TextField(blank=True, null=True)
    document_contrat_signe = models.FileField(
        upload_to="contrats/documents/", blank=True, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    PERIODICITE_CHOICES = [
        ("MENSUEL", "Mensuel"),
        ("TRIMESTRIEL", "Trimestriel"),
        ("SEMESTRIEL", "Semestriel"),
    ]
    periodicite = models.CharField(
        max_length=20, choices=PERIODICITE_CHOICES, default="MENSUEL"
    )

    def __str__(self):
        return f"Contrat du {self.date_debut} au {self.date_fin}"

    @property
    def bureau_effectif(self):
        if self.reservation and self.reservation.bureau:
            return self.reservation.bureau
        return self.bureau

    @property
    def statut_temporel(self):
        aujourdhui = timezone.now().date()
        if self.date_debut and aujourdhui < self.date_debut:
            return "À VENIR"
        elif (
            self.date_debut
            and self.date_fin
            and self.date_debut <= aujourdhui <= self.date_fin
        ):
            return "EN COURS"
        elif self.date_fin and aujourdhui > self.date_fin:
            return "EXPIRÉ"
        return "INCONNU"

    def clean(self):
        super().clean()
        if self.date_debut and self.date_fin and self.date_fin < self.date_debut:
            raise ValidationError(
                {
                    "date_fin": _(
                        "La date de fin doit être postérieure à la date de début."
                    )
                }
            )

        if not self.reservation and not self.bureau:
            raise ValidationError(
                {
                    "bureau": _(
                        "Un contrat doit être lié à une réservation ou à un bureau (location directe)."
                    )
                }
            )
        if self.reservation and self.bureau:
            raise ValidationError(
                {
                    "bureau": _(
                        "Un contrat ne peut pas avoir à la fois une réservation et un bureau direct."
                    )
                }
            )

        if self.reservation:
            res = self.reservation
            if self.client is None and res.client_id:
                self.client = res.client
            if self.date_debut and res.date_debut and res.date_fin:
                if not (res.date_debut <= self.date_debut <= res.date_fin):
                    raise ValidationError(
                        {
                            "date_debut": _(
                                "La date de début du contrat doit être comprise dans l'intervalle de la réservation."
                            )
                        }
                    )
        else:
            if (
                self.bureau
                and self.bureau.statut == Bureau.BureauStatus.OCCUPE
                and not self.pk
            ):
                raise ValidationError({"bureau": _("Ce bureau n'est pas disponible.")})

    def save(self, *args, **kwargs):
        user_performing_action = kwargs.pop("user", None)
        if user_performing_action:
            self._history_user = user_performing_action
        if user_performing_action and not self.created_by_id:
            self.created_by = user_performing_action

        # Si c'est un CLIENT qui crée une demande de location directe (pas de réservation liée)
        if (
            not self.pk
            and user_performing_action
            and hasattr(user_performing_action, "client_profile")
        ):
            role_utilisateur = user_performing_action.client_profile.role
            if (
                role_utilisateur == "CLIENT"
                and self.bureau_id
                and not self.reservation_id
            ):
                self.statut = self.ContratStatus.EN_ATTENTE
                self.date_debut = (
                    None  # sera fixée à la validation, le jour de la signature
                )

        bureau = self.bureau_effectif
        periodicite = self.periodicite or "MENSUEL"
        prix_bureau = bureau.prix if bureau and bureau.prix else Decimal("0.00")

        if periodicite == "MENSUEL":
            self.montant = prix_bureau * Decimal("30.00")
        elif periodicite == "TRIMESTRIEL":
            self.montant = prix_bureau * Decimal("90.00")
        elif periodicite == "SEMESTRIEL":
            self.montant = prix_bureau * Decimal("180.00")
        else:
            self.montant = prix_bureau * Decimal("30.00")

        self.montant = self.montant.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        self.full_clean()
        super().save(*args, **kwargs)


class Location(BaseModel):  # Hérite désormais de BaseModel
    id = models.AutoField(primary_key=True)
    # SÉCURITÉ : Impossible de supprimer le bureau physique s'il est au cœur d'une location en cours/passée
    bureau = models.ForeignKey(
        Bureau, on_delete=models.PROTECT, related_name="locations"
    )
    # SÉCURITÉ : Empêcher la destruction d'un profil client s'il a des locations enregistrées
    client = models.ForeignKey(
        Client, on_delete=models.PROTECT, related_name="locations"
    )
    # SÉCURITÉ : Le contrat cadre protège la location
    contrat = models.ForeignKey(
        Contrat, on_delete=models.PROTECT, related_name="locations"
    )
    date_debut = models.DateField(null=True, blank=True)
    date_fin = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Location du {self.date_debut} au {self.date_fin} - {self.client.user.first_name} {self.client.user.last_name}"

    @property
    def statut_temporel(self):
        aujourdhui = timezone.now().date()
        if self.contrat.date_debut and aujourdhui < self.contrat.date_debut:
            return "À VENIR"
        elif (
            self.contrat.date_debut
            and self.contrat.date_fin
            and self.contrat.date_debut <= aujourdhui <= self.contrat.date_fin
        ):
            return "EN COURS"
        elif self.contrat.date_fin and aujourdhui > self.contrat.date_fin:
            return "EXPIRÉ"
        return "INCONNU"

    def clean(self):
        super().clean()
        if (
            self.contrat.date_debut
            and self.contrat.date_fin
            and self.contrat.date_fin < self.contrat.date_debut
        ):
            raise ValidationError(
                {
                    "date_fin": _(
                        "La date de fin doit être postérieure à la date de début."
                    )
                }
            )
        if (
            self.contrat.bureau_effectif
            and self.bureau_id != self.contrat.bureau_effectif.id
        ):
            raise ValidationError(
                {
                    "bureau": _(
                        "Le bureau de la location ne correspond pas à celui du contrat."
                    )
                }
            )

    def save(self, *args, **kwargs):
        if self.contrat and not self.date_debut:
            self.date_debut = self.contrat.date_debut
        if self.contrat and not self.date_fin:
            self.date_fin = self.contrat.date_fin
        self.full_clean()
        super().save(*args, **kwargs)


class Paiement(BaseModel):  # Hérite désormais de BaseModel
    class PaiementStatus(models.TextChoices):
        PENDING = "PENDING", _("En attente")
        COMPLETED = "PAID", _("Payé")
        PENDING_ADMIN = "PENDING_ADMIN", _("En attente administrateur")
        FAILED = "FAILED", _("Échoué")

    CHOIX_MOIS = [
        (1, "Janvier"),
        (2, "Février"),
        (3, "Mars"),
        (4, "Avril"),
        (5, "Mai"),
        (6, "Juin"),
        (7, "Juillet"),
        (8, "Août"),
        (9, "Septembre"),
        (10, "Octobre"),
        (11, "Novembre"),
        (12, "Décembre"),
    ]

    id = models.AutoField(primary_key=True)
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)

    mois_paye = models.IntegerField(choices=CHOIX_MOIS, null=True, blank=False)
    annee_paye = models.IntegerField(default=2026, null=True, blank=False)

    mode = models.CharField(
        max_length=20,
        choices=[
            ("CASH", "Espèces"),
            ("CARD", "Carte bancaire"),
            ("TRANSFER", "Virement bancaire"),
        ],
        default="CASH",
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="paiements_crees",
    )

    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        related_name="paiements",
        null=True,
        blank=True,
    )
    # SÉCURITÉ : Un flux d'argent encaissé implique une interdiction stricte de supprimer le client
    client = models.ForeignKey(
        Client, on_delete=models.PROTECT, related_name="paiements"
    )
    # SÉCURITÉ : Garder le contrat intact pour justifier comptablement le paiement perçu
    contrat = models.ForeignKey(
        Contrat,
        on_delete=models.PROTECT,
        related_name="paiements",
        null=True,
        blank=True,
    )
    statut = models.CharField(
        max_length=20, choices=PaiementStatus.choices, default=PaiementStatus.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("contrat", "mois_paye", "annee_paye")

    def __str__(self):
        mois_str = self.get_mois_paye_display() if self.mois_paye else "Inconnu"
        return f"Paiement {mois_str} {self.annee_paye} ({self.montant} CFA) - {self.client.user.first_name}"

    def clean(self):
        super().clean()
        if self.montant is not None and self.montant <= Decimal("0.00"):
            raise ValidationError(
                {
                    "montant": _(
                        "Le montant du paiement doit être strictement supérieur à 0."
                    )
                }
            )

        # ✅ AJOUT : impossible de créer/modifier un paiement tant que le contrat
        # associé n'est pas VALIDE (approuvé par un ADMIN/TRAVAILLEUR/MANAGER).
        if self.contrat and self.contrat.statut != Contrat.ContratStatus.VALIDE:
            raise ValidationError(
                {
                    "contrat": _(
                        "Impossible d'enregistrer un paiement : ce contrat n'a pas encore été approuvé."
                    )
                }
            )

        if self.contrat and self.contrat.statut_temporel == "EXPIRÉ":
            raise ValidationError(
                {
                    "contrat": _(
                        "Impossible d'enregistrer un paiement pour un contrat expiré."
                    )
                }
            )

        if self.location and self.location.statut_temporel == "EXPIRÉ":
            raise ValidationError(
                {
                    "location": _(
                        "Impossible d'enregistrer un paiement pour une location expirée."
                    )
                }
            )

        if self.statut == self.PaiementStatus.COMPLETED and self.contrat:
            reste = self.reste_a_payer
            if reste <= Decimal("0.00"):
                raise ValidationError(
                    {"montant": _("Ce contrat est déjà totalement payé.")}
                )
            if self.montant > reste:
                raise ValidationError(
                    {
                        "montant": _(
                            f"Le montant soumis dépasse le reste à payer ({reste} FBU)."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        user_performing_action = kwargs.pop("user", None)
        if user_performing_action:
            self._history_user = user_performing_action
        if user_performing_action and not self.created_by_id:
            self.created_by = user_performing_action

        if user_performing_action and hasattr(user_performing_action, "client_profile"):
            role_utilisateur = user_performing_action.client_profile.role
            if role_utilisateur in ["TRAVAILLEUR", "MANAGER"] and self.statut == "PAID":
                self.statut = self.PaiementStatus.PENDING_ADMIN
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def loyer_mensuel_prevu_30_jours(self):
        bureau = None
        if self.location and self.location.bureau:
            bureau = self.location.bureau
        elif self.contrat:
            bureau = self.contrat.bureau_effectif

        if bureau and bureau.prix:
            return bureau.prix * 30
        return Decimal("0.00")

    @property
    def reste_a_payer(self):
        if not self.contrat or self.contrat.montant is None:
            return Decimal("0.00")
        loyer_attendu = self.contrat.montant  # ✅ tient compte de la périodicité

        autres_paiements = Paiement.objects.filter(
            contrat=self.contrat, statut="PAID", is_active=True
        )
        if self.pk:
            autres_paiements = autres_paiements.exclude(pk=self.pk)

        total_deja_paye = sum(p.montant for p in autres_paiements)
        if self.statut == "PAID":
            total_deja_paye += self.montant
        return max(loyer_attendu - total_deja_paye, Decimal("0.00"))
