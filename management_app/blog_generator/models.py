from django.db import models
from django.utils import timezone


class BlogGeneral(models.Model):
    user_id = models.IntegerField()
    username = models.CharField(max_length=150, default='')
    email = models.EmailField(default='')
    topic = models.CharField(max_length=255)
    content = models.TextField()
    sample_blog_url = models.URLField(max_length=500, blank=True, null=True)  # Optional sample blog URL
    website_urls = models.JSONField(default=list, blank=True)  # Optional list of website URLs for content extraction
    image_prompts = models.JSONField(default=list, blank=True)  # Store generated image prompts
    prompts_count = models.IntegerField(default=0)  # Number of generated prompts (deprecated - use image_urls length)
    image_urls = models.JSONField(default=list, blank=True)  # Store S3 bucket URLs for section-specific images
    
    # Organization-based isolation
    organization_id = models.CharField(max_length=255, null=True, blank=True, help_text="Clerk organization ID")
    organization_name = models.CharField(max_length=255, null=True, blank=True, help_text="Organization name/slug")
    
    # SEO Metadata Fields
    seo_title = models.CharField(max_length=60, blank=True, null=True, help_text="SEO-optimized title (50-60 chars)")
    seo_meta_description = models.TextField(max_length=160, blank=True, null=True, help_text="Meta description (150-160 chars)")
    seo_keywords = models.JSONField(default=list, blank=True, help_text="SEO keywords array")
    seo_slug = models.SlugField(max_length=100, blank=True, null=True, unique=True, help_text="URL-friendly slug")
    canonical_url = models.URLField(max_length=500, blank=True, null=True, help_text="Canonical URL for the blog post")
    
    # Content Metrics
    reading_time_minutes = models.IntegerField(default=0, help_text="Estimated reading time in minutes")
    word_count = models.IntegerField(default=0, help_text="Total word count")
    content_hash = models.CharField(max_length=64, blank=True, null=True, help_text="SHA256 hash for duplicate detection")
    
    # HTML Content
    html_content = models.TextField(blank=True, null=True, help_text="SEO-optimized HTML content")
    
    # Social Media Metadata
    og_title = models.CharField(max_length=100, blank=True, null=True, help_text="Open Graph title")
    og_description = models.TextField(max_length=200, blank=True, null=True, help_text="Open Graph description")
    og_image_url = models.URLField(max_length=500, blank=True, null=True, help_text="Open Graph image URL")
    twitter_card_type = models.CharField(max_length=50, default="summary_large_image", help_text="Twitter Card type")
    
    # Structured Data
    structured_data = models.JSONField(default=dict, blank=True, help_text="JSON-LD structured data schemas")
    
    # Publishing Status
    seo_optimized = models.BooleanField(default=False, help_text="Whether SEO optimization has been applied")
    is_published = models.BooleanField(default=False, help_text="Whether the blog is published")
    published_at = models.DateTimeField(blank=True, null=True, help_text="Publication date")
    robots_index = models.BooleanField(default=True, help_text="Whether search engines should index (noindex if False)")
    is_ai_generated = models.BooleanField(default=True, help_text="Mark as AI-generated content for transparency")
    
    # Tags and Categories (for internal linking)
    tags = models.JSONField(default=list, blank=True, help_text="Tags for categorization and internal linking")
    categories = models.JSONField(default=list, blank=True, help_text="Categories for taxonomy")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "blog_general"

    def __str__(self):
        return f"{self.topic} - {self.organization_name}"