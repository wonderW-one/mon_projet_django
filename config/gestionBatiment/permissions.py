from rest_framework import permissions
from rest_framework.permissions import SAFE_METHODS


ADMIN_ROLE = 'ADMIN'
WORKER_ROLES = ['TRAVAILLEUR', 'MANAGER', 'AGENT']
CLIENT_ROLES = ['CLIENT']


class BaseRolePermission(permissions.BasePermission):
    """Classe de base pour les permissions basées sur les rôles."""
    
    def get_user_role(self, request):
        """Récupère le rôle de l'utilisateur."""
        user = request.user
        if not user or not user.is_authenticated:
            return None
        
        # Vérifie si c'est un superuser
        if user.is_superuser:
            return ADMIN_ROLE
        
        # Vérifie le profil Client
        profile = getattr(user, 'client_profile', None)
        if profile is not None:
            return profile.role
        
        # Vérifie les groupes
        groups = set(user.groups.values_list('name', flat=True))
        if ADMIN_ROLE in groups:
            return ADMIN_ROLE
        for role in WORKER_ROLES:
            if role in groups:
                return role
        if CLIENT_ROLES[0] in groups:
            return CLIENT_ROLES[0]
        return None


class ClientPermission(BaseRolePermission):
    """
    Permissions pour ClientViewSet:
    - ADMIN: voir tous, créer, modifier tous
    - TRAVAILLEUR/MANAGER: voir tous, lire les informations
    - CLIENT: voir et modifier son propre profil uniquement
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        role = self.get_user_role(request)
        
        if role == ADMIN_ROLE:
            return True
        
        if role in WORKER_ROLES:
            # Les travailleurs peuvent voir tous les clients (GET)
            # Mais ne peuvent pas créer/modifier/supprimer
            return request.method in SAFE_METHODS
        
        if role in CLIENT_ROLES:
            # Les clients peuvent GET et POST (créer leur propre profil)
            # et PATCH/PUT (modifier leur propre profil)
            return request.method in ('GET', 'HEAD', 'OPTIONS', 'POST', 'PATCH', 'PUT')
        
        return False
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        role = self.get_user_role(request)
        
        if role == ADMIN_ROLE:
            return True
        
        if role in WORKER_ROLES:
            # Les travailleurs peuvent seulement lire (GET)
            return request.method in SAFE_METHODS
        
        if role in CLIENT_ROLES:
            # Les clients ne peuvent accéder que à leur propre profil
            user_client = getattr(request.user, 'client_profile', None)
            if user_client and obj.id == user_client.id:
                return request.method in ('GET', 'HEAD', 'OPTIONS', 'PATCH', 'PUT')
        
        return False


class BatimentPermission(BaseRolePermission):
    """
    Permissions pour BatimentViewSet:
    - ADMIN: accès complet
    - TRAVAILLEUR/MANAGER: lecture seule
    - CLIENT: pas d'accès
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        role = self.get_user_role(request)
        
        if role == ADMIN_ROLE:
            return True
        
        if role in WORKER_ROLES:
            return request.method in SAFE_METHODS
        
        return False
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        role = self.get_user_role(request)
        
        if role == ADMIN_ROLE:
            return True
        
        if role in WORKER_ROLES:
            return request.method in SAFE_METHODS
        
        return False


class NiveauPermission(BaseRolePermission):
    """
    Permissions pour NiveauViewSet:
    - ADMIN: accès complet
    - TRAVAILLEUR/MANAGER: lecture seule
    - CLIENT: pas d'accès
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        role = self.get_user_role(request)
        
        if role == ADMIN_ROLE:
            return True
        
        if role in WORKER_ROLES:
            return request.method in SAFE_METHODS
        
        return False
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        role = self.get_user_role(request)
        
        if role == ADMIN_ROLE:
            return True
        
        if role in WORKER_ROLES:
            return request.method in SAFE_METHODS
        
        return False


class TypeBureauPermission(BaseRolePermission):
    """
    Permissions pour TypeBureauViewSet:
    - ADMIN: accès complet
    - TRAVAILLEUR/MANAGER: lecture seule
    - CLIENT: pas d'accès
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        role = self.get_user_role(request)
        
        if role == ADMIN_ROLE:
            return True
        
        if role in WORKER_ROLES:
            return request.method in SAFE_METHODS
        
        return False
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        role = self.get_user_role(request)
        
        if role == ADMIN_ROLE:
            return True
        
        if role in WORKER_ROLES:
            return request.method in SAFE_METHODS
        
        return False


