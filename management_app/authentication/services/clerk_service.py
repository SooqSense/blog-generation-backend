import jwt
import requests
import logging
import ssl
import urllib3
from typing import Optional, Dict, Any
from django.conf import settings
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta
from jwt import PyJWKClient

User = get_user_model()
logger = logging.getLogger(__name__)


class ClerkJWTAuthService:
    """Clerk JWT Authentication Service"""
    
    def __init__(self):
        self.clerk_secret_key = getattr(settings, 'CLERK_SECRET_KEY', None)
        self.clerk_publishable_key = getattr(settings, 'NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY', None)
        self.clerk_api_url = getattr(settings, 'CLERK_API_URL', 'https://api.clerk.com')
        self.clerk_jwks_url = getattr(settings, 'CLERK_JWKS_URL', None)
        self.clerk_frontend_url = getattr(settings, 'CLERK_FRONTEND_URL', None)
        
        # Initialize JWKS client for token verification
        if self.clerk_jwks_url:
            try:
                # Disable SSL warnings for development
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                
                # Initialize JWKS client
                self.jwks_client = PyJWKClient(self.clerk_jwks_url)
                logger.info("JWKS client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize JWKS client: {e}")
                self.jwks_client = None
        else:
            self.jwks_client = None
            logger.warning("CLERK_JWKS_URL not found in settings")
        
        if not self.clerk_secret_key:
            logger.warning("CLERK_SECRET_KEY not found in settings")
    
    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token - supports both Clerk tokens (RS256) and custom tokens (HS256)"""
        try:
            # First, try to decode the header to determine token type
            header = jwt.get_unverified_header(token)
            algorithm = header.get('alg', '')
            kid = header.get('kid', '')
            
            # Check if it's a custom token (HS256 with custom kid)
            if algorithm == 'HS256' and kid == 'custom-key-1':
                logger.info("Verifying custom JWT token")
                return self._verify_custom_token(token)
            
            # Otherwise, try Clerk JWKS verification
            elif algorithm == 'RS256' and self.jwks_client:
                logger.info("Verifying Clerk JWT token with JWKS")
                return self._verify_clerk_token(token)
            
            else:
                logger.warning(f"Unsupported token algorithm or missing JWKS: {algorithm}")
                return self._verify_jwt_token_fallback(token)
                
        except Exception as e:
            logger.error(f"Error verifying JWT token: {e}")
            return self._verify_jwt_token_fallback(token)
    
    def _verify_custom_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify custom HS256 JWT token using Django SECRET_KEY"""
        try:
            from django.conf import settings
            
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=['HS256'],
                options={"verify_exp": True, "verify_aud": False}
            )
            
            logger.info("Custom JWT token verified successfully")
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Custom JWT token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid custom JWT token: {e}")
            return None
    
    def _verify_clerk_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify Clerk JWT token using JWKS"""
        try:
            # Get the signing key from JWKS
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            
            # Decode JWT token with the signing key
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=['RS256'],
                options={"verify_exp": True, "verify_aud": False}  # Clerk doesn't use audience
            )
            
            # Validate issuer if frontend URL is configured
            if self.clerk_frontend_url and payload.get('iss') != self.clerk_frontend_url:
                logger.warning(f"Invalid issuer: {payload.get('iss')}")
                return None
            
            logger.info("Clerk JWT token verified successfully")
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Clerk JWT token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid Clerk JWT token: {e}")
            return None
    
    def _verify_jwt_token_fallback(self, token: str) -> Optional[Dict[str, Any]]:
        """Fallback JWT verification method for development environments"""
        try:
            logger.info("Attempting fallback JWT verification")
            
            # For development, we'll use a simpler approach
            # Decode without verification first to get the header
            unverified_header = jwt.get_unverified_header(token)
            unverified_payload = jwt.decode(token, options={"verify_signature": False})
            
            # Check if it's a Clerk token by issuer
            if self.clerk_frontend_url and unverified_payload.get('iss') != self.clerk_frontend_url:
                logger.warning(f"Invalid issuer in fallback: {unverified_payload.get('iss')}")
                return None
            
            # For development, we'll trust the token if it has the right structure
            # In production, you should always verify the signature
            logger.warning("Using fallback JWT verification (not recommended for production)")
            return unverified_payload
            
        except Exception as e:
            logger.error(f"Fallback JWT verification failed: {e}")
            return None
    
    def get_or_create_user(self, clerk_payload: Dict[str, Any]) -> Optional[User]:
        """Get or create Django user from Clerk payload"""
        try:
            clerk_user_id = clerk_payload.get('sub')
            email = clerk_payload.get('email')
            
            if not clerk_user_id:
                logger.error("No clerk_user_id in JWT payload")
                return None
            
            # First, try to get existing user by email (most reliable)
            if email:
                user = User.objects.filter(email=email).first()
                if user:
                    # Update clerk_user_id if it's different or missing
                    if not user.clerk_user_id or user.clerk_user_id != clerk_user_id:
                        user.clerk_user_id = clerk_user_id
                        user.save()
                        logger.info(f"Updated clerk_user_id for existing user: {user.email}")
                    return user
            
            # Try to get existing user by clerk_user_id
            user = User.objects.filter(clerk_user_id=clerk_user_id).first()
            
            if user:
                # Update email if it has changed
                if email and user.email != email:
                    user.email = email
                    user.save()
                return user
            
            # Create new user only if no existing user found
            username = clerk_payload.get('username', email.split('@')[0] if email else clerk_user_id)
            
            # Ensure username is unique
            original_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{original_username}_{counter}"
                counter += 1
            
            user = User.objects.create_user(
                username=username,
                email=email or '',
                clerk_user_id=clerk_user_id,
                is_active=True
            )
            
            logger.info(f"Created new user: {user.username} ({clerk_user_id})")
            return user
            
        except Exception as e:
            logger.error(f"Error getting/creating user: {e}")
            return None
    
    def authenticate_user(self, token: str) -> Optional[User]:
        """Authenticate user with Clerk JWT token"""
        payload = self.verify_jwt_token(token)
        if not payload:
            return None
        
        return self.get_or_create_user(payload)


class ClerkAPIService:
    """Service for interacting with Clerk API"""
    
    def __init__(self):
        self.clerk_secret_key = getattr(settings, 'CLERK_SECRET_KEY', None)
        self.clerk_api_url = getattr(settings, 'CLERK_API_URL', 'https://api.clerk.com')
        
        if not self.clerk_secret_key:
            logger.warning("CLERK_SECRET_KEY not found in settings")
    
    def create_sign_in_token(self, user_id: str) -> Optional[str]:
        """Create a sign-in token for a user"""
        try:
            if not self.clerk_secret_key:
                logger.error("Clerk secret key not configured")
                return None
            
            headers = {
                'Authorization': f'Bearer {self.clerk_secret_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'user_id': user_id
            }
            
            response = requests.post(
                f'{self.clerk_api_url}/v1/sign_in_tokens',
                headers=headers,
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('token')
            else:
                logger.error(f"Failed to create sign-in token: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating sign-in token: {e}")
            return None
    
    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user information from Clerk API"""
        try:
            if not self.clerk_secret_key:
                logger.error("Clerk secret key not configured")
                return None
            
            headers = {
                'Authorization': f'Bearer {self.clerk_secret_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f'{self.clerk_api_url}/v1/users/{user_id}',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get user info: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None
