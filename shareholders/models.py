from decimal import Decimal
import os
from django.db import models
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
import uuid


from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone

from shareholders.constants import KeycloakRoles, ShareholderStatus
from simple_history.models import HistoricalRecords
from django.contrib.contenttypes.fields import GenericForeignKey

from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType


class DocumentType(models.TextChoices):
    """
    Enumeration of document types for consistent classification
    """
    NATIONAL_ID = 'national_id', 'National ID'
    PASSPORT = 'passport', 'Passport'
    PROOF_OF_ADDRESS = 'proof_address', 'Proof of Address'
    FINANCIAL_DOCUMENT = 'financial', 'Financial Document'
    TAX_DOCUMENT = 'tax', 'Tax Document'
    REGISTRATION = 'registration', 'Registration Document'
    OTHER = 'other', 'Other Document'

def document_file_path(instance, filename):
    """
    Generate a unique file path for uploaded documents
    """
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join(
        'documents', 
        instance.content_type.model, 
        str(instance.object_id), 
        filename
    )
def validate_file_extension(value):
    allowed_extensions = [
        '.pdf', '.jpg', '.jpeg', '.png', 
        '.doc', '.docx', '.xls', '.xlsx'
    ]
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in allowed_extensions:
        raise ValidationError("Unsupported file type")

class FileDocument(models.Model):
    """
    Generic model for managing files across different models
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(
        upload_to=document_file_path, 
        validators=[validate_file_extension],
        max_length=255
    )
    document_type = models.CharField(
        max_length=30, 
        choices=DocumentType.choices, 
        default=DocumentType.OTHER
    )
    description = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='uploaded_documents'
    )
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='verified_documents'
    )

    # Generic relation to link documents to any model
    content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE)
    object_id = models.UUIDField()
    content_object = GenericForeignKey('content_type', 'object_id') 

    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self):
        return f"{self.document_type} - {self.file.name}"



class KeycloakUser(models.Model):
    """
    Extension du modèle User de Django pour intégrer les informations Keycloak
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='keycloak_user')
    keycloak_id = models.CharField(max_length=255, unique=True)
    username = models.CharField(max_length=255)
    email = models.EmailField()
    roles = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'shareholders_keycloakuser'
        verbose_name = 'Keycloak User'
        verbose_name_plural = 'Keycloak Users'

    def __str__(self):
        return self.username

    def has_role(self, role):
        """Vérifie si l'utilisateur a un rôle spécifique"""
        return role in self.roles
    

