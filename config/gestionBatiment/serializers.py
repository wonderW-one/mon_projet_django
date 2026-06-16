from rest_framework import serializers
from django.contrib.auth.models import User 
from .models import Client, Batiment, Niveau,  TypeBureau, Bureau, Reservation,  Contrat, Location, Paiement



class ClientSerializer(serializers.ModelSerializer):
    user_detail = serializers.SerializerMethodField(method_name='get_user')
    telephone = serializers.SerializerMethodField()
    class Meta:
        model = Client
        fields = ['id', 'user', 'user_detail', 'telephone', 'addresse', 'date_naissance', 'created_at', 'updated_at']
        read_only_fields = ['user']

    def get_telephone(self, obj):
        """Convertit l'objet PhoneNumber en chaîne de caractères propre pour le JSON"""
        if obj.telephone:
            return obj.telephone.as_e164  # Génère un format propre standardisé (+237...)
        return None

    def get_user_detail(self, obj):
        if obj.user:
            return {
                'id': obj.user.id,
                'username': obj.user.username,
                'first_name': obj.user.first_name,
                'last_name': obj.user.last_name,
                'email': obj.user.email,
                'telephone': obj.telephone.as_e164,
            }
        return None
        
class BatimentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batiment
        fields = ['id', 'nom', 'adresse', 'nombre_etages', 'date_construction', 'created_at', 'updated_at', 'is_active']
        
        


class NiveauSerializer(serializers.ModelSerializer):
    batiment_detail = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Niveau
        fields = ['id', 'nom', 'batiment', 'batiment_detail', 'created_at', 'updated_at', 'is_active']
    
    def get_batiment_detail(self, obj):
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
    type_detail = serializers.SerializerMethodField(read_only=True)
    batiment_detail = serializers.SerializerMethodField(read_only=True)
    niveau_detail = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Bureau
        fields = ['id', 'numero', 'type', 'type_detail', 'unite', 'espace', 'prix', 'batiment', 'batiment_detail', 'niveau', 'niveau_detail', 'created_at', 'updated_at', 'is_active']

    def get_type_detail(self, obj):
        if obj.type:
            return {
                'id': obj.type.id,
                'nom': obj.type.nom,
                'description': obj.type.description,
            }
        return None

    def get_batiment_detail(self, obj):
        if obj.batiment:
            return {
                'id': obj.batiment.id,
                'nom': obj.batiment.nom,
                'adresse': obj.batiment.adresse,
                'nombre_etages': obj.batiment.nombre_etages,
                'date_construction': obj.batiment.date_construction,
            }
        return None

    def get_niveau_detail(self, obj):
        if obj.niveau:
            return {
                'id': obj.niveau.id,
                'nom': obj.niveau.nom,
                'batiment': obj.niveau.batiment.id if obj.niveau.batiment else None,
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
    client_detail = serializers.SerializerMethodField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    is_active = serializers.BooleanField(default=True)

    class Meta:
        model = Location
        fields = ['id', 'date_debut', 'date_fin', 'bureau', 'client', 'client_detail', 'created_at', 'updated_at', 'is_active']
       
       
    def get_client_detail(self, obj):
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
    client_detail = serializers.SerializerMethodField(read_only=True)
    mode = serializers.ChoiceField(choices=[('CASH', 'Espèces'), ('CARD', 'Carte bancaire'), ('TRANSFER', 'Virement bancaire')], default='CASH')
    montant = serializers.FloatField()
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    is_active = serializers.BooleanField(default=True)
    
    class Meta:
        model = Paiement
        fields = ['id', 'date', 'montant', 'mode', 'location', 'client', 'client_detail', 'contrat', 'statut', 'created_at', 'updated_at', 'is_active']

    def get_client_detail(self, obj):
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

class ReservationSerializer(serializers.ModelSerializer):
    montant_calcule = serializers.SerializerMethodField(read_only=True)
    client_detail = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Reservation
        fields = ['id', 'date_debut', 'montant_calcule', 'date_fin', 'bureau', 'client', 'client_detail', 'created_at', 'updated_at', 'is_active']
        

    def get_montant_calcule(self, obj):
        if obj.bureau and obj.date_debut and obj.date_fin:
            delta = obj.date_fin - obj.date_debut
            nombre_jours = delta.days 
            montant_total = nombre_jours * float(obj.bureau.prix) / 2
            return montant_total
        return 0.0
    
    def get_client_detail(self, obj):
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