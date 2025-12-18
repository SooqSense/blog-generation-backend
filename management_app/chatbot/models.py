"""
Chat database models for persistent chat storage
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import json

User = get_user_model()


class ChatSession(models.Model):
    """Chat session model for storing chat sessions"""
    # Match the actual database schema
    session_id = models.CharField(max_length=100, unique=True)
    user_id = models.IntegerField(default=0)
    username = models.CharField(max_length=150, default='')
    email = models.EmailField(max_length=254, default='')
    is_active = models.BooleanField(default=True)
    total_messages = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'chat_sessions'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user_id', 'created_at']),
            models.Index(fields=['session_id']),
        ]
    
    def __str__(self):
        return f"Chat Session {self.session_id} - {self.username}"
    
    @property
    def message_count(self):
        return self.total_messages
    
    @property
    def last_message_time(self):
        return self.updated_at


class ChatMessage(models.Model):
    """Chat message model for storing individual messages"""
    MESSAGE_TYPES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]
    
    # Use session_id as ForeignKey to chat_sessions.id (bigint)
    session_id = models.ForeignKey(
        ChatSession, 
        on_delete=models.CASCADE, 
        db_column='session_id',
        related_name='messages'
    )
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES)
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    
    # Additional metadata for AI responses - match database schema
    relevant_documents = models.JSONField(default=list, blank=True)
    sources_used = models.JSONField(default=list, blank=True)
    processing_time = models.FloatField(default=0.0)
    tokens_used = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'chat_messages'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['session_id', 'created_at']),
            models.Index(fields=['message_type']),
        ]
    
    def __str__(self):
        return f"{self.message_type}: {self.content[:50]}..."
    
    @property
    def formatted_timestamp(self):
        return self.created_at.strftime('%H:%M:%S')


class ChatConversationContext(models.Model):
    """Model for storing conversation context for AI continuity"""
    user_id = models.IntegerField(default=0)
    session_id = models.CharField(max_length=100, default='')
    context_data = models.JSONField(default=list)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'chat_conversation_context'
        unique_together = ['user_id', 'session_id']
        indexes = [
            models.Index(fields=['user_id', 'session_id']),
        ]
    
    def __str__(self):
        return f"Context for user {self.user_id} - {self.session_id}"