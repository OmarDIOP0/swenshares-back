from django.utils.translation import gettext_lazy as _
class IssuingCompanyStatus:
    # DRAFT = 'DRAFT'
    SUBMITTED = 'SUBMITTED'
    EXAMINED = 'EXAMINED'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'

    CHOICES =[
        # (DRAFT, _('Draft')),
        (SUBMITTED, _('Submitted')),
        (EXAMINED, _('Examined')),
        (APPROVED, _('Approved')),
        (REJECTED, _('Rejected'))
    ]

    
    FCFA = 'FCFA'
    USD = 'USD'
    EUR = 'EUR'
    GBP = 'GBP'
    JPY = 'JPY'

    CASH_CURRENT=[
        (FCFA, _('Franc CFA')),
        (USD, _('Dollar American')),
        (EUR, _('EURO')),
        (GBP, _('Livre sterling')),
        (JPY, _('Yen japonais')),
    ]

class SocialActType:
    ORDINARY = 'ORDINARY'
    EXTRAORDINARY = 'EXTRAORDINARY'

    TYPE_GENERAL_ASSEMBLY = [
        (ORDINARY, _('Ordinary')),
        (EXTRAORDINARY, _('Extraordinary'))
    ]

    STORE_INCORPORATION = 'STORE_INCORPORATION'
    RESOURCE_EXTERN = 'RESOURCE_EXTERN'

    TYPE_SOCIAL_ACT =[
        (STORE_INCORPORATION, _('Store_Incorporation')),
        (RESOURCE_EXTERN, _('Resource_Extern'))
    ]

    # DRAFT = 'DRAFT'
    SUBMITTED = 'SUBMITTED'
    EXAMINED = 'EXAMINED'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'

    CHOICES =[
        # (DRAFT, _('Draft')),
        (SUBMITTED, _('Submitted')),
        (EXAMINED, _('Examined')),
        (APPROVED, _('Approved')),
        (REJECTED, _('Rejected'))
    ]


class TransactionType:
    PURCHASE = 'PURCHASE'
    SALE = 'SALE'
    TRANSFER = 'TRANSFER'
    
    CHOICES = [
        (PURCHASE, _('Purchase')),
        (SALE, _('Sale')),
        (TRANSFER, _('Transfer'))
    ]

class TransactionStatus:
    PENDING = 'PENDING'
    VALIDATED = 'VALIDATED'
    REJECTED = 'REJECTED'

    CHOICES = [
        (PENDING, _('Pending')),
        (VALIDATED, _('Validated')),
        (REJECTED, _('Rejected'))
    ]