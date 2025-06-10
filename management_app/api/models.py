from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone


class BlogGeneral(models.Model):
    user_id = models.IntegerField()
    username = models.CharField(max_length=150, default='')
    email = models.EmailField(default='')
    topic = models.CharField(max_length=255)
    content = models.TextField()
    sample_blog_url = models.URLField(max_length=500, blank=True, null=True)  # Optional sample blog URL
    image_prompts = models.JSONField(default=list, blank=True)  # Store generated image prompts
    prompts_count = models.IntegerField(default=0)  # Number of generated prompts
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'blogs_general'


class BlogAiNews(models.Model):
    user_id = models.IntegerField(null=True, blank=True)
    username = models.CharField(max_length=150, default='')
    email = models.EmailField(default='')
    news_date = models.DateField()  # Keep original field name as requested
    country = models.CharField(max_length=100, default='', blank=True)  # Country for news filtering
    keywords = models.JSONField(default=list, blank=True)  # Keywords used for news search
    summary = models.TextField()
    content = models.TextField()  # Markdown content
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


class LinkedinPostingContent(models.Model):
    user_id = models.IntegerField()
    username = models.CharField(max_length=150, default='')  # User's app username
    email = models.EmailField(default='')
    linkedin_profile_id = models.CharField(max_length=255)  # LinkedIn profile ID
    linkedin_username = models.CharField(max_length=150, default='')  # LinkedIn profile username
    content = models.TextField()  # The content that was posted
    post_date = models.DateTimeField(default=timezone.now)  # When the post was made
    linkedin_post_id = models.CharField(max_length=255, blank=True, null=True)  # LinkedIn's post ID (if available)
    post_status = models.CharField(max_length=50, default='success')  # success, failed, pending
    image_urls = models.JSONField(default=list, blank=True)  # Store image URLs that were posted
    images_count = models.IntegerField(default=0)  # Number of images posted
    post_type = models.CharField(max_length=20, default='text')  # 'text' or 'image'
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'linkedin_posting_content'


class ImageGeneration(models.Model):
    user_id = models.IntegerField()
    username = models.CharField(max_length=150, default='')
    email = models.EmailField(default='')
    prompt = models.TextField()
    image_url = models.URLField(max_length=500)  # Keep for backward compatibility
    image_urls = models.JSONField(default=list, blank=True)  # Store multiple image URLs
    images_count = models.IntegerField(default=1)  # Number of images generated
    enhanced_prompts = models.JSONField(default=list, blank=True)  # Store enhanced prompts for each image
    generation_method = models.CharField(max_length=50, default='sora_style')  # Generation method used
    image_style = models.CharField(max_length=50, default='professional_cinematic')  # Style of images
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


class SchedulePosts(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('posted', 'Posted'),
        ('partially_posted', 'Partially Posted'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    user_id = models.IntegerField()
    username = models.CharField(max_length=150, default='')
    email = models.EmailField(default='')
    linkedin_profile_id = models.CharField(max_length=255)  # LinkedIn profile ID for posting
    linkedin_username = models.CharField(max_length=150, default='')  # LinkedIn profile username
    
    # Post content
    content = ArrayField(models.TextField(), default=list)  # The LinkedIn post content as array
    image_urls = models.JSONField(default=list, blank=True)  # Optional images to post
    images_count = models.IntegerField(default=0)  # Number of images
    post_type = models.CharField(max_length=20, default='text')  # 'text' or 'image'
    
    # Scheduling details
    scheduled_datetime = models.DateTimeField()  # When to post
    user_timezone = models.CharField(max_length=50, default='UTC')  # User's timezone
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    celery_task_id = models.CharField(max_length=255, blank=True, null=True)  # Celery task ID for cancellation
    
    # Result tracking
    linkedin_post_id = models.CharField(max_length=255, blank=True, null=True)  # LinkedIn's post ID after posting
    posted_at = models.DateTimeField(blank=True, null=True)  # Actual posting time
    error_message = models.TextField(blank=True, null=True)  # Error details if failed
    
    # Metadata
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'schedule_posts'
        ordering = ['-scheduled_datetime'] 