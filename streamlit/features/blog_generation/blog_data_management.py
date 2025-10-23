"""
Blog Data Management Component for Streamlit
Handles blog post data management functionality
"""

import streamlit as st
from typing import List, Dict, Any
from base.data_management_ui import DataManagementUI


class BlogDataManagement(DataManagementUI):
    """Data management component for blog generation feature"""
    
    def __init__(self, api_client):
        super().__init__(api_client, "blog")
    
    def get_api_list_method(self):
        """Get the API list method for blog posts"""
        return self.api.list_blogs()
    
    def get_api_delete_method(self, ids: List[int]):
        """Get the API delete method for blog posts"""
        return self.api.delete_blogs(ids)
    
    def get_api_download_method(self, item_id: int):
        """Get the API download method for blog posts"""
        return self.api.download_blog_pdf(item_id)
    
    def supports_image_download(self) -> bool:
        """Blog posts support image download"""
        return True
    
    def get_image_download_method(self, item_id: int):
        """Get the image download method for blog posts"""
        return self.api.download_blog_images(item_id)
