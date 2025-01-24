# Create your models here.
import uuid
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models
from django.forms import ValidationError
from simple_history.models import HistoricalRecords

from sharedapp.constants import (AnnouncementType, NotificationStatus,
                                 NotificationType)


class Announcement(models.Model):
    """
    Model for share purchase/sale announcements
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    description = models.TextField()
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=10, decimal_places=2)
    announcement_date = models.DateField(auto_now_add=True)
    type = models.CharField(
        max_length=10,
        choices=AnnouncementType.CHOICES,
        default=AnnouncementType.SALE
    )
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=True)
    expiration_date = models.DateField()
    # Référence à l'action de la société émettrice
    share = models.ForeignKey('issuingCompany.IssuingCompany', on_delete=models.CASCADE, related_name='announcements')

    history = HistoricalRecords()

    def clean(self):
        if self.expiration_date <= self.announcement_date:
            raise ValidationError("Expiration date must be after announcement date")


    def __str__(self):
        return f"{self.quantity} shares at {self.price}"

    class Meta:
        ordering = ['-announcement_date']
        indexes = [
            models.Index(fields=['announcement_date']),
            models.Index(fields=['type']),
        ]

    def __str__(self):
        return f"{self.get_type_display()} - {self.quantity} shares at {self.price}"

class Notification(models.Model):
    """
    Model for system notifications
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField()
    date_created = models.DateTimeField(auto_now_add=True)
    date_sent = models.DateTimeField(null=True, blank=True)
    type = models.CharField(
        max_length=10,
        choices=NotificationType.CHOICES,
        default=NotificationType.EMAIL
    )
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    is_read = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=NotificationStatus.CHOICES,
        default=NotificationStatus.PENDING
    )

    history = HistoricalRecords()

    def clean(self):
        if self.date_sent and self.date_sent < self.date_created:
            raise ValidationError("Sent date cannot be before created date")


    class Meta:
        ordering = ['-date_created']
        indexes = [
        models.Index(fields=['date_created']),
    ]

    def __str__(self):
        return f"{self.title} - {self.get_type_display()}"

class Dividend(models.Model):
    """
    Model for shareholder dividends
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    general_assembly_date = models.DateField()
    general_assembly_minutes = models.FileField(upload_to='assembly_minutes/')
    total_dividend_amount = models.DecimalField(max_digits=15, decimal_places=2) # le montant total des dividends
    dividend_per_share = models.DecimalField(max_digits=10, decimal_places=2) # le dividende par action
    payment_date = models.DateField()
    is_validated = models.BooleanField(default=False)
    validated_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='validated_dividends'
    ) # l'utilisateur qui a valide le dividende
    # Référence à la société émettrice
    issuing_company = models.ForeignKey('issuingCompany.IssuingCompany', on_delete=models.CASCADE, related_name='dividends') # la société emetteur
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords() 

    def clean(self):
        if self.payment_date <= self.general_assembly_date:
            raise ValidationError("Payment date must be after the general assembly date")
        if self.dividend_per_share <= 0:
            raise ValidationError("Dividend per share must be greater than zero")
        if self.total_dividend_amount <= 0:
            raise ValidationError("Total dividend amount must be greater than zero")


    class Meta:
        ordering = ['-general_assembly_date']
        indexes = [
        models.Index(fields=['general_assembly_date']),
        models.Index(fields=['is_validated']),
    ]

    def __str__(self):
        return f"Dividend {self.general_assembly_date} - {self.total_dividend_amount}"
