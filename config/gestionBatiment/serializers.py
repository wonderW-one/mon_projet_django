from rest_framework import serializers
from django.contrib.auth.models import User 
from django.db import transaction
from decimal import Decimal
from .models import Client, Batiment, Niveau, TypeBureau, Bureau, Reservation, Contrat, Location, Paiement

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from .permissions import ADMIN_ROLE, WORKER_ROLES, CLIENT_ROLES


# --- Token ---
class MonTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # 1. Vérification si Superuser
        if user.is_superuser:
            token['role'] = ADMIN_ROLE
            return token

        # 2. Vérification par profil lié (Client)
        try:
            client_profile = Client.objects.get(user=user)
            token['role'] = str(client_profile.role)
            return token
        except Client.DoesNotExist:
            pass

        # 3. Vérification par Groupes Django (Workers / Admins)
        groups = set(user.groups.values_list('name', flat=True))
        if ADMIN_ROLE in groups:
            token['role'] = ADMIN_ROLE
        elif any(role in groups for role in WORKER_ROLES):
            for role in WORKER_ROLES:
                if role in groups:
                    token['role'] = role
                    break
        elif CLIENT_ROLES and CLIENT_ROLES[0] in groups:
            token['role'] = CLIENT_ROLES[0]
        else:
            token['role'] = 'ANONYME'

        return token


class MonTokenObtainPairView(TokenObtainPairView):
    serializer_class = MonTokenObtainPairSerializer
    

# --- SÉRIALISEURS COMPACTS DE LECTURE ---

class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']


class ClientDetailSerializer(serializers.ModelSerializer):
    user = UserDetailSerializer(read_only=True)
    telephone = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = ['user_id', 'user', 'telephone', 'addresse', 'date_naissance']

    def get_telephone(self, obj):
        return str(obj.telephone) if obj.telephone else None


# --- SÉRIALISEURS PRINCIPAUX ---

class ClientSerializer(serializers.ModelSerializer):
    user_detail = serializers.SerializerMethodField(read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)

    username = serializers.CharField(write_only=True, required=False, max_length=150)
    password = serializers.CharField(write_only=True, required=False)
    email = serializers.EmailField(write_only=True, required=False)
    first_name = serializers.CharField(write_only=True, required=False, max_length=150)
    last_name = serializers.CharField(write_only=True, required=False, max_length=150)

    class Meta:
        model = Client
        fields = [
            'user_id', 'user_detail', 'username', 'password', 'email', 
            'first_name', 'last_name', 'telephone', 'addresse', 
            'date_naissance', 'created_at', 'updated_at'
        ]

    def get_user_detail(self, obj):
        return UserDetailSerializer(obj.user).data

    def validate_username(self, value):
        query = User.objects.filter(username=value)
        if self.instance and self.instance.user:
            query = query.exclude(pk=self.instance.user.id)
        if query.exists():
            raise serializers.ValidationError("Ce nom d'utilisateur est déjà pris.")
        return value

    def create(self, validated_data):
        with transaction.atomic():
            user = User.objects.create(
                username=validated_data.pop('username'),
                email=validated_data.pop('email', ''),
                first_name=validated_data.pop('first_name', ''),
                last_name=validated_data.pop('last_name', '')
            )
            user.set_password(validated_data.pop('password'))
            user.save()

            client = Client.objects.create(
                user=user,
                role='CLIENT',
                **validated_data
            )
            return client

    def update(self, instance, validated_data):
        user_data = {}
        for field in ['username', 'email', 'first_name', 'last_name']:
            if field in validated_data:
                user_data[field] = validated_data.pop(field)
        
        password = validated_data.pop('password', None)

        with transaction.atomic():
            if user_data or password:
                user = instance.user
                for attr, value in user_data.items():
                    setattr(user, attr, value)
                if password:
                    user.set_password(password)
                user.save()

            return super().update(instance, validated_data)


class BatimentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batiment
        fields = '__all__'


