from django.contrib import admin
from .models import Client, Niveau, TypeBureau, Batiment, Bureau, Paiement, Reservation, Contrat, Location

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    # CORRECTION : On utilise les méthodes personnalisées (get_first_name...) au lieu de user__first_name
    list_display = ('id', 'user__id', 'get_first_name', 'get_last_name', 'telephone', 'addresse', 'date_naissance', 'created_at')
    search_fields = ('user__first_name', 'user__last_name', 'user__username', 'telephone')
    list_filter = ('created_at',)
    
    # Amélioration de l'affichage des méthodes dans l'admin
    def get_first_name(self, obj):
        return obj.user.first_name
    get_first_name.short_description = 'Prénom'

    def get_last_name(self, obj):
        return obj.user.last_name
    get_last_name.short_description = 'Nom'


@admin.register(Batiment)
class BatimentAdmin(admin.ModelAdmin):
    # AJOUT : 'taux_occupation' et 'revenues_totaux' visibles en direct
    list_display = ('id', 'nom', 'adresse', 'nombre_etages', 'taux_occupation_visuel', 'revenues_totaux_visuel', 'is_active')
    search_fields = ('nom', 'adresse')
    list_filter = ('is_active', 'created_at')
    
    def taux_occupation_visuel(self, obj):
        return f"{obj.taux_occupation}%"
    taux_occupation_visuel.short_description = "Taux d'occupation"

    def revenues_totaux_visuel(self, obj):
        return f"{obj.revenues_totaux} CFA"
    revenues_totaux_visuel.short_description = "Revenus encaissés"


@admin.register(Niveau)
class NiveauAdmin(admin.ModelAdmin):
    # AJOUT : 'taux_occupation' et 'revenues_totaux' par étage
    list_display = ('id', 'nom', 'batiment', 'taux_occupation_visuel', 'revenues_totaux_visuel', 'is_active')
    search_fields = ('nom', 'batiment__nom')
    list_filter = ('batiment', 'is_active')

    def taux_occupation_visuel(self, obj):
        return f"{obj.taux_occupation}%"
    taux_occupation_visuel.short_description = "Taux d'occupation"

    def revenues_totaux_visuel(self, obj):
        return f"{obj.revenues_totaux} CFA"
    revenues_totaux_visuel.short_description = "Revenus de l'étage"


@admin.register(TypeBureau)
class TypeBureauAdmin(admin.ModelAdmin):
    list_display = ('id', 'nom', 'description', 'created_at', 'is_active')
    search_fields = ('nom',)
    list_filter = ('is_active', 'created_at')


@admin.register(Bureau)
class BureauAdmin(admin.ModelAdmin):
    list_display = ('id', 'numero', 'batiment', 'niveau', 'type', 'unite', 'espace', 'prix', 'is_active')
    search_fields = ('numero', 'batiment__nom')
    list_filter = ('batiment', 'niveau', 'type', 'is_active')
    # CORRECTION : Seul le champ 'prix' doit être en readonly. L'utilisateur doit pouvoir saisir l'espace et l'unite !
    readonly_fields = ('prix',)


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    # AJOUT : Le 'statut_temporel' (À VENIR, EN COURS...) s'affiche dynamiquement
    list_display = ('id', 'client', 'bureau', 'date_debut', 'date_fin', 'statut_temporel', 'is_active')
    search_fields = ('client__user__first_name', 'client__user__last_name', 'bureau__numero')
    list_filter = ('is_active', 'date_debut', 'date_fin')


@admin.register(Contrat)
class ContratAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'reservation', 'date_debut', 'date_fin', 'montant', 'statut_temporel', 'is_active')
    search_fields = ('client__user__first_name', 'client__user__last_name', 'reservation__bureau__numero')
    list_filter = ('is_active', 'date_debut', 'date_fin')
    readonly_fields = ('montant',) # Géré automatiquement dans le modèle désormais


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    # AJOUT : Enregistrement de la table Location manquante
    list_display = ('id', 'client', 'bureau', 'date_debut', 'date_fin', 'statut_temporel', 'is_active')
    search_fields = ('client__user__first_name', 'client__user__last_name', 'bureau__numero')
    list_filter = ('is_active', 'date_debut', 'date_fin')


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    
    list_display = ('id', 'client', 'montant', 'reste_a_payer_visuel', 'statut', 'mode', 'contrat', 'location', 'date')
    search_fields = ('client__user__first_name', 'client__user__last_name', 'contrat__id')
    list_filter = ('statut', 'mode', 'date')

    def reste_a_payer_visuel(self, obj):
        return f"{obj.reste_a_payer} CFA"
    reste_a_payer_visuel.short_description = "Reste à payer"