# Ajout de la classe ContactPerson pour les actionnaires physiques
class ContactPerson(models.Model):
    """
    Model for shareholder contact persons
    """
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)  # Ajout de l'unicité
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in format: '+999999999'"
    )
    phone = models.CharField(validators=[phone_regex], max_length=16, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Contact Person'
        verbose_name_plural = 'Contact Persons'

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

# Modèle Adresse (Address) - Mise à jour de la relation pour Shareholder
class Address(models.Model):
    """
    Modèle pour les adresses des actionnaires.
    """
    street = models.CharField(max_length=255)  # Nom de la rue
    city = models.CharField(max_length=100)    # Ville
    postal_code = models.CharField(max_length=20)  # Code postal
    country = models.CharField(max_length=100)  # Pays
    is_primary = models.BooleanField(default=False)  # Indique si l'adresse est principale
    effective_date = models.DateField()  # Date d'effet de l'adresse

    class Meta:
        verbose_name_plural = 'addresses'
        ordering = ['-effective_date']
    
    @property
    def full_address(self):
        return f"{self.street}, {self.postal_code} {self.city}, {self.country}"

    def is_valid_for_period(self, date):
        return self.effective_date <= date

    def __str__(self):
        return f"{self.street}, {self.city} - {self.country}"
    

# Modèle de base pour les actionnaires
class Shareholder(models.Model):
    """
    Modèle de base pour les actionnaires (physiques et moraux)
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Modification ici pour utiliser le User model de Django
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='%(class)s_created')
    examined_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='%(class)s_examined')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='%(class)s_approved')
    status = models.CharField(max_length=20, choices=ShareholderStatus.CHOICES, default=ShareholderStatus.SUBMITTED)
    effective_date = models.DateField()
    activity_sector = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)  # Nouveau champ pour les notes
    total_shares = models.PositiveIntegerField(
        validators=[
            MinValueValidator(Decimal('1')), 
            MaxValueValidator(Decimal('1000000'))
        ]
    ) # Le nombre de part de l'actionnaire

    issuing_company = models.ForeignKey('issuingCompany.IssuingCompany', on_delete=models.SET_NULL, null=True, blank=True)    # Ajout de la relation avec la société emettrice

    history = HistoricalRecords(inherit=True) # Pour stocker l'historique des modifications
    class Meta:
        abstract = True
        ordering = ['-created_at']



    def validate_future_date(value):
        if value < timezone.now().date():
          raise ValidationError("La date d'effet ne peut pas être dans le passé.")
        
    def can_be_modified_by(self, user):
        """
        Vérifie si l'utilisateur peut modifier l'actionnaire
        basé sur son rôle et le statut actuel
        """
        try:
            keycloak_user = user.keycloak_user
            if keycloak_user.has_role(KeycloakRoles.ADMIN):
                return True
                
            status_role_map = {
                ShareholderStatus.SUBMITTED: KeycloakRoles.EDITOR,
                ShareholderStatus.EXAMINED: KeycloakRoles.EXAMINER,
                ShareholderStatus.APPROVED and ShareholderStatus.REJECTED : KeycloakRoles.APPROVER
            }
            
            required_role = status_role_map.get(self.status)
            if required_role and keycloak_user.has_role(required_role):
                if self.status == ShareholderStatus.SUBMITTED :
                    return True
                return True
                
            return False
        except KeycloakUser.DoesNotExist:
            return False

    def transition_status(self, new_status, user):
        valid_transitions = {
            ShareholderStatus.SUBMITTED: [ShareholderStatus.EXAMINED],
            ShareholderStatus.EXAMINED: [ShareholderStatus.APPROVED, ShareholderStatus.REJECTED],
            ShareholderStatus.APPROVED: [],
            ShareholderStatus.REJECTED: [ShareholderStatus.SUBMITTED]
        }

        if new_status in valid_transitions[self.status]:
            if self.status == ShareholderStatus.SUBMITTED and new_status == ShareholderStatus.EXAMINED:
                if user.keycloak_user.has_role(KeycloakRoles.EXAMINER):
                    self.status = new_status
                    self.examined_by = user
                    self.save()
                    return True
            elif self.status == ShareholderStatus.EXAMINED and new_status in ShareholderStatus.APPROVED:
                if user.keycloak_user.has_role(KeycloakRoles.APPROVER):
                    self.status = new_status
                    if new_status == ShareholderStatus.APPROVED:
                        self.approved_by = user
                    self.save()
                    return True
                
            elif self.status == ShareholderStatus.EXAMINED and new_status == ShareholderStatus.REJECTED:
                    if user.keycloak_user.has_role(KeycloakRoles.APPROVER):
                        self.status = new_status
                    # Ne pas modifier created_by, il reste le même
                    self.save()
                    return True
            
        return False


# Modèle pour les Actionnaires Physiques (PhysicalShareholder)
class PhysicalShareholder(Shareholder):
    """
    Modèle pour les actionnaires physiques
    """
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in format: '+999999999'"
    )
    
    national_id = models.CharField(max_length=50, unique=True)
    national_id_expiration = models.DateField()
    date_of_birth = models.DateField() # Date de naissance de l'actionnaire
    # Ajout de la relation avec Address
    addresses = models.ManyToManyField(Address, related_name='physical_shareholders')
    # Référence aux dividendes (from sharedapp)
    dividends = models.ManyToManyField('sharedapp.Dividend', related_name='physical_shareholders')
    reference_number = models.CharField(max_length=50, unique=True)  # Ajout du numéro de référence
    # Ajout de la relation avec ContactPerson
    contact_person = models.ForeignKey(ContactPerson, null=True, on_delete=models.SET_NULL)

    class Meta:
        verbose_name = 'Physical Shareholder'
        verbose_name_plural = 'Physical Shareholders'

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


# Modèle pour les Actionnaires Moraux (LegalShareholder)
class LegalShareholder(Shareholder):
    """
    Modèle pour les actionnaires moraux
    """
    company_name = models.CharField(max_length=200)
    registration_number = models.CharField(max_length=100, unique=True)
    tax_id = models.CharField(max_length=100, unique=True)
    legal_representative = models.CharField(max_length=200)
    representative_email = models.EmailField()
    representative_phone = models.CharField(max_length=16)
    # Pourcentage de capital détenu
    capital_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    # Pourcentage du groupe si l'entreprise est membre d'un groupe
    is_group_member = models.BooleanField(default=False)
    group_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        null=True, 
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # Ajout de la relation avec Address
    addresses = models.ManyToManyField(Address, related_name='legal_shareholders')
    effective_beneficiary = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    visa_date = models.DateField(null=True, blank=True)
    # visa_document = models.FileField(upload_to='visa_documents/', null=True, blank=True)
    visa_document = GenericRelation(FileDocument)
    
    # Référence aux dividendes (from sharedapp)
    dividends = models.ManyToManyField('sharedapp.Dividend', related_name='legal_shareholders')
    reference_number = models.CharField(max_length=50, unique=True)  # Ajout du numéro de référence
    # Ajout de la relation avec ContactPerson
    contact_person = models.ForeignKey(ContactPerson, null=True, on_delete=models.SET_NULL)

    class Meta:
        verbose_name = 'Legal Shareholder'
        verbose_name_plural = 'Legal Shareholders'

    def __str__(self):
        return f"{self.company_name} - Ref: {self.reference_number}"

    def clean(self):
        if self.is_group_member and self.group_percentage is None:
            raise ValidationError("Group percentage is required when shareholder is a group member")


# Modèle pour les Actions des actionnaires
class Share(models.Model):
    """
    Represents a company share with its characteristics
    """ 
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    label = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    is_validated = models.BooleanField(default=False)
    
    issuing_company = models.ForeignKey(
        'issuingCompany.IssuingCompany', 
        on_delete=models.CASCADE, 
        related_name='shares'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.label} ({self.issuing_company})"

    def validate(self):
        """
        Custom method to validate a share.
        """
        self.is_validated = True
        self.save()

    class Meta:
        verbose_name = "Share"
        verbose_name_plural = "Shares"