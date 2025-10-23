"""
Image Data Management Component for Streamlit
Handles image generation data management functionality
"""

import streamlit as st
from typing import List, Dict, Any
from base.data_management_ui import DataManagementUI


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
    
    def get_api_download_method(self, item_id: int):
        """Get the API download method for images"""
        # Images are typically accessed via URLs, not downloaded as PDFs
        return {"success": False, "message": "Image download not available as PDF"}
    
    def supports_image_download(self) -> bool:
        """Images don't support PDF download, but they have direct URLs"""
        return False
    
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
        elif 'image_url' in item and item['image_url']:
            st.markdown("**🖼️ Image:**")
            try:
                st.image(item['image_url'], caption="Generated Image", width=200)
            except:
                st.caption("Image preview unavailable")
    
    def display_card_actions(self, item: Dict[str, Any], index: int):
        """Display action buttons for the card with image-specific actions"""
        st.markdown("**Actions:**")
        
        # View details button
        if st.button("👁️ View", key=f"view_card_{index}", help="View full details"):
            self.show_card_details(item)
        
        # View images button (specific to images)
        if st.button("🖼️ Images", key=f"images_card_{index}", help="View all images"):
            self.view_single_item_images(item)
        
        # Delete button
        if st.button("🗑️ Delete", key=f"delete_card_{index}", help="Delete this item", type="secondary"):
            self.delete_single_item(item)
    
    def view_single_item_images(self, item: Dict[str, Any]):
        """View images for a single item"""
        with st.expander(f"🖼️ Images for {item.get('title', item.get('prompt', 'Item'))}", expanded=True):
            # Display image URLs if available
            if 'image_urls' in item and item['image_urls']:
                for i, url in enumerate(item['image_urls']):
                    st.image(url, caption=f"Image {i+1}")
            elif 'image_url' in item and item['image_url']:
                st.image(item['image_url'], caption="Generated Image")
            else:
                st.info("No images available for this item.")
