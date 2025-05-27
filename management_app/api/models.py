from django.db import models
from django.utils import timezone


class BlogGeneral(models.Model):
    user_id = models.IntegerField()
    username = models.CharField(max_length=150, default='')
    email = models.EmailField(default='')
    topic = models.CharField(max_length=255)
    content = models.TextField()
    sample_blog_url = models.URLField(max_length=500, blank=True, null=True)  # Optional sample blog URL
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'blogs_general'


class BlogAiNews(models.Model):
    news_week_start = models.DateField()
    username = models.CharField(max_length=150, default='')
    email = models.EmailField(default='')
    summary = models.TextField()
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'blogs_ai_news'


class LinkedinPost(models.Model):
    user_id = models.IntegerField()
    username = models.CharField(max_length=150, default='')
    email = models.EmailField(default='')
    topic = models.CharField(max_length=255)
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'linkedin_posts'


class ImageGeneration(models.Model):
    user_id = models.IntegerField()
    username = models.CharField(max_length=150, default='')
    email = models.EmailField(default='')
    prompt = models.TextField()
    image_url = models.URLField(max_length=500)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'image_generation'


class TrendingTopics(models.Model):
    keyword = models.CharField(max_length=255)
    rising_topics = models.JSONField(default=list)  # Stores rising related topics as JSON
    top_topics = models.JSONField(default=list)  # Stores top related topics as JSON
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'trending_topics'


class LinkedinAnalytics(models.Model):
    user_id = models.IntegerField()
    username = models.CharField(max_length=150, default='')
    email = models.EmailField(default='')
    linkedin_profile_id = models.CharField(max_length=255)  # LinkedIn profile identifier
    
    # Profile Analytics
    total_followers = models.IntegerField(default=0)
    total_posts = models.IntegerField(default=0)
    
    # Post Analytics (stored as JSON for flexibility)
    posts_analytics = models.JSONField(default=list)  # Array of post analytics objects
    
    # Summary metrics
    total_reactions = models.IntegerField(default=0)
    total_comments = models.IntegerField(default=0)
    total_reposts = models.IntegerField(default=0)
    total_impressions = models.IntegerField(default=0)
    total_engagement = models.IntegerField(default=0)
    
    # Metadata
    last_updated = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'linkedin_analytics'
        unique_together = ['user_id', 'linkedin_profile_id']  # Prevent duplicate entries 