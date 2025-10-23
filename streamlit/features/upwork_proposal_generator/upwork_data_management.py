"""
Upwork Data Management Component for Streamlit
Handles Upwork proposal data management functionality
"""

import streamlit as st
from typing import List, Dict, Any
from base.data_management_ui import DataManagementUI


class UpworkDataManagement(DataManagementUI):
    """Data management component for Upwork proposal feature"""
    
    def __init__(self, api_client):
        super().__init__(api_client, "upwork")
    
    def get_api_list_method(self):
        """Get the API list method for Upwork proposals"""
        return self.api.list_upwork_proposals()
    
    def get_api_delete_method(self, ids: List[int]):
        """Get the API delete method for Upwork proposals"""
        return self.api.delete_upwork_proposals(ids)
    
    def get_api_download_method(self, item_id: int):
        """Get the API download method for Upwork proposals"""
        return self.api.download_proposal_pdf(item_id)
    
    def supports_image_download(self) -> bool:
        """Upwork proposals don't support image download"""
        return False
