from django.db import models
from django.utils import timezone


class BlogAiNews(models.Model):
    user_id = models.IntegerField(null=True, blank=True)
    username = models.CharField(max_length=150, default='')
    email = models.EmailField(default='')
    news_date = models.DateField()  # Keep original field name as requested
    country = models.CharField(max_length=100, default='', blank=True)  # Country for news filtering
    keywords = models.JSONField(default=list, blank=True)  # Keywords used for news search
    summary = models.TextField()
    content = models.TextField()  # Markdown content
    sources = models.JSONField(default=list, blank=True)  # Source articles with title, link, source, etc.
    
    # Organization-based isolation
    organization_id = models.CharField(max_length=255, null=True, blank=True, help_text="Clerk organization ID")
    organization_name = models.CharField(max_length=255, null=True, blank=True, help_text="Organization name/slug")
    
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'blogs_ai_news'

    def __str__(self):
        return f"AI News - {self.news_date} - {self.country}"