from django.db import models
from management_app.blog_generator.models import BlogGeneral

class AnalyticSession(models.Model):
    """Tracks an individual user session potentially browsing multiple blogs."""
    session_key = models.CharField(max_length=255, unique=True, help_text="Unique session identifier (UUID)")
    ip_hash = models.CharField(max_length=64, help_text="Hashed IP address for privacy-safe uniqueness tracking")
    user_agent = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Session {self.session_key[:8]}"

class AnalyticEvent(models.Model):
    """Logs specific granular interactions."""
    EVENT_TYPES = [
        ('pixel_load', 'Pixel Load (Initial View)'),
        ('heartbeat', 'Heartbeat (Active Reading)'),
        ('scroll', 'Scroll Depth Update'),
        ('visibility', 'Page Visibility Change')
    ]

    blog = models.ForeignKey(BlogGeneral, on_delete=models.CASCADE, related_name='analytics_events')
    session = models.ForeignKey(AnalyticSession, on_delete=models.SET_NULL, null=True, related_name='events')
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    
    # Granular data
    scroll_percent = models.IntegerField(default=0, help_text="Percentage of page scrolled")
    time_delta_ms = models.IntegerField(default=0, help_text="Time elapsed since last heartbeat in ms")
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

class BlogAggregate(models.Model):
    """Stores pre-computed statistics for fast retrieval."""
    blog = models.OneToOneField(BlogGeneral, on_delete=models.CASCADE, related_name='analytics_aggregate')
    
    total_views = models.PositiveIntegerField(default=0)
    unique_views = models.PositiveIntegerField(default=0)
    engaged_reads = models.PositiveIntegerField(default=0)
    
    avg_scroll_depth = models.FloatField(default=0.0, help_text="Average scroll depth percentage")
    avg_time_on_page_sec = models.FloatField(default=0.0, help_text="Average time on page in seconds")
    
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Aggregates for Blog {self.blog_id}"
