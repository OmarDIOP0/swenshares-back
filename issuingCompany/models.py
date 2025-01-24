from django.db import models
from django.core.validators import MinValueValidator,MinLengthValidator
from django.core.exceptions import ValidationError

from django.utils import timezone
from issuingCompany.constants import IssuingCompanyStatus,SocialActType, TransactionStatus
from django.contrib.auth.models import User
from issuingCompany.exceptions import Exception

from django.core.validators import MinValueValidator
from django.contrib.auth.models import User
import uuid

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


from issuingCompany.constants import TransactionType
from django.core.validators import  RegexValidator
from simple_history.models import HistoricalRecords
from simple_history.models import HistoricalRecords
from shareholders.models import Address

# Create your models here.

class IssuingCompany(models.Model):
    """
    Creation du modele de la societe emettrice
    """
    
    name = models.CharField(max_length=255,verbose_name="Company Name") #nom de la societe
    description = models.TextField(max_length=1000,blank=True, null=True) 
    legal = models.CharField(max_length=255,verbose_name="Legal Status")
    logo = models.ImageField(upload_to='logos/',validators=[Exception.validate_image_extension,Exception.validate_file_size],
                             help_text="Upload the Company logo when creating it")
    founded_date = models.DateField() #date de creation
    currency = models.CharField(max_length=10,choices=IssuingCompanyStatus.CASH_CURRENT,default='FCFA') #monnaie de l entreprise
    status_document = models.FileField(upload_to='documents/',validators=[Exception.validate_file_extension,Exception.validate_file_size])#document de status
    internal_regulations_document = models.FileField(upload_to='documents/',validators=[Exception.validate_file_extension,Exception.validate_file_size])#document de reglement interieur
    registration_trade_register = models.FileField(upload_to='documents/',validators=[Exception.validate_file_extension,Exception.validate_file_size])#rccm
    # ninea = models.CharField(max_length=12,validators=[MinLengthValidator(9)],help_text="Enter a NINEA between 9 to 12 digits")
    ninea = models.CharField(
    max_length=12,
    validators=[MinLengthValidator(9), RegexValidator(regex=r'^\d+$', message="Le NINEA doit contenir uniquement des chiffres.")],
    help_text="Enter a NINEA between 9 to 12 digits"
)

    organization_chart = models.FileField(upload_to='documents/',validators=[Exception.validate_file_extension,Exception.validate_file_size]) #organigramme
    capital_social = models.DecimalField(max_digits=10,decimal_places=2,validators=[MinValueValidator(0.01)]) #capital social
    number_of_shares = models.IntegerField(validators=[MinValueValidator(0)]) #nombre de parts sociales
    value_of_shares = models.DecimalField(max_digits=10,decimal_places=2,validators=[MinValueValidator(0.01)]) #valeur des parts sociales
    head_office_address = models.ForeignKey(
        Address,  # Utilisation du string ici aussi
         related_name="issuing_company",on_delete=models.CASCADE,null=True, blank=True, 
        ) #adresse du siege
    #head_office_address = models.CharField(max_length=100,default="Ouakam",blank=True,null=True)
    status = models.CharField(max_length=20,choices=IssuingCompanyStatus.CHOICES,default=IssuingCompanyStatus.SUBMITTED)
    notes = models.TextField(blank=True)  # Notes en cas de rejet
    created_by = models.ForeignKey(User,on_delete=models.SET_NULL,null=True, related_name='%(class)s_created')
    examined_by = models.ForeignKey(User,on_delete=models.SET_NULL,null=True, related_name='%(class)s_examined')
    approved_by = models.ForeignKey(User,on_delete=models.SET_NULL,null=True, related_name='%(class)s_approved')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # address = models.ForeignKey('shareholders.Address', on_delete=models.SET_NULL, null=True, blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Issuing Company"
        verbose_name_plural = "Issuing Companies"
        ordering = ['name']

    def transition_status(self,new_status):
        valid_transitions ={
            IssuingCompanyStatus.SUBMITTED:[IssuingCompanyStatus.EXAMINED],
            IssuingCompanyStatus.EXAMINED:[IssuingCompanyStatus.APPROVED,IssuingCompanyStatus.REJECTED],
            IssuingCompanyStatus.APPROVED:[],
            IssuingCompanyStatus.REJECTED:[IssuingCompanyStatus.SUBMITTED]
        }
        possible_transitions = valid_transitions.get(self.status,[])
        if new_status not in possible_transitions:
            raise ValueError(
                    f"Transition d'état invalide : '{self.status}' -> '{new_status}'. "
                    f"États possibles : {possible_transitions}."
                    )
        self.status = new_status
        self.save()

    def __str__(self):
        return self.name


