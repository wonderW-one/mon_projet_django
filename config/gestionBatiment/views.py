from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError

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
   
   def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return super().get_permissions()

   def get_queryset(self):
        role = self.get_user_role()
        profile = self.get_client_profile()
        base_query = Client.objects.select_related('user')
        if self.action == 'create':
            return Client.objects.none()

        if role == ADMIN_ROLE or role in WORKER_ROLES:
            return base_query.all().order_by('user_id')
        if role in CLIENT_ROLES and profile is not None:
            return base_query.filter(user_id=profile.user.id)
        
        return Client.objects.none()

   @action(detail=False, methods=['post'], permission_classes=[AllowAny], url_path='inscription')
   def inscription(self, request):
        """Permet a un utilisateur (anonyme ou connecté sans profil) de creer SON profil"""
        if request.user.is_authenticated and self.get_client_profile() is not None:
            return Response(
                {"detail": "Vous avez déjà un profil client créé."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            if request.user.is_authenticated:
                client = serializer.save(user=request.user)
            else:
                client = serializer.save()
            return Response(self.get_serializer(client).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

   @action(detail=False, methods=['get'], url_path='mon-profil')
   def mon_profil(self, request):
        """Point d'accès crucial pour le Frontend pour vérifier l'état du profil"""
        profile = self.get_client_profile()
        if profile is None:
            return Response(
                {"has_profile": False, "detail": "Aucun profil client trouvé pour cet utilisateur."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(profile)
        data = serializer.data
        data["has_profile"] = True
        return Response(data, status=status.HTTP_200_OK)
    

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
        """Filtre et retourne les réservations actives qui n'ont pas encore de contrat lié"""
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

    # 🔵 NOUVELLE ACTION ADAPTÉE : Conversion de la réservation courante en Contrat
    @action(detail=True, methods=['post'], url_path='convertir-contrat')
    def convertir_contrat(self, request, pk=None):
        """
        Génère un contrat actif à partir d'une réservation existante.
        POST /api/reservations/<id>/convertir-contrat/
        """
        reservation = self.get_object()

        # Sécurités de base
        if not reservation.is_active:
            return Response(
                {"detail": "Impossible de convertir une réservation inactive."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if Contrat.objects.filter(reservation=reservation, is_active=True).exists():
            return Response(
                {"detail": "Un contrat actif est déjà associé à cette réservation."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Récupération optionnelle de la facturation envoyée par le body
        type_facturation = request.data.get('type_facturation', 'MENSUEL')
        if type_facturation not in ['MENSUEL', 'TRIMESTRIEL', 'SEMESTRIEL']:
            type_facturation = 'MENSUEL'

        try:
            # Création du contrat en reprenant les données de réservation
            contrat = Contrat(
                reservation=reservation,
                client=reservation.client,
                date_debut=reservation.date_debut,
                date_fin=reservation.date_fin,
                type_facturation=type_facturation,
                is_active=True
            )
            # Enclenche l'attribution de created_by & calcul du montant via le modèle
            contrat.save(user=request.user)

            return Response(
                {
                    "detail": f"La réservation #{reservation.id} a été convertie en contrat avec succès.",
                    "contrat_id": contrat.id,
                    "montant_genere": contrat.montant
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {"detail": f"Erreur lors de la génération du contrat : {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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
        role = self.get_user_role()
        profile = self.get_client_profile()
        
        data = self.request.data
        contrat_id = data.get('contrat')
        location_id = data.get('location')
        
        maintenant = timezone.now()
        mois_auto = data.get('mois_paye', maintenant.month)
        annee_auto = data.get('annee_paye', maintenant.year)
    
        montant_auto = None
        client_final = None

        if contrat_id:
            try:
                contrat = Contrat.objects.get(pk=contrat_id, is_active=True)
                if role in CLIENT_ROLES and contrat.client != profile:
                    raise DRFValidationError({"contrat": "Ce contrat ne vous appartient pas."})
                
                montant_auto = contrat.montant or getattr(contrat.reservation, 'montant_calcule', None)
                client_final = contrat.client
            except Contrat.DoesNotExist:
                raise DRFValidationError({"contrat": "Contrat introuvable ou inactif."})

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

        if montant_auto is None or float(montant_auto) <= 0:
            raise DRFValidationError({"montant": "Impossible de générer un montant automatique valide pour cette entité."})

        if role in CLIENT_ROLES:
            serializer.save(
                client=profile, 
                montant=montant_auto, 
                statut='PENDING', 
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
            
    @action(detail=True, methods=['post'], url_path='valider-paiement')
    def valider_paiement(self, request, pk=None):
        """Action personnalisée pour passer un paiement en statut 'PAID'."""
        paiement = get_object_or_404(Paiement, pk=pk)
        
        user = request.user
        if not hasattr(user, 'client_profile') or user.client_profile.role not in ['ADMIN', 'TRAVAILLEUR', 'MANAGER']:
            return Response(
                {"detail": "Vous n'avez pas la permission de valider ce paiement."}, 
                status=status.HTTP_403_FORBIDDEN
            )
            
        if paiement.statut == 'PAID':
            return Response(
                {"detail": "Ce paiement a déjà été validé et encaissé."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        paiement.statut = 'PAID'
        paiement.save(user=user) 
        
        return Response(
            {"detail": "Le paiement a été validé avec succès !", "statut": paiement.statut}, 
            status=status.HTTP_200_OK
        )