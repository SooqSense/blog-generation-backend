import streamlit as st
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from .auth_service import StreamlitAuthManager


class AuthUI:
    """Authentication UI Components for Streamlit"""
    
    def __init__(self):
        self.auth_manager = StreamlitAuthManager()
    
    def render_login_form(self) -> bool:
        """Render login form and return True if login successful"""
        st.subheader("🔐 Login")
        
        st.markdown("### Authenticate with Clerk")
        st.success("✅ **Clerk Authentication is now available!** Enter your registered email.")
        st.info("ℹ️ **Note**: This uses Clerk's API to authenticate. Make sure you have a Clerk account.")
        
        with st.form("clerk_login_form"):
            email = st.text_input("Email", placeholder="Enter your registered email", key="clerk_email")
            password = st.text_input("Password", type="password", placeholder="Enter your password", key="clerk_password", help="Password is required for verification but not used in API call")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                login_button = st.form_submit_button("🔐 Login with Clerk", use_container_width=True)
            with col2:
                if st.form_submit_button("🗑️ Clear", use_container_width=True):
                    st.rerun()
            
            if login_button:
                if not email.strip():
                    st.error("❌ Please enter your email address")
                    return False
                
                if not password.strip():
                    st.error("❌ Please enter your password")
                    return False
                
                with st.spinner("🔐 Authenticating with Clerk..."):
                    success = self.auth_manager.login(email.strip(), password.strip())
                    if success:
                        st.success("🎉 Authentication successful! Redirecting...")
                        st.rerun()
                        return True
                    else:
                        st.error("❌ Authentication failed. Please check your credentials.")
                        return False
        
        return False
    
    def render_user_info(self):
        """Render user information in sidebar"""
        user = self.auth_manager.get_user()
        if user:
            st.sidebar.markdown("---")
            st.sidebar.markdown("### 👤 User Info")
            st.sidebar.write(f"**Username:** {user.get('username', 'N/A')}")
            st.sidebar.write(f"**Email:** {user.get('email', 'N/A')}")
            st.sidebar.write(f"**ID:** {user.get('id', 'N/A')}")
    
    def render_logout_button(self):
        """Render logout button in sidebar"""
        if st.sidebar.button("🚪 Logout", use_container_width=True):
            self.auth_manager.logout()
    
    def render_auth_status(self):
        """Render authentication status"""
        if self.auth_manager.is_authenticated():
            user = self.auth_manager.get_user()
            st.success(f"✅ Authenticated as {user.get('username', 'Unknown')}")
        else:
            st.warning("⚠️ Not authenticated")
    
    def render_login_page(self):
        """Render full login page"""
        st.title("🔐 AI Blog Generator - Login")
        st.markdown("Please login to access the AI Blog Generator features.")
        
        # Center the login form
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            self.render_login_form()
        
        # Add some helpful information
        st.markdown("---")
        st.markdown("### 📝 How to get started:")
        st.markdown("""
        1. **Enter your credentials** - Use your registered email and password
        2. **Access features** - Once logged in, you can use all AI tools
        3. **Generate content** - Create blogs, images, LinkedIn posts, and more
        4. **Manage your data** - View history and manage your generated content
        """)
        
        # Debug section for testing
        with st.expander("🔧 Debug & Testing", expanded=False):
            st.markdown("### Configuration Check")
            auth_service = self.auth_manager.auth_service
            st.write(f"**Backend URL:** {auth_service.base_url}")
            st.write(f"**Clerk Secret Key:** {'✅ Configured' if auth_service.clerk_secret_key else '❌ Not configured'}")


class SidebarAuth:
    """Sidebar Authentication Components"""
    
    def __init__(self):
        self.auth_manager = StreamlitAuthManager()
    
    def render_auth_section(self):
        """Render authentication section in sidebar"""
        if self.auth_manager.is_authenticated():
            self._render_authenticated_section()
        else:
            self._render_unauthenticated_section()
    
    def _render_authenticated_section(self):
        """Render authenticated user section"""
        user = self.auth_manager.get_user()
        
        st.sidebar.markdown("### 🔐 Authentication")
        st.sidebar.success(f"✅ Logged in as {user.get('username', 'Unknown')}")
        
        # User info
        with st.sidebar.expander("👤 User Details", expanded=False):
            st.write(f"**Username:** {user.get('username', 'N/A')}")
            st.write(f"**Email:** {user.get('email', 'N/A')}")
            st.write(f"**User ID:** {user.get('id', 'N/A')}")
            if user.get('clerk_user_id'):
                st.write(f"**Clerk ID:** {user.get('clerk_user_id')}")
        
        # Logout button
        if st.sidebar.button("🚪 Logout", use_container_width=True):
            self.auth_manager.logout()
    
    def _render_unauthenticated_section(self):
        """Render unauthenticated user section"""
        st.sidebar.markdown("### 🔐 Authentication")
        st.sidebar.warning("⚠️ Not logged in")
        
        st.sidebar.markdown("Please login to access all features:")
        
        # Quick login form in sidebar
        with st.sidebar.form("sidebar_login"):
            email = st.text_input("Email", key="sidebar_email", placeholder="Enter your email")
            password = st.text_input("Password", type="password", key="sidebar_password", placeholder="Enter your password")
            
            if st.form_submit_button("🔐 Login with Clerk", use_container_width=True):
                if email and password:
                    with st.spinner("🔐 Authenticating with Clerk..."):
                        success = self.auth_manager.login(email, password)
                        if success:
                            st.sidebar.success("🎉 Login successful!")
                            st.rerun()
                        else:
                            st.sidebar.error("❌ Login failed. Check your credentials.")
                else:
                    st.sidebar.error("❌ Please enter both email and password")
        
        st.sidebar.markdown("---")
        st.sidebar.markdown("**Need an account?** Contact your administrator.")
