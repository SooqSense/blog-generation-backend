"""
UI Components Module - Facade/Orchestrator
Main entry point for UI components. Delegates to specialized component modules.
"""

from ui_components.components.header_components import HeaderComponents
from ui_components.components.sidebar_components import SidebarComponents
from ui_components.components.home_components import HomeComponents
from ui_components.components.styling import CustomCSS

# Export CustomCSS for backward compatibility
__all__ = ['UIComponents', 'CustomCSS']


class UIComponents:
    """
    Main UI Components facade class.
    Orchestrates specialized component modules for a clean API.
    """
    
    @staticmethod
    def render_header(api_base_url: str, auth_handler=None):
        """Render the main application header"""
        HeaderComponents.render_header(api_base_url, auth_handler)
    
    @staticmethod
    def render_sidebar(auth_handler, api_endpoints_count: int):
        """Render the sidebar navigation"""
        return SidebarComponents.render_sidebar(auth_handler, api_endpoints_count)
    
    @staticmethod
    def render_home(api_base_url: str):
        """Render the home page"""
        HomeComponents.render_home(api_base_url)
