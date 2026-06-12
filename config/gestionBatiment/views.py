from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import ValidationError
from .serializers import (
    ClientSerializer, BatimentSerializer, NiveauSerializer, 
    TypeBureauSerializer, BureauSerializer, LocationSerializer,
    ContratSerializer, PaiementSerializer, 
    ReservationSerializer

)
from .models import Client, Batiment, TypeBureau, Bureau, Niveau, Contrat, Location, Paiement, Reservation

# ==================== Vues simples ====================

#def hello(request):
#    return HttpResponse('<h1>Bienvenue dans la gestion de bâtiments!</h1>')

#def index(request):
 #   batiments = Batiment.objects.all()
 #   bureaux = Bureau.objects.all()
 #   context = {
 #       'batiments': batiments,
 #      'bureaux': bureaux,
 #       'nombre_batiments': batiments.count(),
 #       'nombre_bureaux': bureaux.count(),
 #   }
 #   return render(request, 'gestionBatiment/index.html', context)

# ==================== ViewSets API REST ====================

class ClientViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les Clients"""
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [AllowAny]

class BatimentViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les Bâtiments"""
    queryset = Batiment.objects.all()
    serializer_class = BatimentSerializer
    permission_classes = [AllowAny]

class NiveauViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les Niveaux"""
    queryset = Niveau.objects.all()
    serializer_class = NiveauSerializer
    permission_classes = [AllowAny]

class TypeBureauViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les Types de Bureau"""
    queryset = TypeBureau.objects.all()
    serializer_class = TypeBureauSerializer
    permission_classes = [AllowAny]

class BureauViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les Bureaux"""
    queryset = Bureau.objects.all()
    serializer_class = BureauSerializer
    permission_classes = [AllowAny] 
    
# Action personnalisé pour filtrer les bureaux par type
    @action(detail=False, methods=['get'], url_path='par-type/(?P<type_id>[0-9]+)')
    
    def par_type(self, request, type_id=None):

        bureaux = Bureau.objects.filter(type_id=type_id, is_active=True)
        serializer = self.get_serializer(bureaux, many=True)
        return Response(serializer.data)


class ReservationViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les Réservations"""
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except DjangoValidationError as e:
            # Convertir les erreurs de validation du modèle en réponse 400
            error_dict = e.error_dict if hasattr(e, 'error_dict') else {'detail': str(e)}
            raise ValidationError(error_dict)
    
    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except DjangoValidationError as e:
            error_dict = e.error_dict if hasattr(e, 'error_dict') else {'detail': str(e)}
            raise ValidationError(error_dict)
    
    
class ContratViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les Contrats"""
    queryset = Contrat.objects.all()
    serializer_class = ContratSerializer
    permission_classes = [AllowAny]
    
class LocationViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les Locations"""
    queryset = Location.objects.all()
    serializer_class = LocationSerializer   
    permission_classes = [AllowAny]
    

class PaiementViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les Paiements"""
    queryset = Paiement.objects.all()
    serializer_class = PaiementSerializer
    permission_classes = [AllowAny]
    