from django.http import HttpResponse
from django.shortcuts import render
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.utils import timezone

from .serializers import (
    ClientSerializer, BatimentSerializer, NiveauSerializer, 
    TypeBureauSerializer, BureauSerializer, LocationSerializer,
    ContratSerializer, PaiementSerializer, ReservationSerializer
)
from .models import Client, Batiment, TypeBureau, Bureau, Niveau, Contrat, Location, Paiement, Reservation
from .permissions import (
    ClientPermission, BatimentPermission, NiveauPermission,
    TypeBureauPermission, BureauPermission, ReservationPermission,
    ContratPermission, LocationPermission, PaiementPermission,
    ADMIN_ROLE, WORKER_ROLES, CLIENT_ROLES
)


class BaseModelViewSet(viewsets.ModelViewSet):
    """Base viewset qui convertit proprement les Django ValidationError en HTTP 400 DRF."""

    def _format_django_validation_error(self, exc):
        if hasattr(exc, 'message_dict'):
            return exc.message_dict
        if hasattr(exc, 'error_dict'):
            return {k: v.messages if hasattr(v, 'messages') else v for k, v in exc.error_dict.items()}
        if hasattr(exc, 'messages'):
            return {'detail': exc.messages}
        return {'detail': str(exc)}

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except DjangoValidationError as e:
            raise DRFValidationError(self._format_django_validation_error(e))

    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except DjangoValidationError as e:
            raise DRFValidationError(self._format_django_validation_error(e))

    def partial_update(self, request, *args, **kwargs):
        try:
            return super().partial_update(request, *args, **kwargs)
        except DjangoValidationError as e:
            raise DRFValidationError(self._format_django_validation_error(e))

    def get_permissions(self):
        if getattr(self, 'permission_classes', None):
            return [permission() for permission in self.permission_classes]
        return [IsAuthenticated()]

    def get_client_profile(self):
        return getattr(self.request.user, 'client_profile', None)

    def get_user_role(self):
        user = self.request.user
        if not user or user.is_anonymous:
            return None
        if user.is_superuser:
            return ADMIN_ROLE

        profile = self.get_client_profile()
        if profile is not None:
            return profile.role

        groups = set(user.groups.values_list('name', flat=True))
        if ADMIN_ROLE in groups:
            return ADMIN_ROLE
        for role in WORKER_ROLES:
            if role in groups:
                return role
        if CLIENT_ROLES and CLIENT_ROLES[0] in groups:
            return CLIENT_ROLES[0]
        return None


# ==================== Vues Classiques (HTML) ====================

def hello(request):
    return HttpResponse('<h1>Bienvenue dans la gestion de bâtiments!</h1>')

def index(request):
    batiments = Batiment.objects.all()
    bureaux = Bureau.objects.select_related('batiment', 'type', 'niveau').all()
    context = {
        'batiments': batiments,
        'bureaux': bureaux,
        'nombre_batiments': batiments.count(),
        'nombre_bureaux': bureaux.count(),
    }
    return render(request, 'gestionBatiment/index.html', context)


# ==================== ViewSets API REST ====================

class ClientViewSet(BaseModelViewSet):
    """ViewSet pour gérer les Clients"""
    serializer_class = ClientSerializer
    permission_classes = [ClientPermission]
    ordering = ['user_id']

    def get_queryset(self):
        role = self.get_user_role()
        profile = self.get_client_profile()
        base_query = Client.objects.select_related('user')

        if role == ADMIN_ROLE or role in WORKER_ROLES:
            return base_query.all().order_by('user_id')
        if role in CLIENT_ROLES and profile is not None:
            return base_query.filter(user_id=profile.user_id)
        
        return Client.objects.none()


