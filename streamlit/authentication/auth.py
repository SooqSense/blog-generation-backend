"""
Simple Clerk Authentication for Streamlit
Handles user ID-based authentication using Clerk's backend API
"""

import streamlit as st
import os
import jwt
import requests
from pathlib import Path
from dotenv import load_dotenv
import logging

# Import Clerk backend API
try:
    from clerk_backend_api import Clerk
    CLERK_BACKEND_AVAILABLE = True
except ImportError:
    CLERK_BACKEND_AVAILABLE = False
    print("⚠️ clerk_backend_api not installed. Please install with: pip install clerk-backend-api")

# Load environment variables
project_root = Path(__file__).parent.parent.parent
env_path = project_root / '.env'
load_dotenv(env_path)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleClerkAuth:
    """Simple Clerk authentication using user ID and backend API"""
    
    def __init__(self):
        # Load Clerk credentials
        self.clerk_secret = os.getenv('CLERK_SECRET_KEY', '').strip('"\'')
        self.clerk_publishable_key = os.getenv('NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY', '').strip('"\'')
        
        # Validate configuration
        if not self.clerk_secret:
            logger.error("CLERK_SECRET_KEY not found in environment variables")
        if not self.clerk_publishable_key:
            logger.error("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY not found in environment variables")
        if not CLERK_BACKEND_AVAILABLE:
            logger.error("clerk_backend_api package not available")
            
        logger.info(f"Clerk Auth initialized for user ID authentication")
        logger.info(f"  Backend API Available: {CLERK_BACKEND_AVAILABLE}")
        logger.info(f"  Secret Key Configured: {'Yes' if self.clerk_secret else 'No'}")
        
        # Initialize Clerk client
        self.clerk_client = None
        if CLERK_BACKEND_AVAILABLE and self.clerk_secret:
            try:
                self.clerk_client = Clerk(bearer_auth=self.clerk_secret)
                logger.info("✅ Clerk backend client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Clerk client: {e}")
                self.clerk_client = None
    
    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated"""
        return st.session_state.get('authenticated', False)
    
    def get_user(self) -> dict:
        """Get current user data"""
        return st.session_state.get('user_data', {})
    
    def authenticate_with_user_id(self, user_id: str) -> bool:
        """Authenticate user using Clerk user ID"""
        if not self.clerk_client:
            logger.error("Clerk client not available")
            return False
        
        if not user_id or not user_id.strip():
            logger.error("User ID cannot be empty")
            return False
        
        try:
            logger.info(f"🔐 Attempting to authenticate user: {user_id}")
            
            # Generate sign-in token for the user ID
            res = self.clerk_client.sign_in_tokens.create(request={
                "user_id": user_id.strip(),
            })
            
            if res is None:
                logger.error("Failed to create sign-in token - no response")
                return False
            
            # Extract token from response
            if hasattr(res, 'token'):
                token = res.token
            elif hasattr(res, 'id'):
                token = res.id
            else:
                # If response is a dict
                if isinstance(res, dict):
                    token = res.get('token') or res.get('id')
                else:
                    token = str(res)
            
            if not token:
                logger.error("No token received from Clerk API")
                return False
            
            logger.info(f"✅ Sign-in token generated successfully")
            
            # Get user details from Clerk
            user_info = self.get_user_info(user_id)
            
            if not user_info:
                logger.warning("Could not retrieve user info, using basic data")
                user_info = {
                    'id': user_id,
                    'email': f'user-{user_id[-8:]}@clerk.dev',
                    'name': f'Clerk User {user_id[-4:]}',
                }
            
            # Set user as authenticated
            self.set_authenticated_user({
                'id': user_id,
                'email': user_info.get('email', f'user-{user_id[-8:]}@clerk.dev'),
                'name': user_info.get('name', f'Clerk User {user_id[-4:]}'),
                'authenticated': True,
                'token': token,
                'clerk_user_id': user_id
            })
            
            logger.info(f"✅ User {user_id} authenticated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Authentication failed for user {user_id}: {str(e)}")
            return False
    
    def get_user_info(self, user_id: str) -> dict:
        """Get user information from Clerk"""
        if not self.clerk_client:
            return {}
        
        try:
            # This would typically use the users API to get user details
            # For now, we'll return basic info based on user_id
            return {
                'id': user_id,
                'email': f'user-{user_id[-8:]}@clerk.dev',
                'name': f'Clerk User {user_id[-4:]}',
                'user_id': user_id
            }
        except Exception as e:
            logger.error(f"Failed to get user info for {user_id}: {str(e)}")
            return {}
    
    def handle_auth_callback(self) -> bool:
        """Handle authentication - check session state for pending auth"""
        try:
            # Check if there's a pending user ID authentication
            if 'pending_user_id' in st.session_state:
                user_id = st.session_state.pending_user_id
                del st.session_state.pending_user_id
                
                logger.info(f"Processing pending authentication for user: {user_id}")
                return self.authenticate_with_user_id(user_id)
            
            # Check if already authenticated
            return self.is_authenticated()
            
        except Exception as e:
            logger.error(f"Error handling auth callback: {str(e)}")
            return False
    
    
    def set_authenticated_user(self, user_data: dict):
        """Set user as authenticated in session state"""
        st.session_state.authenticated = True
        st.session_state.user_data = user_data
        
        # Also set individual fields for backward compatibility
        st.session_state.user_email = user_data.get('email')
        st.session_state.username = user_data.get('name', user_data.get('email', '').split('@')[0])
        st.session_state.user_id = user_data.get('id')
        
        logger.info(f"User authenticated: {user_data.get('email')}")
    
    def logout(self):
        """Clear authentication state"""
        # Clear session state
        keys_to_clear = ['authenticated', 'user_data', 'user_email', 'username', 'user_id']
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        
        logger.info("User logged out")
        st.rerun()
    
    def require_auth(self, feature_name: str = "this feature"):
        """Require authentication for a feature - shows user ID input if not authenticated"""
        if not self.is_authenticated():
            st.warning(f"🔒 Please authenticate to access {feature_name}")
            
            col1, col2, col3 = st.columns([1, 3, 1])
            with col2:
                st.markdown("### 🔐 Authentication Required")
                st.info("Enter your Clerk User ID to access this feature")
                
                # User ID input (masked for security)
                user_id_input = st.text_input(
                    "Clerk User ID",
                    placeholder="",
                    help="Enter your Clerk user ID (starts with 'user_')",
                    key="require_auth_user_id",
                    type="password"
                )
                
                # Authenticate button
                if st.button("🚀 Authenticate", type="primary", use_container_width=True, key="require_authenticate"):
                    if user_id_input and user_id_input.strip():
                        with st.spinner("Authenticating..."):
                            if self.authenticate_with_user_id(user_id_input.strip()):
                                st.success("✅ Authentication successful! Refreshing...")
                                st.rerun()
                            else:
                                st.error("❌ Authentication failed. Please check your User ID.")
                    else:
                        st.error("Please enter a valid User ID")
                
                st.markdown("---")
                st.markdown("**User ID format:** `user_xxxxxxxxxxxxxxxxxx`")
                st.caption("🔒 Input is masked for security")
            
            st.stop()
        return True
    
    def render_auth_status(self):
        """Render authentication status in sidebar"""
        if self.is_authenticated():
            user = self.get_user()
            st.sidebar.markdown("### 👤 Authenticated")
            st.sidebar.write(f"**{user.get('name', 'User')}**")
            st.sidebar.write(f"{user.get('email', '')}")
            
            # Show Clerk User ID
            clerk_user_id = user.get('clerk_user_id', user.get('id', ''))
            if clerk_user_id:
                st.sidebar.code(f"ID: {clerk_user_id[-8:]}", language="text")
            
            if st.sidebar.button("🚪 Logout", use_container_width=True, type="secondary"):
                self.logout()
        else:
            st.sidebar.markdown("### 🔐 Authentication")
            st.sidebar.write("Enter your Clerk User ID")
            
            # User ID input in sidebar (masked for security)
            user_id_input = st.sidebar.text_input(
                "Clerk User ID",
                placeholder="",
                help="Your Clerk user ID",
                key="sidebar_user_id",
                type="password"
            )
            
            # Authenticate button
            if st.sidebar.button("🚀 Authenticate", use_container_width=True, type="primary"):
                if user_id_input and user_id_input.strip():
                    with st.spinner("Authenticating..."):
                        if self.authenticate_with_user_id(user_id_input.strip()):
                            st.sidebar.success("✅ Authentication successful!")
                            st.rerun()
                        else:
                            st.sidebar.error("❌ Authentication failed")
                else:
                    st.sidebar.error("Please enter User ID")
            
            # Help text
            st.sidebar.markdown("---")
            st.sidebar.caption("💡 User ID format: user_xxxxxxxxxx")
            st.sidebar.caption("🔒 Input is masked for security")
            
            # Show Clerk backend status
            if CLERK_BACKEND_AVAILABLE and self.clerk_client:
                st.sidebar.success("🔗 Clerk API Connected")
            else:
                st.sidebar.error("⚠️ Clerk API Unavailable")

# Global authentication instance
_auth_instance = None

def get_auth() -> SimpleClerkAuth:
    """Get the global authentication instance"""
    global _auth_instance
    if _auth_instance is None:
        _auth_instance = SimpleClerkAuth()
    return _auth_instance

def is_authenticated() -> bool:
    """Check if user is authenticated"""
    return get_auth().is_authenticated()

def require_auth(feature_name: str = "this feature"):
    """Require authentication for a feature"""
    return get_auth().require_auth(feature_name)

def get_user() -> dict:
    """Get current user data"""
    return get_auth().get_user()

def logout():
    """Logout current user"""
    return get_auth().logout()
