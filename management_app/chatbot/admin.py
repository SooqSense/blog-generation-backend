from django.contrib import admin
from .models import ChatSession, ChatMessage, ChatConversationContext

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'user', 'title', 'created_at', 'updated_at', 'is_active']
    list_filter = ['is_active', 'created_at', 'updated_at']
    search_fields = ['session_id', 'user__username', 'title']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-updated_at']

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['session', 'message_type', 'content_preview', 'timestamp']
    list_filter = ['message_type', 'timestamp']
    search_fields = ['content', 'session__session_id']
    readonly_fields = ['timestamp']
    ordering = ['-timestamp']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content Preview'

@admin.register(ChatConversationContext)
class ChatConversationContextAdmin(admin.ModelAdmin):
    list_display = ['user', 'session', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user__username', 'session__session_id']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-updated_at']
