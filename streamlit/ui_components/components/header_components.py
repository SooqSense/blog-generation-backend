"""
Header Components Module
Handles header rendering, user info display, and logout functionality
"""

import streamlit as st
from base.config import APP_CONFIG, API_ENDPOINTS


class HeaderComponents:
    """Components for rendering the application header"""
    
    @staticmethod
    def render_app_title():
        """Render the main application title banner"""
        st.markdown(f"""
        <div style="background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); 
                    padding: 1rem; margin: -1rem -1rem 2rem -1rem; border-radius: 0px;">
            <h1 style="color: white; text-align: center; margin: 0; font-size: 2.5rem;">
                {APP_CONFIG['icon']} {APP_CONFIG['title']}
            </h1>
            <p style="color: white; text-align: center; margin: 0.5rem 0 0 0; opacity: 0.9;">
                {APP_CONFIG['subtitle']}
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def render_user_info_bar(user: dict, selected_org: str):
        """Render user information and organization display"""
        username = user.get('username', 'Unknown User')
        email = user.get('email', 'N/A')
        
        col_info, col_logout = st.columns([4, 1])
        
        with col_info:
            st.markdown(f"""
            <div style='display: flex; align-items: center; padding: 15px 20px; background: rgba(255, 255, 255, 0.05); border-radius: 10px;'>
                <div style='flex: 1; text-align: left;'>
                    <div style='color: #ffffff; font-weight: 600; font-size: 14px; margin-bottom: 4px;'>👤 {username}</div>
                    <div style='color: rgba(255, 255, 255, 0.7); font-size: 12px;'>📧 {email if email != "N/A" else ""}</div>
                </div>
                <div style='flex: 1; text-align: center;'>
                    <div style='color: rgba(255, 255, 255, 0.8); font-size: 11px; margin-bottom: 6px; letter-spacing: 1px;'>🏢 ORGANIZATION</div>
                    <div style='background: linear-gradient(135deg, rgba(102, 126, 234, 0.3) 0%, rgba(118, 75, 162, 0.3) 100%); padding: 8px 20px; border-radius: 20px; border: 1.5px solid rgba(255, 255, 255, 0.3); font-weight: 700; font-size: 15px; color: #ffffff; white-space: nowrap; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2); display: inline-block;'>🏛️ {selected_org}</div>
                </div>
                <div style='flex: 1;'></div>
            </div>
            """, unsafe_allow_html=True)
        
        with col_logout:
            st.markdown("<div style='padding-top: 15px;'></div>", unsafe_allow_html=True)
            if st.button("🚪 Logout", type="primary", key="logout_btn", use_container_width=True):
                return True  # Signal logout action
        
        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
        return False
    
    @staticmethod
    def render_api_status(api_base_url: str):
        """Render API connection status"""
        st.success(f"✅ Connected to Django API at {api_base_url}")
        st.info(f"📡 {len(API_ENDPOINTS)} API endpoints available")
    
    @staticmethod
    def render_header(api_base_url: str, auth_handler=None):
        """Main header rendering method - orchestrates all header components"""
        HeaderComponents.render_app_title()
        
        if auth_handler and auth_handler.auth_manager.is_authenticated():
            user = auth_handler.auth_manager.get_user()
            selected_org = st.session_state.get('selected_organization', 'No organization')
            
            if HeaderComponents.render_user_info_bar(user, selected_org):
                auth_handler.auth_manager.logout()
                return
        
        HeaderComponents.render_api_status(api_base_url)

