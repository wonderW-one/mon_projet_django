from django.contrib import admin
from .models import Client, Niveau, TypeBureau, Batiment, Bureau, Paiement, Reservation, Contrat, Location

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'get_user_id', 'get_first_name', 'get_last_name', 'telephone',
        'type_piece_identite', 'numero_piece_identite', 'nationalite', 'profession',
        'date_naissance', 'lieu_naissance', 'created_at'
    )
    # ...


    search_fields = (
        'user__first_name', 'user__last_name', 'user__username',
        'telephone', 'numero_piece_identite', 'nationalite', 'profession'
    )
    list_filter = ('created_at', 'type_piece_identite', 'nationalite')

    def get_user_id(self, obj):
        return obj.user.id
    get_user_id.short_description = 'ID Utilisateur'
    def get_first_name(self, obj):
        return obj.user.first_name
    get_first_name.short_description = 'Prénom'

    def get_last_name(self, obj):
        return obj.user.last_name
    get_last_name.short_description = 'Nom'


@admin.register(Batiment)
class BatimentAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'nom', 'adresse', 'nombre_etages',
        'proprietaire_nom', 'proprietaire_prenom', 'proprietaire_telephone',
         'taux_occupation_visuel', 'revenues_totaux_visuel', 'is_active'
    )
    search_fields = ('nom', 'adresse', 'proprietaire_nom', 'proprietaire_prenom', 'proprietaire_numero_piece')
    list_filter = ('is_active', 'created_at')

    def taux_occupation_visuel(self, obj):
        return f"{obj.taux_occupation}%"
    taux_occupation_visuel.short_description = "Taux d'occupation"

    def revenues_totaux_visuel(self, obj):
        return f"{obj.revenues_totaux} CFA"
    revenues_totaux_visuel.short_description = "Revenus encaissés"

@admin.register(Niveau)
class NiveauAdmin(admin.ModelAdmin):
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
    readonly_fields = ('prix',)


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'bureau', 'date_debut', 'date_fin', 'statut_temporel', 'is_active')
    search_fields = ('client__user__first_name', 'client__user__last_name', 'bureau__numero')
    list_filter = ('is_active', 'date_debut', 'date_fin')


@admin.register(Contrat)
class ContratAdmin(admin.ModelAdmin):
    # AJOUT : 'bureau' visible pour les contrats en location directe (sans réservation)
    list_display = ('id', 'client', 'reservation', 'bureau', 'periodicite', 'date_debut', 'date_fin', 'date_paiement', 'montant', 'statut_temporel', 'is_active')
    search_fields = ('client__user__first_name', 'client__user__last_name', 'reservation__bureau__numero', 'bureau__numero')
    list_filter = ('is_active', 'date_debut', 'date_fin', 'periodicite')
    readonly_fields = ('montant',)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'bureau', 'contrat', 'date_debut', 'date_fin', 'statut_temporel', 'is_active')
    search_fields = ('client__user__first_name', 'client__user__last_name', 'bureau__numero')
    list_filter = ('is_active', 'date_debut', 'date_fin')


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'montant', 'get_loyer_mensuel_30', 'mois_paye', 'annee_paye', 'reste_a_payer_visuel', 'statut', 'mode', 'contrat', 'location', 'date')
    search_fields = ('client__user__first_name', 'client__user__last_name', 'contrat__id')
    list_filter = ('statut', 'mode', 'date')
    readonly_fields = ('montant', 'statut', 'reste_a_payer_visuel')

    @admin.display(description='Loyer Mensuel Prévu (30j)')
    def get_loyer_mensuel_30(self, obj):
        return f"{obj.loyer_mensuel_prevu_30_jours} FBU"

    @admin.display(description='Reste à payer')
    def reste_a_payer_visuel(self, obj):
        return f"{obj.reste_a_payer} FBU"
