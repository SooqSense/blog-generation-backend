"""
Django chat service for database operations with user isolation
"""
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from django.contrib.auth import get_user_model

User = get_user_model()
from django.db import transaction
from django.utils import timezone

from .models import ChatSession, ChatMessage, ChatConversationContext

logger = logging.getLogger(__name__)


class DjangoChatService:
    """Django service for managing chat data with user isolation"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID with error handling"""
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            self.logger.error(f"User with ID {user_id} not found")
            return None
        except Exception as e:
            self.logger.error(f"Error getting user {user_id}: {e}")
            return None
    
    def create_chat_session(self, user_id: int, session_id: str, title: str = None) -> Optional[ChatSession]:
        """Create a new chat session for a user"""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return None
            
            session = ChatSession.objects.create(
                user=user,
                session_id=session_id,
                title=title or f"Chat Session {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            
            self.logger.info(f"Created chat session {session_id} for user {user.username}")
            return session
            
        except Exception as e:
            self.logger.error(f"Error creating chat session: {e}")
            return None
    
    def get_user_sessions(self, user_id: int, limit: int = 50) -> List[ChatSession]:
        """Get all chat sessions for a user (user isolation)"""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return []
            
            sessions = ChatSession.objects.filter(
                user=user,
                is_active=True
            ).order_by('-updated_at')[:limit]
            
            return list(sessions)
            
        except Exception as e:
            self.logger.error(f"Error getting user sessions: {e}")
            return []
    
    def get_session_messages(self, user_id: int, session_id: str) -> List[ChatMessage]:
        """Get messages for a specific session (user isolation)"""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return []
            
            session = ChatSession.objects.filter(
                user=user,
                session_id=session_id,
                is_active=True
            ).first()
            
            if not session:
                self.logger.warning(f"Session {session_id} not found for user {user_id}")
                return []
            
            messages = ChatMessage.objects.filter(session=session).order_by('timestamp')
            return list(messages)
            
        except Exception as e:
            self.logger.error(f"Error getting session messages: {e}")
            return []
    
    def save_message(self, user_id: int, session_id: str, message_type: str, 
                    content: str, sources: List = None, processing_info: Dict = None) -> Optional[ChatMessage]:
        """Save a message to a session (user isolation)"""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return None
            
            # Get or create session
            session = ChatSession.objects.filter(
                user=user,
                session_id=session_id,
                is_active=True
            ).first()
            
            if not session:
                session = self.create_chat_session(user_id, session_id)
                if not session:
                    return None
            
            # Create message
            message = ChatMessage.objects.create(
                session=session,
                message_type=message_type,
                content=content,
                sources=sources or [],
                processing_info=processing_info or {}
            )
            
            # Update session timestamp
            session.updated_at = timezone.now()
            session.save()
            
            self.logger.info(f"Saved {message_type} message for user {user.username}")
            return message
            
        except Exception as e:
            self.logger.error(f"Error saving message: {e}")
            return None
    
    def save_conversation_context(self, user_id: int, session_id: str, context_data: List) -> bool:
        """Save conversation context for AI continuity (user isolation)"""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False
            
            session = ChatSession.objects.filter(
                user=user,
                session_id=session_id,
                is_active=True
            ).first()
            
            if not session:
                return False
            
            # Update or create context
            context, created = ChatConversationContext.objects.update_or_create(
                user=user,
                session=session,
                defaults={'context_data': context_data}
            )
            
            self.logger.info(f"Saved conversation context for user {user.username}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving conversation context: {e}")
            return False
    
    def get_conversation_context(self, user_id: int, session_id: str) -> List:
        """Get conversation context for a session (user isolation)"""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return []
            
            session = ChatSession.objects.filter(
                user=user,
                session_id=session_id,
                is_active=True
            ).first()
            
            if not session:
                return []
            
            context = ChatConversationContext.objects.filter(
                user=user,
                session=session
            ).first()
            
            return context.context_data if context else []
            
        except Exception as e:
            self.logger.error(f"Error getting conversation context: {e}")
            return []
    
    def delete_session(self, user_id: int, session_id: str) -> bool:
        """Delete a chat session (user isolation)"""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False
            
            session = ChatSession.objects.filter(
                user=user,
                session_id=session_id,
                is_active=True
            ).first()
            
            if not session:
                return False
            
            # Soft delete by marking as inactive
            session.is_active = False
            session.save()
            
            self.logger.info(f"Deleted session {session_id} for user {user.username}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting session: {e}")
            return False
    
    def clear_user_sessions(self, user_id: int) -> bool:
        """Clear all sessions for a user (user isolation)"""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False
            
            # Soft delete all user sessions
            ChatSession.objects.filter(user=user, is_active=True).update(is_active=False)
            
            self.logger.info(f"Cleared all sessions for user {user.username}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error clearing user sessions: {e}")
            return False
    
    def get_session_stats(self, user_id: int) -> Dict:
        """Get chat statistics for a user (user isolation)"""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return {}
            
            sessions = ChatSession.objects.filter(user=user, is_active=True)
            total_sessions = sessions.count()
            total_messages = ChatMessage.objects.filter(session__in=sessions).count()
            
            return {
                'total_sessions': total_sessions,
                'total_messages': total_messages,
                'user_id': user_id,
                'username': user.username
            }
            
        except Exception as e:
            self.logger.error(f"Error getting session stats: {e}")
            return {}
