from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField
from django.core.exceptions import ValidationError
from decimal import Decimal
   
class Client(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='client_profile')
    telephone = PhoneNumberField(region='CM', blank=True, null=True)
    addresse = models.CharField(max_length=255, blank=True, null=True)
    date_naissance = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username
    
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
    
class Niveau(models.Model):
    id = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=50)
    batiment = models.ForeignKey(Batiment, on_delete=models.CASCADE, related_name='niveaux')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.nom
    
    
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
        return self.numero
    
    def save(self, *args, **kwargs):
        # Calculer l'espace en fonction du type de bureau
        self.prix = Decimal(str(self.espace)) * self.unite
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
    
    def clean(self):
        super().clean()
        
        # 1. Vérification de la cohérence des dates
        if self.date_debut and self.date_fin and self.date_fin < self.date_debut:
            raise ValidationError({'date_fin': _("La date de fin doit être postérieure à la date de début.")})

        # 2. Vérification de la disponibilité du bureau (anti-chevauchement)
        if self.date_debut and self.date_fin and self.bureau:
            # On cherche s'il existe une réservation existante sur les mêmes dates
            chevauchements = Reservation.objects.filter(
                bureau=self.bureau,
                is_active=True,                  
                date_debut__lt=self.date_fin,    
                date_fin__gt=self.date_debut     # Fin existante > Début demandé
            )
            
            # Exclure la réservation actuelle en cas de mise à jour (UPDATE)
            if self.pk:
                chevauchements = chevauchements.exclude(pk=self.pk)
                
            if chevauchements.exists():
                raise ValidationError({
                    'date_debut': _("Ce bureau est déjà réservé pour tout ou partie de ces dates.")
                })

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
    
    def clean(self):
        super().clean()
        # Validation du montant
        if self.montant is not None and self.montant <= Decimal('0.00'):
            raise ValidationError({
                'montant': _("Le montant du paiement doit être strictement supérieur à 0.")
            })
        # Validation des dates
        if self.date_debut and self.date_fin and self.date_fin < self.date_debut:
            raise ValidationError({'date_fin': _("La date de fin doit être postérieure à la date de début.")})

    def save(self, *args, **kwargs):
        self.full_clean()
        
        # CALCUL AUTOMATIQUE DU MONTANT
        if self.date_debut and self.date_fin and self.reservation and self.reservation.bureau:
            delta = self.date_fin - self.date_debut
            nombre_jours = max(delta.days, 0)
            # Utiliser Decimal pour le calcul et protéger contre une valeur prix nulle
            prix_bureau = self.reservation.bureau.prix or Decimal('0.00')
            montant_total = Decimal(nombre_jours) * prix_bureau
            self.montant = montant_total
            
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
    location = models.ForeignKey(Bureau, on_delete=models.CASCADE, related_name='paiements')
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='paiements')
    contrat = models.ForeignKey(Contrat, on_delete=models.CASCADE, related_name='paiements', null=True, blank=True)
    statut = models.CharField(max_length=20, choices=PaiementStatus.choices, default=PaiementStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Paiement de {self.montant}€ [{self.get_statut_display()}] - {self.client.user.first_name} {self.client.user.last_name}"

    # --- NOUVELLE VALIDATION AJOUTÉE ICI ---
    def clean(self):
        super().clean()
        # Vérifie si le montant existe et s'il est inférieur ou égal à 0
        if self.montant is not None and self.montant <= Decimal('0.00'):
            raise ValidationError({
                'montant': _("Le montant du paiement doit être strictement supérieur à 0.")
            })

    # --- FORCE LA VALIDATION AVANT CHAQUE SAVE ---
    def save(self, *args, **kwargs):
        self.full_clean()  # Déclenche automatiquement la méthode clean()
        super().save(*args, **kwargs)

    @property
    def reste_a_payer(self):
        """
        Calcule dynamiquement le reste à payer sur le contrat associé.
        """
        if not self.contrat:
            return Decimal('0.00')

        paiements_valides = self.contrat.paiements.filter(statut='PAID') 
        if self.pk:
            paiements_valides = paiements_valides.exclude(pk=self.pk)

        # 2. Somme des anciens paiements validés
        total_deja_paye = sum(p.montant for p in paiements_valides)
        # 3. Si le paiement actuel est EN COURS de validation (PAID), on l'ajoute aussi au calcul
        if self.statut == 'PAID':
            total_deja_paye += self.montant
        # 4. Calcul final
        reste = self.contrat.montant - Decimal(str(total_deja_paye))
        return max(reste, Decimal('0.00'))