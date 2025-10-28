import streamlit as st
from typing import Dict, Any, Optional

# Import API client
from api_client import image_api
# Import data management
from .image_data_management import ImageDataManagement

class ImageGenerationFeature:
    """Image Generation feature for Streamlit UI - API-based"""
    
    def __init__(self):
        self.api = image_api
        self.data_management = ImageDataManagement(image_api)
    
    def render(self):
        """Main render method"""
        st.title("🎨 Image Generation")
        st.markdown("Generate stunning images for your content using AI.")
        
        # Create tabs for different features
        tab1, tab2, tab3 = st.tabs([
            "🚀 Generate Images", 
            "✏️ Edit Images",
            "📊 Data Management"
        ])
        
        with tab1:
            self.render_image_generation()
        
        with tab2:
            self.render_image_editing()
        
        with tab3:
            self.data_management.render_data_management_tab()
    
    def render_image_generation(self):
        """Render image generation form"""
        st.subheader("🚀 Generate New Images")
        
        with st.form("image_generation_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                prompt = st.text_area(
                    "Image Prompt *",
                    placeholder="A professional business meeting in a modern office",
                    help="Describe the image you want to generate"
                )
                
                keywords = st.text_input(
                    "Keywords (Optional)",
                    placeholder="professional, modern, business",
                    help="Additional keywords to enhance the image"
                )
            
            with col2:
                count = st.number_input(
                    "Number of Images",
                    min_value=1,
                    max_value=10,
                    value=1,
                    help="How many images to generate"
                )
                
                model = st.selectbox(
                    "AI Model",
                    ["flux_dev", "flux_schnell"],
                    help="Choose the AI model for generation"
                )
            
            submitted = st.form_submit_button("🎨 Generate Images", use_container_width=True)
            
            if submitted:
                if not prompt:
                    st.error("Please enter an image prompt.")
                    return
                
                # Prepare data for API
                image_data = {
                    "prompt": prompt,
                    "keywords": keywords,
                    "count": count,
                    "model": model
                }
                
                # Generate images
                self.generate_images(**image_data)
    
    def generate_images(self, **kwargs):
        """Generate images using API"""
        with st.spinner("🎨 Generating images... This may take up to 5 minutes for high-quality images."):
            try:
                response = self.api.generate_image(**kwargs)
                
                if response and response.get("status") == "success":
                    self.display_generated_images(response)
                else:
                    error_msg = response.get("message", "Unknown error") if response else "No response from server"
                    st.error(f"❌ Image generation failed: {error_msg}")
                    
            except Exception as e:
                st.error(f"❌ Error generating images: {str(e)}")
    
    def display_generated_images(self, images_data: Dict[str, Any]):
        """Display the generated images"""
        st.success("✅ Images generated successfully!")
        
        # Display metadata
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Images Generated", images_data.get("total_generated", 0))
        
        with col2:
            st.metric("Model Used", images_data.get("model", "N/A"))
        
        with col3:
            st.metric("Failed Generations", images_data.get("failed_generations", 0))
        
        # Display images
        st.subheader("🖼️ Generated Images")
        
        if "images" in images_data and images_data["images"]:
            for i, image_info in enumerate(images_data["images"]):
                st.markdown(f"### Image {i+1}")
                
                if "image_url" in image_info:
                    st.image(image_info["image_url"], caption=f"Image {i+1}")
                
                if "enhanced_prompt" in image_info:
                    with st.expander(f"Enhanced Prompt for Image {i+1}"):
                        st.text(image_info["enhanced_prompt"])
        
        # Display stored URLs if available
        if "stored_image_urls" in images_data and images_data["stored_image_urls"]:
            st.subheader("📁 Stored Image URLs")
            for i, url in enumerate(images_data["stored_image_urls"]):
                st.markdown(f"{i+1}. [{url}]({url})")
    
    def render_image_editing(self):
        """Render image editing form"""
        st.subheader("✏️ Edit Existing Images")
        
        with st.form("image_editing_form"):
            uploaded_file = st.file_uploader(
                "Upload Image",
                type=['png', 'jpg', 'jpeg', 'webp'],
                help="Upload an image to edit"
            )
            
            prompt = st.text_area(
                "Edit Instructions *",
                placeholder="Change the background to a sunset scene",
                help="Describe what changes you want to make to the image"
            )
            
            keywords = st.text_input(
                "Keywords (Optional)",
                placeholder="sunset, warm colors, dramatic",
                help="Additional keywords to guide the editing"
            )
            
            submitted = st.form_submit_button("✏️ Edit Image", use_container_width=True)
            
            if submitted:
                if not uploaded_file:
                    st.error("Please upload an image.")
                    return
                
                if not prompt:
                    st.error("Please enter edit instructions.")
                    return
                
                # Edit image
                self.edit_image(uploaded_file, prompt, keywords)
    
    def edit_image(self, uploaded_file, prompt: str, keywords: str = ""):
        """Edit image using API"""
        with st.spinner("✏️ Editing image... This may take up to 5 minutes for complex edits."):
            try:
                response = self.api.edit_image(
                    prompt=prompt,
                    keywords=keywords.split(',') if keywords else [],
                    image=uploaded_file
                )
                
                if response and response.get("status") == "success":
                    self.display_edited_image(response)
                else:
                    error_msg = response.get("message", "Unknown error") if response else "No response from server"
                    st.error(f"❌ Image editing failed: {error_msg}")
                    
            except Exception as e:
                st.error(f"❌ Error editing image: {str(e)}")
    
    def display_edited_image(self, edited_data: Dict[str, Any]):
        """Display the edited image"""
        st.success("✅ Image edited successfully!")
        
        # Display metadata
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Original Size", f"{edited_data.get('original_image_size', 0)} bytes")
        
        with col2:
            st.metric("Processing Time", f"{edited_data.get('processing_time', 0):.2f}s")
        
        # Display edited image
        st.subheader("✏️ Edited Image")
        
        if "edited_image_url" in edited_data:
            st.image(edited_data["edited_image_url"], caption="Edited Image")
        
        # Display enhanced prompt
        if "enhanced_prompt" in edited_data:
            with st.expander("Enhanced Prompt Used"):
                st.text(edited_data["enhanced_prompt"])
        
        # Display database record info
        if "database_record_id" in edited_data:
            st.info(f"📁 Saved to database with ID: {edited_data['database_record_id']}")