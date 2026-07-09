from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username

        profile = getattr(user, 'client_profile', None)
        if user.is_superuser:
            role = 'ADMIN'
        elif profile is not None:
            role = profile.role
        else:
            groups = list(user.groups.values_list('name', flat=True))
            role = groups[0] if groups else None

        token['role'] = role
        token['has_profile'] = profile is not None
        token['client_id'] = profile.id if profile is not None else None
        return token

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