class BatimentViewSet(BaseModelViewSet):
    """ViewSet pour gérer les Bâtiments"""
    serializer_class = BatimentSerializer
    permission_classes = [BatimentPermission]

    def get_queryset(self):
        role = self.get_user_role()
        if role == ADMIN_ROLE or role in WORKER_ROLES:
            return Batiment.objects.all()
        return Batiment.objects.none()

    @action(detail=False, methods=['get'], url_path='actifs')
    def actifs(self, request):
        batiments = Batiment.objects.filter(is_active=True)
        serializer = self.get_serializer(batiments, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='statistiques')
    def statistiques(self, request, pk=None):
        batiment = self.get_object()
        return Response({
            'id': batiment.id,
            'nom': batiment.nom,
            'taux_occupation': batiment.taux_occupation,
            'revenues_totaux': batiment.revenues_totaux,
            'nombre_bureaux': batiment.bureaux.count(),
        })


class NiveauViewSet(BaseModelViewSet):
    """ViewSet pour gérer les Niveaux"""
    serializer_class = NiveauSerializer
    permission_classes = [NiveauPermission]

    def get_queryset(self):
        role = self.get_user_role()
        if role == ADMIN_ROLE or role in WORKER_ROLES:
            return Niveau.objects.select_related('batiment').all()
        return Niveau.objects.none()

    @action(detail=False, methods=['get'], url_path='par-batiment/(?P<batiment_id>[0-9]+)')
    def par_batiment(self, request, batiment_id=None):
        niveaux = Niveau.objects.filter(batiment_id=batiment_id, is_active=True)
        serializer = self.get_serializer(niveaux, many=True)
        return Response(serializer.data)


class TypeBureauViewSet(BaseModelViewSet):
    """ViewSet pour gérer les Types de Bureau"""
    serializer_class = TypeBureauSerializer
    permission_classes = [TypeBureauPermission]

    def get_queryset(self):
        role = self.get_user_role()
        if role == ADMIN_ROLE or role in WORKER_ROLES:
            return TypeBureau.objects.all()
        return TypeBureau.objects.none()


class BureauViewSet(BaseModelViewSet):
    """ViewSet pour gérer les Bureaux"""
    serializer_class = BureauSerializer
    permission_classes = [BureauPermission]

    def get_queryset(self):
        role = self.get_user_role()
        profile = self.get_client_profile()
        today = timezone.now().date()

        if role == ADMIN_ROLE or role in WORKER_ROLES:
            return Bureau.objects.select_related('batiment', 'type', 'niveau').all()

        if role in CLIENT_ROLES and profile is not None:
            base_queryset = Bureau.objects.select_related('batiment', 'type', 'niveau')
            bureaux_reserves = base_queryset.filter(reservations__client=profile, reservations__is_active=True)
            
            bureaux_libres = base_queryset.filter(is_active=True).exclude(
                reservations__is_active=True,
                reservations__date_debut__lte=today,
                reservations__date_fin__gte=today
            )
            return (bureaux_reserves | bureaux_libres).distinct()

        return Bureau.objects.none()

    @action(detail=False, methods=['get'], url_path='disponibles')
    def disponibles(self, request):
        today = timezone.now().date()
        livres = Bureau.objects.filter(is_active=True).exclude(
            reservations__is_active=True,
            reservations__date_debut__lte=today,
            reservations__date_fin__gte=today
        ).select_related('batiment', 'type', 'niveau')
        serializer = self.get_serializer(livres.distinct(), many=True)
        return Response(serializer.data)


