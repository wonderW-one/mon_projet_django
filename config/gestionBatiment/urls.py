from django.urls import path, include
from rest_framework.routers import DefaultRouter
from gestionBatiment.views import  ClientViewSet, BatimentViewSet, LocationViewSet, NiveauViewSet, TypeBureauViewSet, BureauViewSet, ContratViewSet,  PaiementMenthodeViewSet , PaiementViewSet, ReservationViewSet

router = DefaultRouter()
router.register(r'clients', ClientViewSet)
router.register(r'batiments', BatimentViewSet)
router.register(r'types-bureau', TypeBureauViewSet)
router.register(r'niveaux', NiveauViewSet)
router.register(r'bureaux', BureauViewSet)
router.register(r'reservations', ReservationViewSet)
router.register(r'contrats', ContratViewSet)
router.register(r'locations', LocationViewSet)
router.register(r'paiements', PaiementViewSet)