class SocialAct(models.Model):
    """
    Creation du modele de l'acte social
    """
    general_assembly_pv = models.FileField(upload_to='documents/',validators=[Exception.validate_file_extension,Exception.validate_file_size]) #pv de l'assemblée générale
    date = models.DateField()
    general_assembly_type = models.CharField(max_length=20, choices=SocialActType.TYPE_GENERAL_ASSEMBLY,default=SocialActType.ORDINARY) #type de l'assemblée générale ordinaire ou extraordinaire
    social_act_type = models.CharField(max_length=20, choices=SocialActType.TYPE_SOCIAL_ACT,default=SocialActType.STORE_INCORPORATION) #type de l'acte social incorporation de reserves/ressources internes
    older_capital = models.DecimalField(max_digits=10, decimal_places=2,validators=[MinValueValidator(0.01)]) #ancien capital
    new_capital = models.DecimalField(max_digits=10, decimal_places=2,validators=[MinValueValidator(0.01)]) #nouveau capital
    amount = models.DecimalField(max_digits=10, blank=True, decimal_places=2,validators=[MinValueValidator(0.01)]) #montant
    issuing_company = models.ForeignKey(IssuingCompany,on_delete=models.SET_NULL,null=True,related_name='%(class)s_company')
    status = models.CharField(max_length=20,choices=SocialActType.CHOICES,default=SocialActType.SUBMITTED)
    notes = models.TextField(blank=True)  # Notes en cas de rejet
    created_by = models.ForeignKey(User,on_delete=models.SET_NULL,null=True, related_name='%(class)s_created')
    examined_by = models.ForeignKey(User,on_delete=models.SET_NULL,null=True, related_name='%(class)s_examined')
    approved_by = models.ForeignKey(User,on_delete=models.SET_NULL,null=True, related_name='%(class)s_approved') 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = models.JSONField(default=list,blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Social Act"
        verbose_name_plural = "Social Acts"
        ordering =['-created_at']
    
    #Fonction permettant de verifier si la date de l'assemblee est correcte
    def is_valid_for_a_period(self,date):
        return self.date <= date
    
    #Fonction permettant de verifier si le nouveau capaital est superieur a l'ancien
    def valid_capital(self):
        if self.new_capital < self.older_capital:
            raise ValidationError("Le nouveau capital doit etre superieur a l'ancien capital")

    #Calculer du montant de l'assemblee  
    def save(self, *args, **kwargs):
        # Calculer `amount` avant de sauvegarder
        if self.new_capital and self.older_capital:
            self.amount = self.new_capital - self.older_capital
        else:
            raise ValidationError(("Older and new capital must be defined before saving."))
        super().save(*args, **kwargs)
    
    #Fonction permettant d'afficher le type de l'acte social
    def get_social_act_type_display(self):
        return dict(SocialActType.TYPE_SOCIAL_ACT).get(self.social_act_type,"Inconnu")
    
    def transition_status(self,new_status):
        valid_transitions ={
            SocialActType.SUBMITTED:[SocialActType.EXAMINED],
            SocialActType.EXAMINED:[SocialActType.APPROVED,SocialActType.REJECTED],
            SocialActType.APPROVED:[],
            SocialActType.REJECTED:[SocialActType.SUBMITTED]
        }
        possible_transitions = valid_transitions.get(self.status,[])
        if new_status not in possible_transitions:
            raise ValueError(
                f"Transition d'état invalide : '{self.status}' -> '{new_status}'. "
                f"États possibles : {possible_transitions}."
                )
        self.status = new_status
        self.save()
    
    def __str__(self):
        return f"Social Act ({self.issuing_company}) - {self.date}"


class ActeSocialAugmentation(SocialAct):
    """
    Model for capital increase acts
    """
    # New capital value (calculated)
    nouveau_capital = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        null=True,
        blank=True
    )
    
    def save(self, *args, **kwargs):
     
        """
        Calculate new capital on save
        """
        if self.nouveau_capital <= self.ancien_capital:
            raise ValidationError("Le nouveau capital doit être supérieur à l'ancien.")
        self.nouveau_capital = self.ancien_capital + self.montant
        super().save(*args, **kwargs)

    
    class Meta:
        verbose_name = 'Capital Increase Act'
        verbose_name_plural = 'Capital Increase Acts'

