import streamlit as st
import json
import logging
from typing import Dict, Any, Optional, List

# Import API client
from api_client import blog_api

logger = logging.getLogger(__name__)


class SEOOptimizationFeature:
    """SEO Optimization feature for Streamlit UI - Separate component for generating SEO HTML"""

    def __init__(self):
        self.api = blog_api

    def _get_theme(self) -> str:
        """Detect current Streamlit theme (light or dark)"""
        try:
            # Try to get theme from Streamlit config
            import streamlit as st
            # Streamlit doesn't expose theme directly, so we check CSS variables
            # Default to light mode if we can't detect
            return "light"  # We'll use CSS media queries to handle both
        except:
            return "light"

    def _wrap_html_with_theme(self, html_content: str) -> str:
        """Wrap HTML content with theme-aware CSS that adapts to dark/light mode"""
        
        # Extract body content if it's a full HTML document
        body_content = html_content
        
        try:
            from bs4 import BeautifulSoup
            # Try to parse and extract body content
            soup = BeautifulSoup(html_content, 'html.parser')
            body = soup.find('body')
            if body:
                body_content = str(body)
            else:
                # If no body tag, check if it's already a full HTML document
                if '<html' in html_content.lower() or '<!doctype' in html_content.lower():
                    # It's a full document, wrap the whole thing
                    body_content = html_content
                else:
                    # It's just body content
                    body_content = html_content
        except ImportError:
            # BeautifulSoup not available, use simple string matching
            if '<body' in html_content.lower():
                # Try to extract body tag manually
                import re
                body_match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.DOTALL | re.IGNORECASE)
                if body_match:
                    body_content = f"<body>{body_match.group(1)}</body>"
        except Exception:
            # Any other error, use content as-is
            pass
        
        # Theme-aware CSS with JavaScript detection for Streamlit theme
        theme_css = """
        <style>
            /* Base styles that work in both themes */
            * {
                box-sizing: border-box;
            }
            
            /* CSS Variables for theme colors */
            :root {
                --text-color: #262730;
                --bg-color: #ffffff;
                --heading-color: #262730;
                --code-bg: #f0f2f6;
                --code-color: #262730;
                --pre-bg: #f0f2f6;
                --pre-color: #262730;
                --blockquote-border: #e2e8f0;
                --blockquote-color: #4a5568;
                --link-color: #1f77b4;
                --link-hover: #2c5aa0;
                --table-border: #e2e8f0;
                --th-bg: #f7fafc;
            }
            
            /* Dark theme variables */
            .dark-theme {
                --text-color: #fafafa;
                --bg-color: #0e1117;
                --heading-color: #fafafa;
                --code-bg: #1e1e1e;
                --code-color: #d4d4d4;
                --pre-bg: #1e1e1e;
                --pre-color: #d4d4d4;
                --blockquote-border: #4a5568;
                --blockquote-color: #cbd5e0;
                --link-color: #60a5fa;
                --link-hover: #93c5fd;
                --table-border: #4a5568;
                --th-bg: #1a202c;
            }
            
            /* Light mode (default) */
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                line-height: 1.6;
                color: var(--text-color);
                background-color: var(--bg-color);
                padding: 20px;
                margin: 0;
                transition: background-color 0.3s ease, color 0.3s ease;
            }
            
            h1, h2, h3, h4, h5, h6 {
                color: var(--heading-color);
            }
            
            p, li, td, th {
                color: var(--text-color);
            }
            
            code {
                background-color: var(--code-bg);
                color: var(--code-color);
            }
            
            pre {
                background-color: var(--pre-bg);
                color: var(--pre-color);
            }
            
            blockquote {
                border-left-color: var(--blockquote-border);
                color: var(--blockquote-color);
            }
            
            a {
                color: var(--link-color);
            }
            
            a:hover {
                color: var(--link-hover);
            }
            
            table {
                border-color: var(--table-border);
            }
            
            th, td {
                border-color: var(--table-border);
            }
            
            th {
                background-color: var(--th-bg);
            }
            
            /* Dark mode support using prefers-color-scheme as fallback */
            @media (prefers-color-scheme: dark) {
                :root:not(.light-theme) {
                    --text-color: #fafafa;
                    --bg-color: #0e1117;
                    --heading-color: #fafafa;
                    --code-bg: #1e1e1e;
                    --code-color: #d4d4d4;
                    --pre-bg: #1e1e1e;
                    --pre-color: #d4d4d4;
                    --blockquote-border: #4a5568;
                    --blockquote-color: #cbd5e0;
                    --link-color: #60a5fa;
                    --link-hover: #93c5fd;
                    --table-border: #4a5568;
                    --th-bg: #1a202c;
                }
            }
            
            /* Ensure images are responsive */
            img {
                max-width: 100%;
                height: auto;
            }
            
            /* Style headings */
            h1, h2, h3, h4, h5, h6 {
                margin-top: 1.5em;
                margin-bottom: 0.5em;
                font-weight: 600;
            }
            
            /* Style paragraphs */
            p {
                margin-bottom: 1em;
            }
            
            /* Style lists */
            ul, ol {
                margin-bottom: 1em;
                padding-left: 2em;
            }
            
            /* Style code blocks */
            code {
                padding: 2px 6px;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
                font-size: 0.9em;
            }
            
            pre {
                padding: 1em;
                border-radius: 5px;
                overflow-x: auto;
            }
            
            pre code {
                padding: 0;
            }
            
            /* Style blockquotes */
            blockquote {
                border-left: 4px solid;
                padding-left: 1em;
                margin-left: 0;
                font-style: italic;
            }
            
            /* Style tables */
            table {
                border-collapse: collapse;
                width: 100%;
                margin: 1em 0;
            }
            
            th, td {
                padding: 0.75em;
                text-align: left;
                border-bottom: 1px solid;
            }
            
            th {
                font-weight: 600;
            }
        </style>
        """
        
        # JavaScript to detect Streamlit theme from parent window
        theme_js = """
        <script>
            (function() {
                function detectTheme() {
                    try {
                        // Try to access parent window to detect Streamlit theme
                        if (window.parent && window.parent.document) {
                            const parentDoc = window.parent.document;
                            const streamlitBody = parentDoc.body;
                            
                            // Check for Streamlit's theme classes or data attributes
                            if (streamlitBody) {
                                // Look for Streamlit's theme indicator
                                const computedStyle = window.parent.getComputedStyle(streamlitBody);
                                const bgColor = computedStyle.backgroundColor;
                                
                                // Check if background is dark (Streamlit dark theme)
                                if (bgColor) {
                                    const rgb = bgColor.match(/\\d+/g);
                                    if (rgb && rgb.length >= 3) {
                                        const brightness = (parseInt(rgb[0]) + parseInt(rgb[1]) + parseInt(rgb[2])) / 3;
                                        if (brightness < 128) {
                                            document.documentElement.classList.add('dark-theme');
                                            return;
                                        }
                                    }
                                }
                                
                                // Alternative: check for data-theme attribute
                                const themeAttr = streamlitBody.getAttribute('data-theme') || 
                                                 streamlitBody.getAttribute('theme');
                                if (themeAttr === 'dark' || streamlitBody.classList.contains('dark')) {
                                    document.documentElement.classList.add('dark-theme');
                                    return;
                                }
                            }
                        }
                    } catch (e) {
                        // Cross-origin or other error, use system preference
                        console.log('Theme detection error:', e);
                    }
                    
                    // Fallback to system preference
                    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
                        document.documentElement.classList.add('dark-theme');
                    }
                }
                
                // Run on load
                if (document.readyState === 'loading') {
                    document.addEventListener('DOMContentLoaded', detectTheme);
                } else {
                    detectTheme();
                }
                
                // Also listen for theme changes
                if (window.matchMedia) {
                    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', detectTheme);
                }
            })();
        </script>
        """
        
        # Wrap content with theme-aware CSS and JavaScript
        wrapped_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            {theme_css}
        </head>
        {body_content}
        {theme_js}
        </html>
        """
        
        return wrapped_html

    def render(self):
        """Render the SEO optimization interface"""
        st.title("🔍 SEO Optimization")
        st.markdown("Generate SEO-optimized HTML content for your blog posts.")

        # Check authentication first
        if not st.session_state.get('authenticated', False):
            st.error("🔐 Please login to generate SEO HTML")
            return

        if not st.session_state.get('token'):
            st.error("🔐 Authentication token not found. Please login again.")
            return

        if not st.session_state.get('selected_organization'):
            st.error("🏢 Please select an organization to generate SEO HTML.")
            return

        # Blog selection section
        st.subheader("📝 Select Blog")
        self._render_blog_selection()
        
        st.divider()
        
        # SEO generation section
        st.subheader("🔍 Generate SEO HTML")
        self._render_seo_generation()

    def _render_blog_selection(self):
        """Render blog selection dropdown"""
        try:
            # Fetch blogs from API
            with st.spinner("Loading blogs..."):
                blogs_response = self.api.list_blogs()

            if not blogs_response or not blogs_response.get("success"):
                st.error("❌ Failed to load blogs. Please try again.")
                return

            blogs = blogs_response.get("data", [])
            if not blogs:
                st.info("📝 No blogs found. Please generate a blog first.")
                return

            # Create dropdown options
            blog_options = {}
            for blog in blogs:
                blog_id = blog.get("id")
                topic = blog.get("topic", "Untitled")
                created_at = blog.get("created_at", "")
                seo_optimized = blog.get("seo_optimized", False)
                
                # Format display text
                status_icon = "✅" if seo_optimized else "⏳"
                display_text = f"{status_icon} {topic}"
                if created_at:
                    try:
                        from datetime import datetime
                        # Parse ISO format datetime
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        date_str = dt.strftime("%Y-%m-%d")
                        display_text += f" ({date_str})"
                    except:
                        pass
                
                blog_options[display_text] = blog_id

            # Blog selection dropdown
            selected_display = st.selectbox(
                "Choose a blog to optimize:",
                options=list(blog_options.keys()),
                key="seo_blog_selection",
                help="Select a blog post to generate SEO-optimized HTML"
            )

            if selected_display:
                selected_blog_id = blog_options[selected_display]
                st.session_state["selected_seo_blog_id"] = selected_blog_id
                
                # Show blog details in a cleaner format
                selected_blog = next((b for b in blogs if b.get("id") == selected_blog_id), None)
                if selected_blog:
                    # Display blog info in columns
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Topic", selected_blog.get('topic', 'N/A'))
                    with col2:
                        seo_status = "✅ Optimized" if selected_blog.get('seo_optimized') else "⏳ Not Optimized"
                        st.metric("SEO Status", seo_status)
                    with col3:
                        image_count = len(selected_blog.get('image_urls', [])) if selected_blog.get('image_urls') else 0
                        st.metric("Images", image_count)
                    
                    # Show creation date if available
                    if selected_blog.get('created_at'):
                        try:
                            from datetime import datetime
                            dt = datetime.fromisoformat(selected_blog.get('created_at').replace('Z', '+00:00'))
                            date_str = dt.strftime("%B %d, %Y at %I:%M %p")
                            st.caption(f"📅 Created: {date_str}")
                        except:
                            st.caption(f"📅 Created: {selected_blog.get('created_at', 'N/A')}")

        except Exception as e:
            logger.error(f"Error loading blogs: {e}", exc_info=True)
            st.error(f"❌ Error loading blogs: {str(e)}")

    def _render_seo_generation(self):
        """Render SEO generation interface"""
        selected_blog_id = st.session_state.get("selected_seo_blog_id")

        if not selected_blog_id:
            st.info("👈 Please select a blog from the dropdown above to generate SEO HTML.")
            return

        # Check if SEO already generated
        seo_result = st.session_state.get("seo_result")
        seo_in_progress = st.session_state.get("seo_generation_in_progress", False)

        # SEO Generation Button Section
        button_container = st.container()
        with button_container:
            if seo_in_progress:
                st.button(
                    "🔄 Generating SEO HTML...",
                    disabled=True,
                    use_container_width=True,
                    type="primary"
                )
                st.info("⏳ SEO optimization in progress... This may take 5-10 minutes. Please wait...")
            elif seo_result and seo_result.get("status") == "success" and seo_result.get("blog_id") == selected_blog_id:
                st.button(
                    "✅ SEO HTML Generated",
                    disabled=True,
                    use_container_width=True,
                    type="secondary"
                )
            else:
                # Generate SEO button
                button_key = f"generate_seo_button_{selected_blog_id}"
                trigger_key = f"seo_trigger_{selected_blog_id}"

                # Check if button was clicked
                button_clicked = st.button(
                    "🚀 Generate SEO-Optimized HTML",
                    use_container_width=True,
                    type="primary",
                    key=button_key
                )

                # If button clicked, set trigger in session state
                if button_clicked:
                    logger.info(f"🔍 SEO button clicked for blog_id: {selected_blog_id}")
                    st.session_state[trigger_key] = True
                    st.rerun()

                # Check for trigger in session state (handles rerun after button click)
                if st.session_state.get(trigger_key, False):
                    logger.info(f"🚀 SEO trigger detected for blog_id: {selected_blog_id}")
                    # Clear trigger
                    st.session_state[trigger_key] = False

                    # Validate blog_id
                    if not selected_blog_id:
                        st.error("❌ Blog ID is missing. Cannot generate SEO HTML.")
                        return

                    # Set in-progress state immediately
                    st.session_state["seo_generation_in_progress"] = True
                    st.session_state["seo_result"] = None

                    # Call the generation function directly
                    try:
                        self._generate_seo_html(selected_blog_id)
                    except Exception as e:
                        logger.error(f"❌ Exception in _generate_seo_html: {str(e)}", exc_info=True)
                        st.error(f"❌ Error: {str(e)}")
                        st.session_state["seo_generation_in_progress"] = False
        
        # Display SEO Results if available
        if seo_result and seo_result.get("status") == "success" and seo_result.get("blog_id") == selected_blog_id:
            st.divider()
            self._display_seo_results(seo_result)

    def _generate_seo_html(self, blog_id: int):
        """Generate SEO HTML for a blog post."""
        logger.info(f"🚀 Starting SEO generation for blog_id: {blog_id}")

        # Show initial status
        status_placeholder = st.empty()
        status_placeholder.info("🔄 Initializing SEO optimization...")

        # Use spinner for long-running operation
        try:
            with st.spinner("🔍 Optimizing content for SEO... This may take 5-10 minutes. Please wait..."):
                logger.info(f"📡 Calling SEO API for blog_id: {blog_id}")
                status_placeholder.info("📡 Connecting to SEO API...")

                # Make the API call
                response = self.api.generate_seo_html(blog_id)
                logger.info(f"📥 Received SEO API response: {response is not None}")

                if response and response.get("status") == "success":
                    logger.info(f"✅ SEO generation successful for blog_id: {blog_id}")
                    st.session_state["seo_result"] = response
                    st.session_state["seo_generation_done"] = True
                    st.session_state["seo_generation_in_progress"] = False
                    status_placeholder.success("✅ SEO optimization completed successfully!")
                    # Rerun to show results
                    st.rerun()
                else:
                    error_msg = response.get("error", "Unknown error") if response else "No response from server"
                    logger.error(f"❌ SEO generation failed: {error_msg}")
                    status_placeholder.error(f"❌ SEO optimization failed: {error_msg}")
                    st.session_state["seo_generation_in_progress"] = False
                    st.session_state["seo_generation_error"] = error_msg

        except Exception as e:
            error_msg = f"Error generating SEO HTML: {str(e)}"
            logger.error(f"❌ SEO generation exception: {error_msg}", exc_info=True)
            status_placeholder.error(f"❌ {error_msg}")
            st.session_state["seo_generation_in_progress"] = False
            st.session_state["seo_generation_error"] = error_msg

    def _display_seo_results(self, seo_result: Dict[str, Any]):
        """Display SEO optimization results."""
        st.success("✅ SEO optimization completed!")

        # Create tabs for different views
        tab1, tab2, tab3 = st.tabs([
            "📄 HTML Preview",
            "📊 SEO Metadata",
            "🔗 Structured Data"
        ])

        with tab1:
            st.subheader("HTML Content Preview")

            full_html = seo_result.get("full_html", "")
            html_content = seo_result.get("html_content", "")

            if full_html or html_content:
                # Get theme-aware HTML wrapper
                content_to_display = full_html if full_html else html_content
                theme_aware_html = self._wrap_html_with_theme(content_to_display)
                
                # Display HTML using streamlit's HTML component with theme support
                st.components.v1.html(theme_aware_html, height=600, scrolling=True)

                # Download button for HTML (use original full_html if available)
                if full_html:
                    st.download_button(
                        label="📄 Download HTML",
                        data=full_html,
                        file_name=f"blog_seo_{seo_result.get('blog_id', 'unknown')}.html",
                        mime="text/html",
                        key="download_seo_html"
                    )
            else:
                st.warning("No HTML content available")

            # HTML Validation Results
            html_validation = seo_result.get("html_validation", {})
            if html_validation:
                with st.expander("🔍 HTML Validation Results"):
                    st.json(html_validation)

        with tab2:
            st.subheader("SEO Metadata")

            seo_metadata = seo_result.get("seo_metadata", {})
            social_metadata = seo_result.get("social_metadata", {})

            if seo_metadata:
                # Basic SEO
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("SEO Score", f"{seo_result.get('seo_score', 0)}/100")
                    st.text_input("SEO Title", seo_metadata.get("seo_title", ""), disabled=True)
                    st.text_area(
                        "Meta Description",
                        seo_metadata.get("meta_description", ""),
                        height=100,
                        disabled=True
                    )

                with col2:
                    st.metric("Reading Time", f"{seo_metadata.get('reading_time_minutes', 0)} min")
                    st.metric("Word Count", f"{seo_metadata.get('word_count', 0):,}")
                    st.text_input("Slug", seo_metadata.get("slug", ""), disabled=True)
                    st.text_input("Canonical URL", seo_metadata.get("canonical_url", ""), disabled=True)

                # Keywords
                keywords = seo_metadata.get("keywords", [])
                if keywords:
                    st.subheader("Keywords")
                    st.write(", ".join(keywords))

                # Social Metadata
                if social_metadata:
                    st.subheader("Social Media Metadata")
                    st.json(social_metadata)

                # Download metadata JSON
                metadata_json = json.dumps({
                    "seo_metadata": seo_metadata,
                    "social_metadata": social_metadata,
                }, indent=2)

                st.download_button(
                    label="📋 Download Metadata JSON",
                    data=metadata_json,
                    file_name=f"seo_metadata_{seo_result.get('blog_id', 'unknown')}.json",
                    mime="application/json",
                    key="download_seo_metadata"
                )
            else:
                st.warning("No SEO metadata available")

        with tab3:
            st.subheader("Structured Data (JSON-LD)")

            structured_data = seo_result.get("structured_data", {})

            if structured_data:
                # Article Schema
                if structured_data.get("article_schema"):
                    st.markdown("### 📄 Article Schema")
                    st.json(structured_data["article_schema"])

                # Breadcrumb Schema
                if structured_data.get("breadcrumb_schema"):
                    st.markdown("### 🍞 Breadcrumb Schema")
                    st.json(structured_data["breadcrumb_schema"])

                # Organization Schema
                if structured_data.get("organization_schema"):
                    st.markdown("### 🏢 Organization Schema")
                    st.json(structured_data["organization_schema"])

                # Website Schema
                if structured_data.get("website_schema"):
                    st.markdown("### 🌐 Website Schema")
                    st.json(structured_data["website_schema"])

                # Download structured data JSON
                structured_json = json.dumps(structured_data, indent=2)

                st.download_button(
                    label="📋 Download Structured Data JSON",
                    data=structured_json,
                    file_name=f"structured_data_{seo_result.get('blog_id', 'unknown')}.json",
                    mime="application/json",
                    key="download_structured_data"
                )
            else:
                st.warning("No structured data available")

