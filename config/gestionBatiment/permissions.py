from rest_framework import permissions
from rest_framework.permissions import SAFE_METHODS

ADMIN_ROLE = 'ADMIN'
WORKER_ROLES = ['TRAVAILLEUR', 'MANAGER', 'AGENT']
CLIENT_ROLES = ['CLIENT']


class BaseRolePermission(permissions.BasePermission):
    """Classe de base pour les permissions basées sur les rôles."""
    
    def get_user_role(self, request):
        """Récupère le rôle de l'utilisateur de manière sécurisée."""
        user = request.user
        if not user or not user.is_authenticated:
            return None
        
        if user.is_superuser:
            return ADMIN_ROLE
        
        profile = getattr(user, 'client_profile', None)
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


class ClientPermission(BaseRolePermission):
    """
    Permissions pour ClientViewSet:
    - Inscription / Création : Bloquée pour les clients et anonymes. Réservée à l'ADMIN.
    - ADMIN : Accès complet (Création, Lecture, Modification, Suppression).
    - TRAVAILLEUR : Lecture seule globale.
    - CLIENT : Peut voir et modifier SON propre profil uniquement. Interdit de créer.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        role = self.get_user_role(request)
        
        if role in (ADMIN_ROLE, *WORKER_ROLES):
            return True
        
        if role in CLIENT_ROLES:
            return request.method in ('GET', 'HEAD', 'OPTIONS', 'PATCH', 'PUT')
        
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
            user_client = getattr(request.user, 'client_profile', None)
            return user_client and obj == user_client
        
        return False


class BatimentPermission(BaseRolePermission):
    """ADMIN: complet | TRAVAILLEUR: lecture | CLIENT: aucun accès."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role = self.get_user_role(request)
        if role == ADMIN_ROLE: return True
        if role in WORKER_ROLES: return request.method in SAFE_METHODS
        return False
    
    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class NiveauPermission(BaseRolePermission):
    """ADMIN: complet | TRAVAILLEUR: lecture | CLIENT: aucun accès."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role = self.get_user_role(request)
        if role == ADMIN_ROLE: return True
        if role in WORKER_ROLES: return request.method in SAFE_METHODS
        return False
    
    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class TypeBureauPermission(BaseRolePermission):
    """ADMIN: complet | TRAVAILLEUR: lecture | CLIENT: aucun accès."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role = self.get_user_role(request)
        if role == ADMIN_ROLE: return True
        if role in WORKER_ROLES: return request.method in SAFE_METHODS
        return False
    
    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class BureauPermission(BaseRolePermission):
    """ADMIN: complet | TRAVAILLEUR & CLIENT: lecture seule."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role = self.get_user_role(request)
        if role == ADMIN_ROLE: return True
        if role in WORKER_ROLES or role in CLIENT_ROLES:
            return request.method in SAFE_METHODS
        return False
    
    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class ReservationPermission(BaseRolePermission):
    """ADMIN: complet | TRAVAILLEUR: voir tout & modifier | CLIENT: voir & créer les SIENNES uniquement."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role = self.get_user_role(request)
        if role in (ADMIN_ROLE, *WORKER_ROLES, *CLIENT_ROLES):
            return request.method in ('GET', 'HEAD', 'OPTIONS', 'POST')
        return False
    
    def has_object_permission(self, request, view, obj):
        role = self.get_user_role(request)
        if role == ADMIN_ROLE: return True
        if role in WORKER_ROLES: return True
        
        if role in CLIENT_ROLES:
            user_client = getattr(request.user, 'client_profile', None)
            return user_client and obj.client == user_client and request.method in SAFE_METHODS
        return False


class ContratPermission(BaseRolePermission):
    """ADMIN: complet | TRAVAILLEUR: voir tout & créer | CLIENT: voir & signer les SIENS uniquement."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role = self.get_user_role(request)
        if role in (ADMIN_ROLE, *WORKER_ROLES, *CLIENT_ROLES):
            return request.method in ('GET', 'HEAD', 'OPTIONS', 'POST', 'PATCH', 'PUT')
        return False
    
    def has_object_permission(self, request, view, obj):
        role = self.get_user_role(request)
        if role == ADMIN_ROLE: return True
        if role in WORKER_ROLES: return True
        
        if role in CLIENT_ROLES:
            user_client = getattr(request.user, 'client_profile', None)
            return user_client and obj.client == user_client and request.method in ('GET', 'HEAD', 'OPTIONS', 'PATCH', 'PUT')
        return False


class LocationPermission(BaseRolePermission):
    """ADMIN: complet | TRAVAILLEUR: complet | CLIENT: voir uniquement les SIENNES."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role = self.get_user_role(request)
        if role in (ADMIN_ROLE, *WORKER_ROLES, *CLIENT_ROLES):
            return request.method in ('GET', 'HEAD', 'OPTIONS', 'POST')
        return False
    
    def has_object_permission(self, request, view, obj):
        role = self.get_user_role(request)
        if role == ADMIN_ROLE: return True
        if role in WORKER_ROLES: return True
        
        if role in CLIENT_ROLES:
            user_client = getattr(request.user, 'client_profile', None)
            return user_client and obj.client == user_client and request.method in SAFE_METHODS
        return False


class PaiementPermission(BaseRolePermission):
    """ADMIN: complet | TRAVAILLEUR: enregistre & liste | CLIENT: effectue & voit ses propres paiements."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        role = self.get_user_role(request)
        if role == ADMIN_ROLE: return True
        
        # CORRECTION : On rajoute le 'POST' pour le rôle CLIENT pour lui permettre de payer
        if role in WORKER_ROLES or role in CLIENT_ROLES:
            return request.method in ('GET', 'HEAD', 'OPTIONS', 'POST')
            
        return False

    def has_object_permission(self, request, view, obj):
        role = self.get_user_role(request)
        if role == ADMIN_ROLE: return True
        if role in WORKER_ROLES: return True
        
        if role in CLIENT_ROLES:
            user_client = getattr(request.user, 'client_profile', None)
            if not user_client: return False
                
            is_owner = (
                obj.client == user_client or 
                (obj.contrat and obj.contrat.client == user_client) or 
                (obj.location and obj.location.client == user_client)
            )
            # Un client ne peut lire que ses propres reçus/paiements (Lecture seule sur l'objet individuel)
            return is_owner and request.method in SAFE_METHODS
        return False