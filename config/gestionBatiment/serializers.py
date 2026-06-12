from rest_framework import serializers
from django.contrib.auth.models import User 
from .models import Client, Batiment, Niveau, TypeBureau, Bureau, Reservation, Contrat, Location, Paiement


class ClientSerializer(serializers.ModelSerializer):
    user_details = serializers.SerializerMethodField(method_name='get_user')

    class Meta:
        model = Client
        fields = ['id', 'user', 'user_details', 'telephone', 'addresse', 'date_naissance', 'created_at', 'updated_at']

    def get_user(self, obj):
        if obj.user:
            return {
                'id': obj.user.id,
                'username': obj.user.username,
                'first_name': obj.user.first_name,
                'last_name': obj.user.last_name,
                'email': obj.user.email,
            }
        return None


class BatimentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batiment
        fields = ['id', 'nom', 'adresse', 'nombre_etages', 'date_construction', 'created_at', 'updated_at', 'is_active']


class NiveauSerializer(serializers.ModelSerializer):
    batiment_details = serializers.SerializerMethodField(method_name='get_batiment')

    class Meta:
        model = Niveau
        fields = ['id', 'nom', 'batiment', 'batiment_details', 'created_at', 'updated_at', 'is_active']
    
    def get_batiment(self, obj):
        if obj.batiment:
            return {
                'id': obj.batiment.id,
                'nom': obj.batiment.nom,
                'adresse': obj.batiment.adresse,
                'nombre_etages': obj.batiment.nombre_etages,
                'date_construction': obj.batiment.date_construction,
            }
        return None


class TypeBureauSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypeBureau
        fields = ['id', 'nom', 'description', 'created_at', 'is_active']


class BureauSerializer(serializers.ModelSerializer):
    typebureau = serializers.SerializerMethodField(method_name='get_type')
    batiment_details = serializers.SerializerMethodField(method_name='get_batiment')
    niveau_details = serializers.SerializerMethodField(method_name='get_niveau')

    class Meta:
        model = Bureau
        fields = ['id', 'numero', 'type', 'typebureau', 'unite', 'espace', 'prix', 'batiment', 'batiment_details', 'niveau', 'niveau_details', 'created_at', 'updated_at', 'is_active']

    def get_type(self, obj):
        if obj.type:
            return {
                'id': obj.type.id,
                'nom': obj.type.nom,
                'description': obj.type.description,
            }
        return None

    def get_batiment(self, obj):
        if obj.batiment:
            return {
                'id': obj.batiment.id,
                'nom': obj.batiment.nom,
                'adresse': obj.batiment.adresse,
            }
        return None

    def get_niveau(self, obj):
        if obj.niveau:
            return {
                'id': obj.niveau.id,
                'nom': obj.niveau.nom,
            }
        return None


class ReservationSerializer(serializers.ModelSerializer):
    montant_calcule = serializers.SerializerMethodField(read_only=True)
    client_details = serializers.SerializerMethodField(method_name='get_client')
    bureau_details = serializers.SerializerMethodField(method_name='get_bureau')

    class Meta:
        model = Reservation
        fields = ['id', 'date_debut', 'date_fin', 'montant_calcule', 'bureau', 'bureau_details', 'client', 'client_details', 'created_at', 'updated_at', 'is_active']

    def get_montant_calcule(self, obj):
        if obj.bureau and obj.date_debut and obj.date_fin:
            delta = obj.date_fin - obj.date_debut
            nombre_jours = max(delta.days, 0)
            montant_total = nombre_jours * float(obj.bureau.prix) / 2
            return montant_total
        return 0.0
    
    def get_client(self, obj):
        if obj.client:
            return {
                'id': obj.client.id,
                'user': {
                    'id': obj.client.user.id,
                    'username': obj.client.user.username,
                    'first_name': obj.client.user.first_name,
                    'last_name': obj.client.user.last_name,
                    'email': obj.client.user.email,
                },
                'telephone': str(obj.client.telephone) if obj.client.telephone else None,
                'addresse': obj.client.addresse,
                'date_naissance': obj.client.date_naissance,
            }
        return None

    def get_bureau(self, obj):
        if obj.bureau:
            return {
                'id': obj.bureau.id,
                'nom': f"Bureau N° {obj.bureau.numero}",
                'typebureau': {'nom': obj.bureau.type.nom if obj.bureau.type else 'Standard'}
            }
        return None


class ContratSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    is_active = serializers.BooleanField(default=True)

    class Meta:
        model = Contrat
        fields = ['id', 'reservation', 'client', 'date_debut', 'date_fin', 'montant', 'description', 'created_at', 'updated_at', 'is_active']


class LocationSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    is_active = serializers.BooleanField(default=True)
    client_details = serializers.SerializerMethodField(method_name='get_client')

    class Meta:
        model = Location
        fields = ['id', 'date_debut', 'date_fin', 'bureau', 'client', 'client_details', 'created_at', 'updated_at', 'is_active']
       
    def get_client(self, obj):
        if obj.client:
            return {
                'id': obj.client.id,
                'user': {
                    'id': obj.client.user.id,
                    'username': obj.client.user.username,
                    'first_name': obj.client.user.first_name,
                    'last_name': obj.client.user.last_name,
                    'email': obj.client.user.email,
                },
                'telephone': str(obj.client.telephone) if obj.client.telephone else None,
                'addresse': obj.client.addresse,
                'date_naissance': obj.client.date_naissance,
            }
        return None 


class PaiementSerializer(serializers.ModelSerializer):
    mode = serializers.ChoiceField(choices=[('CASH', 'Espèces'), ('CARD', 'Carte bancaire'), ('TRANSFER', 'Virement bancaire')], default='CASH')
    montant = serializers.FloatField()
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    is_active = serializers.BooleanField(default=True)
    client_details = serializers.SerializerMethodField(method_name='get_client')
    bureau = serializers.SerializerMethodField(method_name='get_bureau_depuis_location')
    methode_display = serializers.CharField(source='get_mode_display', read_only=True)
    status_display = serializers.CharField(source='get_statut_display', read_only=True)

    class Meta:
        model = Paiement
        fields = ['id', 'date', 'montant', 'mode', 'methode_display', 'location', 'bureau', 'client', 'client_details', 'contrat', 'statut', 'status_display', 'created_at', 'updated_at', 'is_active']

    def get_client(self, obj):
        if obj.client:
            return {
                'id': obj.client.id,
                'user': {
                    'id': obj.client.user.id,
                    'username': obj.client.user.username,
                    'first_name': obj.client.user.first_name,
                    'last_name': obj.client.user.last_name,
                    'email': obj.client.user.email,
                },
                'telephone': str(obj.client.telephone) if obj.client.telephone else None,
                'addresse': obj.client.addresse,
                'date_naissance': obj.client.date_naissance,
            }
        return None 

    def get_bureau_depuis_location(self, obj):
        # Dans votre modèle Paiement, la clé étrangère s'appelle "location" mais pointe vers le modèle Bureau
        if obj.location: 
            return {
                'id': obj.location.id,
                'nom': f"Bureau {obj.location.numero}"
            }
        return None