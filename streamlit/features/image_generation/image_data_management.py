"""
Image Data Management Component for Streamlit
Handles image generation data management functionality
"""

import streamlit as st
from typing import List, Dict, Any
from ui_components.data_management_ui import DataManagementUI


class ImageDataManagement(DataManagementUI):
    """Data management component for image generation feature"""
    
    def __init__(self, api_client):
        super().__init__(api_client, "image")
    
    def get_api_list_method(self):
        """Get the API list method for images"""
        return self.api.list_images()
    
    def get_api_delete_method(self, ids: List[int]):
        """Get the API delete method for images"""
        return self.api.delete_images(ids)
    
    def download_images(self, item_id: int):
        """Download images as ZIP file"""
        try:
            # Get image details
            image_data = self.api.get_image(item_id)
            if image_data and 'success' in image_data and image_data['success']:
                image_info = image_data['data']
                image_urls = image_info.get('image_urls', [])
                
                if not image_urls:
                    st.warning("No images available for this generation")
                    return False
                
                # Show ZIP download button
                st.subheader("📸 Download Images")
                
                # Import download service
                from services.download_service import download_service
                
                try:
                    # Generate ZIP file
                    zip_data = download_service.generate_image_generation_zip(image_info)
                    
                    # Create filename
                    prompt_safe = "".join(c for c in image_info.get('prompt', 'images')[:30] if c.isalnum() or c in (' ', '-', '_')).rstrip()
                    filename = f"images_{prompt_safe}_{item_id}.zip"
                    
                    # Show download button
                    st.download_button(
                        label=f"📦 Download All Images ({len(image_urls)} images)",
                        data=zip_data,
                        file_name=filename,
                        mime="application/zip",
                        key=f"download_zip_{item_id}",
                        help="Download all images as a ZIP file with metadata"
                    )
                    
                    # Show individual image previews (simplified to avoid column nesting)
                    st.subheader("🖼️ Image Previews")
                    for i, image_url in enumerate(image_urls):
                        try:
                            st.image(image_url, caption=f"Image {i+1}", width=300)
                        except Exception as e:
                            st.error(f"Failed to load image {i+1}")
                
                except Exception as e:
                    st.error(f"Failed to create ZIP file: {str(e)}")
                    # Fallback to individual downloads
                    st.subheader("📥 Individual Downloads (Fallback)")
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
                st.error("Failed to retrieve image data")
                return False
        except Exception as e:
            st.error(f"Error downloading images: {str(e)}")
            return False
    
    def supports_image_download(self) -> bool:
        """Images support ZIP download"""
        return True
    
    # Removed custom load_and_display_data method to use the new card-based UI from base class
    
    def display_card_info(self, item: Dict[str, Any]):
        """Display key information in the card with image preview"""
        # Call parent method first
        super().display_card_info(item)
        
        # Add image preview for images
        if 'image_urls' in item and item['image_urls']:
            st.markdown("**🖼️ Images:**")
            # Show first image as preview
            try:
                st.image(item['image_urls'][0], caption="Preview", width=200)
                if len(item['image_urls']) > 1:
                    st.caption(f"+ {len(item['image_urls']) - 1} more images")
            except:
                st.caption("Image preview unavailable")
        
        # Display additional image metadata
        if 'images_count' in item:
            st.markdown(f"**📊 Count:** {item['images_count']} images")
        if 'generation_method' in item:
            st.markdown(f"**⚙️ Method:** {item['generation_method']}")
        if 'image_style' in item:
            st.markdown(f"**🎨 Style:** {item['image_style']}")
    
    def display_card_actions(self, item: Dict[str, Any], index: int):
        """Display action buttons for the card with image-specific actions"""
        st.markdown("**Actions:**")
        
        # Download images button
        if st.button("📥 Download", key=f"download_card_{index}", help="Download images"):
            self.download_images(item.get('id'))
        
        # Delete button
        if st.button("🗑️ Delete", key=f"delete_card_{index}", help="Delete this item", type="secondary"):
            self.delete_single_item(item)
    
    def view_single_item_images(self, item: Dict[str, Any]):
        """View images for a single item"""
        with st.expander(f"🖼️ Images for {item.get('title', item.get('prompt', 'Item'))}", expanded=True):
            # Display image URLs if available
            if 'image_urls' in item and item['image_urls']:
                # Show metadata
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Images Count", item.get('images_count', len(item['image_urls'])))
                with col2:
                    st.metric("Generation Method", item.get('generation_method', 'Unknown'))
                with col3:
                    st.metric("Style", item.get('image_style', 'Unknown'))
                
                # Display images (simplified to avoid column nesting)
                for i, url in enumerate(item['image_urls']):
                    try:
                        st.image(url, caption=f"Image {i+1}", width=300)
                    except Exception as e:
                        st.error(f"Failed to load image {i+1}")
            else:
                st.info("No images available for this item.")
