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
    
    def is_admin(self) -> bool:
        """Check if the current user has admin role in their organization"""
        if not self.auth_available or not self.auth_manager:
            return False
        
        user = self.auth_manager.get_user()
        if not user:
            return False
        
        org_role = user.get('organization_role', '').lower()
        return org_role == 'admin'
    
    def require_admin(self, feature_name: str = "this feature"):
        """Require admin role for a feature"""
        if not self.auth_available:
            st.error(f"⚠️ Authentication service not available for {feature_name}")
            st.stop()
        
        if not is_authenticated():
            st.error(f"🔐 Please login to access {feature_name}")
            st.stop()
        
        # Check if user is admin of the selected organization
        if not self.is_organization_admin():
            user = self.auth_manager.get_user() if self.auth_manager else {}
            current_org = user.get('organization_name', 'your organization')
            st.error(f"🚫 Access Denied: Admin privileges required")
            st.warning(f"Only administrators of the selected organization can access {feature_name}.")
            st.info(f"💡 You are currently in **{current_org}** organization. Please ensure you have admin role in this organization.")
            st.stop()
    
    def is_organization_admin(self) -> bool:
        """Check if the current user is admin of the selected organization"""
        if not self.auth_available or not self.auth_manager:
            return False
        
        user = self.auth_manager.get_user()
        if not user:
            return False
        
        # Check new multi-organization structure first
        org_names = user.get('organization_names', [])
        org_roles = user.get('organization_roles', [])
        
        if org_names and org_roles:
            # Find selected organization index
            selected_org = self.auth_manager.get_selected_organization()
            if not selected_org:
                return False
                
            try:
                org_index = None
                for i, org_name in enumerate(org_names):
                    if org_name.lower() == selected_org.lower():
                        org_index = i
                        break
                
                if org_index is not None and org_index < len(org_roles):
                    role = org_roles[org_index].lower().strip()
                    # Handle both 'admin' and 'org:admin' formats
                    is_admin = role == 'admin' or role == 'org:admin' or role.endswith(':admin')
                    return is_admin
            except (IndexError, TypeError) as e:
                pass
        
        # Fallback to legacy single organization structure
        selected_org = self.auth_manager.get_selected_organization()
        if not selected_org:
            return False
            
        current_org = user.get('organization_name', '').lower()
        if current_org == selected_org.lower():
            org_role = user.get('organization_role', '').lower().strip()
            # Handle both 'admin' and 'org:admin' formats
            is_admin = org_role == 'admin' or org_role == 'org:admin' or org_role.endswith(':admin')
            return is_admin
        
        return False