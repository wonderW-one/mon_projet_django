from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import (
    Batiment,
    Bureau,
    Client,
    Contrat,
    Location,
    Niveau,
    Paiement,
    Reservation,
    TypeBureau,
)


class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email"]


class ClientDetailSerializer(serializers.ModelSerializer):
    user = UserDetailSerializer(read_only=True)
    telephone = serializers.SerializerMethodField()
    type_piece_identite_display = serializers.CharField(
        source="get_type_piece_identite_display", read_only=True
    )

    class Meta:
        model = Client
        fields = [
            "id",
            "user",
            "telephone",
            "addresse",
            "date_naissance",
            "lieu_naissance",
            "nationalite",
            "profession",
            "type_piece_identite",
            "type_piece_identite_display",
            "numero_piece_identite",
            "photo_profil",
            "created_at",
            "updated_at",
        ]

    def get_telephone(self, obj):
        return str(obj.telephone) if obj.telephone else None


class ClientSerializer(serializers.ModelSerializer):
    user_detail = serializers.SerializerMethodField(read_only=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True)

    username = serializers.CharField(write_only=True, required=False, max_length=150)
    password = serializers.CharField(write_only=True, required=False)
    email = serializers.EmailField(write_only=True, required=False)
    first_name = serializers.CharField(write_only=True, required=False, max_length=150)
    last_name = serializers.CharField(write_only=True, required=False, max_length=150)

    class Meta:
        model = Client
        fields = [
            # 🔴 BUG CORRIGÉ : 'id' (la clé primaire du profil Client) n'était pas
            # exposé par ce serializer. Or admin-dashboard.ts (onChangerRoleClient)
            # et api.ts (mettreAJourRoleClient) utilisent précisément client.id
            # pour construire l'URL PATCH /clients/{id}/ — sans ce champ, client.id
            # valait toujours "undefined" côté frontend et la requête échouait.
            "id",
            "user_id",
            "user_detail",
            "username",
            "password",
            "email",
            "first_name",
            "last_name",
            "telephone",
            "addresse",
            "date_naissance",
            "lieu_naissance",
            "nationalite",
            "profession",
            "type_piece_identite",
            "numero_piece_identite",
            "photo_profil",
            "role",
            "created_at",
            "updated_at",
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
            # 🔴 BUG CORRIGÉ : quand views.py appelle serializer.save(user=request.user)
            # (cas d'un utilisateur déjà authentifié), DRF injecte ce 'user' dans
            # validated_data. Le code créait pourtant TOUJOURS un nouveau User via
            # username/password puis faisait Client.objects.create(user=user, **validated_data)
            # → 'user' se retrouvait passé deux fois, d'où le TypeError
            # "got multiple values for keyword argument 'user'".
            # On distingue maintenant explicitement les deux cas.
            existing_user = validated_data.pop("user", None)

            username = validated_data.pop("username", None)
            password = validated_data.pop("password", None)
            email = validated_data.pop("email", "")
            first_name = validated_data.pop("first_name", "")
            last_name = validated_data.pop("last_name", "")
            # SÉCURITÉ : le rôle est toujours forcé à CLIENT lors de l'inscription publique,
            # quoi que le payload contienne (évite aussi un crash "role" en double via **validated_data)
            validated_data.pop("role", None)

            if existing_user is not None:
                # Cas : un utilisateur déjà authentifié complète/crée son profil client.
                # On réutilise son compte User existant, on ne crée rien d'autre.
                user = existing_user
            else:
                # Cas : inscription publique (anonyme) → un compte User est créé.
                if not username or not password:
                    raise serializers.ValidationError(
                        {
                            "detail": "Les champs 'username' et 'password' sont obligatoires pour créer un profil."
                        }
                    )

                # ✅ CORRIGÉ (FAILLE DE SÉCURITÉ) : avant, si le username existait déjà,
                # le code réutilisait silencieusement le compte existant et écrasait son
                # mot de passe avec celui fourni dans la requête — n'importe qui pouvait
                # ainsi prendre le contrôle d'un compte existant (y compris un ADMIN) en
                # "s'inscrivant" avec son nom d'utilisateur. On rejette maintenant
                # explicitement toute inscription sur un username déjà pris.
                if User.objects.filter(username=username).exists():
                    raise serializers.ValidationError(
                        {"username": "Ce nom d'utilisateur est déjà pris."}
                    )

                user = User.objects.create(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                )
                user.set_password(password)
                user.save()

            client = Client.objects.create(
                user=user, role=Client.UserRole.CLIENT, **validated_data
            )
            return client

    def update(self, instance, validated_data):
        user_data = {}
        for field in ["username", "email", "first_name", "last_name"]:
            if field in validated_data:
                user_data[field] = validated_data.pop(field)

        password = validated_data.pop("password", None)

        # SÉCURITÉ : seul un ADMIN peut modifier le rôle d'un profil (le sien ou celui d'un autre).
        if "role" in validated_data:
            request = self.context.get("request")
            est_admin = bool(
                request
                and request.user
                and (
                    request.user.is_superuser
                    or getattr(
                        getattr(request.user, "client_profile", None), "role", None
                    )
                    == "ADMIN"
                )
            )
            if not est_admin:
                validated_data.pop("role")

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
    proprietaire_type_piece_display = serializers.CharField(
        source="get_proprietaire_type_piece_display", read_only=True
    )

    class Meta:
        model = Batiment
        fields = [
            "id",
            "nom",
            "adresse",
            "nombre_etages",
            "date_construction",
            "created_at",
            "updated_at",
            "is_active",
            "proprietaire_nom",
            "proprietaire_prenom",
            "proprietaire_telephone",
            "proprietaire_email",
            "proprietaire_adresse",
            "proprietaire_type_piece",
            "proprietaire_type_piece_display",
            "proprietaire_numero_piece",
        ]


class NiveauSerializer(serializers.ModelSerializer):
    batiment_detail = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Niveau
        fields = [
            "id",
            "nom",
            "batiment",
            "batiment_detail",
            "created_at",
            "updated_at",
            "is_active",
        ]

    def get_batiment_detail(self, obj):
        if obj.batiment:
            return {
                "id": obj.batiment.id,
                "nom": obj.batiment.nom,
                "adresse": obj.batiment.adresse,
                "nombre_etages": obj.batiment.nombre_etages,
                "date_construction": obj.batiment.date_construction,
            }
        return None


class TypeBureauSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypeBureau
        fields = ["id", "nom", "description", "created_at", "is_active"]


class BureauSerializer(serializers.ModelSerializer):
    type_detail = serializers.SerializerMethodField(read_only=True)
    batiment_detail = serializers.SerializerMethodField(read_only=True)
    niveau_detail = serializers.SerializerMethodField(read_only=True)
    date_disponibilite_prevue = serializers.ReadOnlyField()

    class Meta:
        model = Bureau
        fields = [
            "id",
            "numero",
            "type",
            "type_detail",
            "unite",
            "espace",
            "prix",
            "batiment",
            "batiment_detail",
            "niveau",
            "niveau_detail",
            "statut",
            "date_disponibilite_prevue",  # <-- Ajouté ici
        ]
        read_only_fields = ["prix", "statut"]

    def get_type_detail(self, obj):
        if obj.type:
            return {
                "id": obj.type.id,
                "nom": obj.type.nom,
                "description": obj.type.description,
            }
        return None

    def get_batiment_detail(self, obj):
        if obj.batiment:
            # 🟢 AJOUT : on inclut désormais les coordonnées du propriétaire du
            # bâtiment. Elles servent à alimenter la section "Contact Us" côté
            # client (modal) pour qu'il puisse joindre un responsable. Ces champs
            # sont déjà en lecture seule ici (SerializerMethodField), donc aucun
            # risque de modification côté client — uniquement de la lecture, déjà
            # autorisée pour CLIENT via BureauPermission (SAFE_METHODS).
            return {
                "id": obj.batiment.id,
                "nom": obj.batiment.nom,
                "adresse": obj.batiment.adresse,
                "nombre_etages": obj.batiment.nombre_etages,
                "date_construction": obj.batiment.date_construction,
                "proprietaire_nom": obj.batiment.proprietaire_nom,
                "proprietaire_prenom": obj.batiment.proprietaire_prenom,
                "proprietaire_telephone": str(obj.batiment.proprietaire_telephone)
                if obj.batiment.proprietaire_telephone
                else None,
                "proprietaire_email": obj.batiment.proprietaire_email,
            }
        return None

    def get_niveau_detail(self, obj):
        if obj.niveau:
            return {
                "id": obj.niveau.id,
                "nom": obj.niveau.nom,
                "batiment": obj.niveau.batiment.id if obj.niveau.batiment else None,
            }
        return None

    def create(self, validated_data):
        user = validated_data.pop("user", None)
        bureau = Bureau(**validated_data)
        bureau.save(user=user)
        return bureau

    def update(self, instance, validated_data):
        user = validated_data.pop("user", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(user=user)
        return instance


# serializers.py


class ContratSerializer(serializers.ModelSerializer):
    montant = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    client_detail = serializers.SerializerMethodField(read_only=True)
    # ✅ AJOUT : le frontend (fiche client staff/admin) a besoin de savoir à quel
    # bureau un contrat est rattaché, que ce soit via une location directe
    # (self.bureau) ou via une réservation convertie (self.reservation.bureau).
    bureau_detail = serializers.SerializerMethodField(read_only=True)
    reservation_detail = serializers.SerializerMethodField(read_only=True)
    created_by = UserDetailSerializer(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    is_active = serializers.BooleanField(default=True)
    locations = serializers.SerializerMethodField(read_only=True)
    paiements = serializers.SerializerMethodField(read_only=True)
    document_contrat_signe = serializers.FileField(required=False, allow_null=True)
    statut = serializers.ChoiceField(
        choices=Contrat.ContratStatus.choices, read_only=True
    )
    periodicite_display = serializers.CharField(
        source="get_periodicite_display", read_only=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            profile = getattr(request.user, "client_profile", None)
            if profile and profile.role == "CLIENT":
                self.fields["document_contrat_signe"].read_only = True
                self.fields[
                    "date_debut"
                ].read_only = True  # AJOUT : fixée à la validation
                self.fields["client"].read_only = True  # AJOUT : forcé par la vue

    class Meta:
        model = Contrat
        fields = [
            "id",
            "reservation",
            "bureau",
            "client",
            "client_detail",
            "bureau_detail",
            "reservation_detail",
            "statut",
            "date_debut",
            "date_fin",
            "date_paiement",
            "montant",
            "description",
            "created_by",
            "created_at",
            "updated_at",
            "is_active",
            "locations",
            "paiements",
            "periodicite",
            "periodicite_display",
            "document_contrat_signe",
        ]
        read_only_fields = [
            "created_by",
            "created_at",
            "updated_at",
            "is_active",
            "locations",
            "paiements",
            "statut",
        ]

    def get_client_detail(self, obj):
        if obj.client:
            return {
                "id": obj.client.id,
                "user": {
                    "id": obj.client.user.id,
                    "username": obj.client.user.username,
                    "first_name": obj.client.user.first_name,
                    "last_name": obj.client.user.last_name,
                    "email": obj.client.user.email,
                },
                "telephone": (
                    str(obj.client.telephone) if obj.client.telephone else None
                ),
                "addresse": obj.client.addresse,
                "date_naissance": obj.client.date_naissance,
                "lieu_naissance": obj.client.lieu_naissance,
                "nationalite": obj.client.nationalite,
                "profession": obj.client.profession,
                "type_piece_identite": obj.client.type_piece_identite,
                "type_piece_identite_display": obj.client.get_type_piece_identite_display(),
                "numero_piece_identite": obj.client.numero_piece_identite,
                "photo_profil": (
                    obj.client.photo_profil.url if obj.client.photo_profil else None
                ),
            }
        return None

    def get_bureau_detail(self, obj):
        bureau = obj.bureau_effectif
        if not bureau:
            return None
        return {
            "id": bureau.id,
            "numero": bureau.numero,
            "statut": bureau.statut,
        }

    def get_reservation_detail(self, obj):
        if not obj.reservation:
            return None
        return {
            "id": obj.reservation.id,
            "date_debut": obj.reservation.date_debut,
            "date_fin": obj.reservation.date_fin,
            "bureau_detail": self.get_bureau_detail(obj),
        }

    def validate(self, attrs):
        reservation = attrs.get("reservation") or (
            self.instance.reservation if self.instance else None
        )
        bureau = attrs.get("bureau") or (
            self.instance.bureau if self.instance else None
        )
        if not reservation and not bureau:
            raise serializers.ValidationError(
                "Il faut fournir soit 'reservation', soit 'bureau' (location directe)."
            )
        if reservation and bureau:
            raise serializers.ValidationError(
                "Fournissez soit 'reservation', soit 'bureau' — pas les deux."
            )
        if bureau and bureau.statut == Bureau.BureauStatus.OCCUPE and not self.instance:
            raise serializers.ValidationError(
                {"bureau": "Ce bureau n'est pas disponible."}
            )

        # 🟢 AJOUT : bloque toute date passée sur les contrats (idem réservations).
        # Le champ "date_debut" est en lecture seule pour un CLIENT (voir __init__
        # ci-dessus), donc ce contrôle vise surtout ADMIN/TRAVAILLEUR/MANAGER qui
        # peuvent la préciser manuellement lors d'une location directe.
        date_debut = attrs.get("date_debut") or (
            self.instance.date_debut if self.instance else None
        )
        date_fin = attrs.get("date_fin") or (
            self.instance.date_fin if self.instance else None
        )
        aujourdhui = timezone.localdate()

        if "date_debut" in attrs and date_debut and date_debut < aujourdhui:
            raise serializers.ValidationError(
                {
                    "date_debut": "La date de début ne peut pas être antérieure à aujourd'hui."
                }
            )

        if "date_fin" in attrs and date_fin and date_fin < aujourdhui:
            raise serializers.ValidationError(
                {"date_fin": "La date de fin ne peut pas être antérieure à aujourd'hui."}
            )

        if date_debut and date_fin and date_fin < date_debut:
            raise serializers.ValidationError(
                {"date_fin": "La date de fin doit être postérieure ou égale à la date de début."}
            )

        return attrs

    def get_locations(self, obj):
        qs = obj.locations.all()
        return [
            {
                "id": loc.id,
                "date_debut": loc.date_debut,
                "date_fin": loc.date_fin,
                "bureau_id": loc.bureau_id,
            }
            for loc in qs
        ]

    def get_paiements(self, obj):
        qs = obj.paiements.all()
        return [
            {
                "id": p.id,
                "date": p.date,
                "montant": str(p.montant),
                "mode": p.mode,
                "statut": p.statut,
                "location_id": p.location_id,
                "client_id": p.client_id,
            }
            for p in qs
        ]

    def create(self, validated_data):
        user = validated_data.pop("user", None)
        contrat = Contrat(**validated_data)
        contrat.save(user=user)
        return contrat

    def update(self, instance, validated_data):
        user = validated_data.pop("user", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(user=user)
        return instance


class ReservationSerializer(serializers.ModelSerializer):
    client_detail = serializers.SerializerMethodField(read_only=True)
    bureau_detail = serializers.SerializerMethodField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    is_active = serializers.BooleanField(default=True)
    # ✅ AJOUT : le statut d'approbation, jamais modifiable directement par un client
    # (seules les actions dédiées 'valider'/'rejeter' côté vue peuvent le changer).
    statut = serializers.ChoiceField(
        choices=Reservation.ReservationStatus.choices, read_only=True
    )

    # 🔴 BUG CORRIGÉ : sans ceci, le champ 'client' restait toujours obligatoire
    # dans le payload JSON. Or la vue (ReservationViewSet.perform_create) ne le
    # transmet en dur (client=profile) QUE pour un CLIENT — mais cette injection
    # arrive APRÈS la validation du serializer, qui rejetait déjà la requête
    # avec "client: This field is required." avant même d'atteindre perform_create.
    # On applique ici le même correctif que ContratSerializer : 'client' devient
    # facultatif/lecture-seule pour un CLIENT (déduit automatiquement de son
    # profil), mais reste modifiable pour ADMIN/TRAVAILLEUR/MANAGER qui doivent
    # préciser pour quel client ils créent la réservation.
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            profile = getattr(request.user, "client_profile", None)
            if profile and profile.role == "CLIENT":
                self.fields["client"].required = False
                self.fields["client"].read_only = True

    class Meta:
        model = Reservation
        fields = [
            "id",
            "date_debut",
            "date_fin",
            "bureau",
            "client",
            "client_detail",
            "bureau_detail",
            "statut",
            "created_at",
            "updated_at",
            "is_active",
        ]
        read_only_fields = ["statut"]

    def get_client_detail(self, obj):
        if obj.client:
            return {
                "id": obj.client.id,
                "user": {
                    "id": obj.client.user.id,
                    "username": obj.client.user.username,
                    "first_name": obj.client.user.first_name,
                    "last_name": obj.client.user.last_name,
                    "email": obj.client.user.email,
                },
                "telephone": (
                    str(obj.client.telephone) if obj.client.telephone else None
                ),
                "addresse": obj.client.addresse,
                "date_naissance": obj.client.date_naissance,
                "lieu_naissance": obj.client.lieu_naissance,
                "nationalite": obj.client.nationalite,
                "profession": obj.client.profession,
                "type_piece_identite": obj.client.type_piece_identite,
                "type_piece_identite_display": obj.client.get_type_piece_identite_display(),
                "numero_piece_identite": obj.client.numero_piece_identite,
                "photo_profil": (
                    obj.client.photo_profil.url if obj.client.photo_profil else None
                ),
            }
        return None

    def get_bureau_detail(self, obj):
        if obj.bureau:
            return {
                "id": obj.bureau.id,
                "numero": obj.bureau.numero,
                "batiment": obj.bureau.batiment.nom if obj.bureau.batiment else None,
                "niveau": obj.bureau.niveau.nom if obj.bureau.niveau else None,
                "prix": str(obj.bureau.prix) if obj.bureau.prix else None,
                "statut": obj.bureau.statut,
            }
        return None

    # 🟢 AJOUT : bloque côté serveur toute réservation dont la date de début (ou
    # de fin) est déjà passée. Le contrôle côté frontend (attribut HTML "min")
    # peut être contourné (DevTools, appel direct à l'API) : cette validation
    # est donc la protection réelle.
    def validate(self, attrs):
        date_debut = attrs.get("date_debut") or (
            self.instance.date_debut if self.instance else None
        )
        date_fin = attrs.get("date_fin") or (
            self.instance.date_fin if self.instance else None
        )

        aujourdhui = timezone.localdate()

        # On ne vérifie "date_debut dans le passé" que si elle est fournie/modifiée
        # dans la requête (à la création, ou si un ADMIN/TRAVAILLEUR la modifie
        # explicitement) — on ne casse pas les réservations existantes déjà en cours.
        if "date_debut" in attrs and date_debut and date_debut < aujourdhui:
            raise serializers.ValidationError(
                {
                    "date_debut": "La date de début ne peut pas être antérieure à aujourd'hui."
                }
            )

        if "date_fin" in attrs and date_fin and date_fin < aujourdhui:
            raise serializers.ValidationError(
                {"date_fin": "La date de fin ne peut pas être antérieure à aujourd'hui."}
            )

        if date_debut and date_fin and date_fin < date_debut:
            raise serializers.ValidationError(
                {"date_fin": "La date de fin doit être postérieure ou égale à la date de début."}
            )

        return attrs

    # ✅ AJOUT : nécessaire pour que le "user" transmis par la vue (perform_create)
    # atteigne bien Reservation.save(user=...) et déclenche la logique EN_ATTENTE.
    def create(self, validated_data):
        user = validated_data.pop("user", None)
        reservation = Reservation(**validated_data)
        reservation.save(user=user)
        return reservation

    def update(self, instance, validated_data):
        user = validated_data.pop("user", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(user=user)
        return instance


class LocationSerializer(serializers.ModelSerializer):
    client_detail = serializers.SerializerMethodField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    is_active = serializers.BooleanField(default=True)

    class Meta:
        model = Location
        fields = [
            "id",
            "date_debut",
            "date_fin",
            "bureau",
            "contrat",
            "client",
            "client_detail",
            "created_at",
            "updated_at",
            "is_active",
        ]
        read_only_fields = ["date_debut", "date_fin"]

    def get_client_detail(self, obj):
        if obj.client:
            return {
                "id": obj.client.id,
                "user": {
                    "id": obj.client.user.id,
                    "username": obj.client.user.username,
                    "first_name": obj.client.user.first_name,
                    "last_name": obj.client.user.last_name,
                    "email": obj.client.user.email,
                },
                "telephone": (
                    str(obj.client.telephone) if obj.client.telephone else None
                ),
                "addresse": obj.client.addresse,
                "date_naissance": obj.client.date_naissance,
                "lieu_naissance": obj.client.lieu_naissance,
                "nationalite": obj.client.nationalite,
                "profession": obj.client.profession,
                "type_piece_identite": obj.client.type_piece_identite,
                "type_piece_identite_display": obj.client.get_type_piece_identite_display(),
                "numero_piece_identite": obj.client.numero_piece_identite,
                "photo_profil": (
                    obj.client.photo_profil.url if obj.client.photo_profil else None
                ),
            }
        return None


class PaiementSerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(), required=False, allow_null=True
    )
    client_detail = serializers.SerializerMethodField(read_only=True)
    created_by = UserDetailSerializer(read_only=True)
    mode = serializers.ChoiceField(
        choices=[
            ("CASH", "Espèces"),
            ("CARD", "Carte bancaire"),
            ("TRANSFER", "Virement bancaire"),
        ],
        default="CASH",
    )
    montant = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
    )
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    is_active = serializers.BooleanField(default=True)

    class Meta:
        model = Paiement
        fields = [
            "id",
            "date",
            "montant",
            "mode",
            "location",
            "client",
            "client_detail",
            "contrat",
            "statut",
            "mois_paye",
            "annee_paye",
            "created_by",
            "created_at",
            "updated_at",
            "is_active",
        ]
        read_only_fields = [
            "created_by",
            "statut",
            "created_at",
            "updated_at",
            "is_active",
            "date",
        ]

    def get_client_detail(self, obj):
        if obj.client:
            return {
                "id": obj.client.id,
                "user": {
                    "id": obj.client.user.id,
                    "username": obj.client.user.username,
                    "first_name": obj.client.user.first_name,
                    "last_name": obj.client.user.last_name,
                    "email": obj.client.user.email,
                },
                "telephone": (
                    str(obj.client.telephone) if obj.client.telephone else None
                ),
                "addresse": obj.client.addresse,
                "date_naissance": obj.client.date_naissance,
                "lieu_naissance": obj.client.lieu_naissance,
                "nationalite": obj.client.nationalite,
                "profession": obj.client.profession,
                "type_piece_identite": obj.client.type_piece_identite,
                "type_piece_identite_display": obj.client.get_type_piece_identite_display(),
                "numero_piece_identite": obj.client.numero_piece_identite,
                "photo_profil": (
                    obj.client.photo_profil.url if obj.client.photo_profil else None
                ),
            }
        return None

    def validate(self, attrs):
        client = attrs.get("client")
        contrat = attrs.get("contrat")
        location = attrs.get("location")

        if not client and not contrat and not location:
            raise serializers.ValidationError(
                "Un paiement doit etre lie a un client, un contrat ou une location."
            )

        if client and contrat and contrat.client_id != client.id:
            raise serializers.ValidationError(
                {"client": "Le client ne correspond pas au client du contrat."}
            )

        if client and location and location.client_id != client.id:
            raise serializers.ValidationError(
                {"client": "Le client ne correspond pas au client de la location."}
            )

        # ✅ AJOUT : un paiement ne peut être soumis/affiché comme faisable que si le
        # contrat associé est déjà VALIDE. Sécurité côté API — même contournement
        # frontend impossible. (Vérification également faite dans Paiement.clean()
        # au niveau du modèle, en filet de sécurité supplémentaire.)
        if contrat and contrat.statut != Contrat.ContratStatus.VALIDE:
            raise serializers.ValidationError(
                {
                    "contrat": "Impossible d'enregistrer un paiement : ce contrat n'a pas encore été approuvé."
                }
            )

        return attrs

    def create(self, validated_data):
        user = validated_data.pop("user", None)
        contrat = validated_data.get("contrat")
        location = validated_data.get("location")
        client = validated_data.get("client")

        if not client:
            if contrat:
                if hasattr(contrat, "client"):
                    validated_data["client"] = contrat.client
                elif isinstance(contrat, int):
                    try:
                        validated_data["client"] = Contrat.objects.get(
                            pk=contrat
                        ).client
                    except Contrat.DoesNotExist:
                        pass
            elif location:
                if hasattr(location, "client"):
                    validated_data["client"] = location.client
                elif isinstance(location, int):
                    try:
                        validated_data["client"] = Location.objects.get(
                            pk=location
                        ).client
                    except Location.DoesNotExist:
                        pass

        paiement = Paiement(**validated_data)
        paiement.save(user=user)
        return paiement

    def update(self, instance, validated_data):
        user = validated_data.pop("user", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(user=user)
        return instance