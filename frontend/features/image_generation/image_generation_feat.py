import streamlit as st
import sys
import os
from pathlib import Path
import base64
from io import BytesIO
from PIL import Image

# Add the project root to the path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import AI tools directly without Django setup
try:
    from tools.ai.image_generation.image_generator import generate_image_with_flux, generate_image_with_flux_schnell
    from tools.ai.image_generation.edit_images import edit_image_with_flux, convert_image_to_base64
    
    AI_TOOLS_AVAILABLE = True
    AI_TOOLS_ERROR = None
    print("✅ Image generation feature: AI tools imported successfully")
    
except Exception as e:
    AI_TOOLS_AVAILABLE = False
    AI_TOOLS_ERROR = str(e)
    print(f"⚠️ Image generation feature: AI tools import failed - {str(e)}")
    
    # Create dummy functions for graceful degradation
    def generate_image_with_flux(*args, **kwargs):
        raise Exception(f"FLUX AI image generation not available: {AI_TOOLS_ERROR}")
    
    def generate_image_with_flux_schnell(*args, **kwargs):
        raise Exception(f"FLUX AI image generation not available: {AI_TOOLS_ERROR}")
    
    def edit_image_with_flux(*args, **kwargs):
        raise Exception(f"FLUX AI image editing not available: {AI_TOOLS_ERROR}")
    
    def convert_image_to_base64(*args, **kwargs):
        raise Exception(f"Image conversion tools not available: {AI_TOOLS_ERROR}")

