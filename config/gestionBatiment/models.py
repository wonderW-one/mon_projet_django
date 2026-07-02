from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q

class Client(models.Model):
    class UserRole(models.TextChoices):
        ADMIN = 'ADMIN', _('Administrateur')
        TRAVAILLEUR = 'TRAVAILLEUR', _('Travailleur')
        MANAGER = 'MANAGER', _('Gestionnaire')
        CLIENT = 'CLIENT', _('Client')

    id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='client_profile')

    # Nouvelle catégorie pour gérer les permissions dans les views
    role = models.CharField(
        max_length=15,
        choices=UserRole.choices,
        default=UserRole.CLIENT
    )
    
    telephone = PhoneNumberField(region='CM', blank=True, null=True)
    addresse = models.CharField(max_length=255, blank=True, null=True)
    date_naissance = models.DateField(blank=True, null=True)
    lieu_naissance = models.CharField(max_length=100, blank=True, null=True)
    nationalite = models.CharField(max_length=50, blank=True, null=True)
    profession = models.CharField(max_length=100, blank=True, null=True)

    TYPE_PIECE_CHOICES = [
        ('CNI', 'Carte Nationale d\'Identité'),
        ('PASSPORT', 'Passeport'),
        ('PERMIS', 'Permis de conduire'),
        ('ACTE_NAISSANCE', 'Acte de naissance'),
        ('AUTRE', 'Autre'),
    ]
    type_piece_identite = models.CharField(max_length=20, choices=TYPE_PIECE_CHOICES, blank=True, null=True)
    numero_piece_identite = models.CharField(max_length=50, blank=True, null=True)
    photo_profil = models.ImageField(upload_to='clients/photos/', blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username
       
    

class Batiment(models.Model):
    id = models.AutoField(primary_key=True)
    user= models.ForeignKey(settings.AUTH_USER_MODEL,on_delete =models.CASCADE)
    nom = models.CharField(max_length=100)
    adresse = models.CharField(max_length=50)
    nombre_etages = models.IntegerField(default=0)
    date_construction = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    proprietaire_nom = models.CharField(max_length=100, blank=True, null=True)
    proprietaire_prenom = models.CharField(max_length=100, blank=True, null=True)
    proprietaire_telephone = PhoneNumberField(region='CM', blank=True, null=True)
    proprietaire_email = models.EmailField(max_length=254, blank=True, null=True)
    proprietaire_adresse = models.CharField(max_length=255, blank=True, null=True)
    proprietaire_type_piece = models.CharField(max_length=20, choices=Client.TYPE_PIECE_CHOICES, blank=True, null=True)
    proprietaire_numero_piece = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    PERIODICITE_CHOICES = [
        ('MENSUEL', 'Mensuel'),
        ('TRIMESTRIEL', 'Trimestriel'),
        ('SEMESTRIEL', 'Semestriel'),
    ]
    periodicite = models.CharField(max_length=20, choices=PERIODICITE_CHOICES, default='MENSUEL')
    def __str__(self):
        return self.nom

    @property
    def taux_occupation(self):
        total_bureaux = self.bureaux.count()
        if total_bureaux == 0:
            return 0.0
        bureaux_occupes = self.bureaux.filter(locations__is_active=True).distinct().count()
        return round((bureaux_occupes / total_bureaux) * 100, 2)

    @property
    def revenues_totaux(self):
        return sum(p.montant for p in Paiement.objects.filter(
            statut='PAID'
        ).filter(
            models.Q(contrat__reservation__bureau__batiment=self) |
            models.Q(contrat__bureau__batiment=self)
        ))


class Niveau(models.Model):
    id = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=50)
    batiment = models.ForeignKey(Batiment, on_delete=models.CASCADE, related_name='niveaux')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.batiment.nom} - {self.nom}"

    @property
    def taux_occupation(self):
        total_bureaux = self.bureaux.count()
        if total_bureaux == 0:
            return 0.0
        bureaux_occupes = self.bureaux.filter(locations__is_active=True).distinct().count()
        return round((bureaux_occupes / total_bureaux) * 100)

    @property
    def revenues_totaux(self):
        return sum(p.montant for p in Paiement.objects.filter(
            statut='PAID'
        ).filter(
            models.Q(contrat__reservation__bureau__niveau=self) |
            models.Q(contrat__bureau__niveau=self)
        ))
    
    
class TypeBureau(models.Model):
    id = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.nom
    

