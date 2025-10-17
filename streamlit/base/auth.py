"""
Authentication module for Streamlit application.
Handles Clerk authentication integration and session management.
"""

import streamlit as st
import logging

logger = logging.getLogger(__name__)

# Import Simple Clerk authentication
try:
    from authentication.auth_service import StreamlitAuthManager
    from authentication.ui_components import AuthUI, SidebarAuth
    
    # Create auth manager instance
    auth_manager = StreamlitAuthManager()
    
    def get_auth():
        return auth_manager
    
    def is_authenticated():
        return auth_manager.is_authenticated()
    
    def require_auth(feature_name="this feature"):
        if not auth_manager.is_authenticated():
            st.error(f"Please login to access {feature_name}")
            st.stop()
    
    def get_user():
        return auth_manager.get_user()
    
    def logout():
        auth_manager.logout()
    
    AUTH_AVAILABLE = True
    print("✅ Simple Clerk authentication imported successfully")
    
except Exception as e:
    AUTH_AVAILABLE = False
    print(f"⚠️ Authentication not available: {str(e)}")
    
    # Create dummy functions for graceful degradation
    def get_auth():
        return None
    
    def is_authenticated():
        return False
    
    def require_auth(feature_name="this feature"):
        st.error(f"Authentication service not available for {feature_name}")
        st.stop()
    
    def get_user():
        return {}
    
    def logout():
        pass

class AuthHandler:
    """Authentication handler for the Streamlit application"""
    
    def __init__(self):
        self.auth_manager = get_auth() if AUTH_AVAILABLE else None
        self.auth_available = AUTH_AVAILABLE
    
    def initialize_session_state(self):
        """Initialize session state variables and handle authentication"""
        # Clear any potentially corrupted auth state
        if 'auth_token' in st.session_state:
            try:
                # Validate existing token before using it
                if self.auth_available and self.auth_manager:
                    # Verify the existing token
                    if not self.auth_manager.verify_session():
                        logger.warning("Clearing invalid auth token")
                        if 'auth_token' in st.session_state:
                            del st.session_state['auth_token']
                        if 'user_info' in st.session_state:
                            del st.session_state['user_info']
            except Exception as e:
                # If there's an issue with existing auth state, clear it
                logger.warning(f"Clearing corrupted auth state: {e}")
                if 'auth_token' in st.session_state:
                    del st.session_state['auth_token']
                if 'user_info' in st.session_state:
                    del st.session_state['user_info']
        
        # Initialize other session state variables if needed
        if 'app_initialized' not in st.session_state:
            st.session_state.app_initialized = True
    
    def render_auth_section(self):
        """Render authentication section in sidebar"""
        if self.auth_available and self.auth_manager:
            # Show authentication status
            if self.auth_manager.is_authenticated():
                user = self.auth_manager.get_user()
                st.markdown("### 🔐 Authentication")
                st.success(f"✅ Logged in as {user.get('username', 'Unknown') if user else 'Unknown'}")
                st.markdown("---")
            else:
                st.markdown("### 🔐 Authentication")
                st.warning("⚠️ Not logged in")
                st.markdown("---")
        else:
            st.markdown("### ⚠️ Authentication")
            st.caption("Service Unavailable")
            st.markdown("---")
    
    def get_auth_status(self):
        """Get authentication status for display"""
        if self.auth_available:
            return "✅ Logged In" if is_authenticated() else "🔐 Login Required"
        else:
            return "⚠️ Auth: Disabled"
    
    def check_auth_for_feature(self, feature_name: str):
        """Check authentication for a specific feature"""
        if self.auth_available and not is_authenticated():
            require_auth(feature_name)
