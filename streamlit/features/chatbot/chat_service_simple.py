"""
Simple chat service that works without Django models
Fallback for when database models are not available
"""
import logging
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class SimpleChatService:
    """Simple chat service that uses session state as fallback"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info("Using simple chat service (no database)")
    
    def get_user_sessions(self, user_id: int, limit: int = 50) -> List[Dict]:
        """Get user sessions from session state"""
        import streamlit as st
        
        if 'saved_chat_sessions' not in st.session_state:
            return []
        
        # Filter by user
        all_sessions = st.session_state.saved_chat_sessions
        user_sessions = [session for session in all_sessions if session.get('user_id') == user_id]
        return user_sessions[:limit]
    
    def get_session_messages(self, user_id: int, session_id: str) -> List[Dict]:
        """Get session messages from session state"""
        import streamlit as st
        
        if 'saved_chat_sessions' not in st.session_state:
            return []
        
        # Find the session
        for session in st.session_state.saved_chat_sessions:
            if session.get('session_id') == session_id and session.get('user_id') == user_id:
                return session.get('messages', [])
        
        return []
    
    def save_message(self, user_id: int, session_id: str, message_type: str, 
                    content: str, sources: List = None, processing_info: Dict = None) -> bool:
        """Save message to session state"""
        import streamlit as st
        
        try:
            # Initialize if not exists
            if 'saved_chat_sessions' not in st.session_state:
                st.session_state.saved_chat_sessions = []
            
            # Find or create session
            session_found = False
            for session in st.session_state.saved_chat_sessions:
                if session.get('session_id') == session_id and session.get('user_id') == user_id:
                    # Add message to existing session
                    if 'messages' not in session:
                        session['messages'] = []
                    
                    message = {
                        'type': message_type,
                        'content': content,
                        'timestamp': datetime.now().strftime('%H:%M:%S'),
                        'sources': sources or [],
                        'processing_info': processing_info or {}
                    }
                    session['messages'].append(message)
                    session['message_count'] = len(session['messages'])
                    session['saved_at'] = datetime.now()
                    session_found = True
                    break
            
            if not session_found:
                # Create new session
                session_data = {
                    'session_id': session_id,
                    'user_id': user_id,
                    'username': st.session_state.get('username', 'Anonymous'),
                    'messages': [{
                        'type': message_type,
                        'content': content,
                        'timestamp': datetime.now().strftime('%H:%M:%S'),
                        'sources': sources or [],
                        'processing_info': processing_info or {}
                    }],
                    'message_count': 1,
                    'saved_at': datetime.now()
                }
                st.session_state.saved_chat_sessions.append(session_data)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving message: {e}")
            return False
    
    def delete_session(self, user_id: int, session_id: str) -> bool:
        """Delete session from session state"""
        import streamlit as st
        
        try:
            if 'saved_chat_sessions' in st.session_state:
                st.session_state.saved_chat_sessions = [
                    session for session in st.session_state.saved_chat_sessions
                    if not (session.get('session_id') == session_id and session.get('user_id') == user_id)
                ]
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting session: {e}")
            return False
    
    def clear_user_sessions(self, user_id: int) -> bool:
        """Clear all user sessions from session state"""
        import streamlit as st
        
        try:
            if 'saved_chat_sessions' in st.session_state:
                st.session_state.saved_chat_sessions = [
                    session for session in st.session_state.saved_chat_sessions
                    if session.get('user_id') != user_id
                ]
            return True
            
        except Exception as e:
            self.logger.error(f"Error clearing user sessions: {e}")
            return False
    
    def get_session_stats(self, user_id: int) -> Dict:
        """Get session statistics"""
        import streamlit as st
        
        try:
            if 'saved_chat_sessions' not in st.session_state:
                return {'total_sessions': 0, 'total_messages': 0, 'user_id': user_id}
            
            user_sessions = [
                session for session in st.session_state.saved_chat_sessions
                if session.get('user_id') == user_id
            ]
            
            total_sessions = len(user_sessions)
            total_messages = sum(session.get('message_count', 0) for session in user_sessions)
            
            return {
                'total_sessions': total_sessions,
                'total_messages': total_messages,
                'user_id': user_id
            }
            
        except Exception as e:
            self.logger.error(f"Error getting session stats: {e}")
            return {'total_sessions': 0, 'total_messages': 0, 'user_id': user_id}