class Bureau(models.Model):
    class BureauStatus(models.TextChoices):
        DISPONIBLE = 'DISPONIBLE', _('Disponible')
        OCCUPE = 'OCCUPE', _('Occupé')

    id = models.AutoField(primary_key=True)
    numero = models.CharField(max_length=20)
    type = models.ForeignKey(TypeBureau, on_delete=models.CASCADE, related_name='bureaux', null=True, blank=True)
    unite = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    espace = models.FloatField(default=0.0)
    prix = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    batiment = models.ForeignKey(Batiment, on_delete=models.CASCADE, related_name='bureaux')
    niveau = models.ForeignKey(Niveau, on_delete=models.CASCADE, related_name='bureaux', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    statut = models.CharField(max_length=20, choices=BureauStatus.choices, default=BureauStatus.DISPONIBLE)
    

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['batiment', 'numero'], name='unique_numero_bureau_par_batiment')
        ]

    def __str__(self):
        return f"Bureau {self.numero} ({self.type.nom if self.type else 'Sans type'})"
    
    def clean(self):
        super().clean()
        if self.unite is not None and self.unite < Decimal('0.00'):
            raise ValidationError({'unite': _("Le prix unitaire du bureau ne peut pas être inférieur à 0.")})
        if self.espace is not None and self.espace <= 0:
            raise ValidationError({'espace': _("L'espace du bureau doit être strictement supérieur à 0 m².")})
        if self.niveau and self.batiment and self.niveau.batiment != self.batiment:
            raise ValidationError({
                'niveau': _(f"Incohérence : Le niveau '{self.niveau.nom}' n'appartient pas au bâtiment '{self.batiment.nom}'.")
            })

    def save(self, *args, **kwargs):
        user_performing_action = kwargs.pop('user', None)
        if user_performing_action:
            self._history_user = user_performing_action
        self.prix = Decimal(str(self.espace)) * self.unite
        self.prix = self.prix.quantize(Decimal('0.01'))
        self.full_clean()
        super().save(*args, **kwargs)
    

class Reservation(models.Model):
    id = models.AutoField(primary_key=True)
    date_debut = models.DateField(null=True, blank=True)
    date_fin = models.DateField(null=True, blank=True)
    bureau = models.ForeignKey(Bureau, on_delete=models.CASCADE, related_name='reservations')
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='reservations')
    
    def __str__(self):
        return f"Réservation du {self.date_debut} au {self.date_fin} - {self.client.user.first_name} {self.client.user.last_name}"
    
    # --- STATUT TEMPOREL DYNAMIQUE ---
    @property
    def statut_temporel(self):
        aujourdhui = timezone.now().date()
        if self.date_debut and aujourdhui < self.date_debut:
            return "À VENIR"
        elif self.date_debut and self.date_fin and self.date_debut <= aujourdhui <= self.date_fin:
            return "EN COURS"
        elif self.date_fin and aujourdhui > self.date_fin:
            return "EXPIRÉ"
        return "INCONNU"

    def clean(self):
        super().clean()
        if self.date_debut and self.date_fin and self.date_fin < self.date_debut:
            raise ValidationError ({'date_fin': _("La date de fin doit être postérieure à la date de début.")})
        
# pour concerve les dates de reservation coherentes et eviter les conflits de reservation

        if self.date_debut and self.date_fin and self.bureau:
            chevauchements = Reservation.objects.filter(
                bureau=self.bureau,
                is_active=True,                  
                date_debut__lt=self.date_fin,    
                date_fin__gt=self.date_debut     
            )
            if self.pk:
                chevauchements = chevauchements.exclude(pk=self.pk)
            if chevauchements.exists():
                raise ValidationError({'date_debut': _("Ce bureau est déjà réservé pour tout ou partie de ces dates.")})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
         
