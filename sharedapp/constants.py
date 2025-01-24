# constants.py
from django.utils.translation import gettext_lazy as _



# Enumeration for notification types
class NotificationType:
    SMS = 'SMS'
    EMAIL = 'EMAIL'
    PHONE = 'PHONE'

    CHOICES = [
        (SMS, 'SMS'),
        (EMAIL, 'Email'),
        (PHONE, 'Phone')
    ]

# Notification status
class NotificationStatus:
    PENDING = 'PENDING'
    SENT = 'SENT'
    FAILED = 'FAILED'

    CHOICES = [
        (PENDING, 'Pending'),
        (SENT, 'Sent'),
        (FAILED, 'Failed')
    ]

# Enumeration for announcement types
class AnnouncementType:

    PURCHASE = 'PURCHASE'
    SALE = 'SALE'

    CHOICES = [
        (PURCHASE, 'Purchase'),
        (SALE, 'Sale')
    ]
