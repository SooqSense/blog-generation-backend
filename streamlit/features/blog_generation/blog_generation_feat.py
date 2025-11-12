import streamlit as st
import json
import re
import time
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

# Import API client
from api_client import blog_api
# Import markdown processor
from base.markdown_processor import MarkdownProcessor
# Import data management
from .blog_data_management import BlogDataManagement

logger = logging.getLogger(__name__)


class BlogGenerationFeature:
    """Blog Generation feature for Streamlit UI - API-based"""

    def __init__(self):
        self.api = blog_api
        self.data_management = BlogDataManagement(blog_api)

    # ----------------------------
    # INTERNAL HELPERS
    # ----------------------------
    def _linkify_sources(self, text: str) -> str:
        """Convert common source patterns into clickable markdown links.

        Supported patterns:
        - (Source: domain.com) -> (Source: [domain.com](https://domain.com))
        - Source: domain.com    -> (Source: [domain.com](https://domain.com)) at line end
        """
        try:
            md = text or ""

            # (Source: domain.com)
            def _paren_link(m):
                domain = m.group(1).strip().rstrip('.')
                url = domain if domain.startswith('http') else f'https://{domain}'
                return f'(Source: [{domain}]({url}))'

            md = re.sub(r"\(Source:\s*([a-zA-Z0-9_.-]+\.[a-zA-Z]{2,})(?:/[^)]*)?\)", _paren_link, md)

            # Standalone 'Source: domain.com' at end of line -> convert to same (in parens)
            def _line_link(m):
                prefix = m.group(1)
                domain = m.group(2).strip().rstrip('.')
                url = domain if domain.startswith('http') else f'https://{domain}'
                return f"{prefix}(Source: [{domain}]({url}))"

            md = re.sub(r"(?m)(^|\s)Source:\s*([a-zA-Z0-9_.-]+\.[a-zA-Z]{2,})(?:/\S*)?\.?$", _line_link, md)

            return md
        except Exception:
            return text

    def _normalize_headings(self, text: str) -> str:
        """Normalize markdown headings to avoid accidental link-like rendering.

        - Ensure a space after heading hashes
        - Ensure headings start on a new paragraph
        - Strip surrounding brackets in headings like: '## [Title]' -> '## Title'
        """
        try:
            md = text or ""
            # Space after hashes for headings
            md = re.sub(r'(?m)^(#{1,6})([^#\s])', r'\1 \2', md)
            # New paragraph before headings (except at start)
            md = re.sub(r'(?<!\n)(#{1,6}\s)', r'\n\n\1', md)
            # Strip brackets around heading text
            md = re.sub(r'(?m)^(#{1,6}\s*)\[(.+?)\]\s*$', r'\1\2', md)
            return md
        except Exception:
            return text

    def _prepare_stream_md(self, text: str) -> str:
        """Apply safe markdown sanitization and then linkify sources only."""
        # Note: Method name kept for backwards compatibility, but no longer related to streaming
        return self._linkify_sources(self._normalize_headings(text))

    # ----------------------------
    # MAIN RENDER METHOD
    # ----------------------------
    def render(self):
        st.title("📝 Blog Generation")
        st.markdown("Generate SEO-optimized blog posts with AI.")

        tab1, tab2 = st.tabs(["🚀 Generate Blog", "📊 Data Management"])
        with tab1:
            self.render_blog_generation()
        with tab2:
            self.data_management.render_data_management_tab()

    # ----------------------------
    # BLOG GENERATION FORM
    # ----------------------------
    def render_blog_generation(self):
        st.subheader("🚀 Generate New Blog Post")
        
        # Check authentication first
        if not st.session_state.get('authenticated', False):
            st.error("🔐 Please login to generate blog posts")
            return
        
        if not st.session_state.get('token'):
            st.error("🔐 Authentication token not found. Please login again.")
            return
            
        if not st.session_state.get('selected_organization'):
            st.error("🏢 Please select an organization to generate blog posts.")
            return

        with st.form("blog_generation_form"):
            col1, col2 = st.columns(2)
            with col1:
                topic = st.text_input("Blog Topic *", placeholder="e.g., The Future of AI")
                blog_type = st.selectbox("Blog Type", ["News", "Comparison"])
            with col2:
                length_min = st.number_input("Minimum Words", 300, 5000, 800)
                length_max = st.number_input("Maximum Words", 500, 10000, 1500)

            generate_images = st.checkbox("🖼️ Generate Images", value=True)

            submitted = st.form_submit_button("🚀 Start Generation", use_container_width=True)

            if submitted:
                if not topic:
                    st.error("Please enter a blog topic.")
                    return
                blog_data = {
                    "topic": topic,
                    "blog_type": blog_type,
                    "length_min": length_min,
                    "length_max": length_max,
                    "generate_images": generate_images,
                    "generate_image_prompts": generate_images,
                }
                st.session_state.blog_data = blog_data
                st.session_state.blog_generation_triggered = True
                st.rerun()

        # --- Blog output section ---
        st.divider()
        st.subheader("📝 Generated Blog")

        # Ensure TOC stays at the top by declaring it BEFORE content placeholder
        toc_title_placeholder = st.empty()
        toc_placeholder = st.empty()
        content_placeholder = st.empty()
        progress_placeholder = st.empty()

        if "blog_content" not in st.session_state:
            st.session_state.blog_content = {"text": ""}
        blog_content = st.session_state.blog_content

        if not blog_content["text"]:
            toc_title_placeholder.markdown("### 📋 Table of Contents")
            content_placeholder.info("Click **Start Generation** to begin.")
            progress_placeholder.info("Waiting for generation...")

        if blog_content["text"]:
            if st.button("🗑️ Clear Output"):
                st.session_state.blog_content = {"text": ""}
                st.rerun()

        # ---- Trigger blog generation ----
        if st.session_state.get("blog_generation_triggered", False):
            blog_data = st.session_state.get("blog_data", {})
            st.session_state.blog_generation_triggered = False

            # Reset blog content for new generation
            st.session_state.blog_content = {"text": ""}
            blog_content = st.session_state.blog_content

            # Generate blog via standard REST API call
            self.generate_blog_post_api(
                blog_data,
                content_placeholder,
                progress_placeholder,
                toc_placeholder,
                toc_title_placeholder,
            )

    # ----------------------------
    # API IMPLEMENTATION
    # ----------------------------
    def generate_blog_post_api(self, blog_data, content_placeholder, progress_placeholder, toc_placeholder, toc_title_placeholder=None):
        """Generate blog via REST API call."""
        status_placeholder = st.empty()
        blog_content = st.session_state.blog_content

        with st.spinner("⚡ Generating blog content..."):
            try:
                progress_placeholder.info("🔄 Sending request to API... This may take 10-20 minutes. Please wait...")
                
                # Generate blog via REST API
                # Note: Blog generation uses extended timeout (30 minutes) to handle long-running operations
                print(f"📤 [STREAMLIT] Sending blog generation request via REST API (timeout: 30 minutes)")
                response = self.api.generate_blog(**blog_data)
                
                if response and response.get("status") == "success":
                    print(f"✅ [STREAMLIT] Blog generation completed via API")
                    
                    # Extract content from response
                    raw_content = response.get("raw_content", "")
                    structured_content = response.get("content", {})
                    image_urls = response.get("image_urls", [])
                    research_sources = response.get("research_sources", [])
                    
                    # Update blog content
                    if raw_content:
                        blog_content["text"] = raw_content
                        
                        # Display TOC if available
                        if structured_content and isinstance(structured_content, dict):
                            sections = structured_content.get("sections", [])
                            if sections:
                                if toc_title_placeholder is not None:
                                    toc_title_placeholder.markdown("### 📋 Table of Contents")
                                toc_md = "\n".join([f"{i+1}. {s.get('title', '')}" for i, s in enumerate(sections) if isinstance(s, dict)])
                                if toc_md:
                                    toc_placeholder.markdown(toc_md)
                        
                        # Display content
                        content_placeholder.markdown(self._prepare_stream_md(blog_content["text"]))
                        
                        # Display images if available
                        if image_urls:
                            progress_placeholder.success(f"✅ **Blog generated with {len(image_urls)} images!**")
                        else:
                            progress_placeholder.success("✅ **Blog generated successfully!**")
                        
                        status_placeholder.success("✅ **Blog generation completed!**")
                        
                        # Store result in session state
                        st.session_state["blog_result"] = response
                        st.session_state["blog_generation_done"] = True
                        # Extract blog_id if available (might need to fetch from list)
                        blog_id_from_response = None
                        if "id" in response:
                            blog_id_from_response = response["id"]
                        elif "blog_id" in response:
                            blog_id_from_response = response["blog_id"]
                        
                        # Store blog_id as int in session state
                        if blog_id_from_response:
                            try:
                                blog_id_int = int(blog_id_from_response)
                                st.session_state["blog_id"] = blog_id_int
                                print(f"✅ [STREAMLIT] Stored blog_id={blog_id_int} in session state after blog generation")
                            except (ValueError, TypeError):
                                print(f"⚠️ [STREAMLIT] Could not convert blog_id to int: {blog_id_from_response}")
                                st.session_state["blog_id"] = blog_id_from_response
                    else:
                        error_msg = "Blog generated but no content received"
                        status_placeholder.error(f"❌ **Error**: {error_msg}")
                        st.session_state["blog_generation_error"] = error_msg
                else:
                    error_msg = response.get("error", "Unknown error") if response else "No response from server"
                    print(f"❌ [STREAMLIT] Error: {error_msg}")
                    status_placeholder.error(f"❌ **Error**: {error_msg}")
                    st.session_state["blog_generation_error"] = error_msg
                    
            except Exception as e:
                error_msg = f"Error generating blog: {str(e)}"
                print(f"❌ [STREAMLIT] Exception: {error_msg}")
                status_placeholder.error(f"❌ **Error**: {error_msg}")
                st.session_state["blog_generation_error"] = error_msg
        
        # Final update
        if blog_content["text"]:
            content_placeholder.markdown(self._prepare_stream_md(blog_content["text"]))
        
        if st.session_state.get("blog_generation_done"):
            if st.session_state.get("blog_result"):
                st.success("🎉 Blog generation completed successfully!")
        elif not st.session_state.get("blog_generation_error"):
            st.warning("⚠️ Blog generation was interrupted. Please try again.")
    


    # ----------------------------
    # DISPLAY METHODS
    # ----------------------------
    def display_generated_blog(self, blog_data: Dict[str, Any]):
        st.success("✅ Blog generated successfully!")
        MarkdownProcessor.display_with_metadata(
            blog_data,
            "📝 Generated Blog",
            [("images_count", "Images")],
            ["raw_content", "content", "sections"],
        )
        MarkdownProcessor.display_images(blog_data.get("image_urls", []))
        MarkdownProcessor.display_sources(blog_data.get("research_sources", []))
