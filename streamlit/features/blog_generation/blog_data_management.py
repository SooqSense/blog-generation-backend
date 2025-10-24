"""
Blog Data Management Component for Streamlit
Handles blog post data management functionality
"""

import streamlit as st
from typing import List, Dict, Any
from base.data_management_ui import DataManagementUI
from base.download_service import download_service


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
    
    def download_pdf(self, item_id: int):
        """Download blog post as PDF using Streamlit download service"""
        try:
            # Get blog post details
            blog_data = self.api.get_blog(item_id)
            if blog_data and 'success' in blog_data and blog_data['success']:
                blog_info = blog_data['data']
                
                # Generate PDF using the download service
                pdf_bytes = download_service.generate_blog_pdf(blog_info)
                
                # Create filename
                topic = blog_info.get('topic', 'blog_post').replace(' ', '_')
                filename = f"{topic}_{item_id}.pdf"
                
                # Use Streamlit's download button
                st.download_button(
                    label="📄 Download PDF",
                    data=pdf_bytes,
                    file_name=filename,
                    mime="application/pdf",
                    key=f"download_blog_{item_id}"
                )
                return True
            else:
                st.error("Failed to retrieve blog post data")
                return False
        except Exception as e:
            st.error(f"Error generating PDF: {str(e)}")
            return False
    
    def supports_image_download(self) -> bool:
        """Blog posts support image download"""
        return True
    
    def download_images(self, item_id: int):
        """Download blog post images as ZIP"""
        try:
            # Get blog post details
            blog_data = self.api.get_blog(item_id)
            if blog_data and 'success' in blog_data and blog_data['success']:
                blog_info = blog_data['data']
                image_urls = blog_info.get('image_urls', [])
                
                if not image_urls:
                    st.warning("No images available for this blog post")
                    return False
                
                # For now, show individual image download buttons
                st.subheader("📸 Download Images")
                for i, image_url in enumerate(image_urls, 1):
                    try:
                        import requests
                        response = requests.get(image_url)
                        if response.status_code == 200:
                            filename = f"image_{i}_{item_id}.jpg"
                            st.download_button(
                                label=f"Download Image {i}",
                                data=response.content,
                                file_name=filename,
                                mime="image/jpeg",
                                key=f"download_image_{item_id}_{i}"
                            )
                    except Exception as e:
                        st.error(f"Failed to download image {i}: {str(e)}")
                
                return True
            else:
                st.error("Failed to retrieve blog post data")
                return False
        except Exception as e:
            st.error(f"Error downloading images: {str(e)}")
            return False
