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
                
                # Log ALL payload data for debugging
                logger.info("=" * 80)
                logger.info("FULL JWT TOKEN PAYLOAD (unverified):")
                logger.info("=" * 80)
                for key, value in unverified_payload.items():
                    logger.info(f"  {key}: {value}")
                logger.info("=" * 80)
                
                # Extract organization information from Clerk's actual token format
                # Clerk stores organization data in the 'o' field as a nested object
                org_data = unverified_payload.get('o')  # Clerk uses 'o' for organization
                
                if org_data and isinstance(org_data, dict):
                    org_id = org_data.get('id')
                    org_role = org_data.get('rol')  # Clerk uses 'rol' not 'role'
                    org_slug = org_data.get('slg')  # Clerk uses 'slg' not 'slug'
                    
                    logger.info(f"✅ Token contains organization data in 'o' field:")
                    logger.info(f"   - Organization ID: {org_id}")
                    logger.info(f"   - Organization Role: {org_role}")
                    logger.info(f"   - Organization Slug: {org_slug}")
                    logger.info(f"   - Full org object: {org_data}")
                else:
                    logger.warning("⚠️  Token does NOT contain organization data ('o' field is missing or invalid)")
                    logger.warning("   This user may not be part of any organization in Clerk")
                
                # Log user information - check multiple possible fields
                user_id = unverified_payload.get('sub')
                email = unverified_payload.get('email') or unverified_payload.get('email_address')
                username = unverified_payload.get('username') or unverified_payload.get('preferred_username')
                
                # Also check for other common user fields
                first_name = unverified_payload.get('given_name') or unverified_payload.get('first_name')
                last_name = unverified_payload.get('family_name') or unverified_payload.get('last_name')
                
                logger.info(f"📧 User Info - ID: {user_id}")
                logger.info(f"   - Email: {email}")
                logger.info(f"   - Username: {username}")
                logger.info(f"   - First Name: {first_name}")
                logger.info(f"   - Last Name: {last_name}")
                
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
            email = clerk_payload.get('email') or clerk_payload.get('email_address')
            username = clerk_payload.get('username') or clerk_payload.get('preferred_username')
            
            # Extract organization information from JWT payload - Clerk format
            org_data = clerk_payload.get('o')  # Clerk uses 'o' for organization
            org_id = None
            org_role = None
            org_slug = None
            
            if org_data and isinstance(org_data, dict):
                org_id = org_data.get('id')
                org_role = org_data.get('rol')  # Clerk uses 'rol' not 'role'
                org_slug = org_data.get('slg')  # Clerk uses 'slg' not 'slug'
            
            # Initialize first_name and last_name
            first_name = None
            last_name = None
            
            # If user info is missing from JWT, fetch from Clerk API
            if not email or not username:
                logger.info("User info missing from JWT, fetching from Clerk API...")
                api_service = ClerkAPIService()
                user_info = api_service.get_user_info(clerk_user_id)
                
                if user_info:
                    # Extract email addresses
                    email_addresses = user_info.get('email_addresses', [])
                    if email_addresses and not email:
                        email = email_addresses[0].get('email_address')
                    
                    # Extract username
                    if not username:
                        username = user_info.get('username')
                    
                    # Extract first and last name
                    first_name = user_info.get('first_name')
                    last_name = user_info.get('last_name')
                    
                    logger.info(f"Fetched from Clerk API:")
                    logger.info(f"  - Email: {email}")
                    logger.info(f"  - Username: {username}")
                    logger.info(f"  - First Name: {first_name}")
                    logger.info(f"  - Last Name: {last_name}")
            
            logger.info("=" * 80)
            logger.info("GET_OR_CREATE_USER - Processing JWT payload")
            logger.info("=" * 80)
            logger.info(f"Clerk User ID: {clerk_user_id}")
            logger.info(f"Email: {email}")
            logger.info(f"Username: {username}")
            logger.info(f"Organization ID: {org_id}")
            logger.info(f"Organization Role: {org_role}")
            logger.info(f"Organization Slug: {org_slug}")
            logger.info("=" * 80)
            
            if not clerk_user_id:
                logger.error("No clerk_user_id in JWT payload")
                return None
            
            # Try to get existing user by clerk_user_id first (most reliable)
            user = User.objects.filter(clerk_user_id=clerk_user_id).first()
            
            # If not found by clerk_user_id, try by email (but be careful about duplicates)
            if not user and email:
                user_by_email = User.objects.filter(email=email).first()
                if user_by_email:
                    # Found user by email but not by clerk_user_id
                    # This might be an old user without clerk_user_id, so we'll update it
                    logger.info(f"Found user by email but not clerk_user_id - this may be a legacy user")
                    user = user_by_email
            
            if user:
                logger.info(f"Found existing user: {user.username} (ID: {user.id})")
                # Update user information
                updated = False
                
                # Update clerk_user_id if missing
                if not user.clerk_user_id or user.clerk_user_id != clerk_user_id:
                    logger.info(f"Updating clerk_user_id: {user.clerk_user_id} -> {clerk_user_id}")
                    user.clerk_user_id = clerk_user_id
                    updated = True
                
                # Update email - force update from Clerk if we have the real email
                if email and user.email != email:
                    # Check if email is already taken by another user
                    email_exists = User.objects.filter(email=email).exclude(id=user.id).exists()
                    if email_exists:
                        # Find and update the conflicting user
                        conflicting_user = User.objects.filter(email=email).exclude(id=user.id).first()
                        if conflicting_user and not conflicting_user.clerk_user_id:
                            # This is likely a duplicate/old user without Clerk ID - make email unique
                            logger.warning(f"⚠️  Found duplicate user with email {email} - updating conflicting user")
                            conflicting_user.email = f"old-{conflicting_user.id}-{email}"
                            conflicting_user.save()
                            logger.info(f"✅ Updated conflicting user email to: {conflicting_user.email}")
                            # Now we can update this user's email
                            logger.info(f"Updating email: {user.email} -> {email}")
                            user.email = email
                            updated = True
                        else:
                            logger.warning(f"⚠️  Cannot update email from {user.email} to {email} - email already exists for another Clerk user")
                            logger.warning(f"    Keeping existing email: {user.email}")
                    else:
                        logger.info(f"Updating email: {user.email} -> {email}")
                        user.email = email
                        updated = True
                    
                # Update username only if available
                if username and user.username != username:
                    # Check if username is available
                    if not User.objects.filter(username=username).exclude(id=user.id).exists():
                        logger.info(f"Updating username: {user.username} -> {username}")
                        user.username = username
                        updated = True
                    else:
                        logger.warning(f"⚠️  Username {username} already exists - keeping {user.username}")
                
                # Update first and last name (handle None values gracefully)
                if first_name is not None and user.first_name != first_name:
                    logger.info(f"Updating first_name: '{user.first_name}' -> '{first_name}'")
                    user.first_name = first_name
                    updated = True
                if last_name is not None and user.last_name != last_name:
                    logger.info(f"Updating last_name: '{user.last_name}' -> '{last_name}'")
                    user.last_name = last_name
                    updated = True
                
                # Update organization information
                if org_id and user.organization_id != org_id:
                    logger.info(f"Updating organization_id: {user.organization_id} -> {org_id}")
                    user.organization_id = org_id
                    updated = True
                if org_role and user.organization_role != org_role:
                    logger.info(f"Updating organization_role: {user.organization_role} -> {org_role}")
                    user.organization_role = org_role
                    updated = True
                if org_slug and user.organization_name != org_slug:
                    logger.info(f"Updating organization_name: {user.organization_name} -> {org_slug}")
                    user.organization_name = org_slug
                    updated = True
                
                if updated:
                    try:
                        user.save()
                        logger.info(f"✅ Updated existing user: {user.username}")
                        logger.info(f"   - Email: {user.email}")
                        logger.info(f"   - First Name: {user.first_name}")
                        logger.info(f"   - Last Name: {user.last_name}")
                        logger.info(f"   - Organization ID: {user.organization_id}")
                        logger.info(f"   - Organization Name: {user.organization_name}")
                        logger.info(f"   - Organization Role: {user.organization_role}")
                    except Exception as save_error:
                        logger.error(f"❌ Error saving user updates: {save_error}")
                        # Don't raise - return the user with old data rather than failing
                        logger.warning("Returning user without updates due to save error")
                        # Refresh from database to ensure we have clean state
                        user.refresh_from_db()
                        return user
                else:
                    logger.info(f"ℹ️  No updates needed for user: {user.username}")
                
                return user
            
            # Create new user only if no existing user found
            logger.info("No existing user found - creating new user")
            display_username = username or (email.split('@')[0] if email else clerk_user_id)
            
            # Ensure username is unique
            original_username = display_username
            counter = 1
            while User.objects.filter(username=display_username).exists():
                display_username = f"{original_username}_{counter}"
                counter += 1
            
            logger.info(f"Creating new user with:")
            logger.info(f"   - Username: {display_username}")
            logger.info(f"   - Email: {email}")
            logger.info(f"   - First Name: {first_name}")
            logger.info(f"   - Last Name: {last_name}")
            logger.info(f"   - Clerk User ID: {clerk_user_id}")
            logger.info(f"   - Organization ID: {org_id}")
            logger.info(f"   - Organization Name: {org_slug}")
            logger.info(f"   - Organization Role: {org_role}")
            
            user = User.objects.create_user(
                username=display_username,
                email=email or '',
                clerk_user_id=clerk_user_id,
                first_name=first_name or '',
                last_name=last_name or '',
                organization_id=org_id,
                organization_name=org_slug,
                organization_role=org_role,
                is_active=True
            )
            
            logger.info(f"✅ Created new user: {user.username} ({clerk_user_id})")
            logger.info(f"   - Email: {user.email}")
            logger.info(f"   - First Name: {user.first_name}")
            logger.info(f"   - Last Name: {user.last_name}")
            logger.info(f"   - Organization ID: {user.organization_id}")
            logger.info(f"   - Organization Name: {user.organization_name}")
            logger.info(f"   - Organization Role: {user.organization_role}")
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
                user_data = response.json()
                logger.info("=" * 80)
                logger.info("CLERK API USER DATA:")
                logger.info("=" * 80)
                logger.info(f"Full response: {user_data}")
                logger.info("=" * 80)
                return user_data
            else:
                logger.error(f"Failed to get user info: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None
