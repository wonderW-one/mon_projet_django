import logging
from django.http import HttpResponse
from django.shortcuts import render
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from datetime import timedelta
from rest_framework import viewsets, status
from rest_framework import permissions
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
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

from django.core.mail import send_mail
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from django.conf import settings
logger = logging.getLogger(__name__)

class BaseModelViewSet(viewsets.ModelViewSet):
    """Base viewset gérant les erreurs de validation ET implémentant le Soft-Delete global."""

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

    def destroy(self, request, *args, **kwargs):
        """
        SURCHARGE SÉCURITÉ : Intercepte le DELETE pour faire un Soft-Delete
        au lieu d'une destruction définitive en base de données.
        """
        instance = self.get_object()

        if hasattr(instance, 'is_active'):
            instance.is_active = False
            instance.save(user=request.user) if hasattr(instance, 'save') else instance.save()
            return Response(
                {"detail": "L'élément a été archivé avec succès (Soft-delete)."},
                status=status.HTTP_200_OK
            )

        # Fallback au cas où le modèle n'aurait pas le champ is_active
        return super().destroy(request, *args, **kwargs)

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


# ==================== Vues simples ====================

def hello(request):
    return HttpResponse('<h1>Bienvenue dans la gestion de bâtiments!</h1>')

def index(request):
    batiments = Batiment.objects.filter(is_active=True)
    bureaux = Bureau.objects.filter(is_active=True)
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
        # Filtrer pour ne lister que les profils encore actifs
        base_query = Client.objects.filter(is_active=True).select_related('user')

        if role == ADMIN_ROLE or role in WORKER_ROLES:
            return base_query.order_by('user_id')
        if role in CLIENT_ROLES and profile is not None:
            return base_query.filter(id=profile.id)

        return Client.objects.none()

   @action(detail=False, methods=['post'], permission_classes=[AllowAny], url_path='inscription')
   def inscription(self, request):
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
        profile = self.get_client_profile()
        if profile is None or not profile.is_active:
            return Response(
                {"has_profile": False, "detail": "Aucun profil client actif trouvé."},
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
            return Batiment.objects.filter(is_active=True)
        return Batiment.objects.none()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        serializer.save(user=self.request.user)

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
            'nombre_bureaux': batiment.bureaux.filter(is_active=True).count(),
        })


class NiveauViewSet(BaseModelViewSet):
    """ViewSet pour gérer les Niveaux"""
    serializer_class = NiveauSerializer
    permission_classes = [NiveauPermission]

    def get_queryset(self):
        role = self.get_user_role()
        if role == ADMIN_ROLE or role in WORKER_ROLES:
            return Niveau.objects.filter(is_active=True)
        return Niveau.objects.none()


class TypeBureauViewSet(BaseModelViewSet):
    """ViewSet pour gérer les Types de Bureau"""
    serializer_class = TypeBureauSerializer
    permission_classes = [TypeBureauPermission]

    def get_queryset(self):
        role = self.get_user_role()
        if role == ADMIN_ROLE or role in WORKER_ROLES:
            return TypeBureau.objects.filter(is_active=True)
        return TypeBureau.objects.none()


