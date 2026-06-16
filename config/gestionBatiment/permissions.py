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
    - Inscription : Ouverte à tous (gérée par AllowAny au niveau de l'action).
    - ADMIN : Accès complet.
    - TRAVAILLEUR : Lecture seule globale.
    - CLIENT : Accès et modification de son propre profil uniquement.
    """
    
    def has_permission(self, request, view):
        # CORRECTION : Permettre l'accès à l'action 'inscription' pour les utilisateurs anonymes
        if view.action == 'inscription':
            return True

        if not request.user or not request.user.is_authenticated:
            return False
        
        role = self.get_user_role(request)
        if role == ADMIN_ROLE:
            return True
        
        if role in WORKER_ROLES:
            return request.method in SAFE_METHODS
        
        if role in CLIENT_ROLES:
            # Un client n'a pas à faire de POST sur la liste générale des clients (sauf inscription)
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
            # Un client ne peut voir/modifier QUE son propre profil
            if user_client and obj.id == user_client.id:
                return request.method in ('GET', 'HEAD', 'OPTIONS', 'PATCH', 'PUT')
        
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
        if role == ADMIN_ROLE:
            return True
        if role in WORKER_ROLES or role in CLIENT_ROLES:
            return request.method in SAFE_METHODS
        return False
    
    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class ReservationPermission(BaseRolePermission):
    """ADMIN: complet | TRAVAILLEUR: voir tout & créer | CLIENT: voir & créer les siennes."""
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
        if role in WORKER_ROLES: return request.method in SAFE_METHODS
        
        if role in CLIENT_ROLES:
            user_client = getattr(request.user, 'client_profile', None)
            return user_client and obj.client_id == user_client.id and request.method in SAFE_METHODS
        return False


class ContratPermission(BaseRolePermission):
    """ADMIN: complet | TRAVAILLEUR: voir tout & créer | CLIENT: voir & signer les siens."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role = self.get_user_role(request)
        if role in (ADMIN_ROLE, *WORKER_ROLES):
            return request.method in ('GET', 'HEAD', 'OPTIONS', 'POST')
        if role in CLIENT_ROLES:
            return request.method in ('GET', 'HEAD', 'OPTIONS', 'POST', 'PATCH', 'PUT')
        return False
    
    def has_object_permission(self, request, view, obj):
        role = self.get_user_role(request)
        if role == ADMIN_ROLE: return True
        if role in WORKER_ROLES: return request.method in SAFE_METHODS
        
        if role in CLIENT_ROLES:
            user_client = getattr(request.user, 'client_profile', None)
            if user_client and obj.client_id == user_client.id:
                return request.method in ('GET', 'HEAD', 'OPTIONS', 'PATCH', 'PUT')
        return False


class LocationPermission(BaseRolePermission):
    """ADMIN: complet | TRAVAILLEUR: complet | CLIENT: aucun accès (géré par le staff)."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role = self.get_user_role(request)
        if role in (ADMIN_ROLE, *WORKER_ROLES):
            return request.method in ('GET', 'HEAD', 'OPTIONS', 'POST')
        return False
    
    def has_object_permission(self, request, view, obj):
        role = self.get_user_role(request)
        if role == ADMIN_ROLE: return True
        if role in WORKER_ROLES: return request.method in SAFE_METHODS
        return False


class PaiementPermission(BaseRolePermission):
    """
    Permissions pour PaiementViewSet:
    - ADMIN : Accès complet (Seul à pouvoir modifier/valider un paiement).
    - TRAVAILLEUR : Peut voir tous les paiements et enregistrer (POST) un nouveau paiement.
    - CLIENT : Peut uniquement voir (GET) ses propres paiements.
    """
    
    # def has_permission(self, request, view):
    #    if not request.user or not request.user.is_authenticated:
    #        return False
    #    
    #    role = self.get_user_role(request)
    #    if role == ADMIN_ROLE:
    #        return True
    #    
    #    if role in WORKER_ROLES:
    #        return request.method in ('GET', 'HEAD', 'OPTIONS', 'POST')
    #    
    #    if role in CLIENT_ROLES:
    #        return request.method in SAFE_METHODS
    #    
    #    return False
    def has_permission(self, request, view):
        # 1. Si c'est l'action d'auto-inscription, on laisse passer (Anonyme ou futur client)
        if view.action == 'inscription':
            return True

        # 2. Si l'utilisateur n'est pas connecté, on bloque
        if not request.user or not request.user.is_authenticated:
            return False
    
        role = self.get_user_role(request)
        if role == ADMIN_ROLE:
            return True
    
        if role in WORKER_ROLES:
            return request.method in SAFE_METHODS  # Lecture seule (GET)
    
        if role in CLIENT_ROLES:
            # CORRECTION : Le client n'a plus le droit de faire "POST" sur la liste globale.
            # Il peut seulement voir (GET) ou modifier (PATCH/PUT) son propre compte.
            return request.method in ('GET', 'HEAD', 'OPTIONS', 'PATCH', 'PUT')
    
        return False


    def has_object_permission(self, request, view, obj):
        role = self.get_user_role(request)
        if role == ADMIN_ROLE:
            return True
        
        if role in WORKER_ROLES:
            return request.method in SAFE_METHODS
        
        if role in CLIENT_ROLES:
            user_client = getattr(request.user, 'client_profile', None)
            if not user_client:
                return False
                
            # CORRECTION CRITIQUE : Résolution dynamique et sécurisée du propriétaire du paiement
            # On vérifie de manière cascade si le paiement appartient au client connecté
            is_owner = False
            if obj.client_id == user_client.id:
                is_owner = True
            elif obj.contrat and obj.contrat.client_id == user_client.id:
                is_owner = True
            elif obj.location and obj.location.client_id == user_client.id:
                is_owner = True
                
            if is_owner:
                return request.method in SAFE_METHODS
        
        return False