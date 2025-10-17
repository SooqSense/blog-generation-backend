import jwt
import requests
import logging
import ssl
import urllib3
from typing import Optional, Dict, Any
from django.conf import settings
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta, timezone
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
        
        # Configuration for JWT validation tolerance
        self.jwt_max_leeway = getattr(settings, 'JWT_MAX_LEEWAY_SECONDS', 600)  # Default 10 minutes
        self.jwt_disable_iat_on_failure = getattr(settings, 'JWT_DISABLE_IAT_ON_FAILURE', True)
        
        # Session expiry configuration - 1 day
        self.session_expiry_hours = getattr(settings, 'CLERK_SESSION_EXPIRY_HOURS', 24)  # Default 24 hours
        
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
        """Verify Clerk JWT token using JWKS - Single authentication solution"""
        try:
            # First, try to decode the header to determine token type
            header = jwt.get_unverified_header(token)
            algorithm = header.get('alg', '')
            
            # Only support Clerk RS256 tokens
            if algorithm != 'RS256':
                logger.warning(f"Unsupported token algorithm: {algorithm}. Only RS256 tokens are supported.")
                return None
            
            if not self.jwks_client:
                logger.error("JWKS client not initialized. Cannot verify token.")
                return None
            
            logger.info("Verifying Clerk JWT token with JWKS")
            return self._verify_clerk_token(token)
                
        except Exception as e:
            logger.error(f"Error verifying JWT token: {e}")
            return None
    
    def _verify_clerk_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify Clerk JWT token using JWKS - Single authentication method"""
        try:
            # Get the signing key from JWKS
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            
            # Decode token without verification first to get timing info for debugging
            try:
                from datetime import datetime, timezone
                unverified_payload = jwt.decode(token, options={"verify_signature": False})
                iat_time = unverified_payload.get('iat')
                exp_time = unverified_payload.get('exp')
                current_time = datetime.now(timezone.utc).timestamp()
                
                logger.info(f"Token timing debug - IAT: {iat_time}, EXP: {exp_time}, Current: {current_time}")
                logger.info(f"Token IAT datetime: {datetime.fromtimestamp(iat_time, timezone.utc).isoformat()}")
                logger.info(f"Token EXP datetime: {datetime.fromtimestamp(exp_time, timezone.utc).isoformat()}")
                logger.info(f"Current datetime: {datetime.now(timezone.utc).isoformat()}")
                
                # Calculate time differences
                iat_diff = current_time - iat_time
                exp_diff = exp_time - current_time
                logger.info(f"Time since IAT: {iat_diff:.2f} seconds")
                logger.info(f"Time until EXP: {exp_diff:.2f} seconds")
                
            except Exception as debug_e:
                logger.warning(f"Could not decode token for debugging: {debug_e}")
            
            # Try with different leeway values to handle clock synchronization issues
            leeway_values = [30, 60, 120, 300, self.jwt_max_leeway]  # Progressive tolerance up to configured max
            
            for leeway in leeway_values:
                try:
                    # Decode JWT token with the signing key
                    payload = jwt.decode(
                        token,
                        signing_key.key,
                        algorithms=['RS256'],
                        options={
                            "verify_exp": True, 
                            "verify_aud": False,  # Clerk doesn't use audience
                            "verify_iat": True,
                            "leeway": leeway  # Allow tolerance for iat timing issues
                        }
                    )
                    logger.info(f"Clerk JWT token verified successfully with leeway: {leeway}s")
                    break  # Success, exit the loop
                except jwt.InvalidTokenError as e:
                    if "iat" in str(e) and leeway < max(leeway_values):
                        logger.warning(f"Token validation failed with leeway {leeway}s, trying with larger tolerance")
                        continue  # Try with larger leeway
                    else:
                        # If it's still an iat issue after trying all leeway values, 
                        # try one more time with iat validation disabled (last resort)
                        if "iat" in str(e) and leeway == max(leeway_values) and self.jwt_disable_iat_on_failure:
                            logger.warning("All leeway values failed, trying with IAT validation disabled (last resort)")
                            try:
                                payload = jwt.decode(
                                    token,
                                    signing_key.key,
                                    algorithms=['RS256'],
                                    options={
                                        "verify_exp": True, 
                                        "verify_aud": False,
                                        "verify_iat": False,  # Disable IAT validation as last resort
                                        "leeway": 0
                                    }
                                )
                                logger.warning("Token validated with IAT validation disabled - this indicates a significant clock sync issue")
                                break
                            except Exception as final_e:
                                logger.error(f"Even with IAT validation disabled, token failed: {final_e}")
                                raise
                        else:
                            raise  # Re-raise if not an iat issue or we've tried all leeway values
            
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
            # Log more details for debugging
            if "iat" in str(e):
                logger.warning("Token 'issued at' time issue detected - this may be a clock synchronization problem")
                # Log current server time for debugging
                from datetime import datetime, timezone
                logger.warning(f"Current server time: {datetime.now(timezone.utc).isoformat()}")
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
    
    def is_token_expired(self, token: str) -> bool:
        """Check if token is expired - only check Clerk's expiry, not our session policy"""
        try:
            # Decode token without verification to get expiry info
            unverified_payload = jwt.decode(token, options={"verify_signature": False})
            exp_time = unverified_payload.get('exp')
            
            if not exp_time:
                logger.warning("Token has no expiry time")
                return True
            
            current_time = datetime.now(timezone.utc).timestamp()
            
            # Only check if token is expired according to Clerk's expiry
            if current_time > exp_time:
                logger.info(f"Token expired at {datetime.fromtimestamp(exp_time, timezone.utc).isoformat()}")
                return True
            
            # Log token age for debugging but don't enforce our session policy here
            iat_time = unverified_payload.get('iat')
            if iat_time:
                token_age_hours = (current_time - iat_time) / 3600
                logger.info(f"Token age: {token_age_hours:.2f} hours, expires in: {(exp_time - current_time) / 3600:.2f} hours")
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking token expiry: {e}")
            return True  # Assume expired if we can't check
    
    def authenticate_user(self, token: str) -> Optional[User]:
        """Authenticate user with Clerk JWT token - Single authentication method"""
        # First check if token is expired according to Clerk's expiry
        if self.is_token_expired(token):
            logger.warning("Token is expired according to Clerk's expiry")
            return None
        
        # Verify the token
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
    
    def create_session_token(self, user_id: str) -> Optional[str]:
        """Create a session token for a user with 1-day expiry"""
        try:
            if not self.clerk_secret_key:
                logger.error("Clerk secret key not configured")
                return None
            
            headers = {
                'Authorization': f'Bearer {self.clerk_secret_key}',
                'Content-Type': 'application/json'
            }
            
            # Calculate expiry time - 1 day from now
            expiry_time = datetime.now() + timedelta(hours=self.session_expiry_hours)
            
            # First create a session
            session_data = {
                'user_id': user_id,
                'expire_at': int(expiry_time.timestamp())  # Unix timestamp
            }
            
            session_response = requests.post(
                f'{self.clerk_api_url}/v1/sessions',
                headers=headers,
                json=session_data,
                timeout=10
            )
            
            if session_response.status_code == 200:
                session_result = session_response.json()
                session_id = session_result.get('id')
                
                if session_id:
                    # Now create a token for the session
                    token_data = {
                        'session_id': session_id,
                        'expires_in_seconds': self.session_expiry_hours * 3600
                    }
                    
                    token_response = requests.post(
                        f'{self.clerk_api_url}/v1/sessions/{session_id}/tokens',
                        headers=headers,
                        json=token_data,
                        timeout=10
                    )
                    
                    if token_response.status_code == 200:
                        token_result = token_response.json()
                        token = token_result.get('jwt')
                        logger.info(f"Created session token for user {user_id}, expires at {expiry_time.isoformat()}")
                        return token
                    else:
                        logger.error(f"Failed to create session token: {token_response.status_code} - {token_response.text}")
                        return None
                else:
                    logger.error("No session ID returned from Clerk")
                    return None
            else:
                logger.error(f"Failed to create session: {session_response.status_code} - {session_response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating session token: {e}")
            return None
    
    def create_long_lived_token(self, user_id: str) -> Optional[str]:
        """Create a long-lived token for session management"""
        try:
            if not self.clerk_secret_key:
                logger.error("Clerk secret key not configured")
                return None
            
            headers = {
                'Authorization': f'Bearer {self.clerk_secret_key}',
                'Content-Type': 'application/json'
            }
            
            # Calculate expiry time - 1 day from now
            expiry_time = datetime.now() + timedelta(hours=self.session_expiry_hours)
            
            # Create a session with longer expiry
            session_data = {
                'user_id': user_id,
                'expire_at': int(expiry_time.timestamp())  # Unix timestamp
            }
            
            session_response = requests.post(
                f'{self.clerk_api_url}/v1/sessions',
                headers=headers,
                json=session_data,
                timeout=10
            )
            
            if session_response.status_code == 200:
                session_result = session_response.json()
                session_id = session_result.get('id')
                
                if session_id:
                    # Create a token for the session with custom expiry
                    token_data = {
                        'session_id': session_id,
                        'expires_in_seconds': self.session_expiry_hours * 3600
                    }
                    
                    token_response = requests.post(
                        f'{self.clerk_api_url}/v1/sessions/{session_id}/tokens',
                        headers=headers,
                        json=token_data,
                        timeout=10
                    )
                    
                    if token_response.status_code == 200:
                        token_result = token_response.json()
                        token = token_result.get('jwt')
                        logger.info(f"Created long-lived token for user {user_id}, expires at {expiry_time.isoformat()}")
                        return token
                    else:
                        logger.error(f"Failed to create session token: {token_response.status_code} - {token_response.text}")
                        return None
                else:
                    logger.error("No session ID returned from Clerk")
                    return None
            else:
                logger.error(f"Failed to create session: {session_response.status_code} - {session_response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating long-lived token: {e}")
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
