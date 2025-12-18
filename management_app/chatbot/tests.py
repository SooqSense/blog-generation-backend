from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import ChatSession, ChatMessage, ChatConversationContext

User = get_user_model()

class ChatbotModelsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.session = ChatSession.objects.create(
            user=self.user,
            session_id='test-session-123',
            title='Test Session'
        )
    
    def test_chat_session_creation(self):
        """Test ChatSession model creation"""
        self.assertEqual(self.session.user, self.user)
        self.assertEqual(self.session.session_id, 'test-session-123')
        self.assertEqual(self.session.title, 'Test Session')
        self.assertTrue(self.session.is_active)
    
    def test_chat_message_creation(self):
        """Test ChatMessage model creation"""
        message = ChatMessage.objects.create(
            session=self.session,
            message_type='user',
            content='Hello, world!'
        )
        self.assertEqual(message.session, self.session)
        self.assertEqual(message.message_type, 'user')
        self.assertEqual(message.content, 'Hello, world!')
    
    def test_chat_conversation_context_creation(self):
        """Test ChatConversationContext model creation"""
        context = ChatConversationContext.objects.create(
            user=self.user,
            session=self.session,
            context_data=['context1', 'context2']
        )
        self.assertEqual(context.user, self.user)
        self.assertEqual(context.session, self.session)
        self.assertEqual(context.context_data, ['context1', 'context2'])
    
    def test_user_isolation(self):
        """Test that users only see their own data"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        
        # Create session for other user
        other_session = ChatSession.objects.create(
            user=other_user,
            session_id='other-session-456',
            title='Other Session'
        )
        
        # Test that user only sees their own sessions
        user_sessions = ChatSession.objects.filter(user=self.user)
        self.assertEqual(user_sessions.count(), 1)
        self.assertEqual(user_sessions.first(), self.session)
        
        # Test that other user's sessions are not visible
        self.assertNotIn(other_session, user_sessions)
