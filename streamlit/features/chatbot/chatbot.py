import streamlit as st
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

# Import API client
from api_client.api_client import chatbot_api

class ChatbotFeature:
    """AI Chatbot feature for Streamlit UI - API-based"""
    
    def __init__(self):
        self.api = chatbot_api
    
    def render(self):
        """Main render method"""
        st.title("🤖 AI Chatbot")
        st.markdown("Chat with AI about your uploaded documents.")
        
        # Initialize session state for chat
        if "chat_messages" not in st.session_state:
            st.session_state.chat_messages = []
        
        if "session_id" not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())
        
        # Render chat interface directly without tabs
        self.render_chat_interface()
    
    def render_chat_interface(self):
        """Render chat interface"""
        st.subheader("💬 Chat Interface")
        
        # Display chat messages
        self.display_chat_messages()
        
        # Chat input - supports Enter key to send
        user_query = st.chat_input(
            placeholder="Ask a question about your documents... (Press Enter to send)",
            key="chat_input"
        )
        
        # Clear chat button positioned under the input
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🗑️ Clear Chat", use_container_width=True):
                st.session_state.chat_messages = []
                st.rerun()
        
        if user_query:
            self.process_chat_query(user_query)
    
    def display_chat_messages(self):
        """Display chat messages"""
        if st.session_state.chat_messages:
            st.subheader("💬 Chat Messages")
            
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
                    st.rerun()
                else:
                    error_msg = response.get("message", "Unknown error") if response else "No response from server"
                    st.error(f"❌ Chat failed: {error_msg}")
                    
            except Exception as e:
                st.error(f"❌ Error processing chat query: {str(e)}")
    