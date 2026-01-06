import logging
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from .services.clerk_services import ClerkUserService

# Channels imports for WebSocket auth
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from urllib.parse import parse_qs

User = get_user_model()
logger = logging.getLogger(__name__)


class ClerkJWTAuthenticationMiddleware(MiddlewareMixin):
    """Middleware to authenticate requests using Clerk JWT tokens"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.clerk_user_service = ClerkUserService()
        super().__init__(get_response)
    
    def process_request(self, request):
        """Process the request and authenticate user"""
        # Skip authentication for certain paths
        skip_paths = [
            '/admin/',
            '/admin',
            '/docs/',
            '/docs',
            '/schema/',
            '/schema',
            '/auth/verify/',  # Allow unauthenticated access to verify endpoint
            '/auth/verify',
            '/static/',
            '/static',
            '/media/',
            '/media',
            '/api/external/',  # Allow External API Key authentication
        ]
        
        # Check if path matches any skip path (with or without trailing slash)
        if any(request.path.startswith(path) or request.path == path.rstrip('/') for path in skip_paths):
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
        user = self.clerk_user_service.authenticate_user(token)
        
        if not user:
            return JsonResponse(
                {'error': 'Invalid or expired token'}, 
                status=401
            )
        
        # Set user on request
        request.user = user
        return None


class ClerkWebSocketAuthMiddleware(BaseMiddleware):
    """Channels middleware to authenticate WebSocket connections with Clerk JWT.

    It mirrors the behavior of the HTTP ClerkJWTAuthenticationMiddleware:
    - Reads Bearer token from Authorization header
    - Falls back to `token` query param for environments that strip headers
    - Sets scope["user"] to the authenticated user, or AnonymousUser on failure
    """

    def __init__(self, inner):
        super().__init__(inner)
        self.clerk_user_service = ClerkUserService()

    async def __call__(self, scope, receive, send):
        headers = dict(scope.get("headers", []))
        token = None

        # Preferred: Authorization header
        if b"authorization" in headers:
            auth_header = headers[b"authorization"].decode()
            if auth_header.startswith("Bearer "):
                token = auth_header.split("Bearer ", 1)[1].strip()

        # Fallback: token in query string (some proxies strip headers)
        if not token:
            query_string = scope.get("query_string", b"").decode()
            if query_string:
                params = parse_qs(query_string)
                token = params.get("token", [None])[0]

        # Default user
        scope["user"] = AnonymousUser()

        if token:
            try:
                user = await self._authenticate_user_async(token)
                if user:
                    scope["user"] = user
                else:
                    logging.getLogger(__name__).warning("WS auth failed: invalid token")
            except Exception as e:
                logging.getLogger(__name__).error(f"WS auth error: {e}")
        else:
            logging.getLogger(__name__).warning("WS connection without token")

        return await self.inner(scope, receive, send)

    @database_sync_to_async
    def _authenticate_user_async(self, token):
        return self.clerk_user_service.authenticate_user(token)
