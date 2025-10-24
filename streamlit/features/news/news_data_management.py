"""
AI News Data Management Component for Streamlit
Handles AI news data management functionality
"""

import streamlit as st
from typing import List, Dict, Any
from base.data_management_ui import DataManagementUI
from base.download_service import download_service


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
    
    def download_pdf(self, item_id: int):
        """Download AI news as PDF using Streamlit download service"""
        try:
            # Get AI news details
            news_data = self.api.get_news(item_id)
            if news_data and 'success' in news_data and news_data['success']:
                news_info = news_data['data']
                
                # Generate PDF using the download service
                pdf_bytes = download_service.generate_ai_news_pdf(news_info)
                
                # Create filename
                news_date = news_info.get('news_date', 'unknown_date')
                country = news_info.get('country', 'unknown')
                filename = f"ai_news_{country}_{news_date}_{item_id}.pdf"
                
                # Use Streamlit's download button
                st.download_button(
                    label="📄 Download PDF",
                    data=pdf_bytes,
                    file_name=filename,
                    mime="application/pdf",
                    key=f"download_news_{item_id}"
                )
                return True
            else:
                st.error("Failed to retrieve AI news data")
                return False
        except Exception as e:
            st.error(f"Error generating PDF: {str(e)}")
            return False
    
    def supports_image_download(self) -> bool:
        """AI news doesn't support image download"""
        return False
