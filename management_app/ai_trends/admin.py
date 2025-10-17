from django.contrib import admin
from .models import TrendingTopics


@admin.register(TrendingTopics)
class TrendingTopicsAdmin(admin.ModelAdmin):
    list_display = ['keyword', 'user_id', 'username', 'created_at']
    list_filter = ['created_at']
    search_fields = ['keyword', 'username', 'email']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