class BureauPermission(BaseRolePermission):
    """
    Permissions pour BureauViewSet:
    - ADMIN: accès complet
    - TRAVAILLEUR/MANAGER: lecture complète
    - CLIENT: lecture seule (peut voir les bureaux disponibles)
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        role = self.get_user_role(request)
        
        if role == ADMIN_ROLE:
            return True
        
        if role in WORKER_ROLES:
            return request.method in SAFE_METHODS
        
        if role in CLIENT_ROLES:
            # Les clients peuvent voir les bureaux
            return request.method in SAFE_METHODS
        
        return False
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        role = self.get_user_role(request)
        
        if role == ADMIN_ROLE:
            return True
        
        if role in WORKER_ROLES:
            return request.method in SAFE_METHODS
        
        if role in CLIENT_ROLES:
            # Les clients peuvent voir les bureaux
            return request.method in SAFE_METHODS
        
        return False


class ReservationPermission(BaseRolePermission):
    """
    Permissions pour ReservationViewSet:
    - ADMIN: accès complet
    - TRAVAILLEUR/MANAGER: peuvent voir toutes les réservations, créer pour d'autres clients
    - CLIENT: ne peuvent voir et créer que leurs propres réservations
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        role = self.get_user_role(request)
        
        if role == ADMIN_ROLE:
            return True
        
        if role in WORKER_ROLES:
            # Peuvent lire toutes les réservations et créer
            return request.method in ('GET', 'HEAD', 'OPTIONS', 'POST')
        
        if role in CLIENT_ROLES:
            # Peuvent créer et lire leurs propres réservations
            return request.method in ('GET', 'HEAD', 'OPTIONS', 'POST')
        
        return False
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        role = self.get_user_role(request)
        
        if role == ADMIN_ROLE:
            return True
        
        if role in WORKER_ROLES:
            # Peuvent lire toutes les réservations
            return request.method in SAFE_METHODS
        
        if role in CLIENT_ROLES:
            # Peuvent lire seulement leurs propres réservations
            user_client = getattr(request.user, 'client_profile', None)
            if user_client and obj.client.id == user_client.id:
                return request.method in SAFE_METHODS
        
        return False


class ContratPermission(BaseRolePermission):
    """
    Permissions pour ContratViewSet:
    - ADMIN: accès complet
    - TRAVAILLEUR/MANAGER: peuvent voir tous les contrats, créer/modifier pour des clients
    - CLIENT: ne peuvent voir et modifier que leurs propres contrats
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        role = self.get_user_role(request)
        
        if role == ADMIN_ROLE:
            return True
        
        if role in WORKER_ROLES:
            # Peuvent lire tous les contrats et créer
            return request.method in ('GET', 'HEAD', 'OPTIONS', 'POST')
        
        if role in CLIENT_ROLES:
            # Peuvent créer et lire leurs propres contrats
            return request.method in ('GET', 'HEAD', 'OPTIONS', 'POST', 'PATCH', 'PUT')
        
        return False
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        role = self.get_user_role(request)
        
        if role == ADMIN_ROLE:
            return True
        
        if role in WORKER_ROLES:
            # Peuvent lire tous les contrats
            return request.method in SAFE_METHODS
        
        if role in CLIENT_ROLES:
            # Peuvent modifier seulement leurs propres contrats
            user_client = getattr(request.user, 'client_profile', None)
            if user_client and obj.client.id == user_client.id:
                return request.method in ('GET', 'HEAD', 'OPTIONS', 'PATCH', 'PUT')
        
        return False


class LocationPermission(BaseRolePermission):
    """
    Permissions pour LocationViewSet:
    - ADMIN: accès complet
    - TRAVAILLEUR/MANAGER: peuvent lire et créer
    - CLIENT: ne peuvent pas accéder (locations gérées par travailleurs/admin)
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        role = self.get_user_role(request)
        
        if role == ADMIN_ROLE:
            return True
        
        if role in WORKER_ROLES:
            return request.method in ('GET', 'HEAD', 'OPTIONS', 'POST')
        
        return False
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        role = self.get_user_role(request)
        
        if role == ADMIN_ROLE:
            return True
        
        if role in WORKER_ROLES:
            return request.method in SAFE_METHODS
        
        return False


class PaiementPermission(BaseRolePermission):
    """
    Permissions pour PaiementViewSet:
    - ADMIN: accès complet
    - TRAVAILLEUR/MANAGER: peuvent lire, créer (modification = admin seulement)
    - CLIENT: peuvent voir leurs propres paiements
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        role = self.get_user_role(request)
        
        if role == ADMIN_ROLE:
            return True
        
        if role in WORKER_ROLES:
            # Peuvent lire et créer, mais pas modifier/supprimer
            return request.method in ('GET', 'HEAD', 'OPTIONS', 'POST')
        
        if role in CLIENT_ROLES:
            # Peuvent voir leurs paiements
            return request.method in SAFE_METHODS
        
        return False
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        role = self.get_user_role(request)
        
        if role == ADMIN_ROLE:
            return True
        
        if role in WORKER_ROLES:
            return request.method in SAFE_METHODS
        
        if role in CLIENT_ROLES:
            # Peuvent voir seulement leurs propres paiements
            user_client = getattr(request.user, 'client_profile', None)
            if user_client and hasattr(obj, 'contrat') and obj.contrat.client.id == user_client.id:
                return request.method in SAFE_METHODS
        
        return False