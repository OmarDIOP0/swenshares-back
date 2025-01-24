import jwt

from rest_framework.exceptions import AuthenticationFailed
from shareholders.models import KeycloakUser
from rest_framework.authentication import BaseAuthentication
import logging
from django.db import transaction
from django.contrib.auth.models import User
logger = logging.getLogger(__name__)

class KeycloakAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None

        try:
            # Extraire le token
            auth_parts = auth_header.split()
            if len(auth_parts) != 2 or auth_parts[0].lower() != 'bearer':
                raise AuthenticationFailed('Invalid authorization header format')

            token = auth_parts[1]

            # Décoder le token
            # Note: Dans un environnement de production, vous devriez vérifier la signature
            decoded_token = jwt.decode(token, options={"verify_signature": False})
            
            logger.debug(f"Decoded token: {decoded_token}")

            with transaction.atomic():
                # Créer ou récupérer l'utilisateur Django
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

                logger.debug(f"Authentication successful for user: {django_user.username}")
                return (django_user, decoded_token)

        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token error: {str(e)}")
            raise AuthenticationFailed('Invalid token')
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise AuthenticationFailed(f'Authentication error: {str(e)}')

    def authenticate_header(self, request):
        return 'Bearer realm="Keycloak"'