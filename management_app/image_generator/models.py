from django.db import models
from django.utils import timezone


class ImageGeneration(models.Model):
    user_id = models.IntegerField()
    username = models.CharField(max_length=150, default='')
    email = models.EmailField(default='')
    prompt = models.TextField()
    image_url = models.URLField(max_length=500)  # Keep for backward compatibility
    image_urls = models.JSONField(default=list, blank=True)  # Store multiple image URLs
    images_count = models.IntegerField(default=1)  # Number of images generated
    enhanced_prompts = models.JSONField(default=list, blank=True)  # Store enhanced prompts for each image
    generation_method = models.CharField(max_length=50, default='flux')  # Generation method used
    image_style = models.CharField(max_length=50, default='professional_cinematic')  # Style of images
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'image_generation'

    def __str__(self):
        return f"Image Generation - {self.prompt[:50]}..."


class ImageEditing(models.Model):
    user_id = models.IntegerField()
    username = models.CharField(max_length=150, default='')
    email = models.EmailField(default='')
    prompt = models.TextField()  # Edit instruction/prompt
    keywords = models.CharField(max_length=500, blank=True, default='')  # Optional keywords
    uploaded_image = models.TextField()  # Store base64 encoded original image
    image_url = models.URLField(max_length=500)  # URL of the edited result image
    enhanced_prompt = models.TextField(blank=True, default='')  # AI-optimized prompt used
    edit_status = models.CharField(max_length=50, default='success')  # success, failed, processing
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'image_editing'

    def __str__(self):
        return f"Image Editing - {self.prompt[:50]}..."