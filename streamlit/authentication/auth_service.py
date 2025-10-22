import streamlit as st
import requests
import logging
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class ClerkAuthService:
    """Clerk Authentication Service for Streamlit"""
    
    def __init__(self):
        self.base_url = os.getenv("BACKEND_API_BASE_URL", "http://localhost:8000")
        self.auth_endpoints = {
            'login': f"{self.base_url}/auth/login/",
            'verify': f"{self.base_url}/auth/verify/",
            'profile': f"{self.base_url}/auth/profile/"
        }
        
        # Always initialize clerk_secret_key attribute
        self.clerk_secret_key = os.getenv("CLERK_SECRET_KEY")
        
        # Session expiry configuration - match your Clerk dashboard setting
        self.session_expiry_days = int(os.getenv("CLERK_SESSION_EXPIRY_DAYS", "7"))  # Default 7 days
    
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify Clerk JWT token and return user info.
        
        This is the PROPER method for Clerk authentication:
        1. Frontend authenticates with Clerk
        2. Clerk returns JWT token
        3. Call this method with Clerk's JWT token
        4. Backend verifies token using JWKS and creates/updates user
        """
        try:
            response = requests.post(
                self.auth_endpoints['verify'],
                json={'token': token},
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    user_data = data.get('user')
                    logger.info("=" * 80)
                    logger.info("VERIFY TOKEN - Received user data from backend:")
                    logger.info("=" * 80)
                    if user_data:
                        for key, value in user_data.items():
                            logger.info(f"  {key}: {value}")
                    logger.info("=" * 80)
                    
                    return {
                        'success': True,
                        'user': user_data,
                        'message': data.get('message'),
                        'token': token  # Return the original Clerk token
                    }
                else:
                    return {
                        'success': False,
                        'message': data.get('message', 'Token verification failed')
                    }
            else:
                return {
                    'success': False,
                    'message': f'Token verification failed: {response.status_code}'
                }
                
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return {
                'success': False,
                'message': f'Token verification error: {str(e)}'
            }
    
    
    def authenticate_with_clerk_credentials(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate with Clerk using email and get JWT token"""
        try:
            if not self.clerk_secret_key:
                return {
                    'success': False,
                    'message': 'Clerk secret key not configured. Please check your CLERK_SECRET_KEY in .env file.'
                }
            
            headers = {
                'Authorization': f'Bearer {self.clerk_secret_key}',
                'Content-Type': 'application/json'
            }
            
            # Find user by email
            response = requests.get(
                f'https://api.clerk.com/v1/users',
                headers=headers,
                params={'email_address': email},
                timeout=10
            )
            
            if response.status_code == 200:
                users = response.json()
                
                # Handle both list and dict responses from Clerk API
                if isinstance(users, list) and users:
                    user_data = users[0]
                elif isinstance(users, dict) and users.get('data'):
                    user_data = users['data'][0]
                else:
                    return {
                        'success': False,
                        'message': f'User not found with email: {email}. Please create an account in Clerk dashboard.'
                    }
                
                user_id = user_data['id']
                
                # Create a Clerk session for this user with configurable expiry
                from datetime import datetime, timedelta
                expiry_time = datetime.now() + timedelta(days=self.session_expiry_days)
                
                session_payload = {
                    'user_id': user_id,
                    'expire_at': int(expiry_time.timestamp())  # Unix timestamp for 7 days from now
                }
                
                # Create session using Clerk API
                session_response = requests.post(
                    f'https://api.clerk.com/v1/sessions',
                    headers=headers,
                    json=session_payload,
                    timeout=10
                )
                
                if session_response.status_code == 200:
                    session_data = session_response.json()
                    session_id = session_data['id']
                    
                    # Get JWT token from the session with proper expiry
                    token_payload = {
                        'expires_in_seconds': self.session_expiry_days * 24 * 3600  # Convert days to seconds
                    }
                    
                    token_response = requests.post(
                        f'https://api.clerk.com/v1/sessions/{session_id}/tokens',
                        headers=headers,
                        json=token_payload,
                        timeout=10
                    )
                    
                    if token_response.status_code == 200:
                        token_data = token_response.json()
                        clerk_token = token_data.get('jwt')
                        
                        if clerk_token:
                            logger.info(f"Created session token with {self.session_expiry_days}-day expiry for user {user_id}")
                            # Verify the Clerk token with our backend
                            verify_result = self.verify_token(clerk_token)
                            if verify_result['success']:
                                return {
                                    'success': True,
                                    'user': verify_result['user'],
                                    'token': clerk_token,
                                    'message': f'Authentication successful with {self.session_expiry_days}-day token'
                                }
                            else:
                                return {
                                    'success': False,
                                    'message': 'Failed to verify Clerk token. Please try again.',
                                }
                        else:
                            return {
                                'success': False,
                                'message': 'Failed to get Clerk token. Please try again.',
                            }
                    else:
                        return {
                            'success': False,
                            'message': f'Failed to get JWT token from session: {token_response.status_code} - {token_response.text}',
                        }
                else:
                    return {
                        'success': False,
                        'message': f'Failed to create Clerk session: {session_response.status_code} - {session_response.text}',
                    }
            elif response.status_code == 401:
                return {
                    'success': False,
                    'message': 'Invalid Clerk API key. Please check your CLERK_SECRET_KEY.'
                }
            else:
                return {
                    'success': False,
                    'message': f'Authentication failed: {response.status_code} - {response.text}',
                }
                
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'message': 'Request timeout. Please check your internet connection.',
            }
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'message': 'Connection error. Please check your internet connection.',
            }
        except Exception as e:
            logger.error(f"Clerk authentication error: {e}")
            return {
                'success': False,
                'message': f'Authentication error: {str(e)}'
            }
    
    
    def get_profile(self, token: str) -> Dict[str, Any]:
        """Get user profile using JWT token"""
        try:
            response = requests.get(
                self.auth_endpoints['profile'],
                headers={
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json'
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return {
                        'success': True,
                        'user': data.get('user'),
                        'message': data.get('message')
                    }
                else:
                    return {
                        'success': False,
                        'message': data.get('message', 'Profile fetch failed')
                    }
            else:
                return {
                    'success': False,
                    'message': f'Profile fetch failed: {response.status_code}'
                }
                
        except Exception as e:
            logger.error(f"Profile fetch error: {e}")
            return {
                'success': False,
                'message': f'Profile fetch error: {str(e)}'
            }


class StreamlitAuthManager:
    """Streamlit Authentication Manager"""
    
    def __init__(self):
        self.auth_service = ClerkAuthService()
        self._init_session_state()
    
    def _init_session_state(self):
        """Initialize session state for authentication"""
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'user' not in st.session_state:
            st.session_state.user = None
        if 'token' not in st.session_state:
            st.session_state.token = None
    
    def login(self, email: str, password: str) -> bool:
        """Perform login using Clerk authentication and update session state"""
        result = self.auth_service.authenticate_with_clerk_credentials(email, password)
        
        if result['success']:
            st.session_state.authenticated = True
            st.session_state.user = result['user']
            st.session_state.token = result['token']
            
            logger.info("=" * 80)
            logger.info(f"LOGIN SUCCESS - User {email} logged in")
            logger.info("Session state user data:")
            logger.info("=" * 80)
            if result.get('user'):
                for key, value in result['user'].items():
                    logger.info(f"  {key}: {value}")
            logger.info("=" * 80)
            
            return True
        else:
            st.error(result['message'])
            logger.warning(f"Login failed for {email}: {result['message']}")
            return False
    
    
    def logout(self):
        """Logout and clear session state"""
        st.session_state.authenticated = False
        st.session_state.user = None
        st.session_state.token = None
        st.rerun()
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return st.session_state.get('authenticated', False)
    
    def get_user(self) -> Optional[Dict[str, Any]]:
        """Get current user info"""
        return st.session_state.get('user')
    
    def get_token(self) -> Optional[str]:
        """Get current JWT token"""
        return st.session_state.get('token')
    
    def verify_session(self) -> bool:
        """Verify current session token"""
        token = self.get_token()
        if not token:
            return False
        
        result = self.auth_service.verify_token(token)
        if result['success']:
            st.session_state.user = result['user']
            return True
        else:
            self.logout()
            return False
    
    def require_auth(self, feature_name: str = "this feature"):
        """Require authentication for a feature"""
        if not self.is_authenticated():
            st.error(f"Please login to access {feature_name}")
            st.stop()
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API calls"""
        token = self.get_token()
        if token:
            return {'Authorization': f'Bearer {token}'}
        return {}
    
    def login_with_clerk_token(self, clerk_jwt_token: str) -> bool:
        """Login using a Clerk JWT token"""
        result = self.auth_service.verify_token(clerk_jwt_token)
        
        if result['success']:
            st.session_state.authenticated = True
            st.session_state.user = result['user']
            st.session_state.token = result['token']
            return True
        else:
            st.error(result['message'])
            return False
