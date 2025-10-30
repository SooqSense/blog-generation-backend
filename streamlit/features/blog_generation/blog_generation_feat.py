import streamlit as st
import json
import re
import time
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional

# Import API client
from api_client import blog_api
# Import markdown processor
from base.markdown_processor import MarkdownProcessor
# Import data management
from .blog_data_management import BlogDataManagement


class BlogGenerationFeature:
    """Blog Generation feature for Streamlit UI - with real-time streaming"""

    def __init__(self):
        self.api = blog_api
        self.data_management = BlogDataManagement(blog_api)
        
        # Use the unified WebSocket connection from chatbot_api
        # Import chatbot_api to access the unified WebSocket manager
        from api_client import chatbot_api
        self.unified_api = chatbot_api
        
        # Initialize unified WebSocket connection ONCE per session
        # Store the manager in session state to survive reruns
        if 'ws_manager' not in st.session_state:
            print("🚀 Initializing unified WebSocket connection...")
            # Only initialize if authenticated
            if st.session_state.get('authenticated', False) and st.session_state.get('token'):
                manager = self.unified_api.init_persistent_connection()
                if manager:
                    st.session_state.ws_manager = manager
                    st.session_state.ws_initialized = True
                    print("✅ Unified WebSocket manager stored in session state")
        
        # Ensure we have a reference to the unified manager
        self.ws_manager = st.session_state.get('ws_manager')

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
        return self._linkify_sources(self._normalize_headings(text))
    def _ensure_websocket_connection(self) -> bool:
        """Ensure unified WebSocket connection is active and running"""
        try:
            # Validate authentication first
            if not st.session_state.get('authenticated', False):
                print("❌ Not authenticated - cannot establish WebSocket connection")
                return False
            
            if not st.session_state.get('token'):
                print("❌ No authentication token - cannot establish WebSocket connection")
                return False
            
            if not st.session_state.get('selected_organization'):
                print("❌ No organization selected - cannot establish WebSocket connection")
                return False
            
            # Check if we have the unified manager in session state
            manager = st.session_state.get('ws_manager')
            
            if not manager:
                print("🔄 No unified WebSocket manager found, creating new one...")
                manager = self.unified_api.init_persistent_connection()
                if manager:
                    st.session_state.ws_manager = manager
                    st.session_state.ws_initialized = True
                    self.ws_manager = manager
                else:
                    return False
            
            # Check if manager is running
            if not manager.is_running:
                print("🔄 Unified WebSocket manager not running, restarting...")
                manager.start()
                import time as time_module
                time_module.sleep(1.0)  # Wait for connection to establish
            
            print(f"✅ Unified WebSocket connection ready - running: {manager.is_running}")
            return manager.is_running
            
        except Exception as e:
            print(f"⚠️ Failed to ensure unified WebSocket connection: {e}")
            import traceback
            traceback.print_exc()
            return False

    # ----------------------------
    # MAIN RENDER METHOD
    # ----------------------------
    def render(self):
        # Ensure unified WebSocket connection is ready (will check and reconnect if needed)
        if st.session_state.get('authenticated', False) and st.session_state.get('token'):
            manager = st.session_state.get('ws_manager')
            if not manager or not manager.is_running:
                print("🔄 Unified WebSocket needs initialization or restart")
                self._ensure_websocket_connection()
        
        st.title("📝 Blog Generation")
        st.markdown("Generate SEO-optimized blog posts with real-time AI streaming.")

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
            # Streaming is always enabled - no checkbox needed

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

        # --- Streaming display section ---
        st.divider()
        st.subheader("📡 Live Blog Generation")

        # Ensure TOC stays at the top by declaring it BEFORE content placeholder
        toc_title_placeholder = st.empty()
        toc_placeholder = st.empty()
        content_placeholder = st.empty()
        progress_placeholder = st.empty()

        if "live_md" not in st.session_state:
            st.session_state.live_md = {"text": ""}
        live_md = st.session_state.live_md

        if not live_md["text"]:
            toc_title_placeholder.markdown("### 📋 Table of Contents")
            content_placeholder.info("Click **Start Generation** to begin.")
            progress_placeholder.info("Waiting for generation...")

        if live_md["text"]:
            if st.button("🗑️ Clear Output"):
                st.session_state.live_md = {"text": ""}
                st.rerun()

        # ---- Trigger streaming ----
        if st.session_state.get("blog_generation_triggered", False):
            blog_data = st.session_state.get("blog_data", {})
            use_streaming = st.session_state.get("use_streaming", True)
            st.session_state.blog_generation_triggered = False

            # Reset live markdown for new generation
            st.session_state.live_md = {"text": ""}
            live_md = st.session_state.live_md

            # Always use streaming - no fallback
            self.generate_blog_post_stream(
                blog_data,
                content_placeholder,
                progress_placeholder,
                toc_placeholder,
                toc_title_placeholder,
            )

    # ----------------------------
    # STREAMING IMPLEMENTATION
    # ----------------------------
    def generate_blog_post_stream(self, blog_data, content_placeholder, progress_placeholder, toc_placeholder, toc_title_placeholder=None):
        """Generate blog via WebSocket stream using queue-based messaging."""
        import queue
        
        status_placeholder = st.empty()
        live_md = st.session_state.live_md

        st.session_state["blog_stream_done"] = False
        st.session_state["blog_stream_error"] = None

        # Thread-safe queue for receiving events
        event_queue = queue.Queue()
        
        # ----------------- Event Handlers (put events in queue) -----------------
        def queue_event(evt: Dict[str, Any]):
            """Queue event for processing in main thread"""
            event_queue.put(('event', evt))

        def queue_error(error):
            """Queue error for processing in main thread"""
            event_queue.put(('error', str(error)))

        def queue_complete(result):
            """Queue completion for processing in main thread"""
            event_queue.put(('complete', result))

        # Ensure WebSocket connection
        if not self._ensure_websocket_connection():
            st.error("❌ Failed to establish WebSocket connection")
            return

        # Send blog generation request via unified WebSocket
        print(f"📤 [STREAMLIT] Sending blog generation request via unified WebSocket")
        message_id = self.unified_api.send_blog_generation_request(
            blog_data=blog_data,
            on_event=queue_event,
            on_complete=queue_complete,
            on_error=queue_error,
        )
        
        if not message_id:
            st.error("❌ Failed to send blog generation request")
            return
        
        print(f"✅ [STREAMLIT] Request sent with message_id: {message_id}")

        # ----------------- UI Update Loop (poll queue and update UI) -----------------
        max_wait_time = 1200  # 20 minutes timeout
        start_time = time.time()
        last_update_time = time.time()
        last_activity_time = time.time()  # Track last event received
        update_interval = 0.1  # Update UI every 100ms
        activity_timeout = 120  # 2 minutes without activity = timeout
        
        print(f"🎬 [STREAMLIT] Starting UI update loop for message_id: {message_id}")
        
        with st.spinner("⚡ Generating blog content..."):
            while not st.session_state.get("blog_stream_done", False):
                try:
                    # Poll queue for events
                    msg_type, msg_data = event_queue.get(timeout=0.5)
                    
                    # Update last activity time
                    last_activity_time = time.time()
                    
                    if msg_type == 'event':
                        evt = msg_data
                        t = evt.get("type")
                        print(f"📨 [STREAMLIT] Processing event: {t}")

                        if t == "status":
                            stage = evt.get("stage", "")
                            message = evt.get("message", "")
                            status_placeholder.info(f"**{stage.title()}**: {message}")
                            
                        elif t == "toc":
                            toc = evt.get("sections", [])
                            if toc:
                                # Keep TOC fixed at the top
                                if toc_title_placeholder is not None:
                                    toc_title_placeholder.markdown("### 📋 Table of Contents")
                                # Strip surrounding brackets in TOC labels to avoid link-like rendering
                                def _clean_label(s: str) -> str:
                                    try:
                                        s2 = s.strip()
                                        m = re.match(r'^\[(.+?)\]$', s2)
                                        return m.group(1) if m else s2
                                    except Exception:
                                        return s
                                toc_md = "\n".join([f"{i+1}. {_clean_label(s)}" for i, s in enumerate(toc)])
                                toc_placeholder.markdown(toc_md)
                                
                        elif t == "section_start":
                            section = evt.get("section", "")
                            index = evt.get("index", 0)
                            progress_placeholder.info(f"📝 **Section {index}**: {section}")
                            
                        elif t == "section_token":
                            token = evt.get("content", "")
                            if token:
                                live_md["text"] += token
                                # Batch updates for smoother streaming
                                current_time = time.time()
                                if (current_time - last_update_time) >= update_interval:
                                    content_placeholder.markdown(self._prepare_stream_md(live_md["text"]) + " ▌")
                                    last_update_time = current_time
                                    
                        elif t == "image":
                            section = evt.get("section", "")
                            url = evt.get("image_url", "")
                            if url:
                                live_md["text"] += f"\n\n![Section Image]({url})\n\n"
                                content_placeholder.markdown(self._prepare_stream_md(live_md["text"]))
                                progress_placeholder.info(f"🖼️ **Image added** for section: {section}")
                                
                        elif t == "section_complete":
                            section = evt.get("section", "")
                            progress_placeholder.success(f"✅ **Completed section**: {section}")
                            content_placeholder.markdown(self._prepare_stream_md(live_md["text"]))
                            
                    elif msg_type == 'complete':
                        print("🎉 [STREAMLIT] Blog generation completed!")
                        st.session_state["blog_stream_done"] = True
                        st.session_state["blog_result"] = msg_data
                        status_placeholder.success("✅ **Blog generation completed!**")
                        break
                        
                    elif msg_type == 'error':
                        print(f"❌ [STREAMLIT] Error: {msg_data}")
                        st.session_state["blog_stream_error"] = msg_data
                        status_placeholder.error(f"❌ **Error**: {msg_data}")
                        break
                        
                except queue.Empty:
                    # No messages in queue
                    current_time = time.time()
                    
                    # Check absolute timeout
                    if current_time - start_time > max_wait_time:
                        error_msg = "Blog generation timed out after 20 minutes"
                        print(f"⏰ [STREAMLIT] {error_msg}")
                        st.error(f"⏰ {error_msg}. Please try again.")
                        st.session_state["blog_stream_error"] = "Timeout"
                        break
                    
                    # Check activity timeout (no events received)
                    if current_time - last_activity_time > activity_timeout:
                        # Check if unified WebSocket is still connected
                        manager = st.session_state.get('ws_manager')
                        if manager and not manager.is_running:
                            error_msg = "WebSocket connection lost"
                            print(f"🔌 [STREAMLIT] {error_msg}")
                            st.error(f"❌ {error_msg}. Please try again.")
                            st.session_state["blog_stream_error"] = "Connection lost"
                            break
                    
                    # Update display periodically even without new tokens
                    if live_md["text"] and (current_time - last_update_time) >= 1.0:
                        content_placeholder.markdown(self._prepare_stream_md(live_md["text"]) + " ▌")
                        last_update_time = current_time
                
                # Check unified WebSocket connection health periodically
                if time.time() % 5 < 0.5:  # Every ~5 seconds
                    manager = st.session_state.get('ws_manager')
                    if manager:
                        print(f"💓 [STREAMLIT] Unified WebSocket health check - running: {manager.is_running}, callbacks: {len(manager.response_callbacks)}")
                    else:
                        print(f"⚠️ [STREAMLIT] No unified WebSocket manager found in session state")

        # Final update without cursor
        if live_md["text"]:
            content_placeholder.markdown(self._prepare_stream_md(live_md["text"]))
        
        if st.session_state.get("blog_stream_done"):
            if st.session_state.get("blog_result"):
                st.success("🎉 Blog generation completed successfully!")
        elif not st.session_state.get("blog_stream_error"):
            st.warning("⚠️ Blog generation was interrupted. Please try again.")

    # ----------------------------
    # DISPLAY METHODS
    # ----------------------------

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