class BureauViewSet(BaseModelViewSet):
    """ViewSet pour gérer les Bureaux"""
    serializer_class = BureauSerializer
    permission_classes = [BureauPermission]

    def get_queryset(self):
        role = self.get_user_role()

        # Sécurité structurelle : On ne remonte que les bureaux non archivés (soft-deleted)
        base_qs = Bureau.objects.filter(is_active=True)

        # Les admins, travailleurs ET clients voient désormais tous les bureaux actifs
        if role == ADMIN_ROLE or role in WORKER_ROLES or role in CLIENT_ROLES:
            return base_qs

        return Bureau.objects.none()

    @action(detail=False, methods=['get'], url_path='disponibles')
    def disponibles(self, request):
        qs = self.get_queryset().filter(statut=Bureau.BureauStatus.DISPONIBLE)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class ReservationViewSet(BaseModelViewSet):
    """ViewSet pour gérer les Réservations"""
    serializer_class = ReservationSerializer
    permission_classes = [ReservationPermission]

    def get_queryset(self):
        profile = self.get_client_profile()
        role = self.get_user_role()
        base_qs = Reservation.objects.filter(is_active=True)

        if role == ADMIN_ROLE or role in WORKER_ROLES:
            return base_qs
        if role in CLIENT_ROLES and profile is not None:
            return base_qs.filter(client=profile)

        return Reservation.objects.none()

    def perform_create(self, serializer):
        profile = self.get_client_profile()
        if profile and self.get_user_role() in CLIENT_ROLES:
            reservation = serializer.save(client=profile)
        else:
            reservation = serializer.save()
        reservation.bureau.statut = Bureau.BureauStatus.OCCUPE
        reservation.bureau.save()
    @action(detail=True, methods=['post'], url_path='annuler')
    def annuler(self, request, pk=None):
        reservation = self.get_object()
        reservation.is_active = False
        reservation.save()

        bureau = reservation.bureau
        autre_resa_active = Reservation.objects.filter(
            bureau=bureau, is_active=True
        ).exclude(pk=reservation.pk).exists()
        autre_contrat_actif = Contrat.objects.filter(bureau=bureau, is_active=True).exists()

        if not autre_resa_active and not autre_contrat_actif:
            bureau.statut = Bureau.BureauStatus.DISPONIBLE
            bureau.save()

        return Response({'detail': 'Réservation annulée.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='convertir-contrat')
    def convertir_contrat(self, request, pk=None):
        reservation = self.get_object()
        if hasattr(reservation, 'contrat') and reservation.contrat:
            return Response(
                {'detail': 'Cette réservation a déjà un contrat associé.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        contrat = Contrat(
            reservation=reservation,
            client=reservation.client,
            date_debut=reservation.date_debut,
            date_fin=reservation.date_fin,
        )
        contrat.save(user=request.user)

        bureau = contrat.bureau_effectif
        if bureau:
            bureau.statut = Bureau.BureauStatus.OCCUPE
            bureau.save()

        serializer = ContratSerializer(contrat, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)



class ContratViewSet(BaseModelViewSet):
    serializer_class = ContratSerializer
    permission_classes = [ContratPermission]

    def get_queryset(self):
        profile = self.get_client_profile()
        role = self.get_user_role()
        base_qs = Contrat.objects.filter(is_active=True)

        if role == ADMIN_ROLE or role in WORKER_ROLES:
            return base_qs
        if role in CLIENT_ROLES and profile is not None:
            return base_qs.filter(client=profile)

        return Contrat.objects.none()

    def perform_create(self, serializer):
        profile = self.get_client_profile()
        role = self.get_user_role()

        if profile and role in CLIENT_ROLES:
            # Demande de contrat direct : reste EN_ATTENTE, bureau pas encore occupé
            serializer.save(client=profile, user=self.request.user)
        else:
            contrat = serializer.save(user=self.request.user)
            bureau = contrat.bureau_effectif
            if bureau:
                bureau.statut = Bureau.BureauStatus.OCCUPE
                bureau.save()

    @action(detail=True, methods=['post'], url_path='valider-contrat')
    def valider_contrat(self, request, pk=None):
        contrat = self.get_object()

        if contrat.statut == Contrat.ContratStatus.VALIDE:
            return Response({'detail': 'Ce contrat est déjà validé.'}, status=status.HTTP_400_BAD_REQUEST)

        contrat.statut = Contrat.ContratStatus.VALIDE
        if not contrat.date_debut:
            contrat.date_debut = timezone.now().date()  # jour de la signature = jour de validation
        contrat.save(user=request.user)

        bureau = contrat.bureau_effectif
        if bureau:
            bureau.statut = Bureau.BureauStatus.OCCUPE
            bureau.save()

        serializer = self.get_serializer(contrat)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='rejeter-contrat')
    def rejeter_contrat(self, request, pk=None):
        contrat = self.get_object()
        contrat.statut = Contrat.ContratStatus.REJETE
        contrat.is_active = False
        contrat.save(user=request.user)
        return Response({'detail': 'Demande de contrat rejetée.'}, status=status.HTTP_200_OK)


class LocationViewSet(BaseModelViewSet):
    """ViewSet pour gérer les Locations"""
    serializer_class = LocationSerializer
    permission_classes = [LocationPermission]

    def get_queryset(self):
        profile = self.get_client_profile()
        role = self.get_user_role()
        base_qs = Location.objects.filter(is_active=True)

        if role == ADMIN_ROLE or role in WORKER_ROLES:
            return base_qs
        if role in CLIENT_ROLES and profile is not None:
            return base_qs.filter(client=profile)

        return Location.objects.none()


class PaiementViewSet(BaseModelViewSet):
    """ViewSet pour gérer les Paiements"""
    serializer_class = PaiementSerializer
    permission_classes = [PaiementPermission]

    def get_queryset(self):
        profile = self.get_client_profile()
        role = self.get_user_role()
        base_qs = Paiement.objects.filter(is_active=True)

        if role == ADMIN_ROLE or role in WORKER_ROLES:
            return base_qs
        if role in CLIENT_ROLES and profile is not None:
            return base_qs.filter(client=profile)
        return Paiement.objects.none()

    def perform_create(self, serializer):
        # NOUVEAU : sans ceci, created_by reste toujours null (perte de traçabilité)
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], url_path='valider-paiement')
    def valider_paiement(self, request, pk=None):
        paiement = self.get_object()
        paiement.statut = Paiement.PaiementStatus.COMPLETED
        paiement.save(user=request.user)
        # --- LOGIQUE D'ENVOI D'E-MAIL AU CLIENT ---
        try:
            # 1. Récupération des informations du client et du paiement
            email_client = paiement.client.user.email
            nom_client = paiement.client.user.first_name or paiement.client.user.username
            montant = paiement.montant

            # Récupère le nom du mois en français (ex: "Janvier") au lieu du chiffre
            mois = paiement.get_mois_paye_display()
            annee = paiement.annee_paye

            # Récupère le libellé propre du mode de paiement (ex: "Espèces")
            mode_paiement = paiement.get_mode_display()

            if email_client:  # On s'assure que le client a bien une adresse mail
                sujet = f"Confirmation de votre paiement - {mois} {annee}"

                corps_email = (
                    f"Bonjour {nom_client},\n\n"
                    f"Nous vous confirmons la bonne réception de votre paiement.\n\n"
                    f"Détails de la transaction :\n"
                    f"– Période : {mois} {annee}\n"
                    f"– Montant : {montant} FBU\n"
                    f"– Mode de paiement : {mode_paiement}\n\n"
                    f"Merci pour votre confiance.\n"
                    f"L'équipe de gestion."
                )

                send_mail(
                    sujet,
                    corps_email,
                    settings.EMAIL_HOST_USER,  # Votre adresse d'expédition configurée
                    [email_client],            # L'adresse du client
                    fail_silently=False,        # True évite de bloquer l'API si le serveur d'envoi d'e-mail a un problème
                )
        except Exception as e:
            logger.error(e)
            # Optionnel : logguez l'erreur ici si l'envoi échoue pour ne pas bloquer la validation

        # ------------------------------------------

        serializer = self.get_serializer(paiement)
        return Response(serializer.data, status=status.HTTP_200_OK)
