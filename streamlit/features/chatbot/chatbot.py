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
        
        # Create tabs for different features
        tab1, tab2 = st.tabs(["Chat", "Chat History"])
        
        with tab1:
            self.render_chat_interface()
        
        with tab2:
            self.render_chat_history()
    
    def render_chat_interface(self):
        """Render chat interface"""
        st.subheader("💬 Chat Interface")
        
        # Display chat messages
        self.display_chat_messages()
        
        # Chat input
        with st.form("chat_form"):
            user_query = st.text_area(
                "Ask a question about your documents",
                placeholder="What projects have I worked on?",
                help="Ask questions about your uploaded documents"
            )
            
            col1, col2 = st.columns([1, 4])
            
            with col1:
                submit_button = st.form_submit_button("💬 Send", use_container_width=True)
            
            with col2:
                if st.form_submit_button("🗑️ Clear Chat", use_container_width=True):
                    st.session_state.chat_messages = []
                    st.rerun()
            
            if submit_button and user_query:
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
                        st.write(message["content"])
                        
                        # Display sources if available
                        if "sources" in message and message["sources"]:
                            with st.expander("📚 Sources"):
                                for source in message["sources"]:
                                    st.markdown(f"- {source}")
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
                    # Add assistant response to chat
                    assistant_message = {
                        "type": "assistant",
                        "content": response.get("response", "No response received"),
                        "timestamp": datetime.now()
                    }
                    
                    # Add sources if available
                    if "sources" in response:
                        assistant_message["sources"] = response["sources"]
                    
                    st.session_state.chat_messages.append(assistant_message)
                    st.rerun()
                else:
                    error_msg = response.get("message", "Unknown error") if response else "No response from server"
                    st.error(f"❌ Chat failed: {error_msg}")
                    
            except Exception as e:
                st.error(f"❌ Error processing chat query: {str(e)}")
    
    def render_chat_history(self):
        """Render chat history"""
        st.subheader("📚 Chat History")
        st.info("Chat history feature coming soon!")
        st.write("This will show your previous chat sessions and conversations.")