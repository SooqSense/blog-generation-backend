from django.contrib import admin
from .models import ChatSession, ChatMessage, ChatConversationContext

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'user_id', 'username', 'created_at', 'updated_at', 'is_active', 'total_messages']
    list_filter = ['is_active', 'created_at', 'updated_at']
    search_fields = ['session_id', 'username', 'email']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-updated_at']

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'message_type', 'content_preview', 'created_at']
    list_filter = ['message_type', 'created_at']
    search_fields = ['content', 'session_id__session_id']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content Preview'

@admin.register(ChatConversationContext)
class ChatConversationContextAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'session_id', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user_id', 'session_id']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-updated_at']
