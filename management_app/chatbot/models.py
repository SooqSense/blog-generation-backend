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
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions')
    session_id = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['session_id']),
        ]
    
    def __str__(self):
        return f"Chat Session {self.session_id} - {self.user.username}"
    
    @property
    def message_count(self):
        return self.messages.count()
    
    @property
    def last_message_time(self):
        last_message = self.messages.order_by('-created_at').first()
        return last_message.created_at if last_message else self.created_at


class ChatMessage(models.Model):
    """Chat message model for storing individual messages"""
    MESSAGE_TYPES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]
    
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES)
    content = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    
    # Additional metadata for AI responses
    sources = models.JSONField(default=list, blank=True)
    processing_info = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['session', 'timestamp']),
            models.Index(fields=['message_type']),
        ]
    
    def __str__(self):
        return f"{self.message_type}: {self.content[:50]}..."
    
    @property
    def formatted_timestamp(self):
        return self.timestamp.strftime('%H:%M:%S')


class ChatConversationContext(models.Model):
    """Model for storing conversation context for AI continuity"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_contexts')
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='contexts')
    context_data = models.JSONField(default=list)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'session']
        indexes = [
            models.Index(fields=['user', 'session']),
        ]
    
    def __str__(self):
        return f"Context for {self.user.username} - {self.session.session_id}"