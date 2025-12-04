"""
Upwork Data Management Component for Streamlit
Handles Upwork proposal data management functionality
"""

import streamlit as st
from typing import List, Dict, Any
from ui_components.data_management_ui import DataManagementUI
from services.download_service import download_service


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
    
    def download_pdf(self, item_id: int):
        """Download Upwork proposal as MD file using Streamlit download service"""
        try:
            # Get Upwork proposal details
            proposal_data = self.api.get_upwork_proposal(item_id)
            if proposal_data:
                # The API returns the proposal data directly, not wrapped in success/data
                proposal_info = proposal_data
                
                # Generate MD content using the download service
                md_content = download_service.generate_upwork_proposal_md(proposal_info)
                
                # Create filename
                title = proposal_info.get('title', 'upwork_proposal').replace(' ', '_')
                company = proposal_info.get('company_name', 'unknown_company').replace(' ', '_')
                filename = f"upwork_proposal_{company}_{title}_{item_id}.md"
                
                # Use Streamlit's download button
                st.download_button(
                    label="📄 Download MD",
                    data=md_content,
                    file_name=filename,
                    mime="text/markdown",
                    key=f"download_upwork_{item_id}"
                )
                return True
            else:
                st.error("Failed to retrieve Upwork proposal data")
                return False
        except Exception as e:
            st.error(f"Error generating MD file: {str(e)}")
            return False
    
    def get_api_download_method(self, item_id: int):
        """Get the API download method for Upwork proposals"""
        try:
            # Get the proposal data first
            proposal_data = self.api.get_upwork_proposal(item_id)
            if proposal_data:
                # Generate MD content using the download service
                md_content = download_service.generate_upwork_proposal_md(proposal_data)
                return md_content
            else:
                return None
        except Exception as e:
            st.error(f"Error generating MD file: {str(e)}")
            return None
    
    def supports_image_download(self) -> bool:
        """Upwork proposals don't support image download"""
        return False
