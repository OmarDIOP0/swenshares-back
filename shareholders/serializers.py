# serializers.py
from xml.dom.minidom import DocumentType
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Address, ContactPerson, PhysicalShareholder, LegalShareholder, KeycloakUser, Share, FileDocument, DocumentType


class FileDocumentSerializer(serializers.ModelSerializer):
    """
    Serializer for managing file documents
    """
    document_type = serializers.ChoiceField(choices=DocumentType.choices)
    file = serializers.FileField()

    class Meta:
        model = FileDocument
        fields = [
            'id', 
            'file', 
            'document_type', 
            'description', 
            'uploaded_at', 
            'is_verified'
        ]
        read_only_fields = ['id', 'uploaded_at', 'is_verified']

    def create(self, validated_data):
        """
        Custom create method to handle generic relation
        """
        request = self.context.get('request')
        view = self.context.get('view')
        
        # Get the parent object (shareholder in this case)
        parent_object = view.get_object()
        
        validated_data['uploaded_by'] = request.user
        validated_data['content_object'] = parent_object
        
        return FileDocument.objects.create(**validated_data)

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer pour les informations basiques de l'utilisateur
    """
    class Meta:
        model = User
        fields = ('id', 'username', 'email')
        read_only_fields = fields

class KeycloakUserSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = KeycloakUser
        fields = ('id', 'user', 'keycloak_id', 'username', 'email', 'roles', 'is_active')
        read_only_fields = fields

class AddressSerializer(serializers.ModelSerializer):
    """
    Serializer pour les adresses avec validation personnalisée
    """
    class Meta:
        model = Address
        fields = ('id', 'street', 'city', 'postal_code', 'country', 
                 'is_primary', 'effective_date', 'full_address')
        read_only_fields = ('full_address',)

    def validate_postal_code(self, value):
        """Validation personnalisée pour le code postal"""
        if not value.strip():
            raise serializers.ValidationError("Le code postal ne peut pas être vide")
        return value

    def validate(self, data):
        if data.get('is_primary'):
            # Si c'est une adresse principale, vérifier la date d'effet
            if not data.get('effective_date'):
                raise serializers.ValidationError({
                    'effective_date': "La date d'effet est requise pour une adresse principale"
                })
        return data

class ContactPersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactPerson
        fields = ('id', 'first_name', 'last_name', 'email', 'phone',
                 'created_at', 'updated_at')
        read_only_fields = ('created_at', 'updated_at')

class BaseShareholderSerializer(serializers.ModelSerializer):
    """
    Serializer de base pour les actionnaires avec les champs communs
    """
    addresses = AddressSerializer(many=True, required=False)
    contact_person = ContactPersonSerializer()
    created_by = UserSerializer(read_only=True)
    examined_by = UserSerializer(read_only=True)
    approved_by = UserSerializer(read_only=True)
    dividends = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    status = serializers.CharField(read_only=True)
    history = serializers.JSONField(read_only=True)

    def create_addresses(self, shareholder, addresses_data):
        """Crée les adresses associées à l'actionnaire"""
        for address_data in addresses_data:
            address = Address.objects.create(**address_data)
            shareholder.addresses.add(address)

    def create_contact_person(self, contact_person_data):
        contact_person, _ = ContactPerson.objects.get_or_create(**contact_person_data)
        return contact_person


    def handle_addresses_and_contact(self, instance, validated_data):
        """Met à jour les adresses ou les contacts personnes existantes ou en crée de nouvelles"""
        addresses_data = validated_data.pop('addresses', None)
        contact_person_data = validated_data.pop('contact_person', None)

        if contact_person_data:
            if instance.contact_person:
                for attr, value in contact_person_data.items():
                    setattr(instance.contact_person, attr, value)
                instance.contact_person.save()
            else:
                instance.contact_person = self.create_contact_person(contact_person_data)

        if addresses_data is not None:
            instance.addresses.clear()
            self.create_addresses(instance, addresses_data)


    def create(self, validated_data):
        addresses_data = validated_data.pop('addresses', [])
        contact_person_data = validated_data.pop('contact_person', None)
        
        # Utilisation de get_or_create pour éviter les doublons
        if contact_person_data:
            contact_person, _ = ContactPerson.objects.get_or_create(**contact_person_data)
            validated_data['contact_person'] = contact_person

        shareholder = self.Meta.model.objects.create(**validated_data)

        self.create_addresses(shareholder, addresses_data)
        
        return shareholder
    
    def update_contact_person(self, instance, contact_person_data):
        if instance.contact_person:
            for attr, value in contact_person_data.items():
                setattr(instance.contact_person, attr, value)
            instance.contact_person.save()
        else:
            instance.contact_person = self.create_contact_person(contact_person_data)



    def update(self, instance, validated_data):
        self.handle_addresses_and_contact(instance, validated_data)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class PhysicalShareholderSerializer(BaseShareholderSerializer):
    """
    Serializer pour les actionnaires physiques avec validation personnalisée
    """
    class Meta:
        model = PhysicalShareholder
        fields = ('id', 'national_id', 'national_id_expiration', 'date_of_birth',
                  'addresses', 'contact_person', 'created_by', 'examined_by',
                  'approved_by', 'status', 'effective_date', 'activity_sector',
                  'created_at', 'updated_at', 'notes', 'total_shares',
                  'dividends', 'reference_number', 'issuing_company')
        read_only_fields = ('id', 'created_by', 'examined_by', 'approved_by',
                            'status', 'created_at', 'updated_at', 'history')

    def validate_email(self, value):
        """Validation personnalisée pour l'email"""
        if PhysicalShareholder.objects.filter(email=value).exclude(id=self.instance.id if self.instance else None).exists():
            raise serializers.ValidationError("Cet email est déjà utilisé.")
        return value


class LegalShareholderSerializer(BaseShareholderSerializer):
    """
    Serializer pour les actionnaires moraux avec validation personnalisée
    """
    class Meta:
        model = LegalShareholder
        fields = ('id', 'company_name', 'registration_number', 'tax_id',
                  'legal_representative', 'representative_email',
                  'representative_phone', 'capital_percentage', 'is_group_member',
                  'group_percentage', 'addresses', 'effective_beneficiary',
                  'visa_date', 'contact_person', 'created_by',
                  'examined_by', 'approved_by', 'status', 'effective_date',
                  'activity_sector', 'created_at', 'updated_at',
                  'notes', 'total_shares', 'dividends', 'reference_number',
                  'issuing_company')
        read_only_fields = ('id', 'created_by', 'examined_by', 'approved_by',
                            'status', 'created_at', 'updated_at', 'history')

    def validate(self, data):
        if data.get('is_group_member') and not data.get('group_percentage'):
            raise serializers.ValidationError({
                'group_percentage': "Le pourcentage du groupe est requis pour les membres d'un groupe"
            })
        return data


class ShareSerializer(serializers.ModelSerializer):
    # history = serializers.JSONField(read_only=True)
    
    class Meta:
        model = Share
        fields = ('id', 'label', 'description', 'price', 'quantity',
                 'is_validated', 'issuing_company', 'created_at',
                 'updated_at')
        read_only_fields = ('created_at', 'updated_at')

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("The price must be greater than zero.")
        return value

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("The quantity must be a positive integer.")
        return value