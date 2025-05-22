from django.db import models
from django.utils import timezone


class BlogGeneral(models.Model):
    user_id = models.IntegerField()
    username = models.CharField(max_length=150, default='')
    email = models.EmailField(default='')
    topic = models.CharField(max_length=255)
    content = models.TextField()
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