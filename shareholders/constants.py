# constants.py
from django.utils.translation import gettext_lazy as _
# Exemple d'implémentation possible de HasKeycloakRole
from rest_framework.permissions import BasePermission

# Status choices for shareholders
class ShareholderStatus:
    # DRAFT = 'DRAFT'
    SUBMITTED = 'SUBMITTED'
    EXAMINED = 'EXAMINED'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'

    CHOICES = [
        # (DRAFT, _('Draft')),
        (SUBMITTED, _('Submitted')),
        (EXAMINED, _('Examined')),
        (APPROVED, _('Approved')),
        (REJECTED, _('Rejected')),

    ]

# Keycloak roles
class KeycloakRoles:
    ADMIN = 'ADMIN'
    EDITOR = 'EDITOR'
    EXAMINER = 'EXAMINER'
    APPROVER = 'APPROVER'

    ALL_ROLES = [ADMIN, EDITOR, EXAMINER, APPROVER]


# Permissions
class HasKeycloakRole(BasePermission):
    def __init__(self, required_roles):
        self.required_roles = required_roles if isinstance(required_roles, (list, tuple)) else [required_roles]

    def has_permission(self, request, view):
        if hasattr(request.user, 'keycloak_user'):
            return any(role in request.user.keycloak_user.roles for role in self.required_roles)
        return False
    

# Error messages
class ErrorMessages:
    AUTHENTICATION_FAILED = _("Authentication credentials were not provided.")
    PERMISSION_DENIED = _("You do not have permission to perform this action.")
    INVALID_STATUS_TRANSITION = _("Invalid status transition.")
    NOT_FOUND = _("Resource not found.")