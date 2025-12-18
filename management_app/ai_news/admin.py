from django.contrib import admin
from .models import BlogAiNews


@admin.register(BlogAiNews)
class BlogAiNewsAdmin(admin.ModelAdmin):
    list_display = ('id', 'news_date', 'country', 'username', 'email', 'created_at')
    list_filter = ('news_date', 'country', 'created_at')
    search_fields = ('country', 'username', 'email', 'summary')
    readonly_fields = ('created_at',)
    ordering = ('-news_date', '-created_at')