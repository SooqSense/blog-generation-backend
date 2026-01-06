import hashlib
import secrets
from django.contrib.auth.hashers import make_password, check_password
from rest_framework import authentication, exceptions
from ...models import BlogAPIKey

class ExternalAPIKeyAuthentication(authentication.BaseAuthentication):
    """
    Custom authentication for external API access using X-API-Key header.
    Format: prefix.key
    """
    def authenticate(self, request):
        api_key = request.META.get('HTTP_X_API_KEY')
        if not api_key:
            return None

        try:
            prefix, key = api_key.split('.', 1)
        except ValueError:
            raise exceptions.AuthenticationFailed('Invalid API Key format. Expected prefix.key')

        # Find active keys with this prefix
        key_obj = BlogAPIKey.objects.filter(
            prefix=prefix, 
            is_active=True,
            revoked_at__isnull=True
        ).first()

        if not key_obj:
            raise exceptions.AuthenticationFailed('Invalid or inactive API Key')

        # Verify the key using Django's check_password (which handles salting/hashing correctly)
        if not check_password(key, key_obj.hashed_key):
            raise exceptions.AuthenticationFailed('Invalid API Key')

        # Success: Return a dummy user and the key object
        request.organization_name = key_obj.organization_name
        return (None, key_obj)

def generate_api_key(name, organization_name):
    """
    Utility function to generate a new secure API Key.
    """
    prefix = secrets.token_urlsafe(8)
    key = secrets.token_urlsafe(32)
    full_key = f"{prefix}.{key}"
    
    hashed_key = make_password(key)
    
    api_key_obj = BlogAPIKey.objects.create(
        prefix=prefix,
        hashed_key=hashed_key,
        name=name,
        organization_name=organization_name
    )
    
    return full_key, api_key_obj
