from django.db import models
from django.utils import timezone


class ChatSession(models.Model):
    session_id = models.CharField(max_length=100, unique=True)
    user_id = models.IntegerField()
    username = models.CharField(max_length=150, default='')
    email = models.EmailField(default='')
    is_active = models.BooleanField(default=True)
    total_messages = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chat_sessions'
        ordering = ['-updated_at']

    def __str__(self):
        return f"Session {self.session_id} - {self.username}"


class ChatMessage(models.Model):
    MESSAGE_TYPE_CHOICES = [
        ('user', 'User Message'),
        ('assistant', 'Assistant Response'),
    ]
    
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPE_CHOICES)
    content = models.TextField()
    relevant_documents = models.JSONField(default=list, blank=True)  # Store relevant PDF documents found
    sources_used = models.JSONField(default=list, blank=True)  # Store document sources used in response
    processing_time = models.FloatField(default=0.0)  # Time taken to process in seconds
    tokens_used = models.IntegerField(default=0)  # Tokens used for this message
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'chat_messages'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.message_type}: {self.content[:50]}..."