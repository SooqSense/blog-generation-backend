import streamlit as st
import json
import re
from datetime import datetime
from typing import Dict, Any, List, Optional

# Import API client
from api_client import blog_api
# Import markdown processor
from base.markdown_processor import MarkdownProcessor
# Import data management
from .blog_data_management import BlogDataManagement

class BlogGenerationFeature:
    """Blog Generation feature for Streamlit UI - API-based"""
    
    def __init__(self):
        self.api = blog_api
        self.data_management = BlogDataManagement(blog_api)
    
    def render(self):
        """Main render method"""
        st.title("📝 Blog Generation")
        st.markdown("Create professional blog posts with AI-powered content generation.")
        
        # Create tabs for different features
        tab1, tab2 = st.tabs([
            "🚀 Generate Blog", 
            "📊 Data Management"
        ])
        
        with tab1:
            self.render_blog_generation()
        
        with tab2:
            self.data_management.render_data_management_tab()
    
    def render_blog_generation(self):
        """Render blog generation form"""
        st.subheader("🚀 Generate New Blog Post")
        
        # Create form
        with st.form("blog_generation_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                topic = st.text_input(
                    "Blog Topic *",
                    placeholder="e.g., The Future of Artificial Intelligence",
                    help="Enter the main topic for your blog post"
                )
                
                blog_type = st.selectbox(
                    "Blog Type",
                    ["News", "Comparison"],
                    help="Choose the type of blog post to generate"
                )
                
                sample_blog_url = st.text_input(
                    "Sample Blog URL (Optional)",
                    placeholder="https://example.com/blog-post",
                    help="Optional URL to analyze and replicate the style"
                )
            
            with col2:
                length_min = st.number_input(
                    "Minimum Word Count",
                    min_value=300,
                    max_value=5000,
                    value=800,
                    help="Minimum number of words for the blog post"
                )
                
                length_max = st.number_input(
                    "Maximum Word Count",
                    min_value=500,
                    max_value=10000,
                    value=1500,
                    help="Maximum number of words for the blog post"
                )
            
            # Keywords section
            st.subheader("🎯 Keywords")
            keywords_input = st.text_area(
                "Keywords (Optional)",
                placeholder="artificial intelligence, machine learning, automation",
                help="Enter keywords separated by commas. You can also specify usage count like 'AI:5, ML:3'"
            )
            
            # Process keywords
            keywords = []
            if keywords_input:
                for keyword_text in keywords_input.split(','):
                    keyword_text = keyword_text.strip()
                    if ':' in keyword_text:
                        # Format: keyword:count
                        parts = keyword_text.split(':')
                        if len(parts) == 2:
                            keyword = parts[0].strip()
                            try:
                                count = int(parts[1].strip())
                                keywords.append({"keyword": keyword, "count": count})
                            except ValueError:
                                keywords.append({"keyword": keyword_text, "count": 1})
                    else:
                        keywords.append({"keyword": keyword_text, "count": 1})
            
            # Blog structure options
            st.subheader("📋 Blog Structure")
            col3, col4 = st.columns(2)
            
            with col3:
                introduction = st.checkbox("Include Introduction", value=True)
                table_of_content = st.checkbox("Include Table of Contents", value=False)
                faq = st.checkbox("Include FAQ Section", value=False)
            
            with col4:
                cta = st.checkbox("Include Call to Action", value=False)
                conclusion = st.checkbox("Include Conclusion", value=True)
                generate_images = st.checkbox("Generate Images", value=True)
            
            # Target audience
            target_audience = st.multiselect(
                "Target Audience (Optional)",
                ["General Public", "Professionals", "Students", "Developers", "Business Owners"],
                help="Select target audience for the blog post"
            )
            
            # Submit button with toggle for streaming
            col_btn1, col_btn2 = st.columns([3, 1])
            with col_btn1:
                use_streaming = st.checkbox("⚡ Use Real-time Streaming", value=True, help="Stream generation progress in real-time")
            
            submitted = st.form_submit_button("🚀 Generate Blog Post", use_container_width=True)
            
            if submitted:
                if not topic:
                    st.error("Please enter a blog topic.")
                    return
                
                # Prepare data for API
                blog_data = {
                    "topic": topic,
                    "keywords": keywords,
                    "blog_type": blog_type,
                    "length_min": length_min,
                    "length_max": length_max,
                    "introduction": introduction,
                    "table_of_content": table_of_content,
                    "faq": faq,
                    "cta": cta,
                    "conclusion": conclusion,
                    "target_audience": target_audience,
                    "generate_image_prompts": generate_images,
                    "generate_images": generate_images
                }
                
                if sample_blog_url:
                    blog_data["sample_blog_url"] = sample_blog_url
                
                # Generate blog with or without streaming
                if use_streaming:
                    self.generate_blog_post_stream(blog_data)
                else:
                    self.generate_blog_post(**blog_data)
    
    def generate_blog_post(self, **kwargs):
        """Generate blog post using API (non-streaming)"""
        with st.spinner("🤖 Generating blog post... This may take up to 5 minutes for complex content."):
            try:
                response = self.api.generate_blog(**kwargs)
                
                if response and response.get("status") == "success":
                    self.display_generated_blog(response)
                else:
                    error_msg = response.get("message", "Unknown error") if response else "No response from server"
                    st.error(f"❌ Blog generation failed: {error_msg}")
                    
            except Exception as e:
                st.error(f"❌ Error generating blog: {str(e)}")
    
    def generate_blog_post_stream(self, blog_data: Dict[str, Any]):
        """Generate blog post using WebSocket streaming"""
        # Create status container
        status_placeholder = st.empty()
        result_placeholder = st.empty()
        
        current_stage = {"stage": "", "message": ""}
        result_data = {"data": None}
        
        def handle_status(stage: str, message: str):
            """Handle status updates"""
            current_stage["stage"] = stage
            current_stage["message"] = message
            status_placeholder.info(f"**{message}**")
        
        def handle_complete(data: Dict[str, Any]):
            """Handle completion"""
            result_data["data"] = data
            status_placeholder.success("✅ Blog generation completed successfully!")
        
        def handle_error(error: str):
            """Handle error"""
            status_placeholder.error(f"❌ {error}")
        
        try:
            # Start streaming
            self.api.generate_blog_stream(
                blog_data=blog_data,
                on_status=handle_status,
                on_complete=handle_complete,
                on_error=handle_error
            )
            
            # Display result if successful
            if result_data["data"]:
                result_placeholder.empty()
                self.display_generated_blog_stream(result_data["data"])
                
        except Exception as e:
            st.error(f"❌ Error during streaming: {str(e)}")
    
    def display_generated_blog(self, blog_data: Dict[str, Any]):
        """Display the generated blog post"""
        st.success("✅ Blog post generated successfully!")
        
        # Display blog metadata
        metadata_fields = [
            ("images_count", "Images Generated")
        ]
        
        # Display content with metadata using the modular processor
        MarkdownProcessor.display_with_metadata(
            blog_data,
            "📝 Generated Blog Post",
            metadata_fields,
            ["raw_content", "content", "sections"]
        )
        
        # Display images if generated
        MarkdownProcessor.display_images(blog_data.get("image_urls", []))
        
        # Display sources if available
        MarkdownProcessor.display_sources(blog_data.get("research_sources", []), "📚 Research Sources")
    
    def display_generated_blog_stream(self, blog_data: Dict[str, Any]):
        """Display the streamed blog generation result"""
        st.divider()
        
        # Display metadata
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Word Count", blog_data.get('word_count', 0))
        with col2:
            st.metric("🖼️ Images", blog_data.get('images_count', 0))
        with col3:
            st.metric("📚 Sources", blog_data.get('sources_count', 0))
        
        # Display content
        st.subheader("📝 Generated Blog Content")
        content = blog_data.get('content', '')
        if content:
            st.markdown(content)
            
            # Copy button
            st.download_button(
                label="📥 Download Markdown",
                data=content,
                file_name=f"blog_{blog_data.get('topic', 'generated')}.md",
                mime="text/markdown"
            )
        else:
            st.warning("No content generated")
    
