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
        
        # Initialize persistent WebSocket connection ONCE per session
        # Store the manager in session state to survive reruns
        if 'blog_ws_manager' not in st.session_state:
            print("🚀 Initializing persistent WebSocket connection for blog generation...")
            # Only initialize if authenticated
            if st.session_state.get('authenticated', False) and st.session_state.get('token'):
                manager = self._initialize_websocket_manager()
                if manager:
                    st.session_state.blog_ws_manager = manager
                    st.session_state.blog_ws_initialized = True
                    print("✅ Blog WebSocket manager stored in session state")
        
        # Ensure we have a reference to the manager
        self.ws_manager = st.session_state.get('blog_ws_manager')

    # ----------------------------
    # INTERNAL HELPERS
    # ----------------------------
    def _initialize_websocket_manager(self):
        """Initialize WebSocket manager with authentication headers"""
        try:
            headers = self.api.client._get_auth_headers()
            print(f"🔑 Initializing blog WebSocket with headers: {list(headers.keys())}")
            manager = self.api.init_persistent_connection(headers)
            return manager
        except Exception as e:
            print(f"❌ Failed to initialize WebSocket manager: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _ensure_websocket_connection(self) -> bool:
        """Ensure WebSocket connection is active and running"""
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
            
            # Check if we have a manager in session state
            manager = st.session_state.get('blog_ws_manager')
            
            if not manager:
                print("🔄 No WebSocket manager found, creating new one...")
                manager = self._initialize_websocket_manager()
                if manager:
                    st.session_state.blog_ws_manager = manager
                    st.session_state.blog_ws_initialized = True
                    self.ws_manager = manager
                else:
                    return False
            
            # Check if manager is running
            if not manager.is_running:
                print("🔄 WebSocket manager not running, restarting...")
                manager.start()
                import time as time_module
                time_module.sleep(1.0)  # Wait for connection to establish
            
            print(f"✅ WebSocket connection ready - running: {manager.is_running}")
            return manager.is_running
            
        except Exception as e:
            print(f"⚠️ Failed to ensure WebSocket connection: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _cleanup_websocket_connection(self):
        """Clean up WebSocket connection when leaving the feature"""
        if 'blog_ws_manager' in st.session_state and st.session_state.blog_ws_manager:
            try:
                st.session_state.blog_ws_manager.stop()
                print("🔌 Blog WebSocket connection cleaned up")
            except Exception as e:
                print(f"⚠️ Error cleaning up WebSocket: {e}")
            finally:
                st.session_state.blog_ws_manager = None
                st.session_state.blog_ws_initialized = False

    def _handle_feature_switch(self):
        """Handle feature switching and cleanup WebSocket connections"""
        # Initialize current feature tracking
        if 'current_feature' not in st.session_state:
            st.session_state.current_feature = "📝 Blog Generation"
        
        # Get the currently selected feature from the sidebar
        current_selection = st.session_state.get('feature_selector', "📝 Blog Generation")
        
        # If we're switching away from Blog Generation, cleanup WebSocket
        if (st.session_state.current_feature == "📝 Blog Generation" and 
            current_selection != "📝 Blog Generation"):
            print("🔄 Switching away from Blog Generation - cleaning up WebSocket")
            self._cleanup_websocket_connection()
            # Reset the initialization flag so it can be re-established if user comes back
            st.session_state.blog_ws_initialized = False
        
        # Update current feature
        st.session_state.current_feature = current_selection

    # ----------------------------
    # MAIN RENDER METHOD
    # ----------------------------
    def render(self):
        # Check if we're switching away from Blog Generation feature
        self._handle_feature_switch()
        
        # Ensure WebSocket connection is ready (will check and reconnect if needed)
        if st.session_state.get('authenticated', False) and st.session_state.get('token'):
            manager = st.session_state.get('blog_ws_manager')
            if not manager or not manager.is_running:
                print("🔄 WebSocket needs initialization or restart")
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

        content_placeholder = st.empty()
        progress_placeholder = st.empty()
        toc_placeholder = st.empty()

        if "live_md" not in st.session_state:
            st.session_state.live_md = {"text": ""}
        live_md = st.session_state.live_md

        if not live_md["text"]:
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
            self.generate_blog_post_stream(blog_data, content_placeholder, progress_placeholder, toc_placeholder)

    # ----------------------------
    # STREAMING IMPLEMENTATION
    # ----------------------------
    def generate_blog_post_stream(self, blog_data, content_placeholder, progress_placeholder, toc_placeholder):
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

        # Send blog generation request via persistent WebSocket
        print(f"📤 [STREAMLIT] Sending blog generation request via WebSocket")
        message_id = self.api.generate_blog_stream_websocket(
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
                                toc_md = "\n".join([f"{i+1}. {s}" for i, s in enumerate(toc)])
                                toc_placeholder.markdown(f"**📋 Table of Contents:**\n\n{toc_md}")
                                
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
                                    content_placeholder.markdown(live_md["text"] + " ▌")
                                    last_update_time = current_time
                                    
                        elif t == "image":
                            section = evt.get("section", "")
                            url = evt.get("image_url", "")
                            if url:
                                live_md["text"] += f"\n\n![Section Image]({url})\n\n"
                                content_placeholder.markdown(live_md["text"])
                                progress_placeholder.info(f"🖼️ **Image added** for section: {section}")
                                
                        elif t == "section_complete":
                            section = evt.get("section", "")
                            progress_placeholder.success(f"✅ **Completed section**: {section}")
                            content_placeholder.markdown(live_md["text"])
                            
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
                        # Check if WebSocket is still connected
                        manager = st.session_state.get('blog_ws_manager')
                        if manager and not manager.is_running:
                            error_msg = "WebSocket connection lost"
                            print(f"🔌 [STREAMLIT] {error_msg}")
                            st.error(f"❌ {error_msg}. Please try again.")
                            st.session_state["blog_stream_error"] = "Connection lost"
                            break
                    
                    # Update display periodically even without new tokens
                    if live_md["text"] and (current_time - last_update_time) >= 1.0:
                        content_placeholder.markdown(live_md["text"] + " ▌")
                        last_update_time = current_time
                
                # Check WebSocket connection health periodically
                if time.time() % 5 < 0.5:  # Every ~5 seconds
                    manager = st.session_state.get('blog_ws_manager')
                    if manager:
                        print(f"💓 [STREAMLIT] WebSocket health check - running: {manager.is_running}, callbacks: {len(manager.response_callbacks)}")
                    else:
                        print(f"⚠️ [STREAMLIT] No WebSocket manager found in session state")

        # Final update without cursor
        if live_md["text"]:
            content_placeholder.markdown(live_md["text"])
        
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
