from django.db import models
from django.utils import timezone


class TrendingTopics(models.Model):
    keyword = models.CharField(max_length=255)
    rising_topics = models.JSONField(default=list)  # Stores rising related topics as JSON
    top_topics = models.JSONField(default=list)  # Stores top related topics as JSON
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'trending_topics'

    def __str__(self):
        return f"Trending Topics - {self.keyword}"