class ReservationViewSet(BaseModelViewSet):
    """ViewSet pour gérer les Réservations"""
    serializer_class = ReservationSerializer
    permission_classes = [ReservationPermission]

    def get_queryset(self):
        profile = self.get_client_profile()
        role = self.get_user_role()
        query = Reservation.objects.select_related('bureau', 'client__user')

        if role == ADMIN_ROLE or role in WORKER_ROLES:
            return query.all()
        if role in CLIENT_ROLES and profile is not None:
            return query.filter(client=profile)
        return Reservation.objects.none()

    @action(detail=False, methods=['get'], url_path='sans-contrat')
    def sans_contrat(self, request):
        """AJOUT : Filtre et retourne les réservations actives qui n'ont pas encore de contrat lié"""
        role = self.get_user_role()
        profile = self.get_client_profile()
        
        query = Reservation.objects.filter(is_active=True, contrat__isnull=True).select_related('bureau', 'client__user')

        if role == ADMIN_ROLE or role in WORKER_ROLES:
            reservations = query.all()
        elif role in CLIENT_ROLES and profile is not None:
            reservations = query.filter(client=profile)
        else:
            reservations = Reservation.objects.none()

        serializer = self.get_serializer(reservations, many=True)
        return Response(serializer.data)

    def get_serializer(self, *args, **kwargs):
        serializer = super().get_serializer(*args, **kwargs)
        instance_serializer = serializer.child if hasattr(serializer, 'child') else serializer

        if 'bureau' in instance_serializer.fields:
            role = self.get_user_role()
            if role in CLIENT_ROLES:
                instance_serializer.fields['bureau'].queryset = Bureau.objects.filter(is_active=True)
            else:
                instance_serializer.fields['bureau'].queryset = Bureau.objects.all()
                
        return serializer

    def perform_create(self, serializer):
        role = self.get_user_role()
        
        if role in CLIENT_ROLES:
            client = self.get_client_profile()
            if not client:
                raise DRFValidationError({
                    "detail": "Votre compte utilisateur ne possède pas de profil Client actif."
                })
        else:
            client_id = self.request.data.get('client')
            if not client_id:
                raise DRFValidationError({
                    "client": "Ce champ est obligatoire pour les administrateurs et gestionnaires."
                })
            try:
                client = Client.objects.get(pk=client_id)
            except Client.DoesNotExist:
                raise DRFValidationError({
                    "client": "Le client spécifié n'existe pas."
                })

        serializer.save(client=client)


class ContratViewSet(BaseModelViewSet):
    """ViewSet pour gérer les Contrats"""
    serializer_class = ContratSerializer
    permission_classes = [ContratPermission]

    def get_queryset(self):
        profile = self.get_client_profile()
        role = self.get_user_role()
        query = Contrat.objects.select_related('reservation', 'client__user')

        if role == ADMIN_ROLE or role in WORKER_ROLES:
            return query.all()
        if role in CLIENT_ROLES and profile is not None:
            return query.filter(client=profile)
        return Contrat.objects.none()

    def get_serializer(self, *args, **kwargs):
        kwargs['context'] = self.get_serializer_context()
        serializer = super().get_serializer(*args, **kwargs)
        instance_serializer = serializer.child if hasattr(serializer, 'child') else serializer
        
        if 'reservation' in instance_serializer.fields:
            role = self.get_user_role()
            profile = self.get_client_profile()

            if role in CLIENT_ROLES and profile is not None:
                # CORRECTION/AJOUT : Le client ne peut lier qu'une réservation libre de tout contrat
                instance_serializer.fields['reservation'].queryset = Reservation.objects.filter(
                    client=profile, 
                    is_active=True,
                    contrat__isnull=True
                )
            else:
                instance_serializer.fields['reservation'].queryset = Reservation.objects.filter(contrat__isnull=True)
                
        return serializer

    def perform_create(self, serializer):
        role = self.get_user_role()
        reservation = serializer.validated_data.get('reservation')
        
        if not reservation:
            raise DRFValidationError({
                "reservation": "Une réservation valide est obligatoire pour générer un contrat."
            })

        # Sécurité : Empêche d'associer une réservation déjà verrouillée par un autre contrat
        if Contrat.objects.filter(reservation=reservation, is_active=True).exists():
            raise DRFValidationError({
                "reservation": "Un contrat actif existe déjà pour cette réservation."
            })

        if role in CLIENT_ROLES:
            client_connecte = self.get_client_profile()
            if reservation.client != client_connecte:
                raise DRFValidationError({
                    "reservation": "Cette réservation ne vous appartient pas."
                })
            serializer.save(client=client_connecte)
        else:
            serializer.save(client=reservation.client)