class ActeSocialReduction(SocialAct):
    """
    Model for capital reduction acts
    """
    # New capital value (calculated)
    nouveau_capital = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        null=True,
        blank=True
    )
    
    def save(self, *args, **kwargs):
        """
        Calculate new capital on save
        """
        if self.nouveau_capital >= self.ancien_capital:
            raise ValidationError("Le nouveau capital doit être inférieur à l'ancien.")
        self.nouveau_capital = self.ancien_capital - self.montant
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = 'Capital Reduction Act'
        verbose_name_plural = 'Capital Reduction Acts'



class Sociale(models.Model):
    """
    Model representing social capital details
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Social capital as a string (can include currency or formatting)
    capital_social = models.CharField(max_length=200)
    
    # Number of social shares
    nombre_parts_sociales = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Total number of social shares"
    )
    
    # Value of each social share
    valeur_parts_sociales = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Value of each social share"
    )
    
    # Related issuing company
    issuing_company = models.OneToOneField(
        'issuingCompany.IssuingCompany', 
        on_delete=models.CASCADE,
        related_name='sociale_details'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()
    
    class Meta:
        verbose_name = 'Social Capital'
        verbose_name_plural = 'Social Capitals'
    
    def __str__(self):
        return f"Social Capital: {self.capital_social}"
    
    def total_capital_value(self):
        """
        Calculate total capital value
        """
        return self.nombre_parts_sociales * self.valeur_parts_sociales


class Transaction(models.Model):
    """
    Model representing share transactions
    """
    

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False) # Transaction ID
    # Les different types de transactions (achat, vente, transferer)
    type = models.CharField(
        max_length=20, 
        choices=TransactionType.CHOICES,
        default=TransactionType.SALE
    )
    
    # Seller and Buyer can be either Physical or Legal Shareholders
    seller_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name="seller_transactions")
    seller_object_id = models.UUIDField()
    seller = GenericForeignKey('seller_content_type', 'seller_object_id')

    buyer_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name="buyer_transactions")
    buyer_object_id = models.UUIDField()
    buyer = GenericForeignKey('buyer_content_type', 'buyer_object_id')
    
    # Transaction details
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Number of shares in the transaction"
    )
    
    # Prix de la transaction
    price_per_share = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    
    # Montant de la transaction
    total_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    
    transaction_date = models.DateTimeField(auto_now_add=True)
    # Document de la transaction
    transaction_document = models.FileField(
        upload_to='transaction_documents/', 
        null=True, 
        blank=True
    )
    
    # Si la transaction est confidentielle ou non, par defaut c'est non
    is_confidential = models.BooleanField(default=False)
    
    # Statut de la transaction
    status = models.CharField(
        max_length=20, 
        choices=TransactionStatus.CHOICES,
        default=TransactionStatus.PENDING
    )
    
    # Qui a validé la transaction
    validated_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='validated_transactions'
    )
    
    # La societe emettrice contenant la transaction
    issuing_company = models.ForeignKey(
        'issuingCompany.IssuingCompany', 
        on_delete=models.PROTECT,
        related_name='transactions'
    )

    # Autres champs
    total_capital_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    announcement = models.ForeignKey('sharedapp.Announcement', on_delete=models.CASCADE, related_name='transactions')

    notes = models.TextField(blank=True)  # Notes en cas de rejet

    history = HistoricalRecords()
    def save(self, *args, **kwargs):
        # Calcul du capital total
        self.total_capital_value = sum(
            share.capital_value for share in self.shares.all()
        )
        super().save(*args, **kwargs)

    
    
    class Meta:
        indexes = [
            models.Index(fields=['transaction_date']),
            models.Index(fields=['type'])
        ]

        ordering = ['-transaction_date']
        verbose_name_plural = 'Transactions'
        
    def __str__(self):
        return f"{self.type} - {self.quantity} shares - {self.transaction_date}"
    
    def calculate_total_amount(self):
        """
        Calculate total transaction amount
        """
        return self.quantity * self.price_per_share
    
    def save(self, *args, **kwargs):
        """
        Override save method to calculate total amount
        """
        self.total_amount = self.calculate_total_amount()
        super().save(*args, **kwargs)
    
    