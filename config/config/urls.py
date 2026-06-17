from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView 

# 1. IMPORTS REQUIS POUR LA PERSONNALISATION DU TOKEN JWT
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from gestionBatiment.models import Client  # Importation de ton modèle Client

from gestionBatiment.views import (
    ClientViewSet, BatimentViewSet, NiveauViewSet, 
    TypeBureauViewSet, BureauViewSet, ContratViewSet, 
    LocationViewSet, PaiementViewSet, ReservationViewSet
)

# =========================================================================
# 2. CRÉATION DU SÉRIALISEUR ET DE LA VUE DU TOKEN PERSONNALISÉ
# =========================================================================
class MonTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # On cherche si l'utilisateur possède un profil Client pour en extraire le rôle
        try:
            client_profile = Client.objects.get(user=user)
            token['role'] = str(client_profile.role)  # Injecte le rôle (ADMIN, MANAGER, STAFF, CLIENT)
        except Client.DoesNotExist:
            # Sécurité pour l'accès aux superutilisateurs créés via la commande 'createsuperuser'
            if user.is_superuser:
                token['role'] = 'ADMIN'
            else:
                token['role'] = 'CLIENT'

        return token

class MonTokenObtainPairView(TokenObtainPairView):
    serializer_class = MonTokenObtainPairSerializer


# Configuration du routeur de l'API REST
router = DefaultRouter()

# 1. Structure et Infrastructure
router.register(r'batiments', BatimentViewSet, basename='batiment')
router.register(r'niveaux', NiveauViewSet, basename='niveau')
router.register(r'types-bureau', TypeBureauViewSet, basename='typebureau')  
router.register(r'bureaux', BureauViewSet, basename='bureau')

# 2. Utilisateurs & Profils
router.register(r'clients', ClientViewSet, basename='client')

# 3. Flux Opérationnel
router.register(r'reservations', ReservationViewSet, basename='reservation')
router.register(r'contrats', ContratViewSet, basename='contrat')
router.register(r'locations', LocationViewSet, basename='location')
router.register(r'paiements', PaiementViewSet, basename='paiement')


# Motifs d'URL globaux
urlpatterns = [
    # Interface d'administration Django
    path('admin/', admin.site.urls),
    
    # Interface d'authentification pour le mode Navigable (Browsable API) de DRF
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    
    # MODIFICATION ICI : Utilisation de notre nouvelle vue personnalisée qui intègre le rôle
    path('api/token/', MonTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Inclusion de toutes les routes de l'API auto-générées par le routeur
    path('api/', include(router.urls)),
]