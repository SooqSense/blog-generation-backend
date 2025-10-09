"""
Sidebar UI components for authentication system
Handles sidebar authentication interface
"""

import streamlit as st
import logging
from typing import Callable, Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class SidebarUI:
    """UI components for sidebar authentication"""
    
    def __init__(self, authenticate_callback: Callable[[str], bool], 
                 logout_callback: Callable, get_user_callback: Callable):
        """
        Initialize sidebar UI
        
        Args:
            authenticate_callback: Function to call for authentication
            logout_callback: Function to call for logout
            get_user_callback: Function to get current user data
        """
        self.authenticate_callback = authenticate_callback
        self.logout_callback = logout_callback
        self.get_user_callback = get_user_callback
    
    def render_authenticated_sidebar(self, user_data: Dict[str, Any]):
        """
        Render sidebar for authenticated user
        
        Args:
            user_data: User data to display
        """
        st.sidebar.markdown("### 👤 Authenticated")
        st.sidebar.write(f"**{user_data.get('name', 'User')}**")
        st.sidebar.write(f"{user_data.get('email', '')}")
        
        # Show Clerk User ID and Django User ID
        clerk_user_id = user_data.get('clerk_user_id', user_data.get('id', ''))
        django_user_id = user_data.get('django_user_id')
        
        if clerk_user_id:
            st.sidebar.code(f"Clerk ID: {clerk_user_id[-8:]}", language="text")
        if django_user_id:
            st.sidebar.code(f"Django ID: {django_user_id}", language="text")
        
        # Show session info
        auth_timestamp = st.session_state.get('auth_timestamp')
        if auth_timestamp:
            try:
                auth_time = datetime.fromisoformat(auth_timestamp)
                session_age = datetime.now() - auth_time
                st.sidebar.caption(f"Session: {session_age.total_seconds()/3600:.1f}h ago")
            except:
                pass
        
        # Logout button
        if st.sidebar.button("🚪 Logout", use_container_width=True, type="secondary"):
            self.logout_callback()
    
    def render_unauthenticated_sidebar(self, clerk_available: bool, db_available: bool):
        """
        Render sidebar for unauthenticated user
        
        Args:
            clerk_available: Whether Clerk API is available
            db_available: Whether database is available
        """
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
                    if self.authenticate_callback(user_id_input.strip()):
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
        
        # Show system status
        self.render_system_status(clerk_available, db_available)
    
    def render_system_status(self, clerk_available: bool, db_available: bool):
        """
        Render system status indicators in sidebar
        
        Args:
            clerk_available: Whether Clerk API is available
            db_available: Whether database is available
        """
        st.sidebar.markdown("### 🔧 System Status")
        
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            if clerk_available:
                st.sidebar.success("🔗 Clerk API")
            else:
                st.sidebar.error("⚠️ Clerk API")
        
        with col2:
            if db_available:
                st.sidebar.success("🗄️ Database")
            else:
                st.sidebar.error("⚠️ Database")
    
    def render_authentication_sidebar(self, is_authenticated: bool, 
                                    clerk_available: bool, db_available: bool):
        """
        Render authentication sidebar based on authentication status
        
        Args:
            is_authenticated: Whether user is authenticated
            clerk_available: Whether Clerk API is available
            db_available: Whether database is available
        """
        if is_authenticated:
            user_data = self.get_user_callback()
            self.render_authenticated_sidebar(user_data)
        else:
            self.render_unauthenticated_sidebar(clerk_available, db_available)
    
    def render_user_quick_info(self, user_data: Dict[str, Any]):
        """
        Render quick user information in sidebar
        
        Args:
            user_data: User data to display
        """
        st.sidebar.markdown("### 👤 Quick Info")
        
        # Basic info
        st.sidebar.write(f"**{user_data.get('name', 'User')}**")
        st.sidebar.write(f"{user_data.get('email', '')}")
        
        # User IDs (truncated)
        clerk_id = user_data.get('clerk_user_id', '')
        django_id = user_data.get('django_user_id', '')
        
        if clerk_id:
            st.sidebar.caption(f"Clerk: ...{clerk_id[-4:]}")
        if django_id:
            st.sidebar.caption(f"Django: {django_id}")
        
        # Session age
        auth_timestamp = st.session_state.get('auth_timestamp')
        if auth_timestamp:
            try:
                auth_time = datetime.fromisoformat(auth_timestamp)
                session_age = datetime.now() - auth_time
                hours = session_age.total_seconds() / 3600
                st.sidebar.caption(f"Session: {hours:.1f}h")
            except:
                pass
    
    def render_authentication_help_sidebar(self):
        """Render authentication help in sidebar"""
        with st.sidebar.expander("❓ Help", expanded=False):
            st.markdown("""
            **User ID Format:**
            - Starts with `user_`
            - 20+ characters
            - Example: `user_2abc123...`
            
            **Security:**
            - Input is masked
            - Sessions expire
            - Data isolated
            """)
    
    def render_session_warning(self, session_age_hours: float):
        """
        Render session warning if session is getting old
        
        Args:
            session_age_hours: Session age in hours
        """
        if session_age_hours > 20:  # Warning at 20 hours
            st.sidebar.warning("⚠️ Session expiring soon")
        elif session_age_hours > 22:  # Critical at 22 hours
            st.sidebar.error("🚨 Session expiring very soon!")
    
    def render_authentication_debug(self, debug_info: Dict[str, Any]):
        """
        Render authentication debug information
        
        Args:
            debug_info: Debug information to display
        """
        with st.sidebar.expander("🔍 Debug Info", expanded=False):
            st.json(debug_info)
