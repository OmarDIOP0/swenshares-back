# shareholders/middleware.py
from django.utils.functional import SimpleLazyObject
from django.contrib.auth.models import AnonymousUser, User
from django.db import transaction
from shareholders.models import KeycloakUser
import jwt
import logging

logger = logging.getLogger(__name__)

def get_user(request):
    if not hasattr(request, '_cached_user'):
        try:
            auth_header = request.headers.get('Authorization')
            if auth_header:
                try:
                    token = auth_header.split(' ')[1]
                    decoded_token = jwt.decode(
                        token,
                        options={"verify_signature": False}
                    )

                    with transaction.atomic():
                        # Créer ou mettre à jour l'utilisateur Django
                        django_user, created = User.objects.get_or_create(
                            username=decoded_token.get('preferred_username'),
                            defaults={
                                'email': decoded_token.get('email', ''),
                                'is_active': True
                            }
                        )

                        if not created and django_user.email != decoded_token.get('email'):
                            django_user.email = decoded_token.get('email')
                            django_user.save(update_fields=['email'])

                        # Créer ou mettre à jour l'utilisateur Keycloak
                        keycloak_user, k_created = KeycloakUser.objects.get_or_create(
                            user=django_user,
                            defaults={
                                'keycloak_id': decoded_token.get('sub'),
                                'username': decoded_token.get('preferred_username', ''),
                                'email': decoded_token.get('email', ''),
                                'roles': decoded_token.get('realm_access', {}).get('roles', [])
                            }
                        )

                        if not k_created:
                            update_fields = []
                            if keycloak_user.username != decoded_token.get('preferred_username'):
                                keycloak_user.username = decoded_token.get('preferred_username')
                                update_fields.append('username')
                            
                            if keycloak_user.email != decoded_token.get('email'):
                                keycloak_user.email = decoded_token.get('email')
                                update_fields.append('email')
                            
                            roles = decoded_token.get('realm_access', {}).get('roles', [])
                            if keycloak_user.roles != roles:
                                keycloak_user.roles = roles
                                update_fields.append('roles')
                            
                            if update_fields:
                                keycloak_user.save(update_fields=update_fields)

                        request._cached_user = django_user
                        logger.debug(f"User authenticated: {django_user.username} with roles: {keycloak_user.roles}")
                except (jwt.InvalidTokenError, IndexError) as e:
                    logger.error(f"Token error: {str(e)}")
                    request._cached_user = AnonymousUser()
            else:
                request._cached_user = AnonymousUser()
                logger.debug("No authentication token found, using AnonymousUser")

        except Exception as e:
            logger.error(f"Error in KeycloakUserMiddleware: {str(e)}")
            request._cached_user = AnonymousUser()

    return request._cached_user

class KeycloakUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        logger.debug("KeycloakUserMiddleware initialized")

    def __call__(self, request):
        request.user = SimpleLazyObject(lambda: get_user(request))
        
        if logger.isEnabledFor(logging.DEBUG):
            user = request.user
            logger.debug(f"Request user: {user.username if hasattr(user, 'username') else 'AnonymousUser'}")
            if hasattr(user, 'keycloak_user'):
                logger.debug(f"User roles: {user.keycloak_user.roles}")

        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        logger.error(f"Exception in request processing: {str(exception)}")
        return None