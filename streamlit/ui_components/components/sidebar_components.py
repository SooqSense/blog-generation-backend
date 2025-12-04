"""
Sidebar Components Module
Handles sidebar navigation, system info, and quick actions
"""

import streamlit as st
from base.config import APP_CONFIG, FEATURES, API_ENDPOINTS
from ui_components.components.organization_components import OrganizationComponents


class SidebarComponents:
    """Components for rendering the sidebar"""
    
    @staticmethod
    def render_navigation():
        """Render feature navigation selector"""
        st.markdown("### 🚀 Navigation")
        
        feature = st.selectbox(
            "Select Feature:",
            FEATURES,
            key="feature_selector"
        )
        
        st.markdown("---")
        return feature
    
    @staticmethod
    def render_system_info(api_endpoints_count: int, auth_status: str):
        """Render system information section"""
        st.markdown("### ℹ️ System Info")
        st.caption(f"Version: {APP_CONFIG['version']} - API Powered")
        st.caption("✅ Django API: Connected")
        st.caption(f"📡 {api_endpoints_count} endpoints available")
        st.caption(f"Auth: {auth_status}")
    
    @staticmethod
    def render_quick_actions():
        """Render quick action buttons"""
        st.markdown("---")
        st.markdown("### ⚡ Quick Actions")
        
        if st.button("🔄 Refresh Page"):
            st.rerun()
        
        if st.button("🔐 Clear Auth State"):
            SidebarComponents._clear_auth_state()
        
        if st.button("📊 View API Status"):
            SidebarComponents._show_api_status()
    
    @staticmethod
    def _clear_auth_state():
        """Clear authentication state"""
        keys_to_clear = ['auth_token', 'user_info', 'clerk_session']
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        st.success("Authentication state cleared! Please refresh the page.")
        st.rerun()
    
    @staticmethod
    def _show_api_status():
        """Show API endpoints status"""
        with st.expander("API Endpoints", expanded=False):
            for name, url in API_ENDPOINTS.items():
                st.code(f"{name}: {url}")
    
    @staticmethod
    def render_sidebar(auth_handler, api_endpoints_count: int):
        """Main sidebar rendering method - orchestrates all sidebar components"""
        with st.sidebar:
            # Authentication section
            auth_handler.render_auth_section()
            
            # Organization selector
            OrganizationComponents.render_organization_selector()
            
            # Navigation
            feature = SidebarComponents.render_navigation()
            
            # System information
            auth_status = auth_handler.get_auth_status()
            SidebarComponents.render_system_info(api_endpoints_count, auth_status)
            
            # Quick actions
            SidebarComponents.render_quick_actions()
        
        return feature