class LocationViewSet(BaseModelViewSet):
    """ViewSet pour gérer les Locations"""
    serializer_class = LocationSerializer
    permission_classes = [LocationPermission]

    def get_queryset(self):
        profile = self.get_client_profile()
        role = self.get_user_role()
        query = Location.objects.select_related('bureau', 'client__user')

        if role == ADMIN_ROLE or role in WORKER_ROLES:
            return query.all()
        if role in CLIENT_ROLES and profile is not None:
            return query.filter(client=profile)
        return Location.objects.none()

    def perform_create(self, serializer):
        if self.get_user_role() in CLIENT_ROLES:
            serializer.save(client=self.get_client_profile())
        else:
            serializer.save()


class PaiementViewSet(BaseModelViewSet):
    """ViewSet pour gérer les Paiements avec génération et validation de montant automatique"""
    queryset = Paiement.objects.filter(is_active=True)
    serializer_class = PaiementSerializer
    permission_classes = [PaiementPermission]

    def get_queryset(self):
        role = self.get_user_role()
        profile = self.get_client_profile()
        query = self.queryset.select_related('client__user', 'contrat', 'location')

        if role == ADMIN_ROLE or role in WORKER_ROLES:
            return query
        if role in CLIENT_ROLES and profile is not None:
            return query.filter(client=profile)
        return Paiement.objects.none()

    def perform_create(self, serializer):
        """Calcule automatiquement le montant, le mois, l'année sans saisie utilisateur et sécurise le client"""
        role = self.get_user_role()
        profile = self.get_client_profile()
        
        # CORRECTION : Récupération des données de la requête
        data = self.request.data
        contrat_id = data.get('contrat')
        location_id = data.get('location')
        
        # Gestion automatique du temps (Mois et Année)
        maintenant = timezone.now()
        mois_auto = data.get('mois_paye', maintenant.month)
        annee_auto = data.get('annee_paye', maintenant.year)
    
        montant_auto = None
        client_final = None

        # 1. Traitement si relié à un contrat (Scénario principal)
        if contrat_id:
            try:
                contrat = Contrat.objects.get(pk=contrat_id, is_active=True)
                if role in CLIENT_ROLES and contrat.client != profile:
                    raise DRFValidationError({"contrat": "Ce contrat ne vous appartient pas."})
                
                # Récupère le montant calculé ou défini sur le contrat
                montant_auto = contrat.montant or getattr(contrat.reservation, 'montant_calcule', None)
                client_final = contrat.client
            except Contrat.DoesNotExist:
                raise DRFValidationError({"contrat": "Contrat introuvable ou inactif."})

        # 2. Traitement alternatif si paiement direct sur une Location
        elif location_id:
            try:
                location = Location.objects.get(pk=location_id, is_active=True)
                if role in CLIENT_ROLES and location.client != profile:
                    raise DRFValidationError({"location": "Cette location ne vous appartient pas."})
                
                if hasattr(location, 'montant') and location.montant:
                    montant_auto = location.montant
                elif location.bureau:
                    montant_auto = location.bureau.prix
                
                client_final = location.client
            except Location.DoesNotExist:
                raise DRFValidationError({"location": "Location introuvable ou inactive."})
        else:
            raise DRFValidationError({"detail": "Un identifiant de contrat ou de location valide est requis."})

        # 3. Contrôle de validité du montant extrait du système
        if montant_auto is None or float(montant_auto) <= 0:
            raise DRFValidationError({"montant": "Impossible de générer un montant automatique valide pour cette entité."})

        # 4. Enregistrement unique, forcé et sécurisé (Nettoyé des doublons)
        if role in CLIENT_ROLES:
            serializer.save(
                client=profile, 
                montant=montant_auto, 
                statut='PAID', 
                mois_paye=mois_auto, 
                annee_paye=annee_auto
            )
        else:
            serializer.save(
                client=client_final, 
                montant=montant_auto, 
                statut='PAID', 
                mois_paye=mois_auto, 
                annee_paye=annee_auto
            )
