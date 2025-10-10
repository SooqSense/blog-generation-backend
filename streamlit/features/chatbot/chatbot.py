import streamlit as st
import sys
import os
import re
from pathlib import Path
import time
import uuid
from datetime import datetime
from typing import List, Dict, Any

# Add the project root to the path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import AI tools from Django management app
try:
    from management_app.chatbot.service.agent.agent import ProjectChatbot, project_chatbot
    from management_app.knowledge_base.service.pinecone_indexing.pinecone_indexing import PineconeService
    
    AI_TOOLS_AVAILABLE = True
    AI_TOOLS_ERROR = None
    print("✅ Chatbot feature: AI tools imported successfully")
    
except Exception as e:
    AI_TOOLS_AVAILABLE = False
    AI_TOOLS_ERROR = str(e)
    print(f"⚠️ Chatbot feature: AI tools import failed - {str(e)}")
    
    # Create dummy classes for graceful degradation
    class ProjectChatbot:
        def __init__(self, *args, **kwargs):
            pass
        def generate_response(self, *args, **kwargs):
            return {
                'success': False,
                'error': f"Chatbot not available: {AI_TOOLS_ERROR}",
                'response': "I'm sorry, the chatbot service is not available right now.",
                'sources_used': [],
                'processing_time': 0,
                'tokens_used': 0
            }
        def generate_session_id(self, user_id):
            return f"chat_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        def is_available(self):
            return False
    
    class PineconeService:
        def __init__(self, *args, **kwargs):
            pass
        def search_documents(self, *args, **kwargs):
            return {
                'success': False,
                'error': f"Vector search not available: {AI_TOOLS_ERROR}",
                'results': [],
                'total_results': 0
            }
        def is_available(self):
            return False
    
    project_chatbot = ProjectChatbot()

