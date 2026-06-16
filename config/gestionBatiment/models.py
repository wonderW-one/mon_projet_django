from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField
from django.core.exceptions import ValidationError
from django.utils import timezone  # Ajouté pour gérer la date du jour
from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch import receiver

class Client(models.Model):
    class UserRole(models.TextChoices):
        ADMIN = 'ADMIN', _('Administrateur')
        TRAVAILLEUR = 'TRAVAILLEUR', _('Travailleur')
        MANAGER = 'MANAGER', _('Gestionnaire')
        CLIENT = 'CLIENT', _('Personnel')

    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name='client_profile')
    # Nouvelle catégorie pour gérer les permissions dans les views
    role = models.CharField(
        max_length=15,
        choices=UserRole.choices,
        default=UserRole.CLIENT
    )
    
    telephone = PhoneNumberField(region='CM', blank=True, null=True)
    addresse = models.CharField(max_length=255, blank=True, null=True)
    date_naissance = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


@receiver(post_save, sender=User)
def create_or_save_client_profile(sender, instance, created, **kwargs):
    """
    Dès qu'un User est créé, un Client est créé automatiquement avec le même ID.
    Si l'User est mis à jour, le Client est sauvegardé.
    """
    if created:
        Client.objects.create(user=instance)
    else:
        if hasattr(instance, 'client_profile'):
            instance.client_profile.save()



class Batiment(models.Model):
    id = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=100)
    adresse = models.CharField(max_length=50)
    nombre_etages = models.IntegerField(default=0)
    date_construction = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

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
            contrat__reservation__bureau__batiment=self,
            statut='PAID'
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
            contrat__reservation__bureau__niveau=self,
            statut='PAID'
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
    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE, related_name='contrat')
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='contrats')
    date_debut = models.DateField(null=True, blank=True)
    date_fin = models.DateField(null=True, blank=True)
    montant = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Contrat du {self.date_debut} au {self.date_fin} - {self.client.user.first_name} {self.client.user.last_name}"
    
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
        if self.montant is not None and self.montant <= Decimal('0.00'):
            raise ValidationError({'montant': _("Le montant du contrat doit être strictement supérieur à 0.")})
        if self.date_debut and self.date_fin and self.date_fin < self.date_debut:
            raise ValidationError({'date_fin': _("La date de fin doit être postérieure à la date de début.")})

    def save(self, *args, **kwargs):
        if self.date_debut and self.date_fin and self.reservation and self.reservation.bureau:
            delta = self.date_fin - self.date_debut
            nombre_jours = max(delta.days, 0)
            prix_bureau = self.reservation.bureau.prix or Decimal('0.00')
            self.montant = Decimal(nombre_jours) * prix_bureau
            
        self.full_clean()
        super().save(*args, **kwargs)


class Location(models.Model):
    id = models.AutoField(primary_key=True)
    bureau = models.ForeignKey(Bureau, on_delete=models.CASCADE, related_name='locations')
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='locations')
    date_debut = models.DateField(null=True, blank=True)
    date_fin = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Location du {self.date_debut} au {self.date_fin} - {self.client.user.first_name} {self.client.user.last_name}"

    # --- STATUT TEMPOREL DYNAMIQUE ---
    @property
    def statut_temporel(self):
        """ Détermine le statut de la location par rapport à la date réelle d'aujourd'hui """
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

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Paiement(models.Model):
    class PaiementStatus(models.TextChoices):
        PENDING = 'PENDING', _('En attente')
        COMPLETED = 'PAID', _('Payé')
        FAILED = 'FAILED', _('Échoué') 
        
    id = models.AutoField(primary_key=True)
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(null=True, blank=True)
    mode = models.CharField(max_length=20, choices=[('CASH', 'Espèces'), ('CARD', 'Carte bancaire'), ('TRANSFER', 'Virement bancaire')], default='CASH')
    
    # Relations connectées
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, related_name='paiements', null=True, blank=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='paiements')
    contrat = models.ForeignKey(Contrat, on_delete=models.CASCADE, related_name='paiements', null=True, blank=True)
    statut = models.CharField(max_length=20, choices=PaiementStatus.choices, default=PaiementStatus.PENDING)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Paiement de {self.montant}€ [{self.get_statut_display()}] - {self.client.user.first_name} {self.client.user.last_name}"

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

    def save(self, *args, **kwargs):
        # Récupérer l'utilisateur qui fait l'action (passé depuis la vue)
        user_performing_action = kwargs.pop('user', None)

        if user_performing_action and hasattr(user_performing_action, 'client_profile'):
            role_utilisateur = user_performing_action.client_profile.role
            
            # --- APPLICATION DE LA PROPOSITION 2 ---
            # Si le montant dépasse 100 000 CFA et que c'est un travailleur qui tente de valider directement en 'PAID'
            if self.montant > Decimal('100000.00') and role_utilisateur in ['AGENT', 'TRAVAILLEUR', 'MANAGER'] and self.statut == 'PAID':
                # On force le statut en attente de l'administrateur
                self.statut = self.PaiementStatus.PENDING_ADMIN
        self.full_clean()  
        super().save(*args, **kwargs)

    @property
    def reste_a_payer(self):
        if not self.contrat:
            return Decimal('0.00')

        paiements_valides = self.contrat.paiements.filter(statut='PAID') 
        if self.pk:
            paiements_valides = paiements_valides.exclude(pk=self.pk)

        total_deja_paye = sum(p.montant for p in paiements_valides)
        if self.statut == 'PAID':
            total_deja_paye += self.montant

        reste = self.contrat.montant - Decimal(str(total_deja_paye))
        return max(reste, Decimal('0.00'))