class ImageGenerationFeature:
    """Image Generation feature for Streamlit UI"""
    
    def __init__(self):
        self.ai_tools_available = AI_TOOLS_AVAILABLE
        self.ai_tools_error = AI_TOOLS_ERROR
        
    def render(self):
        """Render the image generation interface"""
        st.markdown("# 🎨 Image Generation")
        st.markdown("Generate stunning images for your content using AI-powered image generation.")
        
        # Create tabs for different functionalities
        tab1, tab2, tab3 = st.tabs(["🖼️ Generate Images", "✏️ Edit Images", "📸 Generated Gallery"])
        
        with tab1:
            self.render_image_generation()
            
        with tab2:
            self.render_image_editing()
            
        with tab3:
            self.render_image_gallery()
    
    def render_image_generation(self):
        """Render the image generation form"""
        st.markdown("### Create AI-Generated Images")
        
        # Two column layout
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Basic image settings
            st.markdown("#### 🎯 Image Settings")
            
            prompt = st.text_area(
                "Image Prompt *",
                placeholder="A professional, high-quality image of artificial intelligence concepts with futuristic elements, clean composition, and vibrant colors",
                help="Describe the image you want to generate",
                height=100
            )
            
            # Advanced settings
            col_adv1, col_adv2 = st.columns(2)
            
            with col_adv1:
                model = st.selectbox(
                    "FLUX AI Model",
                    [
                        ("flux_dev", "FLUX Dev - High Quality (28 steps)"),
                        ("flux_schnell", "FLUX Schnell - Fast Generation (4 steps)")
                    ],
                    format_func=lambda x: x[1],
                    help="Choose between FLUX Dev for high-quality detailed images or FLUX Schnell for faster generation"
                )
                
                # Extract the actual model value (flux_dev or flux_schnell)
                selected_model = model[0]
                
                # Fixed image size for all generations
                image_size = "1920x1080"
                st.info("🖼️ **Image Resolution**: Fixed at 1920x1080 (Full HD) for all generations")
                
            with col_adv2:
                image_count = st.number_input(
                    "Number of Images",
                    min_value=1,
                    max_value=10,
                    value=1,
                    help="How many images to generate"
                )
                
                image_type = st.selectbox(
                    "Image Type",
                    ["content", "banner", "thumbnail", "social", "article"],
                    help="Type of image for optimization"
                )
            
            # Optional enhancement settings
            st.markdown("#### 🔧 Enhancement Settings")
            
            col_enh1, col_enh2 = st.columns(2)
            
            with col_enh1:
                topic = st.text_input(
                    "Blog Topic (Optional)",
                    placeholder="e.g., Artificial Intelligence",
                    help="Main topic for context-aware generation"
                )
                
            with col_enh2:
                keywords = st.text_input(
                    "Keywords (comma-separated)",
                    placeholder="AI, technology, innovation",
                    help="Keywords to focus on in the image"
                )
            
            # Style presets
            st.markdown("#### 🎨 Style Presets")
            
            col_style1, col_style2, col_style3 = st.columns(3)
            
            with col_style1:
                if st.button("🏢 Professional", use_container_width=True):
                    st.session_state.style_preset = "professional, clean, corporate, modern design, minimalist"
                    
            with col_style2:
                if st.button("🎯 Creative", use_container_width=True):
                    st.session_state.style_preset = "creative, artistic, vibrant colors, dynamic composition"
                    
            with col_style3:
                if st.button("🔬 Technical", use_container_width=True):
                    st.session_state.style_preset = "technical, detailed, scientific, high-tech, futuristic"
            
            # Apply style preset to prompt
            if 'style_preset' in st.session_state:
                enhanced_prompt = f"{prompt}, {st.session_state.style_preset}"
                st.info(f"Style applied: {st.session_state.style_preset}")
            else:
                enhanced_prompt = prompt
        
        with col2:
            # Generation preview and controls
            st.markdown("### 🚀 Generation")
            
            # Quick stats
            st.markdown("#### 📊 Generation Info")
            if prompt:
                word_count = len(prompt.split())
                st.metric("Prompt Words", word_count)
                
                if word_count < 10:
                    st.warning("⚠️ Consider adding more details to your prompt")
                elif word_count > 50:
                    st.info("ℹ️ Very detailed prompt - good for specific results")
                else:
                    st.success("✅ Good prompt length")
            
            # Model-specific info
            if selected_model == "flux_dev":
                st.markdown("""
                **FLUX Dev Features:**
                - Highest quality and detail
                - 28 inference steps for precision
                - Rich artistic compositions
                - Best for professional content
                - Slower but superior results
                """)
            else:
                st.markdown("""
                **FLUX Schnell Features:**
                - Fast generation (4 steps)
                - High quality artistic results
                - Optimized for speed
                - Great for quick iterations
                - Excellent quality-to-speed ratio
                """)
            
            # Generation status
            if 'image_generation_status' in st.session_state:
                status = st.session_state.image_generation_status
                if status == 'generating':
                    st.info("🔄 Generating images...")
                elif status == 'completed':
                    st.success("✅ Images generated successfully!")
                elif status == 'error':
                    st.error("❌ Generation failed")
        
        # Generate button
        st.markdown("---")
        
        col_gen1, col_gen2, col_gen3 = st.columns([1, 2, 1])
        
        with col_gen2:
            if st.button(
                "🎨 Generate Images",
                type="primary",
                use_container_width=True,
                disabled=not prompt.strip()
            ):
                if prompt.strip():
                    self.generate_images(
                        prompt=enhanced_prompt,
                        model=selected_model,
                        size=image_size,
                        count=image_count,
                        topic=topic,
                        keywords=keywords.split(',') if keywords else [],
                        image_type=image_type
                    )
                else:
                    st.error("Please enter an image prompt")
        
        # Display generated images
        if 'generated_images' in st.session_state:
            self.display_generated_images(st.session_state.generated_images)
    
    def generate_images(self, **kwargs):
        """Generate images using the AI tools"""
        try:
            st.session_state.image_generation_status = 'generating'
            
            # Show progress
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.text("Initializing image generation...")
            progress_bar.progress(10)
            
            # Determine generation function based on selected model
            model = kwargs.get('model', 'flux_dev')
            if model == 'flux_schnell':
                generation_func = generate_image_with_flux_schnell
                method = "flux_schnell"
                model_name = "FLUX Schnell"
            else:
                generation_func = generate_image_with_flux
                method = "flux"
                model_name = "FLUX Dev"
            
            status_text.text(f"Generating {kwargs.get('count', 1)} image(s) with {model_name}...")
            progress_bar.progress(30)
            
            # Generate images
            images_data, total_generated, failed_generations = generation_func(
                prompt=kwargs.get('prompt'),
                size=kwargs.get('size', '1024x1024'),
                output_dir="streamlit_images",
                topic=kwargs.get('topic'),
                keywords=kwargs.get('keywords', []),
                image_type=kwargs.get('image_type', 'content'),
                count=kwargs.get('count', 1)
            )
            
            status_text.text("Processing generated images...")
            progress_bar.progress(80)
            
            # Store the generated images
            generated_images = {
                'images_data': images_data,
                'total_generated': total_generated,
                'failed_generations': failed_generations,
                'method': method,
                'prompt': kwargs.get('prompt'),
                'settings': {
                    'size': kwargs.get('size'),
                    'count': kwargs.get('count'),
                    'topic': kwargs.get('topic'),
                    'keywords': kwargs.get('keywords'),
                    'image_type': kwargs.get('image_type')
                },
                'generated_by': st.session_state.get('username', 'Anonymous'),
                'user_email': st.session_state.get('user_email', '')
            }
            
            st.session_state.generated_images = generated_images
            st.session_state.image_generation_status = 'completed'
            
            status_text.text("Image generation completed!")
            progress_bar.progress(100)
            
            # Clear progress indicators after a short delay
            import time
            time.sleep(1)
            progress_bar.empty()
            status_text.empty()
            
        except Exception as e:
            st.session_state.image_generation_status = 'error'
            st.error(f"Error generating images: {str(e)}")
    
    def display_generated_images(self, images_data):
        """Display the generated images"""
        st.markdown("---")
        st.markdown("## 🖼️ Generated Images")
        
        # Generation summary
        col_summary1, col_summary2, col_summary3 = st.columns(3)
        
        with col_summary1:
            st.metric("Total Generated", images_data.get('total_generated', 0))
        with col_summary2:
            st.metric("Failed", images_data.get('failed_generations', 0))
        with col_summary3:
            st.metric("Method", images_data.get('method', 'Unknown').upper())
        
        # Display images
        if images_data.get('images_data'):
            st.markdown("### 🎨 Your Images")
            
            # Display images in a grid
            images_list = images_data.get('images_data', [])
            
            # Create columns based on number of images
            if len(images_list) == 1:
                cols = [st.columns(1)[0]]
            elif len(images_list) == 2:
                cols = st.columns(2)
            elif len(images_list) <= 4:
                cols = st.columns(2)
            else:
                cols = st.columns(3)
            
            for i, image_data in enumerate(images_list):
                col_idx = i % len(cols)
                
                with cols[col_idx]:
                    # Display image
                    if image_data.get('image_url'):
                        st.image(
                            image_data['image_url'],
                            caption=f"Image {image_data.get('image_number', i+1)}",
                            use_column_width=True
                        )
                        
                        # Image details
                        with st.expander(f"Details - Image {image_data.get('image_number', i+1)}"):
                            st.write(f"**Enhanced Prompt:** {image_data.get('enhanced_prompt', 'N/A')}")
                            st.write(f"**URL:** {image_data.get('image_url')}")
                        
                        # Download button
                        if st.button(f"⬇️ Download", key=f"download_{i}", use_container_width=True):
                            st.markdown(f"[Download Image]({image_data.get('image_url')})")
            
            # Batch download
            st.markdown("### 📥 Batch Operations")
            
            col_batch1, col_batch2 = st.columns(2)
            
            with col_batch1:
                # Copy all URLs
                if st.button("📋 Copy All URLs", use_container_width=True):
                    urls = [img.get('image_url', '') for img in images_list]
                    urls_text = '\n'.join(urls)
                    st.code(urls_text, language="text")
            
            with col_batch2:
                # Export image data
                if st.button("📊 Export Data", use_container_width=True):
                    export_data = {
                        'prompt': images_data.get('prompt'),
                        'method': images_data.get('method'),
                        'settings': images_data.get('settings'),
                        'images': images_list
                    }
                    st.json(export_data)
        else:
            st.warning("No images were generated successfully.")
    
    def render_image_editing(self):
        """Render image editing interface"""
        st.markdown("### ✏️ Edit Existing Images")
        st.markdown("Upload an image and provide editing instructions to modify it with AI.")
        
        # Image upload
        uploaded_file = st.file_uploader(
            "Choose an image to edit",
            type=['png', 'jpg', 'jpeg'],
            help="Upload an image in PNG, JPG, or JPEG format"
        )
        
        if uploaded_file is not None:
            # Display uploaded image
            col_img1, col_img2 = st.columns(2)
            
            with col_img1:
                st.markdown("#### 📤 Original Image")
                image = Image.open(uploaded_file)
                st.image(image, caption="Original Image", use_column_width=True)
                
                # Image info
                st.info(f"Size: {image.size[0]}x{image.size[1]} pixels")
                st.info(f"Format: {image.format}")
            
            with col_img2:
                st.markdown("#### ✏️ Editing Instructions")
                
                edit_prompt = st.text_area(
                    "Describe how to edit the image",
                    placeholder="Make the background blue, add professional lighting, enhance colors",
                    help="Describe what changes you want to make to the image",
                    height=100
                )
                
                keywords = st.text_input(
                    "Keywords for editing",
                    placeholder="professional, enhanced, colorful",
                    help="Keywords to guide the editing process"
                )
                
                # Quick edit presets
                st.markdown("#### ⚡ Quick Edits")
                
                if st.button("🎨 Enhance Colors", use_container_width=True):
                    edit_prompt = "Enhance colors, improve saturation, professional color grading"
                    
                if st.button("💡 Better Lighting", use_container_width=True):
                    edit_prompt = "Improve lighting, add professional studio lighting, enhance brightness"
                    
                if st.button("🎯 Professional Look", use_container_width=True):
                    edit_prompt = "Make it look more professional, clean, corporate style"
                
                # Edit button
                if st.button(
                    "✏️ Edit Image",
                    type="primary",
                    use_container_width=True,
                    disabled=not edit_prompt.strip()
                ):
                    if edit_prompt.strip():
                        self.edit_image(uploaded_file, edit_prompt, keywords)
                    else:
                        st.error("Please provide editing instructions")
        
        # Display edited image
        if 'edited_image' in st.session_state:
            self.display_edited_image(st.session_state.edited_image)
    
    def edit_image(self, uploaded_file, prompt, keywords):
        """Edit an image using AI"""
        try:
            st.session_state.image_edit_status = 'editing'
            
            with st.spinner("Converting and editing image..."):
                # Convert uploaded file to base64
                image_base64 = convert_image_to_base64(uploaded_file)
                
                if not image_base64:
                    st.error("Failed to process the uploaded image")
                    return
                
                # Edit the image
                result = edit_image_with_flux(
                    prompt=prompt,
                    image_base64=image_base64,
                    keywords=keywords.split(',') if keywords else [],
                    output_dir="streamlit_edited"
                )
                
                if result and result.get('success'):
                    edited_image = {
                        'original_name': uploaded_file.name,
                        'edit_prompt': prompt,
                        'keywords': keywords,
                        'enhanced_prompt': result.get('enhanced_prompt', ''),
                        'edited_url': result.get('image_url', ''),
                        'edited_by': st.session_state.get('username', 'Anonymous'),
                        'user_email': st.session_state.get('user_email', '')
                    }
                    
                    st.session_state.edited_image = edited_image
                    st.session_state.image_edit_status = 'completed'
                    st.success("Image edited successfully!")
                    
                else:
                    st.error("Failed to edit the image. Please try again.")
                    
        except Exception as e:
            st.session_state.image_edit_status = 'error'
            st.error(f"Error editing image: {str(e)}")
    
    def display_edited_image(self, edited_data):
        """Display the edited image"""
        st.markdown("---")
        st.markdown("## ✏️ Edited Image Result")
        
        col_result1, col_result2 = st.columns(2)
        
        with col_result1:
            st.markdown("### 📤 Original")
            st.info("Original image was uploaded above")
            
        with col_result2:
            st.markdown("### ✨ Edited")
            if edited_data.get('edited_url'):
                st.image(
                    edited_data['edited_url'],
                    caption="Edited Image",
                    use_column_width=True
                )
                
                # Download edited image
                if st.button("⬇️ Download Edited Image", use_container_width=True):
                    st.markdown(f"[Download Edited Image]({edited_data.get('edited_url')})")
        
        # Edit details
        st.markdown("### 📋 Edit Details")
        
        col_detail1, col_detail2 = st.columns(2)
        
        with col_detail1:
            st.write(f"**Original:** {edited_data.get('original_name', 'N/A')}")
            st.write(f"**Edit Prompt:** {edited_data.get('edit_prompt', 'N/A')}")
            
        with col_detail2:
            st.write(f"**Keywords:** {edited_data.get('keywords', 'N/A')}")
            st.write(f"**Enhanced Prompt:** {edited_data.get('enhanced_prompt', 'N/A')}")
    
    def render_image_gallery(self):
        """Render image gallery"""
        st.markdown("### 📸 Generated Images Gallery")
        st.markdown("View and manage your generated and edited images.")
        
        # Generated images section
        if 'generated_images' in st.session_state:
            st.markdown("#### 🎨 Generated Images")
            
            images_data = st.session_state.generated_images
            
            with st.expander("View Generated Images", expanded=True):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"**Prompt:** {images_data.get('prompt', 'N/A')[:50]}...")
                    st.write(f"**Method:** {images_data.get('method', 'N/A').upper()}")
                    
                with col2:
                    st.write(f"**Generated:** {images_data.get('total_generated', 0)}")
                    st.write(f"**Failed:** {images_data.get('failed_generations', 0)}")
                    
                with col3:
                    st.write(f"**Author:** {images_data.get('generated_by', 'Anonymous')}")
                    st.write(f"**Email:** {images_data.get('user_email', 'N/A')}")
                
                if st.button("🖼️ View Images", key="view_generated"):
                    self.display_generated_images(images_data)
        
        # Edited images section
        if 'edited_image' in st.session_state:
            st.markdown("#### ✏️ Edited Images")
            
            edited_data = st.session_state.edited_image
            
            with st.expander("View Edited Image", expanded=True):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"**Original:** {edited_data.get('original_name', 'N/A')}")
                    st.write(f"**Edit Prompt:** {edited_data.get('edit_prompt', 'N/A')[:30]}...")
                    
                with col2:
                    st.write(f"**Keywords:** {edited_data.get('keywords', 'N/A')}")
                    
                with col3:
                    st.write(f"**Editor:** {edited_data.get('edited_by', 'Anonymous')}")
                    st.write(f"**Email:** {edited_data.get('user_email', 'N/A')}")
                
                if st.button("✨ View Edited Image", key="view_edited"):
                    self.display_edited_image(edited_data)
        
        # Empty state
        if 'generated_images' not in st.session_state and 'edited_image' not in st.session_state:
            st.info("No images in gallery yet. Generate or edit some images to see them here!")
            
        # Placeholder for database integration
        st.markdown("---")
        st.markdown("#### 🔄 Load from Database")
        st.info("Database integration coming soon! This will show all your previously generated and edited images.")
