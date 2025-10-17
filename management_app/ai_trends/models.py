from django.db import models
from django.utils import timezone


class TrendingTopics(models.Model):
    keyword = models.CharField(max_length=255)
    rising_topics = models.JSONField(default=list)  # Stores rising related topics as JSON
    top_topics = models.JSONField(default=list)  # Stores top related topics as JSON
    
    # Clerk user data (consistent with other apps)
    user_id = models.IntegerField(default=0)
    username = models.CharField(max_length=150, default='')
    email = models.EmailField(default='')
    
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'trending_topics'
        indexes = [
            models.Index(fields=['user_id', 'created_at']),
            models.Index(fields=['keyword']),
        ]

    def __str__(self):
        return f"Trending Topics - {self.keyword} - {self.username}"