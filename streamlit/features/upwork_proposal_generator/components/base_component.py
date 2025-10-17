"""
Base component class for Upwork proposal generator components.
"""

import streamlit as st
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod


class BaseComponent(ABC):
    """Base class for all Upwork proposal generator components."""
    
    def __init__(self, api_client):
        """Initialize component with API client."""
        self.api = api_client
    
    @abstractmethod
    def render(self):
        """Render the component."""
        pass
    
    def show_error(self, message: str):
        """Show error message."""
        st.error(f"❌ {message}")
    
    def show_success(self, message: str):
        """Show success message."""
        st.success(f"✅ {message}")
    
    def show_info(self, message: str):
        """Show info message."""
        st.info(f"ℹ️ {message}")
    
    def show_warning(self, message: str):
        """Show warning message."""
        st.warning(f"⚠️ {message}")
    
    def show_spinner(self, message: str):
        """Show spinner context manager."""
        return st.spinner(message)
    
    def get_status_icon(self, status: str) -> str:
        """Get status icon for given status."""
        status_icons = {
            'pending': '🟡',
            'generating': '🔄',
            'completed': '✅',
            'failed': '❌'
        }
        return status_icons.get(status.lower(), '❓')
    
    def format_date(self, date_str: str) -> str:
        """Format date string for display."""
        if not date_str:
            return "Unknown date"
        try:
            # Simple date formatting - can be enhanced
            return date_str.split('T')[0] if 'T' in date_str else date_str
        except:
            return date_str
