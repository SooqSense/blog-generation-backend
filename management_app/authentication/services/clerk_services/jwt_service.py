"""
Clerk JWT Authentication Service

Handles JWT token verification, validation, and authentication logic.
Provides secure token processing with proper error handling and logging.
"""

import jwt
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from jwt import PyJWKClient

from .base_service import BaseClerkService


class ClerkJWTAuthService(BaseClerkService):
    """
    Service for handling Clerk JWT token authentication.
    
    Provides methods for:
    - JWT token verification using JWKS
    - Token expiry validation
    - Payload extraction and validation
    - User authentication from tokens
    """
    
    def __init__(self):
        """Initialize JWT service with JWKS client."""
        super().__init__()
        self.jwks_client = self._initialize_jwks_client()
    
    def _initialize_jwks_client(self) -> Optional[PyJWKClient]:
        """
        Initialize the JWKS client for token verification.
        
        Returns:
            PyJWKClient instance or None if initialization fails
        """
        if not self.clerk_jwks_url:
            self.logger.warning("CLERK_JWKS_URL not configured")
            return None
        
        try:
            client = PyJWKClient(self.clerk_jwks_url)
            self.logger.info("JWKS client initialized successfully")
            return client
        except Exception as e:
            self.logger.error(f"Failed to initialize JWKS client: {e}")
            return None
    
    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify Clerk JWT token using JWKS.
        
        Args:
            token: JWT token string to verify
            
        Returns:
            Decoded token payload if valid, None otherwise
        """
        try:
            # Validate token format and algorithm
            if not self._validate_token_format(token):
                return None
            
            if not self.jwks_client:
                self.logger.error("JWKS client not initialized. Cannot verify token.")
                return None
            
            self.logger.info("Verifying Clerk JWT token with JWKS")
            return self._verify_clerk_token(token)
            
        except Exception as e:
            self.logger.error(f"Error verifying JWT token: {e}")
            return None
    
    def _validate_token_format(self, token: str) -> bool:
        """
        Validate token format and algorithm.
        
        Args:
            token: JWT token to validate
            
        Returns:
            True if token format is valid, False otherwise
        """
        try:
            header = jwt.get_unverified_header(token)
            algorithm = header.get('alg', '')
            
            if algorithm != 'RS256':
                self.logger.warning(
                    f"Unsupported token algorithm: {algorithm}. Only RS256 tokens are supported."
                )
                return False
            
            return True
        except Exception as e:
            self.logger.error(f"Error validating token format: {e}")
            return False
    
    def _verify_clerk_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify Clerk JWT token using JWKS with progressive leeway handling.
        
        Args:
            token: JWT token to verify
            
        Returns:
            Decoded token payload if valid, None otherwise
        """
        try:
            # Get signing key from JWKS
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            
            # Log debug information
            self._log_token_debug_info(token)
            
            # Try verification with progressive leeway values
            payload = self._verify_with_leeway(token, signing_key.key)
            
            if payload:
                # Validate issuer if configured
                if not self._validate_issuer(payload):
                    return None
                
                self.logger.debug("Clerk JWT token verified successfully")
                return payload
            
            return None
            
        except jwt.ExpiredSignatureError:
            self.logger.warning("Clerk JWT token has expired")
            return None
        except jwt.InvalidTokenError as e:
            self.logger.warning(f"Invalid Clerk JWT token: {e}")
            self._handle_token_error(e)
            return None
    
    def _log_token_debug_info(self, token: str) -> None:
        """
        Log token debug information for troubleshooting.
        
        Args:
            token: JWT token to analyze
        """
        try:
            unverified_payload = jwt.decode(token, options={"verify_signature": False})
            
            # Extract timing information
            iat_time = unverified_payload.get('iat')
            exp_time = unverified_payload.get('exp')
            current_time = datetime.now(timezone.utc).timestamp()
            
            timing_info = {
                'iat_timestamp': iat_time,
                'exp_timestamp': exp_time,
                'current_timestamp': current_time,
                'iat_datetime': datetime.fromtimestamp(iat_time, timezone.utc).isoformat() if iat_time else None,
                'exp_datetime': datetime.fromtimestamp(exp_time, timezone.utc).isoformat() if exp_time else None,
                'current_datetime': datetime.now(timezone.utc).isoformat(),
                'time_since_iat': f"{(current_time - iat_time):.2f} seconds" if iat_time else None,
                'time_until_exp': f"{(exp_time - current_time):.2f} seconds" if exp_time else None
            }
            
            self.log_debug_info("Token Timing Debug", timing_info)
            
            # Log organization and user information
            self._log_token_payload_info(unverified_payload)
            
        except Exception as e:
            self.logger.warning(f"Could not decode token for debugging: {e}")
    
    def _log_token_payload_info(self, payload: Dict[str, Any]) -> None:
        """
        Log token payload information for debugging.
        
        Args:
            payload: Decoded token payload
        """
        # Extract organization information
        org_data = payload.get('o')  # Clerk uses 'o' for organization
        
        if org_data and isinstance(org_data, dict):
            org_info = {
                'organization_id': org_data.get('id'),
                'organization_role': org_data.get('rol'),  # Clerk uses 'rol'
                'organization_slug': org_data.get('slg'),  # Clerk uses 'slg'
                'full_org_object': org_data
            }
            self.log_debug_info("Token Organization Data", org_info)
        else:
            self.logger.warning("⚠️  Token does NOT contain organization data")
        
        # Extract user information
        user_info = {
            'user_id': payload.get('sub'),
            'email': payload.get('email') or payload.get('email_address'),
            'username': payload.get('username') or payload.get('preferred_username'),
            'first_name': payload.get('given_name') or payload.get('first_name'),
            'last_name': payload.get('family_name') or payload.get('last_name')
        }
        self.log_debug_info("Token User Info", user_info)
    
    def _verify_with_leeway(self, token: str, signing_key: str) -> Optional[Dict[str, Any]]:
        """
        Verify token with progressive leeway values to handle clock sync issues.
        
        Args:
            token: JWT token to verify
            signing_key: Signing key for verification
            
        Returns:
            Decoded payload if verification succeeds, None otherwise
        """
        leeway_values = [30, 60, 120, 300, self.jwt_max_leeway]
        
        for leeway in leeway_values:
            try:
                payload = jwt.decode(
                    token,
                    signing_key,
                    algorithms=['RS256'],
                    options={
                        "verify_exp": True,
                        "verify_aud": False,  # Clerk doesn't use audience
                        "verify_iat": True,
                        "leeway": leeway
                    }
                )
                self.logger.info(f"Token verified successfully with leeway: {leeway}s")
                return payload
                
            except jwt.InvalidTokenError as e:
                if "iat" in str(e) and leeway < max(leeway_values):
                    self.logger.warning(
                        f"Token validation failed with leeway {leeway}s, trying larger tolerance"
                    )
                    continue
                else:
                    # Last resort: disable IAT validation if configured
                    if ("iat" in str(e) and 
                        leeway == max(leeway_values) and 
                        self.jwt_disable_iat_on_failure):
                        return self._verify_without_iat(token, signing_key)
                    else:
                        raise
        
        return None
    
    def _verify_without_iat(self, token: str, signing_key: str) -> Optional[Dict[str, Any]]:
        """
        Last resort verification without IAT validation.
        
        Args:
            token: JWT token to verify
            signing_key: Signing key for verification
            
        Returns:
            Decoded payload if verification succeeds, None otherwise
        """
        try:
            self.logger.warning("Trying verification with IAT validation disabled (last resort)")
            
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=['RS256'],
                options={
                    "verify_exp": True,
                    "verify_aud": False,
                    "verify_iat": False,  # Disable IAT validation
                    "leeway": 0
                }
            )
            
            self.logger.warning(
                "Token validated with IAT validation disabled - "
                "this indicates a significant clock sync issue"
            )
            return payload
            
        except Exception as e:
            self.logger.error(f"Even with IAT validation disabled, token failed: {e}")
            return None
    
    def _validate_issuer(self, payload: Dict[str, Any]) -> bool:
        """
        Validate token issuer if frontend URL is configured.
        
        Args:
            payload: Decoded token payload
            
        Returns:
            True if issuer is valid or not configured, False otherwise
        """
        if not self.clerk_frontend_url:
            return True  # Skip validation if not configured
        
        issuer = payload.get('iss')
        if issuer != self.clerk_frontend_url:
            self.logger.warning(f"Invalid issuer: {issuer}")
            return False
        
        return True
    
    def _handle_token_error(self, error: jwt.InvalidTokenError) -> None:
        """
        Handle and log specific token errors for debugging.
        
        Args:
            error: JWT token error
        """
        if "iat" in str(error):
            self.logger.warning(
                "Token 'issued at' time issue detected - "
                "this may be a clock synchronization problem"
            )
            self.logger.warning(
                f"Current server time: {datetime.now(timezone.utc).isoformat()}"
            )
    
    def is_token_expired(self, token: str) -> bool:
        """
        Check if token is expired according to Clerk's expiry time.
        
        Args:
            token: JWT token to check
            
        Returns:
            True if token is expired, False otherwise
        """
        try:
            unverified_payload = jwt.decode(token, options={"verify_signature": False})
            exp_time = unverified_payload.get('exp')
            
            if not exp_time:
                self.logger.warning("Token has no expiry time")
                return True
            
            current_time = datetime.now(timezone.utc).timestamp()
            
            if current_time > exp_time:
                self.logger.info(
                    f"Token expired at {datetime.fromtimestamp(exp_time, timezone.utc).isoformat()}"
                )
                return True
            
            # Log token age for debugging
            iat_time = unverified_payload.get('iat')
            if iat_time:
                token_age_hours = (current_time - iat_time) / 3600
                expires_in_hours = (exp_time - current_time) / 3600
                self.logger.debug(
                    f"Token age: {token_age_hours:.2f} hours, "
                    f"expires in: {expires_in_hours:.2f} hours"
                )
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking token expiry: {e}")
            return True  # Assume expired if we can't check
    
    def extract_user_info(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract user information from JWT payload.
        
        Args:
            payload: Decoded JWT payload
            
        Returns:
            Dictionary containing extracted user information
        """
        # Extract organization information
        org_data = payload.get('o', {})
        org_info = {}
        
        if isinstance(org_data, dict):
            org_info = {
                'organization_id': org_data.get('id'),
                'organization_role': org_data.get('rol'),
                'organization_slug': org_data.get('slg')
            }
        
        # Extract user information
        user_info = {
            'clerk_user_id': payload.get('sub'),
            'email': payload.get('email') or payload.get('email_address'),
            'username': payload.get('username') or payload.get('preferred_username'),
            'first_name': payload.get('given_name') or payload.get('first_name'),
            'last_name': payload.get('family_name') or payload.get('last_name'),
            **org_info
        }
        
        return user_info
