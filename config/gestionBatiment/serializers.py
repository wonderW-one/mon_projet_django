from rest_framework import serializers
from django.contrib.auth.models import User 
from django.db import transaction
from .models import Client, Batiment, Niveau, TypeBureau, Bureau, Reservation, Contrat, Location, Paiement

# --- SÉRIALISEURS COMPACTS DE LECTURE (Pour la réutilisation) ---

class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']


class ClientDetailSerializer(serializers.ModelSerializer):
    user = UserDetailSerializer(read_only=True)
    telephone = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = ['id', 'user', 'telephone', 'addresse', 'date_naissance']

    def get_telephone(self, obj):
        return str(obj.telephone) if obj.telephone else None


# --- SÉRIALISEURS PRINCIPAUX ---

class ClientSerializer(serializers.ModelSerializer):
    user_detail = serializers.SerializerMethodField(read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)

    # CORRECTION : required=False pour permettre les mises à jour partielles (PATCH)
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
        # CORRECTION : Ne pas s'auto-bloquer lors d'une modification
        query = User.objects.filter(username=value)
        if self.instance and self.instance.user:
            query = query.exclude(pk=self.instance.user.id)
        if query.exists():
            raise serializers.ValidationError("Ce nom d'utilisateur est déjà pris.")
        return value

    def create(self, validated_data):
        with transaction.atomic():
            # Extraction sécurisée avec valeurs par défaut au cas où
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
                role=Client.UserRole.CLIENT,
                **validated_data
            )
            return client

    def update(self, instance, validated_data):
        # AJOUT CRITIQUE : Permet de modifier aussi les infos de l'User lié
        user_data = {}
        for field in ['username', 'email', 'first_name', 'last_name']:
            if field in validated_data:
                user_data[field] = validated_data.pop(field)
        
        password = validated_data.pop('password', None)

        with transaction.atomic():
            # 1. Mise à jour de l'User
            if user_data or password:
                user = instance.user
                for attr, value in user_data.items():
                    setattr(user, attr, value)
                if password:
                    user.set_password(password)
                user.save()

            # 2. Mise à jour du Client
            return super().update(instance, validated_data)


class BatimentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batiment
        fields = '__all__'


class NiveauSerializer(serializers.ModelSerializer):
    batiment_detail = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Niveau
        fields = ['id', 'nom', 'batiment', 'batiment_detail', 'created_at', 'updated_at', 'is_active']
    
    def get_batiment_detail(self, obj):
        if obj.batiment:
            return BatimentSerializer(obj.batiment).data
        return None


class TypeBureauSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypeBureau
        fields = '__all__'


class BureauSerializer(serializers.ModelSerializer):
    type_detail = serializers.SerializerMethodField(read_only=True)
    batiment_detail = serializers.SerializerMethodField(read_only=True)
    niveau_detail = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Bureau
        fields = [
            'id', 'numero', 'type', 'type_detail', 'unite', 'espace', 'prix', 
            'batiment', 'batiment_detail', 'niveau', 'niveau_detail', 
            'created_at', 'updated_at', 'is_active'
        ]

    def get_type_detail(self, obj):
        return TypeBureauSerializer(obj.type).data if obj.type else None

    def get_batiment_detail(self, obj):
        return BatimentSerializer(obj.batiment).data if obj.batiment else None

    def get_niveau_detail(self, obj):
        if obj.niveau:
            return {
                'id': obj.niveau.id,
                'nom': obj.niveau.nom,
                'batiment': obj.niveau.batiment.id if obj.niveau.batiment else None,
            }
        return None


class ContratSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contrat
        fields = '__all__'
        # CORRECTION : 'client' ajouté en read_only car assigné automatiquement par la vue
        read_only_fields = ['created_at', 'updated_at', 'montant', 'client'] 
        
        
class LocationSerializer(serializers.ModelSerializer):
    client_detail = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Location
        fields = ['id', 'date_debut', 'date_fin', 'bureau', 'client', 'client_detail', 'created_at', 'updated_at', 'is_active']
        read_only_fields = ['client'] # CORRECTION : Évite le blocage à la création par le client

    def get_client_detail(self, obj):
        return ClientDetailSerializer(obj.client).data if obj.client else None


class PaiementSerializer(serializers.ModelSerializer):
    client_detail = serializers.SerializerMethodField(read_only=True)
    montant = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        model = Paiement
        fields = ['id', 'date', 'montant', 'mode', 'location', 'client', 'client_detail', 'contrat', 'statut', 'created_at', 'updated_at', 'is_active']
        read_only_fields = ['client'] # CORRECTION

    def get_client_detail(self, obj):
        return ClientDetailSerializer(obj.client).data if obj.client else None


class ReservationSerializer(serializers.ModelSerializer):
    montant_calcule = serializers.SerializerMethodField(read_only=True)
    client_detail = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Reservation
        fields = ['id', 'date_debut', 'montant_calcule', 'date_fin', 'bureau', 'client', 'client_detail', 'created_at', 'updated_at', 'is_active']
        read_only_fields = ['client'] # CORRECTION

    def get_montant_calcule(self, obj):
        if obj.bureau and obj.date_debut and obj.date_fin:
            delta = obj.date_fin - obj.date_debut
            nombre_jours = delta.days 
            montant_total = nombre_jours * float(obj.bureau.prix) / 2
            return round(montant_total, 2)
        return 0.0
    
    def get_client_detail(self, obj):
        return ClientDetailSerializer(obj.client).data if obj.client else None