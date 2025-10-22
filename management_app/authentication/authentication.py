import logging
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model
from .services.clerk_services import ClerkUserService

User = get_user_model()
logger = logging.getLogger(__name__)


class ClerkJWTAuthentication(BaseAuthentication):
    """DRF Authentication class for Clerk JWT tokens"""
    
    def authenticate(self, request):
        """Authenticate the request using Clerk JWT token"""
        # Get JWT token from Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header.split(' ')[1]
        
        # Use the ClerkUserService for authentication
        clerk_user_service = ClerkUserService()
        user = clerk_user_service.authenticate_user(token)
        
        if not user:
            raise AuthenticationFailed('Invalid or expired token')
        
        return (user, None)  # Return (user, auth) tuple
    
    def authenticate_header(self, request):
        """Return the authentication header"""
        return 'Bearer'
