import streamlit as st
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

# Import API client
from api_client import chatbot_api
# Import config for endpoints
from base.config import get_api_endpoint

class ChatbotFeature:
    """AI Chatbot feature for Streamlit UI - API-based"""
    
    def __init__(self):
        self.api = chatbot_api
        
        # Initialize persistent WebSocket connection ONCE per session
        # Store the manager in session state to survive reruns
        if 'ws_manager' not in st.session_state:
            print("🚀 Initializing persistent WebSocket connection...")
            manager = self.api.init_persistent_connection()
            st.session_state.ws_manager = manager
            st.session_state.ws_initialized = True
            print("✅ WebSocket manager stored in session state")
        
        # Ensure we have a reference to the manager
        self.ws_manager = st.session_state.ws_manager
    
    def render(self):
        """Main render method"""
        # Initialize session state for chat
        if "chat_messages" not in st.session_state:
            st.session_state.chat_messages = []
        
        if "session_id" not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())
        
        # Track if we're currently processing to prevent duplicate requests
        if "is_processing" not in st.session_state:
            st.session_state.is_processing = False
        
        # Render chat interface directly without tabs
        self.render_chat_interface()
    
    def render_chat_interface(self):
        """Render simple chat interface"""
        st.title("🤖 AI Chatbot")
        st.markdown("Chat with AI about your uploaded documents")
        
        # Display chat messages
        self.display_chat_messages()
        
        # Simple action buttons
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🗑️ Clear Chat", use_container_width=True):
                st.session_state.chat_messages = []
                # Clear processed queries to allow reprocessing
                if 'processed_queries' in st.session_state:
                    st.session_state.processed_queries.clear()
                # Don't use st.rerun() - let natural rerun happen
        
        # Chat input - supports Enter key to send
        # Disable input while processing to prevent duplicate submissions
        user_query = st.chat_input(
            placeholder="Ask a question about your documents... (Press Enter to send)",
            key="chat_input",
            disabled=st.session_state.is_processing
        )
        
        if user_query and not st.session_state.is_processing:
            # Use streaming for faster UX
            self.process_chat_query_stream(user_query)
    
    def display_chat_messages(self):
        """Display chat messages simply"""
        if st.session_state.chat_messages:
            for message in st.session_state.chat_messages:
                if message["type"] == "user":
                    with st.chat_message("user"):
                        st.write(message["content"])
                else:
                    with st.chat_message("assistant"):
                        st.markdown(message["content"])
        else:
            st.info("💬 Start a conversation by asking a question about your documents!")
    
    def process_chat_query(self, query: str):
        """Process chat query using API"""
        # Add user message to chat
        st.session_state.chat_messages.append({
            "type": "user",
            "content": query,
            "timestamp": datetime.now()
        })
        # Immediately show the user's message in the chat UI
        with st.chat_message("user"):
            st.write(query)
        
        with st.spinner("🤖 AI is thinking..."):
            try:
                response = self.api.ask_question(
                    query=query,
                    session_id=st.session_state.session_id
                )
                
                if response and response.get("status") == "success":
                    # Add assistant response to chat (links are now integrated in the response content)
                    assistant_message = {
                        "type": "assistant",
                        "content": response.get("response", "No response received"),
                        "timestamp": datetime.now()
                    }
                    
                    st.session_state.chat_messages.append(assistant_message)
                    # Don't use st.rerun() - let natural rerun happen
                else:
                    error_msg = response.get("message", "Unknown error") if response else "No response from server"
                    st.error(f"❌ Chat failed: {error_msg}")
                    
            except Exception as e:
                st.error(f"❌ Error processing chat query: {str(e)}")

    def process_chat_query_stream(self, query: str):
        """Process chat query using WebSocket streaming and render tokens live."""
        import queue
        import time
        
        # Set processing flag to prevent duplicate submissions
        st.session_state.is_processing = True
        
        # Check if this query is already being processed or completed
        query_hash = f"query_{hash(query)}"
        if query_hash in st.session_state.get('processed_queries', set()):
            st.session_state.is_processing = False
            return
        
        # Initialize processed queries set if not exists
        if 'processed_queries' not in st.session_state:
            st.session_state.processed_queries = set()
        
        # Add user message to chat (only if not already there)
        user_message_exists = False
        if st.session_state.chat_messages:
            last_message = st.session_state.chat_messages[-1]
            if last_message["type"] == "user" and last_message["content"] == query:
                user_message_exists = True
        
        if not user_message_exists:
            st.session_state.chat_messages.append({
                "type": "user",
                "content": query,
                "timestamp": datetime.now()
            })

        # Display user message immediately
        with st.chat_message("user"):
            st.write(query)

        # Create assistant message container
        with st.chat_message("assistant"):
            placeholder = st.empty()
            
            # Thread-safe queue for receiving tokens
            token_queue = queue.Queue()
            streamed_text = ""
            is_complete = False
            error_msg = None

            # Callbacks that put data in queue instead of directly updating UI
            def queue_token(token):
                token_queue.put(('token', token))
            
            def queue_complete(message):
                token_queue.put(('complete', message))
            
            def queue_error(error):
                token_queue.put(('error', error))

            try:
                # Start WebSocket streaming (runs in background thread)
                self.api.ask_question_stream_websocket(
                    query=query,
                    session_id=st.session_state.session_id,
                    on_token=queue_token,
                    on_complete=queue_complete,
                    on_error=queue_error
                )
                
                # Poll the queue and update UI in main thread
                max_wait = 60  # Maximum wait time in seconds
                start_time = time.time()
                last_update_time = time.time()
                update_interval = 0.05  # Update UI every 50ms for smooth streaming
                pending_tokens = []
                
                while not is_complete and (time.time() - start_time) < max_wait:
                    try:
                        msg_type, msg_data = token_queue.get(timeout=0.01)
                        
                        if msg_type == 'token':
                            pending_tokens.append(msg_data)
                            
                        elif msg_type == 'complete':
                            # Flush any pending tokens
                            if pending_tokens:
                                streamed_text += "".join(pending_tokens)
                                pending_tokens = []
                            is_complete = True
                            
                        elif msg_type == 'error':
                            error_msg = msg_data
                            is_complete = True
                            
                    except queue.Empty:
                        pass
                    
                    # Batch update UI for smoother streaming
                    current_time = time.time()
                    if pending_tokens and (current_time - last_update_time) >= update_interval:
                        streamed_text += "".join(pending_tokens)
                        pending_tokens = []
                        # Display with typing cursor
                        placeholder.markdown(streamed_text + " ▌")
                        last_update_time = current_time
                
                # Final display without cursor
                if streamed_text:
                    placeholder.markdown(streamed_text)
                    
                    # Save to session only once when complete
                    if is_complete:
                        st.session_state.chat_messages.append({
                            "type": "assistant",
                            "content": streamed_text,
                            "timestamp": datetime.now()
                        })
                        # Mark this query as processed
                        st.session_state.processed_queries.add(query_hash)
                
                # Handle timeout or error
                if error_msg:
                    if error_msg.strip() and 'ConnectionClosed' not in error_msg:
                        st.error(f"❌ {error_msg}")
                elif not is_complete:
                    st.warning("⏱️ Response timeout")
                
            except Exception as e:
                st.error(f"❌ Error during WebSocket streaming: {str(e)}")
            finally:
                # Always clear processing flag when done
                st.session_state.is_processing = False

    