class NiveauSerializer(serializers.ModelSerializer):
    batiment_detail = BatimentSerializer(source='batiment', read_only=True)

    class Meta:
        model = Niveau
        fields = ['id', 'nom', 'batiment', 'batiment_detail', 'created_at', 'updated_at', 'is_active']


class TypeBureauSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypeBureau
        fields = '__all__'


class BureauSerializer(serializers.ModelSerializer):
    type_detail = TypeBureauSerializer(source='type', read_only=True)
    batiment_detail = BatimentSerializer(source='batiment', read_only=True)
    niveau_detail = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Bureau
        fields = [
            'id', 'numero', 'type', 'type_detail', 'unite', 'espace', 'prix', 
            'batiment', 'batiment_detail', 'niveau', 'niveau_detail', 
            'created_at', 'updated_at', 'is_active'
        ]

    def get_niveau_detail(self, obj):
        if obj.niveau:
            return {
                'id': obj.niveau.id,
                'nom': obj.niveau.nom,
                'batiment': obj.niveau.batiment.id if obj.niveau.batiment else None,
            }
        return None


class ContratSerializer(serializers.ModelSerializer):
    client_prenom = serializers.CharField(source='client.user.first_name', read_only=True)
    
    # MODIFICATION : Permet à la méthode perform_create de remplir le client automatiquement sans bloquer
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all(), required=False)

    class Meta:
        model = Contrat
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'montant']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.user:
            if not request.user.is_superuser and not request.user.groups.filter(name='ADMIN').exists():
                self.fields['client'].read_only = True


class LocationSerializer(serializers.ModelSerializer):
    client_detail = ClientDetailSerializer(source='client', read_only=True)
    client_prenom = serializers.CharField(source='client.user.first_name', read_only=True)
    bureau_name = serializers.CharField(source='bureau.numero', read_only=True)

    class Meta:
        model = Location
        fields = ['id', 'date_debut', 'date_fin', 'bureau', 'bureau_name', 'client', 'client_prenom', 'client_detail', 'created_at', 'updated_at', 'is_active']
        read_only_fields = ['client']


class PaiementSerializer(serializers.ModelSerializer):
    client_detail = ClientDetailSerializer(source='client', read_only=True)
    client_prenom = serializers.CharField(source='client.user.first_name', read_only=True)
    
    # MODIFICATION : required=False évite l'obligation de saisir le montant côté client
    montant = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    mois_paye = serializers.IntegerField(required=False, allow_null=True)
    annee_paye = serializers.IntegerField(required=False, allow_null=True)
    
    class Meta:
        model = Paiement
        fields = [
            'id', 'contrat', 'location', 'mode', 'statut', 
            'montant', 'mois_paye', 'annee_paye', 'client', 'client_prenom', 'client_detail',
            'created_at', 'updated_at'
        ]
        # Ces champs sont calculés par le serveur : invisibles/bloqués au POST
        read_only_fields = ['montant', 'mois_paye', 'annee_paye', 'client']


class ReservationSerializer(serializers.ModelSerializer):
    montant_calcule = serializers.SerializerMethodField(read_only=True)
    client_detail = ClientDetailSerializer(source='client', read_only=True)
    client_prenom = serializers.CharField(source='client.user.first_name', read_only=True)
    bureau_name = serializers.CharField(source='bureau.numero', read_only=True)

    class Meta:
        model = Reservation
        fields = ['id', 'date_debut', 'montant_calcule', 'date_fin', 'bureau', 'bureau_name', 'client', 'client_prenom', 'client_detail', 'created_at', 'updated_at', 'is_active']
        read_only_fields = ['client']

    def get_montant_calcule(self, obj):
        if obj.bureau and obj.date_debut and obj.date_fin:
            delta = obj.date_fin - obj.date_debut
            nombre_jours = max(delta.days, 0)
            
            prix_bureau = Decimal(str(obj.bureau.prix))
            montant_total = (Decimal(nombre_jours) * prix_bureau) / Decimal('2')
            return float(round(montant_total, 2))
        return 0.0