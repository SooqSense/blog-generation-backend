import streamlit as st
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
        
        # WebSocket connection is not needed for standard API calls
        # Removed WebSocket initialization - using standard REST API instead
    
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
            # Use standard REST API call instead of WebSocket streaming
            self.process_chat_query(user_query)
    
    def display_chat_messages(self):
        """Display chat messages simply"""
        if st.session_state.chat_messages:
            for message in st.session_state.chat_messages:
                if message["type"] == "user":
                    with st.chat_message("user"):
                        st.write(message["content"])
                else:
                    with st.chat_message("assistant"):
                        # Display error messages differently
                        if message.get("is_error"):
                            st.error(message["content"])
                        else:
                            st.markdown(message["content"])
        else:
            st.info("💬 Start a conversation by asking a question about your documents!")
    
    def process_chat_query(self, query: str):
        """Process chat query using API"""
        # Set processing flag to prevent duplicate requests
        st.session_state.is_processing = True
        
        # Add user message to chat
        st.session_state.chat_messages.append({
            "type": "user",
            "content": query,
            "timestamp": datetime.now()
        })
        
        with st.spinner("🤖 AI is thinking..."):
            try:
                response = self.api.ask_question(
                    query=query,
                    session_id=st.session_state.session_id
                )
                
                if response and response.get("status") == "success":
                    # Get response content - handle both "response" field and legacy format
                    response_content = response.get("response", "No response received")
                    
                    # Add assistant response to chat
                    assistant_message = {
                        "type": "assistant",
                        "content": response_content,
                        "timestamp": datetime.now(),
                        "documents_found": response.get("documents_found", 0),
                        "processing_time": response.get("processing_time", 0),
                    }
                    
                    st.session_state.chat_messages.append(assistant_message)
                    
                else:
                    # Handle error response - new format returns "error" field
                    error_msg = (
                        response.get("error") or 
                        response.get("message") or 
                        response.get("response") or 
                        "Unknown error"
                    ) if response else "No response from server"
                    
                    # Add error message to chat history
                    error_message = {
                        "type": "assistant",
                        "content": f"❌ Error: {error_msg}",
                        "timestamp": datetime.now(),
                        "is_error": True,
                    }
                    st.session_state.chat_messages.append(error_message)
                    
                    st.error(f"❌ Chat failed: {error_msg}")
                    
            except Exception as e:
                error_msg = f"Error processing chat query: {str(e)}"
                
                # Add error to chat history
                error_message = {
                    "type": "assistant",
                    "content": f"❌ {error_msg}",
                    "timestamp": datetime.now(),
                    "is_error": True,
                }
                st.session_state.chat_messages.append(error_message)
                
                st.error(f"❌ {error_msg}")
            finally:
                # Reset processing flag
                st.session_state.is_processing = False
                # Rerun to display new messages
                st.rerun()


    