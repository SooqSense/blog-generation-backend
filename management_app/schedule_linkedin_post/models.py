from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone


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

    def __str__(self):
        return f"Scheduled Post - {self.linkedin_username} - {self.scheduled_datetime}"