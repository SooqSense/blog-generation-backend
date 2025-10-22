"""
Clerk API Service

Handles direct interactions with the Clerk API.
Provides methods for user management, session creation, and organization queries.
"""

import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from .base_service import BaseClerkService


class ClerkAPIService(BaseClerkService):
    """
    Service for interacting with Clerk API endpoints.
    
    Provides methods for:
    - Creating session tokens
    - Fetching user information
    - Managing user organizations
    - API error handling and retry logic
    """
    
    def __init__(self):
        """Initialize API service with configuration."""
        super().__init__()
        self.request_timeout = 10  # seconds
    
    def create_session_token(self, user_id: str) -> Optional[str]:
        """
        Create a session token for a user with configured expiry.
        
        Args:
            user_id: Clerk user ID
            
        Returns:
            JWT session token if successful, None otherwise
        """
        try:
            if not self.clerk_secret_key:
                self.logger.error("Clerk secret key not configured")
                return None
            
            headers = self.get_auth_headers()
            expiry_time = datetime.now() + timedelta(hours=self.session_expiry_hours)
            
            # Create session
            session_id = self._create_session(user_id, expiry_time, headers)
            if not session_id:
                return None
            
            # Create token for session
            return self._create_session_token(session_id, headers)
            
        except Exception as e:
            self.logger.error(f"Error creating session token: {e}")
            return None
    
    def _create_session(self, user_id: str, expiry_time: datetime, headers: Dict[str, str]) -> Optional[str]:
        """
        Create a session in Clerk.
        
        Args:
            user_id: Clerk user ID
            expiry_time: Session expiry time
            headers: Request headers
            
        Returns:
            Session ID if successful, None otherwise
        """
        try:
            session_data = {
                'user_id': user_id,
                'expire_at': int(expiry_time.timestamp())
            }
            
            response = requests.post(
                f'{self.clerk_api_url}/v1/sessions',
                headers=headers,
                json=session_data,
                timeout=self.request_timeout
            )
            
            if response.status_code == 200:
                session_result = response.json()
                session_id = session_result.get('id')
                
                if session_id:
                    self.logger.info(
                        f"Created session for user {user_id}, expires at {expiry_time.isoformat()}"
                    )
                    return session_id
                else:
                    self.logger.error("No session ID returned from Clerk")
                    return None
            else:
                self.handle_api_error("create session", response.status_code, response.text)
                return None
                
        except requests.RequestException as e:
            self.logger.error(f"Request error creating session: {e}")
            return None
    
    def _create_session_token(self, session_id: str, headers: Dict[str, str]) -> Optional[str]:
        """
        Create a token for an existing session.
        
        Args:
            session_id: Clerk session ID
            headers: Request headers
            
        Returns:
            JWT token if successful, None otherwise
        """
        try:
            token_data = {
                'session_id': session_id,
                'expires_in_seconds': self.session_expiry_hours * 3600
            }
            
            response = requests.post(
                f'{self.clerk_api_url}/v1/sessions/{session_id}/tokens',
                headers=headers,
                json=token_data,
                timeout=self.request_timeout
            )
            
            if response.status_code == 200:
                token_result = response.json()
                token = token_result.get('jwt')
                
                if token:
                    self.logger.info(f"Created session token for session {session_id}")
                    return token
                else:
                    self.logger.error("No JWT token returned from Clerk")
                    return None
            else:
                self.handle_api_error("create session token", response.status_code, response.text)
                return None
                
        except requests.RequestException as e:
            self.logger.error(f"Request error creating session token: {e}")
            return None
    
    def create_long_lived_token(self, user_id: str) -> Optional[str]:
        """
        Create a long-lived token for session management.
        
        This is an alias for create_session_token for backward compatibility.
        
        Args:
            user_id: Clerk user ID
            
        Returns:
            JWT token if successful, None otherwise
        """
        return self.create_session_token(user_id)
    
    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive user information from Clerk API.
        
        Args:
            user_id: Clerk user ID
            
        Returns:
            User data dictionary if successful, None otherwise
        """
        try:
            if not self.clerk_secret_key:
                self.logger.error("Clerk secret key not configured")
                return None
            
            headers = self.get_auth_headers()
            
            response = requests.get(
                f'{self.clerk_api_url}/v1/users/{user_id}',
                headers=headers,
                timeout=self.request_timeout
            )
            
            if response.status_code == 200:
                user_data = response.json()
                self.log_debug_info("Clerk API User Data", user_data)
                return user_data
            else:
                self.handle_api_error("get user info", response.status_code, response.text)
                return None
                
        except requests.RequestException as e:
            self.logger.error(f"Request error getting user info: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error getting user info: {e}")
            return None
    
    def get_user_organizations(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all organizations a user belongs to from Clerk API.
        
        Args:
            user_id: Clerk user ID
            
        Returns:
            List of organization dictionaries
        """
        try:
            if not self.clerk_secret_key:
                self.logger.error("Clerk secret key not configured")
                return []
            
            headers = self.get_auth_headers()
            
            response = requests.get(
                f'{self.clerk_api_url}/v1/users/{user_id}/organization_memberships',
                headers=headers,
                timeout=self.request_timeout
            )
            
            if response.status_code == 200:
                memberships_data = response.json()
                self.log_debug_info("Clerk API User Organizations", memberships_data)
                
                return self._parse_organization_memberships(memberships_data, user_id)
            else:
                self.handle_api_error("get user organizations", response.status_code, response.text)
                return []
                
        except requests.RequestException as e:
            self.logger.error(f"Request error getting user organizations: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error getting user organizations: {e}")
            return []
    
    def _parse_organization_memberships(self, memberships_data: Dict[str, Any], user_id: str) -> List[Dict[str, Any]]:
        """
        Parse organization memberships from Clerk API response.
        
        Args:
            memberships_data: Raw API response data
            user_id: User ID for logging
            
        Returns:
            List of parsed organization dictionaries
        """
        organizations = []
        
        # Handle both direct array and wrapped response formats
        memberships_list = (
            memberships_data.get('data', []) 
            if isinstance(memberships_data, dict) 
            else memberships_data
        )
        
        for membership in memberships_list:
            org_info = membership.get('organization', {})
            
            organization = {
                'organization_id': org_info.get('id'),
                'organization_name': org_info.get('slug') or org_info.get('name'),
                'organization_role': membership.get('role'),
            }
            
            # Only add organizations with valid data
            if organization['organization_id']:
                organizations.append(organization)
        
        self.logger.info(f"✅ Found {len(organizations)} organizations for user {user_id}")
        
        for org in organizations:
            self.logger.info(
                f"   - {org['organization_name']} "
                f"(ID: {org['organization_id']}, Role: {org['organization_role']})"
            )
        
        return organizations
    
    def validate_user_exists(self, user_id: str) -> bool:
        """
        Validate that a user exists in Clerk.
        
        Args:
            user_id: Clerk user ID to validate
            
        Returns:
            True if user exists, False otherwise
        """
        user_info = self.get_user_info(user_id)
        return user_info is not None
    
    def get_organization_info(self, org_id: str) -> Optional[Dict[str, Any]]:
        """
        Get organization information from Clerk API.
        
        Args:
            org_id: Clerk organization ID
            
        Returns:
            Organization data dictionary if successful, None otherwise
        """
        try:
            if not self.clerk_secret_key:
                self.logger.error("Clerk secret key not configured")
                return None
            
            headers = self.get_auth_headers()
            
            response = requests.get(
                f'{self.clerk_api_url}/v1/organizations/{org_id}',
                headers=headers,
                timeout=self.request_timeout
            )
            
            if response.status_code == 200:
                org_data = response.json()
                self.log_debug_info("Clerk API Organization Data", org_data)
                return org_data
            else:
                self.handle_api_error("get organization info", response.status_code, response.text)
                return None
                
        except requests.RequestException as e:
            self.logger.error(f"Request error getting organization info: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error getting organization info: {e}")
            return None
    
    def revoke_session(self, session_id: str) -> bool:
        """
        Revoke a Clerk session.
        
        Args:
            session_id: Clerk session ID to revoke
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.clerk_secret_key:
                self.logger.error("Clerk secret key not configured")
                return False
            
            headers = self.get_auth_headers()
            
            response = requests.post(
                f'{self.clerk_api_url}/v1/sessions/{session_id}/revoke',
                headers=headers,
                timeout=self.request_timeout
            )
            
            if response.status_code == 200:
                self.logger.info(f"Successfully revoked session {session_id}")
                return True
            else:
                self.handle_api_error("revoke session", response.status_code, response.text)
                return False
                
        except requests.RequestException as e:
            self.logger.error(f"Request error revoking session: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error revoking session: {e}")
            return False
