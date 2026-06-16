from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView 

from gestionBatiment.views import (
    ClientViewSet, BatimentViewSet, NiveauViewSet, 
    TypeBureauViewSet, BureauViewSet, ContratViewSet, 
    LocationViewSet, PaiementViewSet, ReservationViewSet
)

# Configuration du routeur de l'API REST
router = DefaultRouter()

# 1. Structure et Infrastructure (Ordre logique et hiérarchique)
router.register(r'batiments', BatimentViewSet, basename='batiment')
router.register(r'niveaux', NiveauViewSet, basename='niveau')
router.register(r'types-bureau', TypeBureauViewSet, basename='typebureau')  
router.register(r'bureaux', BureauViewSet, basename='bureau')

# 2. Utilisateurs & Profils
router.register(r'clients', ClientViewSet, basename='client')

# 3. Flux Opérationnel (Réservation ➔ Contrat ➔ Location ➔ Paiement)
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
    
    # Endpoints d'Authentification JWT sécurisés
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Inclusion de toutes les routes de l'API auto-générées par le routeur
    path('api/', include(router.urls)),
]