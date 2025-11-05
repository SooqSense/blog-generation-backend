"""
Main Streamlit application module.
Refactored to use modular components for better maintainability.
"""

import streamlit as st
from base.config import API_BASE_URL, API_ENDPOINTS, APP_CONFIG, print_config_status
from base.auth import AuthHandler
from base.ui_components import UIComponents, CustomCSS
from base.feature_router import FeatureRouter

class StreamlitApp:
    """Main Streamlit application class for AI Blog Generator - Modular Architecture"""
    
    def __init__(self):
        # Print configuration status
        print_config_status()
        
        # Initialize components
        self.auth_handler = AuthHandler()
        self.ui_components = UIComponents()
        self.feature_router = FeatureRouter(self.auth_handler)
        
        # Initialize session state
        self.auth_handler.initialize_session_state()
        
        # API configuration
        self.api_base_url = API_BASE_URL
        self.api_endpoints = API_ENDPOINTS
        
        print(f"✅ StreamlitApp initialized with modular architecture")
        print(f"🔗 API Base URL: {self.api_base_url}")
        print(f"📡 Available endpoints: {len(self.api_endpoints)}")

    def render_header(self):
        """Render the main application header"""
        self.ui_components.render_header(self.api_base_url, self.auth_handler)
        
    def render_sidebar(self):
        """Render the sidebar navigation"""
        return self.ui_components.render_sidebar(self.auth_handler, len(self.api_endpoints))
        
    def render_home(self):
        """Render the home page"""
        self.ui_components.render_home(self.api_base_url)
    
    def _cleanup_all_connections(self):
        """Clean up any active connections (placeholder for future use)"""
        # No WebSocket connections to clean up - using standard REST API only
        pass
            
    def run(self):
        """Main application runner"""
        # Load custom CSS
        CustomCSS.load_custom_css()
        
        # Check authentication first
        if not self.auth_handler.auth_available:
            st.error("⚠️ Authentication service is not available. Please check your configuration.")
            st.stop()
        
        # Check if user is authenticated
        if not self.auth_handler.auth_manager.is_authenticated():
            # Show login page
            self.render_login_page()
            return
        
        # Verify session token
        if not self.auth_handler.auth_manager.verify_session():
            st.error("Session expired. Please login again.")
            st.stop()
        
        # Render header
        self.render_header()
        
        # Get selected feature from sidebar
        feature = self.render_sidebar()
        
        # Route to appropriate feature
        result = self.feature_router.route_feature(feature)
        
        if result == "home":
            self.render_home()
        elif result == "unknown":
            st.error(f"Unknown feature: {feature}")
            st.info("Please select a valid feature from the sidebar.")
        # Feature rendering is handled by the router
    
    def render_login_page(self):
        """Render the login page"""
        st.title("🔐 AI Blog Generator - Login")
        st.markdown("Please login to access the AI Blog Generator features.")
        
        # Import and use AuthUI for login
        try:
            from authentication.ui_components import AuthUI
            auth_ui = AuthUI()
            auth_ui.render_login_form()
        except Exception as e:
            st.error(f"Login form not available: {str(e)}")
            st.info("Please check your authentication configuration.")