class ChatbotFeature:
    """AI Chatbot feature for Streamlit UI"""
    
    def __init__(self):
        self.ai_tools_available = AI_TOOLS_AVAILABLE
        self.ai_tools_error = AI_TOOLS_ERROR
        try:
            self.chatbot = project_chatbot
            self.pinecone_service = PineconeService()
        except Exception as e:
            self.chatbot = None
            self.pinecone_service = None
            if AI_TOOLS_AVAILABLE:
                self.ai_tools_error = str(e)
        
        # Initialize session state for chat
        self.initialize_chat_session()
        
    def initialize_chat_session(self):
        """Initialize chat session state"""
        if 'chat_messages' not in st.session_state:
            st.session_state.chat_messages = []
        
        if 'chat_session_id' not in st.session_state:
            user_id = st.session_state.get('user_id', 1)
            st.session_state.chat_session_id = self.generate_session_id(user_id)
        
        if 'conversation_context' not in st.session_state:
            st.session_state.conversation_context = []
    
    def generate_session_id(self, user_id):
        """Generate a unique session ID"""
        if self.chatbot and hasattr(self.chatbot, 'generate_session_id'):
            return self.chatbot.generate_session_id(user_id)
        else:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_id = str(uuid.uuid4())[:8]
            return f"chat_{user_id}_{timestamp}_{unique_id}"
        
    def render(self):
        """Render the enhanced chatbot interface"""
        st.markdown("# 🤖 Enhanced AI Portfolio Chat")
        st.markdown("Chat with your project documents using advanced contextual AI. I can intelligently understand vague queries, remember conversation context, and provide comprehensive responses from your knowledge base.")
        
        # Check if AI tools are available
        if not self.ai_tools_available:
            st.error("🚫 Chatbot Tools Not Available")
            st.error(f"Error: {self.ai_tools_error}")
            st.info("Please ensure the AI tools and dependencies are properly configured.")
            return
        
        # Create tabs for different functionalities
        tab1, tab2, tab3 = st.tabs(["💬 Chat", "📜 Chat History", "⚙️ Chat Settings"])
        
        with tab1:
            self.render_chat_interface()
            
        with tab2:
            self.render_chat_history()
            
        with tab3:
            self.render_chat_settings()
    
    def render_chat_interface(self):
        """Render the main chat interface"""
        # Modern chat header with status indicators  
        st.markdown(
            """
            <div style="background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); 
                        padding: 12px 20px; margin: -1rem -1rem 0 -1rem; border-radius: 0px 0px 15px 15px;
                        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);">
                <h3 style="color: white; margin: 0; display: flex; align-items: center; font-size: 1.2rem;">
                    💬 AI Portfolio Chat
                </h3>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Status bar
        col_status1, col_status2, col_status3 = st.columns([1, 1, 2])
        
        with col_status1:
            if self.chatbot and self.chatbot.is_available():
                st.success("🤖 Contextual AI Ready", icon="✅")
            else:
                st.error("🤖 AI Unavailable", icon="❌")
                
        with col_status2:
            if self.pinecone_service and hasattr(self.pinecone_service, 'is_available') and self.pinecone_service.is_available():
                st.success("🔍 Enhanced Search Ready", icon="✅")
            else:
                st.error("🔍 Search Unavailable", icon="❌")
                
        with col_status3:
            st.info(f"**Session:** `{st.session_state.chat_session_id[-12:]}`", icon="🆔")
        
        # Chat messages area with better styling
        with st.container():
            # Display chat messages
            self.display_chat_messages()
        
        
        # Modern chat input area with enhanced styling
        st.markdown(
            """
            <style>
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            @keyframes pulse {
                0% { box-shadow: 0 0 0 0 rgba(102, 126, 234, 0.7); }
                70% { box-shadow: 0 0 0 10px rgba(102, 126, 234, 0); }
                100% { box-shadow: 0 0 0 0 rgba(102, 126, 234, 0); }
            }
            
            .chat-container {
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                border-radius: 15px;
                padding: 20px;
                margin: 10px 0;
                box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
            }
            
            .status-indicator {
                animation: pulse 2s infinite;
            }
            
            .message-bubble {
                animation: fadeIn 0.5s ease-out;
                margin: 10px 0;
            }
            
            .chat-input-container {
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                border-radius: 25px;
                padding: 15px;
                box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
                border: 1px solid rgba(255, 255, 255, 0.18);
            }
            
            .stButton > button {
                border-radius: 50%;
                height: 45px;
                width: 45px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border: none;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
                transition: all 0.3s ease;
            }
            
            .stButton > button:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(102, 126, 234, 0.6);
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        
        # Modern input form with enhanced styling
        st.markdown(
            """
            <div class="chat-input-container" style="background: rgba(255, 255, 255, 0.95); 
                        backdrop-filter: blur(10px); border-radius: 25px; padding: 8px 15px; 
                        box-shadow: 0 8px 32px rgba(31, 38, 135, 0.15); 
                        border: 1px solid rgba(255, 255, 255, 0.18); margin: 15px 0;">
            """,
            unsafe_allow_html=True
        )
        
        with st.container():
            with st.form(key="chat_form", clear_on_submit=True):
                col_input1, col_input2 = st.columns([6, 1])
                
                with col_input1:
                    user_query = st.text_input(
                        "Message",
                        placeholder="💬 Ask me anything! I understand context and can enhance vague queries...",
                        label_visibility="collapsed",
                        key="chat_input_form",
                        help="Type your message - I'll intelligently understand and enhance your query for better results"
                    )
                    
                with col_input2:
                    send_button = st.form_submit_button(
                        "📤",
                        type="primary",
                        use_container_width=True,
                        disabled=not self.ai_tools_available,
                        help="Send message"
                    )
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Process chat input
        if send_button and user_query and user_query.strip():
            self.process_chat_query(user_query)
        
        # Chat controls in a compact row
        st.markdown("---")
        col_control1, col_control2, col_control3 = st.columns(3)
        
        with col_control1:
            if st.button("🆕 New Session", help="Start a new chat session"):
                self.start_new_session()
                
        with col_control2:
            if st.button("🗑️ Clear Chat", help="Clear all messages"):
                st.session_state.chat_messages = []
                st.session_state.conversation_context = []
                st.rerun()
                
        with col_control3:
            if st.button("💾 Save", help="Save this conversation"):
                self.save_chat_session()
    
    def process_markdown_content(self, content):
        """Process markdown content for better HTML display"""
        if not content:
            return content
            
        # Remove or convert common markdown elements
        processed = content
        
        # Handle bold text (**text** or __text__)
        processed = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', processed)
        processed = re.sub(r'__(.*?)__', r'<strong>\1</strong>', processed)
        
        # Handle italic text (*text* or _text_)
        processed = re.sub(r'\*(.*?)\*', r'<em>\1</em>', processed)
        processed = re.sub(r'_(.*?)_', r'<em>\1</em>', processed)
        
        # Handle inline code (`code`)
        processed = re.sub(r'`(.*?)`', r'<code style="background: rgba(255,255,255,0.2); padding: 2px 4px; border-radius: 3px; font-family: monospace;">\1</code>', processed)
        
        # Handle line breaks
        processed = processed.replace(chr(10), '<br>').replace('\n', '<br>')
        
        # Handle bullet points (- or *)
        lines = processed.split('<br>')
        formatted_lines = []
        for line in lines:
            line = line.strip()
            if line.startswith('- ') or line.startswith('* '):
                line = f'• {line[2:]}'  # Replace with bullet symbol
            formatted_lines.append(line)
        processed = '<br>'.join(formatted_lines)
        
        return processed

    def display_chat_messages(self):
        """Display chat messages"""
        # Create a scrollable chat container
        chat_container = st.container()
        
        with chat_container:
            if not st.session_state.chat_messages:
                st.markdown(
                    """
                    <div class="message-bubble" style="display: flex; justify-content: center; margin: 40px 5px;">
                        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                    color: white; padding: 30px 40px; border-radius: 25px; 
                                    text-align: center; max-width: 80%; 
                                    box-shadow: 0 8px 30px rgba(102, 126, 234, 0.4);
                                    border: 3px solid rgba(255, 255, 255, 0.2);">
                            <h3 style="margin: 0 0 15px 0; font-size: 24px;">👋 Welcome to Enhanced AI Portfolio Chat!</h3>
                            <p style="margin: 10px 0; font-size: 16px; opacity: 0.95; line-height: 1.5;">
                                I'm your contextually-aware AI assistant with advanced query understanding. 
                                I can intelligently analyze your questions and provide comprehensive answers about your documents.
                            </p>
                            <div style="background: rgba(255, 255, 255, 0.15); padding: 15px; border-radius: 15px; 
                                        margin-top: 20px; backdrop-filter: blur(10px);">
                                <p style="margin: 0; font-style: italic; font-size: 14px; opacity: 0.9;">
                                    🧠 <strong>New Features:</strong> Contextual query enhancement, conversation memory, and intelligent response generation
                                </p>
                                <p style="margin: 8px 0 0 0; font-style: italic; font-size: 13px; opacity: 0.85;">
                                    💡 Try: "How many projects do I have?" or "Tell me about this project" or "What technologies were used?"
                                </p>
                            </div>
                        </div>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
                return
            
            # Display all messages in a chat-like format
            for i, message in enumerate(st.session_state.chat_messages):
                message_type = message.get('type', 'user')
                content = message.get('content', '')
                timestamp = message.get('timestamp', '')
                
                if message_type == 'user':
                    # User message bubble (right aligned)
                    st.markdown(
                        f"""
                        <div class="message-bubble" style="display: flex; justify-content: flex-end; margin: 15px 5px;">
                            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                        color: white; padding: 14px 18px; border-radius: 20px 20px 8px 20px; 
                                        max-width: 70%; word-wrap: break-word; 
                                        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
                                        font-size: 14px; line-height: 1.4; position: relative;">
                                <div style="font-weight: 600; margin-bottom: 6px; font-size: 12px; opacity: 0.9;">
                                    You
                                </div>
                                <div style="margin-bottom: 8px;">{content}</div>
                                <div style="font-size: 11px; opacity: 0.8; text-align: right; margin-top: 4px;">
                                    {timestamp}
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                else:
                    # Assistant message bubble (left aligned, with beautiful gradient)
                    # Process markdown formatting for better display
                    formatted_content = self.process_markdown_content(content)
                    
                    st.markdown(
                        f"""
                        <div class="message-bubble" style="display: flex; justify-content: flex-start; margin: 15px 5px;">
                            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                        color: white; padding: 16px 20px; border-radius: 8px 20px 20px 20px; 
                                        max-width: 80%; word-wrap: break-word; 
                                        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
                                        font-size: 14px; line-height: 1.5; position: relative;
                                        border: 2px solid rgba(255, 255, 255, 0.1);">
                                <div style="font-weight: 600; margin-bottom: 8px; font-size: 12px; opacity: 0.9;
                                           display: flex; align-items: center; gap: 6px;">
                                    🤖 AI Assistant
                                    <div style="width: 6px; height: 6px; background: rgba(255,255,255,0.6); 
                                               border-radius: 50%; animation: pulse 2s infinite;"></div>
                                </div>
                                <div style="margin-bottom: 10px; font-weight: 400;">{formatted_content}</div>
                                <div style="font-size: 11px; opacity: 0.8; text-align: left; margin-top: 4px;">
                                    {timestamp}
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                
                # Show enhanced processing info for assistant messages
                processing_info = message.get('processing_info', {})
                if processing_info and message_type == 'assistant':
                    with st.expander("🧠 AI Processing Details", expanded=False):
                        col_proc1, col_proc2 = st.columns(2)
                        
                        with col_proc1:
                            st.markdown("**Performance Metrics:**")
                            st.caption(f"⏱️ Processing Time: {processing_info.get('processing_time', 0):.2f}s")
                            st.caption(f"🔤 Tokens Used: {processing_info.get('tokens_used', 0)}")
                            st.caption(f"🤖 Model: {processing_info.get('model_used', 'Unknown')}")
                            st.caption(f"📄 Documents Found: {processing_info.get('documents_found', 0)}")
                            st.caption(f"🔍 Search Strategy: {processing_info.get('search_strategy', 'Standard')}")
                            
                        with col_proc2:
                            query_enhanced = processing_info.get('query_enhanced', False)
                            if query_enhanced:
                                st.markdown("**🔄 Query Enhancement:**")
                                st.success("✅ Query was enhanced for better search")
                                if processing_info.get('original_query'):
                                    st.caption(f"📝 Original: {processing_info.get('original_query', '')}")
                                if processing_info.get('enhanced_query'):
                                    st.caption(f"✨ Enhanced: {processing_info.get('enhanced_query', '')}")
                            else:
                                st.markdown("**🔄 Query Enhancement:**")
                                st.info("Query used as-is")
                
                # Show sources if available
                sources = message.get('sources', [])
                if sources:
                    with st.expander(f"📚 Sources ({len(sources)} documents)", expanded=False):
                        for j, source in enumerate(sources, 1):
                            col_src1, col_src2 = st.columns([3, 1])
                            
                            with col_src1:
                                st.markdown(f"**{j}. {source.get('file_name', 'Unknown File')}**")
                                st.caption(f"Type: {source.get('file_type', 'N/A')} | Score: {source.get('relevance_score', 0):.2f}")
                                
                            with col_src2:
                                if source.get('file_url'):
                                    st.markdown(f"[🔗 View]({source.get('file_url')})")
                
    
    def process_chat_query(self, query: str):
        """Process a chat query and generate response"""
        if not query.strip():
            return
        
        try:
            # Add user message
            user_message = {
                'type': 'user',
                'content': query,
                'timestamp': datetime.now().strftime('%H:%M:%S')
            }
            st.session_state.chat_messages.append(user_message)
            
            # Show modern typing indicator
            typing_placeholder = st.empty()
            typing_placeholder.markdown(
                """
                <div class="message-bubble" style="display: flex; justify-content: flex-start; margin: 15px 5px;">
                    <div style="background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%); 
                                color: #2d3748; padding: 14px 18px; border-radius: 20px 20px 20px 8px; 
                                border: 1px solid #e2e8f0; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
                                animation: pulse 1.5s ease-in-out infinite;">
                        <div style="font-weight: 600; margin-bottom: 6px; font-size: 12px; color: #667eea;">
                            🤖 AI Assistant
                        </div>
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <div style="display: flex; gap: 4px;">
                                <div style="width: 8px; height: 8px; border-radius: 50%; background: #667eea; 
                                           animation: typing 1.4s ease-in-out infinite;"></div>
                                <div style="width: 8px; height: 8px; border-radius: 50%; background: #667eea; 
                                           animation: typing 1.4s ease-in-out infinite; animation-delay: 0.2s;"></div>
                                <div style="width: 8px; height: 8px; border-radius: 50%; background: #667eea; 
                                           animation: typing 1.4s ease-in-out infinite; animation-delay: 0.4s;"></div>
                            </div>
                            <span style="color: #6b7280; font-size: 12px;">AI is thinking...</span>
                        </div>
                    </div>
                </div>
                <style>
                @keyframes typing {
                    0%, 60%, 100% { opacity: 0.3; }
                    30% { opacity: 1; }
                }
                </style>
                """,
                unsafe_allow_html=True
            )
            
            # Use enhanced contextual RAG system - let the chatbot handle search internally
            if self.chatbot:
                # Check if the chatbot has the correct method
                if hasattr(self.chatbot, 'ask'):
                    response_result = self.chatbot.ask(
                        query=query,
                        top_k=30,  # Use more documents for better context
                        user_id=st.session_state.get('user_id', 1)
                    )
                elif hasattr(self.chatbot, 'generate_response'):
                    response_result = self.chatbot.generate_response(
                        query=query,
                        relevant_documents=None,  # Let the enhanced RAG system handle search
                        conversation_history=st.session_state.conversation_context,
                        top_k=30,  # Use more documents for better context
                        user_id=st.session_state.get('user_id', 1)
                    )
                else:
                    response_result = {
                        'success': False,
                        'error': 'Chatbot method not found',
                        'response': 'I apologize, but the chatbot service is not properly configured.',
                        'sources_used': [],
                        'processing_time': 0,
                        'tokens_used': 0
                    }
                
                if response_result.get('success'):
                    ai_response = response_result.get('response', 'I apologize, but I could not generate a response.')
                    sources_used = response_result.get('sources', [])  # 'ask' method returns 'sources', not 'sources_used'
                    processing_time = response_result.get('processing_time', 0)
                    tokens_used = response_result.get('tokens_used', 0)
                    model_used = response_result.get('model_used', 'Unknown')
                    
                    # Extract enhanced contextual information
                    search_strategy = response_result.get('search_strategy', 'standard')
                    query_enhanced = response_result.get('query_enhanced', False)
                    original_query = response_result.get('original_query', query)
                    enhanced_query = response_result.get('enhanced_query', None)
                    
                    # Add assistant message with enhanced metadata
                    assistant_message = {
                        'type': 'assistant',
                        'content': ai_response,
                        'timestamp': datetime.now().strftime('%H:%M:%S'),
                        'sources': sources_used,
                        'processing_info': {
                            'processing_time': processing_time,
                            'tokens_used': tokens_used,
                            'model_used': model_used,
                            'documents_found': len(sources_used),  # Use sources from enhanced system
                            'search_strategy': search_strategy,
                            'query_enhanced': query_enhanced,
                            'original_query': original_query if query_enhanced else None,
                            'enhanced_query': enhanced_query
                        }
                    }
                    st.session_state.chat_messages.append(assistant_message)
                    
                    # Update conversation context
                    st.session_state.conversation_context.append({
                        'role': 'user',
                        'content': query
                    })
                    st.session_state.conversation_context.append({
                        'role': 'assistant',
                        'content': ai_response
                    })
                    
                    # Keep context manageable
                    if len(st.session_state.conversation_context) > 20:
                        st.session_state.conversation_context = st.session_state.conversation_context[-20:]
                    
                    # Clear typing indicator
                    typing_placeholder.empty()
                
                else:
                    # Error response
                    typing_placeholder.empty()  # Clear typing indicator on error too
                    error_message = {
                        'type': 'assistant',
                        'content': f"I'm sorry, I encountered an error: {response_result.get('error', 'Unknown error')}",
                        'timestamp': datetime.now().strftime('%H:%M:%S'),
                        'sources': [],
                        'processing_info': {}
                    }
                    st.session_state.chat_messages.append(error_message)
            
            else:
                # Chatbot not available
                error_message = {
                    'type': 'assistant',
                    'content': "I'm sorry, the chatbot service is not available right now. Please try again later.",
                    'timestamp': datetime.now().strftime('%H:%M:%S'),
                    'sources': [],
                    'processing_info': {}
                }
                st.session_state.chat_messages.append(error_message)
            
            # Form will clear automatically, just refresh to show new message
            st.rerun()
            
        except Exception as e:
            st.error(f"Error processing chat query: {str(e)}")
    
    def start_new_session(self):
        """Start a new chat session"""
        user_id = st.session_state.get('user_id', 1)
        st.session_state.chat_session_id = self.generate_session_id(user_id)
        st.session_state.chat_messages = []
        st.session_state.conversation_context = []
        st.success("🆕 New chat session started!")
        st.rerun()
    
    def save_chat_session(self):
        """Save current chat session"""
        if not st.session_state.chat_messages:
            st.warning("No messages to save!")
            return
        
        # Save to session state history
        if 'saved_chat_sessions' not in st.session_state:
            st.session_state.saved_chat_sessions = []
        
        session_data = {
            'session_id': st.session_state.chat_session_id,
            'messages': st.session_state.chat_messages.copy(),
            'saved_at': datetime.now(),
            'message_count': len(st.session_state.chat_messages),
            'user_id': st.session_state.get('user_id', 1),
            'username': st.session_state.get('username', 'Anonymous')
        }
        
        st.session_state.saved_chat_sessions.append(session_data)
        st.success(f"💾 Chat session saved! ({len(st.session_state.chat_messages)} messages)")
    
    def render_chat_history(self):
        """Render chat history interface"""
        st.markdown("### 📜 Chat History")
        
        if 'saved_chat_sessions' not in st.session_state or not st.session_state.saved_chat_sessions:
            st.info("No saved chat sessions. Your conversations will appear here after you save them.")
            return
        
        # Show saved sessions
        sessions = st.session_state.saved_chat_sessions
        st.markdown(f"#### 💾 Saved Sessions ({len(sessions)})")
        
        for i, session in enumerate(reversed(sessions), 1):
            session_id = session.get('session_id', f'Session {i}')
            message_count = session.get('message_count', 0)
            saved_at = session.get('saved_at', datetime.now())
            
            with st.expander(f"📋 {session_id} - {message_count} messages", expanded=False):
                col_session1, col_session2 = st.columns([2, 1])
                
                with col_session1:
                    st.write(f"**Session ID:** {session_id}")
                    st.write(f"**Messages:** {message_count}")
                    st.write(f"**Saved:** {saved_at.strftime('%Y-%m-%d %H:%M:%S')}")
                    st.write(f"**User:** {session.get('username', 'Anonymous')}")
                    
                with col_session2:
                    if st.button(f"🔄 Load Session", key=f"load_{i}"):
                        st.session_state.chat_messages = session.get('messages', [])
                        st.session_state.chat_session_id = session_id
                        st.success(f"✅ Loaded session: {session_id}")
                        st.rerun()
                    
                    if st.button(f"🗑️ Delete", key=f"delete_{i}"):
                        st.session_state.saved_chat_sessions.remove(session)
                        st.success("🗑️ Session deleted")
                        st.rerun()
                
                # Show message preview
                messages = session.get('messages', [])
                if messages:
                    st.markdown("**Message Preview:**")
                    for msg in messages[:3]:  # Show first 3 messages
                        msg_type = msg.get('type', 'user')
                        content = msg.get('content', '')[:100]
                        icon = "👤" if msg_type == 'user' else "🤖"
                        st.caption(f"{icon} {content}...")
                    
                    if len(messages) > 3:
                        st.caption(f"... and {len(messages) - 3} more messages")
        
        # Clear all history
        if st.button("🗑️ Clear All History", type="secondary"):
            st.session_state.saved_chat_sessions = []
            st.success("🗑️ All chat history cleared!")
            st.rerun()
    
    def render_chat_settings(self):
        """Render chat settings interface"""
        st.markdown("### ⚙️ Chat Settings")
        
        # AI Model settings
        st.markdown("#### 🤖 Enhanced AI Model Configuration")
        
        col_ai1, col_ai2 = st.columns(2)
        
        with col_ai1:
            model_temperature = st.slider(
                "Response Creativity",
                min_value=0.0,
                max_value=1.0,
                value=0.7,
                step=0.1,
                help="Higher values make responses more creative but less focused"
            )
            
            max_tokens = st.slider(
                "Max Response Length",
                min_value=100,
                max_value=2000,
                value=1000,
                help="Maximum length of AI responses"
            )
            
            enable_query_enhancement = st.checkbox(
                "Enable Query Enhancement",
                value=True,
                help="Use AI to enhance vague queries for better search results"
            )
            
        with col_ai2:
            include_sources = st.checkbox(
                "Always Show Sources",
                value=True,
                help="Always display document sources in responses"
            )
            
            show_processing_info = st.checkbox(
                "Show Processing Info",
                value=True,
                help="Display token usage, processing time, and query enhancement details"
            )
            
            contextual_responses = st.checkbox(
                "Contextual Responses",
                value=True,
                help="Generate human-like responses that understand context and intent"
            )
        
        # Search settings
        st.markdown("#### 🔍 Enhanced Document Search Settings")
        
        col_search1, col_search2 = st.columns(2)
        
        with col_search1:
            search_top_k = st.slider(
                "Documents to Search",
                min_value=5,
                max_value=50,
                value=15,
                help="Number of documents to search for each query (increased for better context)"
            )
            
            relevance_threshold = st.slider(
                "Relevance Threshold",
                min_value=0.0,
                max_value=1.0,
                value=0.2,
                step=0.1,
                help="Minimum relevance score for including documents (lowered for better retrieval)"
            )
            
            use_comprehensive_search = st.checkbox(
                "Comprehensive Search",
                value=True,
                help="Use enhanced multi-stage search for more complete results"
            )
            
        with col_search2:
            enable_semantic_search = st.checkbox(
                "Semantic Search",
                value=True,
                help="Use AI-powered semantic search for better results"
            )
            
            search_all_users = st.checkbox(
                "Search All Documents",
                value=False,
                help="Search documents from all users (admin only)"
            )
            
            enable_intent_analysis = st.checkbox(
                "Intent Analysis",
                value=True,
                help="Analyze query intent for count/list/specific queries"
            )
        
        # Conversation settings
        st.markdown("#### 💬 Conversation Settings")
        
        col_conv1, col_conv2 = st.columns(2)
        
        with col_conv1:
            context_length = st.slider(
                "Conversation Memory",
                min_value=2,
                max_value=50,
                value=20,
                help="Number of previous messages to remember"
            )
            
            auto_save = st.checkbox(
                "Auto-save Conversations",
                value=False,
                help="Automatically save conversations after each exchange"
            )
            
        with col_conv2:
            show_timestamps = st.checkbox(
                "Show Message Timestamps",
                value=True,
                help="Display timestamps on chat messages"
            )
            
            compact_view = st.checkbox(
                "Compact Message View",
                value=False,
                help="Use more compact message display"
            )
        
        # Advanced settings
        st.markdown("#### 🔬 Advanced Settings")
        
        with st.expander("🔧 Advanced Configuration", expanded=False):
            col_adv1, col_adv2 = st.columns(2)
            
            with col_adv1:
                enable_debug = st.checkbox("Enable Debug Mode", value=False)
                log_conversations = st.checkbox("Log Conversations", value=True)
                enable_analytics = st.checkbox("Enable Analytics", value=True)
                
            with col_adv2:
                api_timeout = st.slider("API Timeout (seconds)", 30, 300, 120)
                retry_attempts = st.slider("Retry Attempts", 1, 5, 3)
                rate_limit = st.slider("Rate Limit (requests/min)", 10, 100, 30)
        
        # Save settings
        if st.button("💾 Save Chat Settings", type="primary"):
            settings = {
                'model_temperature': model_temperature,
                'max_tokens': max_tokens,
                'enable_query_enhancement': enable_query_enhancement,
                'include_sources': include_sources,
                'show_processing_info': show_processing_info,
                'contextual_responses': contextual_responses,
                'search_top_k': search_top_k,
                'relevance_threshold': relevance_threshold,
                'use_comprehensive_search': use_comprehensive_search,
                'enable_semantic_search': enable_semantic_search,
                'search_all_users': search_all_users,
                'enable_intent_analysis': enable_intent_analysis,
                'context_length': context_length,
                'auto_save': auto_save,
                'show_timestamps': show_timestamps,
                'compact_view': compact_view,
                'enable_debug': enable_debug if 'enable_debug' in locals() else False,
                'log_conversations': log_conversations if 'log_conversations' in locals() else True,
                'enable_analytics': enable_analytics if 'enable_analytics' in locals() else True,
                'api_timeout': api_timeout if 'api_timeout' in locals() else 120,
                'retry_attempts': retry_attempts if 'retry_attempts' in locals() else 3,
                'rate_limit': rate_limit if 'rate_limit' in locals() else 30
            }
            
            st.session_state.chatbot_settings = settings
            st.success("✅ Chat settings saved successfully!")
            
            # Show saved settings
            with st.expander("📋 Saved Settings", expanded=False):
                st.json(settings)
