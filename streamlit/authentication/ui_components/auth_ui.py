"""
Authentication UI components for Streamlit
Handles authentication forms and user interface
"""

import streamlit as st
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)

class AuthUI:
    """UI components for authentication"""
    
    def __init__(self, authenticate_callback: Callable[[str], bool]):
        """
        Initialize authentication UI
        
        Args:
            authenticate_callback: Function to call for authentication
        """
        self.authenticate_callback = authenticate_callback
    
    def render_authentication_form(self, feature_name: str = "this feature") -> bool:
        """
        Render authentication form
        
        Args:
            feature_name: Name of the feature requiring authentication
            
        Returns:
            True if authentication successful, False otherwise
        """
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
                        if self.authenticate_callback(user_id_input.strip()):
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
        return False
    
    def render_authentication_success(self, user_data: dict):
        """
        Render authentication success message
        
        Args:
            user_data: User data to display
        """
        st.success("✅ Authentication successful!")
        
        with st.expander("👤 User Information", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Name:** {user_data.get('name', 'N/A')}")
                st.write(f"**Email:** {user_data.get('email', 'N/A')}")
            
            with col2:
                st.write(f"**Clerk ID:** {user_data.get('clerk_user_id', 'N/A')}")
                st.write(f"**Django ID:** {user_data.get('django_user_id', 'N/A')}")
    
    def render_authentication_error(self, error_message: str):
        """
        Render authentication error message
        
        Args:
            error_message: Error message to display
        """
        st.error(f"❌ Authentication Error: {error_message}")
        
        with st.expander("🔍 Troubleshooting", expanded=False):
            st.markdown("""
            **Common Issues:**
            1. **Invalid User ID**: Make sure you're using the correct Clerk User ID
            2. **Network Issues**: Check your internet connection
            3. **Service Unavailable**: The authentication service might be down
            
            **User ID Format:**
            - Should start with `user_`
            - Followed by alphanumeric characters
            - Example: `user_2abc123def456ghi789`
            """)
    
    def render_authentication_loading(self):
        """Render authentication loading state"""
        with st.spinner("🔐 Authenticating..."):
            st.info("Please wait while we verify your credentials...")
    
    def render_user_profile(self, user_data: dict):
        """
        Render user profile information
        
        Args:
            user_data: User data to display
        """
        st.markdown("### 👤 User Profile")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Name:** {user_data.get('name', 'N/A')}")
            st.write(f"**Email:** {user_data.get('email', 'N/A')}")
            st.write(f"**Username:** {user_data.get('username', 'N/A')}")
        
        with col2:
            st.write(f"**Clerk ID:** {user_data.get('clerk_user_id', 'N/A')}")
            st.write(f"**Django ID:** {user_data.get('django_user_id', 'N/A')}")
            st.write(f"**Created:** {user_data.get('created_at', 'N/A')}")
        
        # Show session info
        auth_timestamp = st.session_state.get('auth_timestamp')
        if auth_timestamp:
            try:
                from datetime import datetime
                auth_time = datetime.fromisoformat(auth_timestamp)
                session_age = datetime.now() - auth_time
                st.write(f"**Session Age:** {session_age.total_seconds()/3600:.1f} hours")
            except:
                pass
    
    def render_authentication_status(self, is_authenticated: bool, user_data: Optional[dict] = None):
        """
        Render authentication status
        
        Args:
            is_authenticated: Whether user is authenticated
            user_data: User data if authenticated
        """
        if is_authenticated and user_data:
            st.success("✅ Authenticated")
            self.render_user_profile(user_data)
        else:
            st.warning("⚠️ Not authenticated")
            st.info("Please authenticate to access all features")
    
    def render_logout_button(self, logout_callback: Callable):
        """
        Render logout button
        
        Args:
            logout_callback: Function to call for logout
        """
        if st.button("🚪 Logout", type="secondary"):
            logout_callback()
    
    def render_authentication_help(self):
        """Render authentication help information"""
        with st.expander("❓ Authentication Help", expanded=False):
            st.markdown("""
            **How to Authenticate:**
            1. Get your Clerk User ID from your Clerk dashboard
            2. Enter the User ID in the authentication form
            3. Click "Authenticate" to log in
            
            **User ID Format:**
            - Starts with `user_`
            - Followed by 20+ alphanumeric characters
            - Example: `user_2abc123def456ghi789`
            
            **Security Features:**
            - User ID input is masked for security
            - Sessions expire after 24 hours
            - Data is isolated per user
            
            **Troubleshooting:**
            - Make sure you're using the correct User ID
            - Check your internet connection
            - Contact support if issues persist
            """)
    
    def render_system_status(self, clerk_available: bool, db_available: bool):
        """
        Render system status indicators
        
        Args:
            clerk_available: Whether Clerk API is available
            db_available: Whether database is available
        """
        st.markdown("### 🔧 System Status")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if clerk_available:
                st.success("🔗 Clerk API Connected")
            else:
                st.error("⚠️ Clerk API Unavailable")
        
        with col2:
            if db_available:
                st.success("🗄️ Database Connected")
            else:
                st.error("⚠️ Database Unavailable")
