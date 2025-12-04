"""
Blog Data Management Component for Streamlit
Handles blog post data management functionality
"""

import streamlit as st
from typing import List, Dict, Any
from ui_components.data_management_ui import DataManagementUI


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
    
    def download_md(self, item_id: int):
        """Download blog post as Markdown file"""
        try:
            # Get blog post details
            blog_data = self.api.get_blog(item_id)
            if blog_data and 'success' in blog_data and blog_data['success']:
                blog_info = blog_data['data']
                
                # Generate Markdown content
                md_content = self._generate_blog_markdown(blog_info)
                
                # Create filename
                topic = blog_info.get('topic', 'blog_post').replace(' ', '_')
                filename = f"{topic}_{item_id}.md"
                
                # Use Streamlit's download button
                st.download_button(
                    label="📄 Download MD",
                    data=md_content,
                    file_name=filename,
                    mime="text/markdown",
                    key=f"download_blog_{item_id}"
                )
                return True
            else:
                st.error("Failed to retrieve blog post data")
                return False
        except Exception as e:
            st.error(f"Error generating Markdown: {str(e)}")
            return False
    
    def _generate_blog_markdown(self, blog_data: Dict[str, Any]) -> str:
        """Generate Markdown content for blog post"""
        try:
            # Extract blog content
            content = blog_data.get('content', '')
            topic = blog_data.get('topic', 'Blog Post')
            
            # Create Markdown header
            md_content = f"# {topic}\n\n"
            
            # Add metadata
            md_content += f"**Author:** {blog_data.get('username', 'Unknown')}\n"
            md_content += f"**Email:** {blog_data.get('email', 'Unknown')}\n"
            md_content += f"**Created:** {blog_data.get('created_at', 'Unknown')}\n"
            md_content += f"**Organization:** {blog_data.get('organization_name', 'Unknown')}\n\n"
            md_content += "---\n\n"
            
            # Add main content
            if content:
                md_content += content
            else:
                md_content += "No content available."
            
            # Add sources if available
            sources = blog_data.get('sources', [])
            if sources:
                md_content += "\n\n## Sources\n\n"
                for i, source in enumerate(sources, 1):
                    title = source.get('title', f'Source {i}')
                    url = source.get('url', '')
                    if url:
                        md_content += f"{i}. [{title}]({url})\n"
                    else:
                        md_content += f"{i}. {title}\n"
            
            # Add images if available
            image_urls = blog_data.get('image_urls', [])
            if image_urls:
                md_content += "\n\n## Images\n\n"
                for i, image_url in enumerate(image_urls, 1):
                    md_content += f"![Image {i}]({image_url})\n\n"
            
            return md_content
            
        except Exception as e:
            return f"# Error generating Markdown\n\nError: {str(e)}"
    
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
