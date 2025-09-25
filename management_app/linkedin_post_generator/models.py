from django.db import models
from django.utils import timezone


class LinkedinPost(models.Model):
    user_id = models.IntegerField()
    username = models.CharField(max_length=150, default='')
    email = models.EmailField(default='')
    topic = models.CharField(max_length=255)
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'linkedin_posts'

    def __str__(self):
        return f"LinkedIn Post - {self.topic}"


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

    def __str__(self):
        return f"LinkedIn Posting - {self.linkedin_username}"


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

    def __str__(self):
        return f"LinkedIn Analytics - {self.username}"