class Contrat(models.Model):
    id = models.AutoField(primary_key=True)
    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE, related_name='contrat', blank=True, null=True)
    bureau = models.ForeignKey('Bureau', on_delete=models.PROTECT, related_name='contrats_directs', blank=True, null=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='contrats')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='contrats_crees')
    date_debut = models.DateField(null=True, blank=True)
    date_fin = models.DateField(null=True, blank=True)
    date_paiement = models.DateField(null=True, blank=True)
    montant = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    document_contrat_signe = models.FileField(upload_to='contrats/documents/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Contrat du {self.date_debut} au {self.date_fin}"

    @property
    def bureau_effectif(self):
        """Le bureau concerné, qu'il vienne d'une réservation ou d'une location directe."""
        if self.reservation and self.reservation.bureau:
            return self.reservation.bureau
        return self.bureau

    @property
    def statut_temporel(self):
        aujourdhui = timezone.now().date()
        if self.date_debut and aujourdhui < self.date_debut:
            return "À VENIR"
        elif self.date_debut and self.date_fin and self.date_debut <= aujourdhui <= self.date_fin:
            return "EN COURS"
        elif self.date_fin and aujourdhui > self.date_fin:
            return "EXPIRÉ"
        return "INCONNU"

    def clean(self):
        super().clean()
        if self.date_debut and self.date_fin and self.date_fin < self.date_debut:
            raise ValidationError({'date_fin': _("La date de fin doit être postérieure à la date de début.")})

        # NOUVEAU : il faut soit une réservation, soit un bureau direct — jamais les deux, jamais ni l'un ni l'autre
        if not self.reservation and not self.bureau:
            raise ValidationError({'bureau': _("Un contrat doit être lié à une réservation ou à un bureau (location directe).")})
        if self.reservation and self.bureau:
            raise ValidationError({'bureau': _("Un contrat ne peut pas avoir à la fois une réservation et un bureau direct.")})

        if self.reservation:
            res = self.reservation
            if self.client is None and res.client_id:
                self.client = res.client
            if self.date_debut and res.date_debut and res.date_fin:
                if not (res.date_debut <= self.date_debut <= res.date_fin):
                    raise ValidationError({'date_debut': _("La date de début du contrat doit être comprise dans l'intervalle de la réservation.")})
        else:
            # Location directe : le bureau doit être disponible
            if self.bureau and self.bureau.statut == Bureau.BureauStatus.OCCUPE and not self.pk:
                raise ValidationError({'bureau': _("Ce bureau n'est pas disponible.")})

    def save(self, *args, **kwargs):
        user_performing_action = kwargs.pop('user', None)
        if user_performing_action:
            self._history_user = user_performing_action
        if user_performing_action and not self.created_by_id:
            self.created_by = user_performing_action

        bureau = self.bureau_effectif
        periodicite = bureau.batiment.periodicite if bureau and bureau.batiment else 'MENSUEL'
        prix_bureau = bureau.prix if bureau and bureau.prix else Decimal('0.00')

        if periodicite == 'MENSUEL':
            self.montant = prix_bureau * Decimal('30.00')
        elif periodicite == 'TRIMESTRIEL':
            self.montant = prix_bureau * Decimal('90.00')
        elif periodicite == 'SEMESTRIEL':
            self.montant = prix_bureau * Decimal('180.00')
        else:
            self.montant = prix_bureau * Decimal('30.00')

        self.montant = self.montant.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.full_clean()
        super().save(*args, **kwargs)


class Location(models.Model):
    id = models.AutoField(primary_key=True)
    bureau = models.ForeignKey(Bureau, on_delete=models.CASCADE, related_name='locations')
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='locations')
    contrat = models.ForeignKey(Contrat, on_delete=models.CASCADE, related_name="locations")  # ← plus null=True, blank=True
    date_debut = models.DateField(null=True, blank=True)
    date_fin = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Location du {self.date_debut} au {self.date_fin} - {self.client.user.first_name} {self.client.user.last_name}"

    @property
    def statut_temporel(self):
        """ contrat est garanti non-null : on peut y accéder directement """
        aujourdhui = timezone.now().date()
        if self.contrat.date_debut and aujourdhui < self.contrat.date_debut:
            return "À VENIR"
        elif self.contrat.date_debut and self.contrat.date_fin and self.contrat.date_debut <= aujourdhui <= self.contrat.date_fin:
            return "EN COURS"
        elif self.contrat.date_fin and aujourdhui > self.contrat.date_fin:
            return "EXPIRÉ"
        return "INCONNU"

    def clean(self):
        super().clean()
        if self.contrat.date_debut and self.contrat.date_fin and self.contrat.date_fin < self.contrat.date_debut:
            raise ValidationError({'date_fin': _("La date de fin doit être postérieure à la date de début.")})
        # NOUVEAU : cohérence bureau ↔ contrat
        if self.contrat.bureau_effectif and self.bureau_id != self.contrat.bureau_effectif.id:
            raise ValidationError({'bureau': _("Le bureau de la location ne correspond pas à celui du contrat.")})

    def save(self, *args, **kwargs):
        if self.contrat and not self.date_debut:
            self.date_debut = self.contrat.date_debut
        if self.contrat and not self.date_fin:
            self.date_fin = self.contrat.date_fin
        self.full_clean()
        super().save(*args, **kwargs)

