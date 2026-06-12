
from django.contrib import admin
from .models import Client , Niveau, TypeBureau,Batiment , Bureau ,Paiement, Reservation, Contrat, Location


# Register your models here.

    
@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'user__first_name', 'user__last_name', 'telephone', 'addresse', 'date_naissance', 'created_at')
    search_fields = ('user__first_name', 'user__last_name', 'telephone')
    list_filter = ('created_at',)
    
    def get_user(self, obj):
        return obj.user.get_full_name() or obj.user.username
    
    def get_first_name(self, obj):
        return obj.user.first_name
    
    def get_last_name(self, obj):
        return obj.user.last_name
    

@admin.register(Batiment)
class BatimentAdmin(admin.ModelAdmin):
    list_display = ('id', 'nom', 'adresse', 'nombre_etages', 'date_construction', 'is_active')
    search_fields = ('nom', 'adresse')
    list_filter = ('nom', 'created_at')
  
  
@admin.register(Niveau)
class NiveauAdmin(admin.ModelAdmin):
    list_display = ('id', 'nom', 'batiment', 'created_at', 'is_active')
    search_fields = ('nom',)
    list_filter = ('batiment',)
    
@admin.register(TypeBureau)
class TypeBureauAdmin(admin.ModelAdmin):
    list_display = ('id', 'nom', 'description', 'created_at', 'is_active')
    search_fields = ('nom',)
    list_filter = ('nom', 'created_at')


@admin.register(Bureau)
class BureauAdmin(admin.ModelAdmin):
    list_display = ('id', 'numero', 'niveau', 'type', 'unite','batiment', 'espace', 'prix', 'created_at', 'is_active')
    search_fields = ('numero',)
    list_filter = ('niveau__nom',)
    readonly_fields = ('espace', 'unite','prix')  # Rendre ces champs en lecture seule car ils sont calculés automatiquement

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('id', 'client','bureau', 'date_debut', 'date_fin', 'created_at')
    search_fields = ('client__user__first_name', 'client__user__last_name', 'bureau__numero')
    list_filter = ('date_debut', 'date_fin')    
    
@admin.register(Contrat)
class ContratAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'reservation', 'date_debut', 'date_fin', 'is_active', 'created_at')
    search_fields = ('client__user__first_name', 'client__user__last_name', 'bureau__numero')
    list_filter = ('date_debut', 'date_fin') 
    


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ('id', 'montant', 'date', 'mode', 'location', 'client', 'created_at')
    search_fields = ('mode',)
    list_filter = ('date',)
 