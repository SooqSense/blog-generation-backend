from django.db import models
from django.utils import timezone


class BlogGeneral(models.Model):
    user_id = models.IntegerField()
    username = models.CharField(max_length=150, default='')
    email = models.EmailField(default='')
    topic = models.CharField(max_length=255)
    content = models.TextField()
    sample_blog_url = models.URLField(max_length=500, blank=True, null=True)  # Optional sample blog URL
    image_prompts = models.JSONField(default=list, blank=True)  # Store generated image prompts
    prompts_count = models.IntegerField(default=0)  # Number of generated prompts (deprecated - use image_urls length)
    image_urls = models.JSONField(default=list, blank=True)  # Store S3 bucket URLs for section-specific images
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'blogs_general'

    def __str__(self):
        return f"{self.topic} - {self.username}"