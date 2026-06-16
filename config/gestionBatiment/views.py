from django.http import HttpResponse
from django.shortcuts import render
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from .serializers import (
    ClientSerializer, BatimentSerializer, NiveauSerializer, 
    TypeBureauSerializer, BureauSerializer, LocationSerializer,
    ContratSerializer, PaiementSerializer, 
    ReservationSerializer

)
from .models import Client, Batiment, TypeBureau, Bureau, Niveau, Contrat, Location, Paiement, Reservation
from .permissions import (
    ClientPermission, BatimentPermission, NiveauPermission,
    TypeBureauPermission, BureauPermission, ReservationPermission,
    ContratPermission, LocationPermission, PaiementPermission,
    ADMIN_ROLE, WORKER_ROLES, CLIENT_ROLES
)


class BaseModelViewSet(viewsets.ModelViewSet):
    """Base viewset that converts Django ValidationError into DRF HTTP 400 responses."""

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
            raise ValidationError(self._format_django_validation_error(e))

    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except DjangoValidationError as e:
            raise ValidationError(self._format_django_validation_error(e))

    def partial_update(self, request, *args, **kwargs):
        try:
            return super().partial_update(request, *args, **kwargs)
        except DjangoValidationError as e:
            raise ValidationError(self._format_django_validation_error(e))

    def get_permissions(self):
        if getattr(self, 'permission_classes', None):
            return [permission() for permission in self.permission_classes]
        return [IsAuthenticated()]

    def get_client_profile(self):
        return getattr(self.request.user, 'client_profile', None)

    def get_user_role(self):
        user = self.request.user
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
        if CLIENT_ROLES[0] in groups:
            return CLIENT_ROLES[0]
        return None


# ==================== Vues simples ====================

def hello(request):
    return HttpResponse('<h1>Bienvenue dans la gestion de bâtiments!</h1>')

def index(request):
    batiments = Batiment.objects.all()
    bureaux = Bureau.objects.all()
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

    def get_queryset(self):
        user = self.request.user
        profile = self.get_client_profile()
        role = self.get_user_role()

        if role == ADMIN_ROLE or role in WORKER_ROLES:
            return Client.objects.all()

        if role in CLIENT_ROLES and profile is not None:
            return Client.objects.filter(user=user)

        return Client.objects.none()

    def perform_create(self, serializer):
        profile = self.get_client_profile()
        role = self.get_user_role()
        if role in CLIENT_ROLES and profile is None:
            serializer.save(user=self.request.user)
        else:
            serializer.save()

    def perform_update(self, serializer):
        serializer.save()


class BatimentViewSet(BaseModelViewSet):
    """ViewSet pour gérer les Bâtiments"""
    serializer_class = BatimentSerializer
    permission_classes = [BatimentPermission]

    def get_queryset(self):
        role = self.get_user_role()
        if role == ADMIN_ROLE or role in WORKER_ROLES:
            return Batiment.objects.all()
        return Batiment.objects.none()

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()

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
            return Niveau.objects.all()
        return Niveau.objects.none()

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()

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

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()

    @action(detail=False, methods=['get'], url_path='actifs')
    def actifs(self, request):
        types_bureau = TypeBureau.objects.filter(is_active=True)
        serializer = self.get_serializer(types_bureau, many=True)
        return Response(serializer.data)


class BureauViewSet(BaseModelViewSet):
    """ViewSet pour gérer les Bureaux"""
    serializer_class = BureauSerializer
    permission_classes = [BureauPermission]

    def get_queryset(self):
        user = self.request.user
        profile = self.get_client_profile()
        role = self.get_user_role()

        if role == ADMIN_ROLE or role in WORKER_ROLES:
            return Bureau.objects.all()

        if role in CLIENT_ROLES and profile is not None:
            bureaux_reserves = Bureau.objects.filter(reservations__client=profile, reservations__is_active=True)
            bureaux_libres = Bureau.objects.filter(is_active=True).exclude(
                reservations__is_active=True,
                reservations__date_fin__gte=timezone.now().date()
            )
            return (bureaux_reserves | bureaux_libres).distinct()

        return Bureau.objects.none()

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()

    @action(detail=False, methods=['get'], url_path='par-type/(?P<type_id>[0-9]+)')
    def par_type(self, request, type_id=None):
        bureaux = Bureau.objects.filter(type_id=type_id, is_active=True)
        serializer = self.get_serializer(bureaux, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='disponibles')
    def disponibles(self, request):
        livres = Bureau.objects.filter(is_active=True).exclude(
            reservations__is_active=True,
            reservations__date_fin__gte=timezone.now().date()
        )
        serializer = self.get_serializer(livres.distinct(), many=True)
        return Response(serializer.data)


