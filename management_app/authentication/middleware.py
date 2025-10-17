import logging
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from .services.clerk_service import ClerkJWTAuthService

User = get_user_model()
logger = logging.getLogger(__name__)


class ClerkJWTAuthenticationMiddleware(MiddlewareMixin):
    """Middleware to authenticate requests using Clerk JWT tokens"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.clerk_auth = ClerkJWTAuthService()
        super().__init__(get_response)
    
    def process_request(self, request):
        """Process the request and authenticate user"""
        # Skip authentication for certain paths
        skip_paths = [
            '/admin/',
            '/docs/',
            '/schema/',
            '/auth/login/',
            '/auth/verify/',
            '/static/',
            '/media/',
        ]
        
        if any(request.path.startswith(path) for path in skip_paths):
            return None
        
        # Get JWT token from Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header.startswith('Bearer '):
            return JsonResponse(
                {'error': 'Missing or invalid Authorization header'}, 
                status=401
            )
        
        token = auth_header.split(' ')[1]
        
        # Authenticate user
        user = self.clerk_auth.authenticate_user(token)
        
        if not user:
            return JsonResponse(
                {'error': 'Invalid or expired token'}, 
                status=401
            )
        
        # Set user on request
        request.user = user
        return None
