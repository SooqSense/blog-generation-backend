"""
AI News Data Management Component for Streamlit
Handles AI news data management functionality
"""

import streamlit as st
from typing import List, Dict, Any
from base.data_management_ui import DataManagementUI


class NewsDataManagement(DataManagementUI):
    """Data management component for AI news feature"""
    
    def __init__(self, api_client):
        super().__init__(api_client, "news")
    
    def get_api_list_method(self):
        """Get the API list method for AI news"""
        return self.api.list_news()
    
    def get_api_delete_method(self, ids: List[int]):
        """Get the API delete method for AI news"""
        return self.api.delete_news(ids)
    
    def get_api_download_method(self, item_id: int):
        """Get the API download method for AI news"""
        return self.api.download_news_pdf(item_id)
    
    def supports_image_download(self) -> bool:
        """AI news doesn't support image download"""
        return False
