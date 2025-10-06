"""
Enhanced Clerk Authentication for Streamlit with Django Integration
Modular authentication system with clean separation of concerns
"""

import streamlit as st
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Import modular components
from .database import DatabaseOperations
from .user_management import UserService, UserValidator
from .session_management import SessionService, SessionValidator
from .ui_components import AuthUI, SidebarUI

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
    """Enhanced Clerk authentication with modular architecture"""
    
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
            
        logger.info(f"Enhanced Clerk Auth initialized with modular architecture")
        logger.info(f"  Backend API Available: {CLERK_BACKEND_AVAILABLE}")
        logger.info(f"  Secret Key Configured: {'Yes' if self.clerk_secret else 'No'}")
        
        # Initialize modular components
        self._init_components()
    
    def _init_components(self):
        """Initialize all modular components"""
        try:
            # Initialize database layer using existing connection
            self.db_operations = DatabaseOperations()
            
            # Initialize user management
            self.user_service = UserService(self.db_operations)
            self.user_validator = UserValidator()
            
            # Initialize session management
            self.session_service = SessionService(self.user_service)
            self.session_validator = SessionValidator()
            
            # Initialize UI components
            self.auth_ui = AuthUI(self.authenticate_with_user_id)
            self.sidebar_ui = SidebarUI(
                self.authenticate_with_user_id,
                self.logout,
                self.get_user
            )
            
            # Initialize Clerk client
            self.clerk_client = None
            if CLERK_BACKEND_AVAILABLE and self.clerk_secret:
                try:
                    self.clerk_client = Clerk(bearer_auth=self.clerk_secret)
                    logger.info("✅ Clerk backend client initialized successfully")
                except Exception as e:
                    logger.error(f"Failed to initialize Clerk client: {e}")
                    self.clerk_client = None
            
            logger.info("✅ All modular components initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize components: {e}")
            raise
    
    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated"""
        return self.session_service.is_authenticated()
    
    def get_user(self) -> dict:
        """Get current user data with Django user information"""
        return self.session_service.get_user_data()
    
    def authenticate_with_user_id(self, user_id: str) -> bool:
        """Enhanced authentication with modular components"""
        # Validate input
        validation_result = self.user_validator.validate_authentication_request(user_id)
        if not validation_result['valid']:
            logger.error(f"Authentication validation failed: {validation_result['errors']}")
            return False
        
        if not self.clerk_client:
            logger.error("Clerk client not available")
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
            token = self._extract_token_from_response(res)
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
            
            # Create or get Django user using user service
            django_user = self.user_service.create_or_get_user(user_id, user_info)
            
            if not django_user:
                logger.error("Failed to create/get Django user")
                return False
            
            # Update last login using user service
            self.user_service.update_user_last_login(django_user['django_user_id'])
            
            # Set user as authenticated using session service
            user_data = {
                'id': user_id,
                'email': user_info.get('email', f'user-{user_id[-8:]}@clerk.dev'),
                'name': user_info.get('name', f'Clerk User {user_id[-4:]}'),
                'authenticated': True,
                'token': token,
                'clerk_user_id': user_id,
                'django_user_id': django_user['django_user_id'],
                'username': django_user['username'],
                'is_new_user': django_user.get('is_new', False),
                'created_at': django_user.get('date_joined'),
                'updated_at': django_user.get('updated_at')
            }
            
            success = self.session_service.set_authenticated_user(user_data)
            
            if success:
                logger.info(f"✅ User {user_id} authenticated successfully with modular integration")
                return True
            else:
                logger.error("Failed to set authenticated user in session")
                return False
            
        except Exception as e:
            logger.error(f"Authentication failed for user {user_id}: {str(e)}")
            return False
    
    def _extract_token_from_response(self, res) -> str:
        """Extract token from Clerk API response"""
        if hasattr(res, 'token'):
            return res.token
        elif hasattr(res, 'id'):
            return res.id
        elif isinstance(res, dict):
            return res.get('token') or res.get('id')
        else:
            return str(res)
    
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
        """Handle authentication with session persistence and validation"""
        # This will automatically try to recover sessions from persistent storage
        return self.session_service.handle_auth_callback()
    
    def logout(self):
        """Clear authentication state and update database"""
        success = self.session_service.clear_authentication_state()
        if success:
            st.rerun()
    
    def require_auth(self, feature_name: str = "this feature"):
        """Require authentication for a feature - shows user ID input if not authenticated"""
        if not self.is_authenticated():
            return self.auth_ui.render_authentication_form(feature_name)
        return True
    
    def render_auth_status(self):
        """Render authentication status in sidebar"""
        is_authenticated = self.is_authenticated()
        clerk_available = CLERK_BACKEND_AVAILABLE and self.clerk_client is not None
        
        # Debug: Log authentication status
        logger.info(f"🔍 Auth Status Check: is_authenticated={is_authenticated}")
        logger.info(f"🔍 Session State: authenticated={st.session_state.get('authenticated', False)}")
        logger.info(f"🔍 User Data: {st.session_state.get('user_data', {})}")
        
        # Check database availability using existing connection
        try:
            from database.db_connection import get_connection
            conn = get_connection()
            db_available = conn is not None
            if conn:
                conn.close()
        except Exception:
            db_available = False
        
        self.sidebar_ui.render_authentication_sidebar(
            is_authenticated, clerk_available, db_available
        )
    
    def get_user_data_isolation_filter(self) -> dict:
        """Get database filter conditions to ensure user data isolation"""
        user_data = self.get_user()
        return self.user_service.get_user_data_isolation_filter(user_data)
    
    def ensure_user_data_isolation(self, query: str, params: list = None) -> tuple:
        """Ensure database queries are filtered by current user"""
        if not self.is_authenticated():
            raise Exception("User not authenticated")
        
        user_filter = self.get_user_data_isolation_filter()
        django_user_id = user_filter['django_user_id']
        
        # Add user filter to query
        if 'WHERE' in query.upper():
            # Query already has WHERE clause
            query += f" AND user_id = %s"
        else:
            # Query doesn't have WHERE clause
            query += f" WHERE user_id = %s"
        
        # Add user_id to parameters
        if params is None:
            params = [django_user_id]
        else:
            params.append(django_user_id)
        
        return query, params
    
    def get_user_specific_data(self, table_name: str, columns: str = "*", additional_filters: str = "", params: list = None) -> list:
        """Get user-specific data from any table with automatic user isolation"""
        if not self.is_authenticated():
            raise Exception("User not authenticated")
        
        user_data = self.get_user()
        django_user_id = user_data.get('django_user_id')
        
        if not django_user_id:
            raise Exception("User not authenticated - cannot provide data isolation")
        
        return self.user_service.get_user_specific_data(
            table_name, django_user_id, columns, additional_filters, params
        )

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