class Paiement(models.Model):
    class PaiementStatus(models.TextChoices):
        PENDING = 'PENDING', _('En attente')
        COMPLETED = 'PAID', _('Payé')
        PENDING_ADMIN = 'PENDING_ADMIN', _('En attente administrateur')
        FAILED = 'FAILED', _('Échoué')

    CHOIX_MOIS = [
        (1, 'Janvier'), (2, 'Février'), (3, 'Mars'), (4, 'Avril'),
        (5, 'Mai'), (6, 'Juin'), (7, 'Juillet'), (8, 'Août'),
        (9, 'Septembre'), (10, 'Octobre'), (11, 'Novembre'), (12, 'Décembre')
    ]

    id = models.AutoField(primary_key=True)
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(null=True, blank=True)
    
    mois_paye = models.IntegerField(choices=CHOIX_MOIS, null=True, blank=False)
    annee_paye = models.IntegerField(default=2026, null=True, blank=False)
    
    mode = models.CharField(max_length=20, choices=[('CASH', 'Espèces'), ('CARD', 'Carte bancaire'), ('TRANSFER', 'Virement bancaire')], default='CASH')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='paiements_crees')
    
    # Relations connectées
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, related_name='paiements', null=True, blank=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='paiements')
    contrat = models.ForeignKey(Contrat, on_delete=models.CASCADE, related_name='paiements', null=True, blank=True)
    statut = models.CharField(max_length=20, choices=PaiementStatus.choices, default=PaiementStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        # Sécurité : un même contrat ne peut pas recevoir 2 paiements validés pour le même mois de la même année
        unique_together = ('contrat', 'mois_paye', 'annee_paye')

    def __str__(self):
        mois_str = self.get_mois_paye_display() if self.mois_paye else "Inconnu"
        return f"Paiement {mois_str} {self.annee_paye} ({self.montant} CFA) - {self.client.user.first_name}"

    
    # --- SÉCURITÉ DE PAIEMENT BASÉE SUR LES STATUTS TEMPORELS ---
    
    def clean(self):
        super().clean()
        if self.montant is not None and self.montant <= Decimal('0.00'):
            raise ValidationError({'montant': _("Le montant du paiement doit être strictement supérieur à 0.")})

        # Sécurité : Empêcher d'encaisser de l'argent sur un contrat ou une location EXPIRÉ(E)
        if self.contrat and self.contrat.statut_temporel == "EXPIRÉ":
            raise ValidationError({'contrat': _("Impossible d'enregistrer un paiement pour un contrat expiré.")})
            
        if self.location and self.location.statut_temporel == "EXPIRÉ":
            raise ValidationError({'location': _("Impossible d'enregistrer un paiement pour une location expirée.")})

        if self.statut == self.PaiementStatus.COMPLETED and self.contrat:
            reste = self.reste_a_payer
            if reste <= Decimal('0.00'):
                raise ValidationError({'montant': _("Ce contrat est déjà totalement payé.")})
            if self.montant > reste:
                raise ValidationError({'montant': _(f"Le montant soumis dépasse le reste à payer ({reste} FBU).")})

    def save(self, *args, **kwargs):
        # Récupérer l'utilisateur qui fait l'action (passé depuis la vue)
        user_performing_action = kwargs.pop('user', None)
        if user_performing_action:
            self._history_user = user_performing_action
        if user_performing_action and not self.created_by_id:
            self.created_by = user_performing_action

        if user_performing_action and hasattr(user_performing_action, 'client_profile'):
            role_utilisateur = user_performing_action.client_profile.role
            
            # --- APPLICATION DE LA PROPOSITION 2 ---
            # Si le montant dépasse 100 000 CFA et que c'est un travailleur qui tente de valider directement en 'PAID'
            if role_utilisateur in ['TRAVAILLEUR' , 'MANAGER'] and self.statut == 'PAID':
                # On force le statut en attente de l'administrateur
                self.statut = self.PaiementStatus.PENDING_ADMIN
        self.full_clean()  
        super().save(*args, **kwargs)
        
        
    @property
    def loyer_mensuel_prevu_30_jours(self):
        """ Va chercher le prix du bureau et fait : prix * 30 jours """
        bureau = None
        if self.location and self.location.bureau:
            bureau = self.location.bureau
        elif self.contrat:
            bureau = self.contrat.bureau_effectif

        if bureau and bureau.prix:
            return bureau.prix * 30
        return Decimal('0.00')
    @property
    def reste_a_payer(self):
        """ Calcule le reste de montant qu'on va paie"""
        loyer_attendu = self.loyer_mensuel_prevu_30_jours
        if loyer_attendu == Decimal('0.00'):
            return Decimal('0.00')

        # On fait la somme de ce que le client a versé CE MOIS-CI pour ce contrat
        autres_paiements = Paiement.objects.filter(
            contrat=self.contrat,
            statut='PAID',
            mois_paye=self.mois_paye,
            annee_paye=self.annee_paye
        )
        
        if self.pk:
            autres_paiements = autres_paiements.exclude(pk=self.pk)

        total_deja_paye_ce_mois = sum(p.montant for p in autres_paiements)
        
        # On ajoute le montant de ce paiement-ci s'il est validé
        if self.statut == 'PAID':
            total_deja_paye_ce_mois += self.montant

        # Le reste = (Prix Bureau * 30) - Ce qui a été payé ce mois-ci
        reste = loyer_attendu - total_deja_paye_ce_mois
        return max(reste, Decimal('0.00'))
    