class ReservationViewSet(BaseModelViewSet):
    """ViewSet pour gérer les Réservations"""
    serializer_class = ReservationSerializer
    permission_classes = [ReservationPermission]

    def get_queryset(self):
        profile = self.get_client_profile()
        role = self.get_user_role()

        if role == ADMIN_ROLE or role in WORKER_ROLES:
            return Reservation.objects.all()

        if role in CLIENT_ROLES and profile is not None:
            return Reservation.objects.filter(client=profile)

        return Reservation.objects.none()

    def perform_create(self, serializer):
        profile = self.get_client_profile()
        if profile and self.get_user_role() in CLIENT_ROLES:
            serializer.save(client=profile)
        else:
            serializer.save()

    @action(detail=False, methods=['get'], url_path='mes-reservations')
    def mes_reservations(self, request):
        profile = self.get_client_profile()
        if profile is None:
            return Response([], status=status.HTTP_200_OK)
        reservations = Reservation.objects.filter(client=profile)
        serializer = self.get_serializer(reservations, many=True)
        return Response(serializer.data)


class ContratViewSet(BaseModelViewSet):
    """ViewSet pour gérer les Contrats"""
    serializer_class = ContratSerializer
    permission_classes = [ContratPermission]

    def get_queryset(self):
        profile = self.get_client_profile()
        role = self.get_user_role()

        if role == ADMIN_ROLE or role in WORKER_ROLES:
            return Contrat.objects.all()

        if role in CLIENT_ROLES and profile is not None:
            return Contrat.objects.filter(client=profile)

        return Contrat.objects.none()

    def perform_create(self, serializer):
        profile = self.get_client_profile()
        if profile and self.get_user_role() in CLIENT_ROLES:
            serializer.save(client=profile)
        else:
            serializer.save()

    @action(detail=False, methods=['get'], url_path='mes-contrats')
    def mes_contrats(self, request):
        profile = self.get_client_profile()
        if profile is None:
            return Response([], status=status.HTTP_200_OK)
        contrats = Contrat.objects.filter(client=profile)
        serializer = self.get_serializer(contrats, many=True)
        return Response(serializer.data)


class LocationViewSet(BaseModelViewSet):
    """ViewSet pour gérer les Locations"""
    serializer_class = LocationSerializer
    permission_classes = [LocationPermission]

    def get_queryset(self):
        profile = self.get_client_profile()
        role = self.get_user_role()

        if role == ADMIN_ROLE or role in WORKER_ROLES:
            return Location.objects.all()

        if role in CLIENT_ROLES and profile is not None:
            return Location.objects.filter(client=profile)

        return Location.objects.none()

    def perform_create(self, serializer):
        profile = self.get_client_profile()
        if profile and self.get_user_role() in CLIENT_ROLES:
            serializer.save(client=profile)
        else:
            serializer.save()

    @action(detail=False, methods=['get'], url_path='mes-locations')
    def mes_locations(self, request):
        profile = self.get_client_profile()
        if profile is None:
            return Response([], status=status.HTTP_200_OK)
        locations = Location.objects.filter(client=profile)
        serializer = self.get_serializer(locations, many=True)
        return Response(serializer.data)


class PaiementViewSet(BaseModelViewSet):
    """ViewSet pour gérer les Paiements"""
    serializer_class = PaiementSerializer
    permission_classes = [PaiementPermission]

    def get_queryset(self):
        profile = self.get_client_profile()
        role = self.get_user_role()

        if role == ADMIN_ROLE or role in WORKER_ROLES:
            return Paiement.objects.all()

        if role in CLIENT_ROLES and profile is not None:
            return Paiement.objects.filter(client=profile)

        return Paiement.objects.none()

    def perform_create(self, serializer):
        profile = self.get_client_profile()
        if profile and self.get_user_role() in CLIENT_ROLES:
            serializer.save(client=profile)
            return

        validated = getattr(serializer, 'validated_data', {})
        client = validated.get('client')
        if not client:
            contrat = validated.get('contrat')
            location = validated.get('location')
            if contrat:
                client = contrat.client
            elif location:
                client = location.client

        if client:
            serializer.save(client=client)
        else:
            serializer.save()

    def perform_update(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'], url_path='mes-paiements')
    def mes_paiements(self, request):
        profile = self.get_client_profile()
        if profile is None:
            return Response([], status=status.HTTP_200_OK)
        paiements = Paiement.objects.filter(client=profile)
        serializer = self.get_serializer(paiements, many=True)
        return Response(serializer.data)
    