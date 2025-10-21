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
            username = user.get('username', 'Unknown User')
            st.sidebar.write(f"**Username:** {username}")
            st.sidebar.write(f"**Email:** {user.get('email', 'N/A')}")
            st.sidebar.write(f"**ID:** {user.get('id', 'N/A')}")
            
            # Display organization information if available
            org_name = user.get('organization_name')
            org_role = user.get('organization_role')
            if org_name:
                st.sidebar.markdown("### 🏢 Organization")
                st.sidebar.write(f"**Organization:** {org_name}")
                if org_role:
                    st.sidebar.write(f"**Role:** {org_role}")
    
    def render_logout_button(self):
        """Render logout button in sidebar"""
        if st.sidebar.button("🚪 Logout", use_container_width=True):
            self.auth_manager.logout()
    
    def render_auth_status(self):
        """Render authentication status"""
        if self.auth_manager.is_authenticated():
            user = self.auth_manager.get_user()
            username = user.get('username', 'Unknown User')
            org_name = user.get('organization_name')
            if org_name:
                st.success(f"✅ Authenticated as {username} ({org_name})")
            else:
                st.success(f"✅ Authenticated as {username}")
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
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info("=" * 80)
        logger.info("SIDEBAR AUTH - Rendering authenticated section")
        logger.info("User data from session state:")
        logger.info("=" * 80)
        if user:
            for key, value in user.items():
                logger.info(f"  {key}: {value}")
        else:
            logger.warning("  User is None!")
        logger.info("=" * 80)
        
        st.sidebar.markdown("### 🔐 Authentication")
        username = user.get('username', 'Unknown User')
        org_name = user.get('organization_name')
        
        logger.info(f"Displaying username: {username}")
        logger.info(f"Organization name: {org_name}")
        
        if org_name:
            st.sidebar.success(f"✅ Logged in as {username}")
            st.sidebar.info(f"🏢 Organization: {org_name}")
        else:
            st.sidebar.success(f"✅ Logged in as {username}")
        
        # Organization dropdown if user has organization
        if org_name:
            st.sidebar.markdown("### 🏢 Organization")
            st.sidebar.success(f"**{org_name}**")
            org_role = user.get('organization_role')
            if org_role:
                st.sidebar.info(f"Role: {org_role}")
            org_id = user.get('organization_id')
            if org_id:
                st.sidebar.caption(f"ID: {org_id}")
            
            # Add organization actions
            with st.sidebar.expander("🏢 Organization Actions", expanded=False):
                if st.button("🔄 Refresh Org", use_container_width=True):
                    st.rerun()
                if st.button("📊 Org Stats", use_container_width=True):
                    st.info("Organization statistics feature coming soon!")
        
        # User info
        with st.sidebar.expander("👤 User Details", expanded=False):
            st.write(f"**Username:** {username}")
            email = user.get('email', 'N/A')
            if email and email != 'N/A':
                st.write(f"**Email:** {email}")
            else:
                st.warning("⚠️ Email not available")
            
            st.write(f"**User ID:** {user.get('id', 'N/A')}")
            if user.get('clerk_user_id'):
                st.write(f"**Clerk ID:** {user.get('clerk_user_id')}")
            
            # Show additional user info if available
            first_name = user.get('first_name')
            last_name = user.get('last_name')
            if first_name or last_name:
                full_name = f"{first_name or ''} {last_name or ''}".strip()
                if full_name:
                    st.write(f"**Full Name:** {full_name}")
        
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
    
    def render_organization_selector(self):
        """Render organization selector for main page"""
        if not self.auth_manager.is_authenticated():
            return None
        
        user = self.auth_manager.get_user()
        org_name = user.get('organization_name')
        org_role = user.get('organization_role')
        org_id = user.get('organization_id')
        
        if org_name:
            # Create a more prominent organization display
            st.markdown("### 🏢 Organization")
            
            col1, col2 = st.columns([2, 1])
            with col1:
                # Display organization info in a more visible way
                st.info(f"**Organization:** {org_name}")
                if org_role:
                    st.info(f"**Your Role:** {org_role}")
                if org_id:
                    st.caption(f"ID: {org_id}")
            
            with col2:
                # Add a refresh button for organization info
                if st.button("🔄 Refresh Org Info", help="Refresh organization information"):
                    st.rerun()
            
            return {
                'organization_id': org_id,
                'organization_name': org_name,
                'organization_role': org_role
            }
        else:
            st.warning("⚠️ No organization associated with your account")
            st.info("Contact your administrator to be added to an organization.")
            return None
