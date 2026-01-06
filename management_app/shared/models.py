from django.db import models


class BlogAPIKey(models.Model):
    """
    Secure API Key model for external blog retrieval.
    Stores only hashed versions of keys for security.
    """
    prefix = models.CharField(max_length=16, db_index=True)
    hashed_key = models.CharField(max_length=255)
    name = models.CharField(max_length=100)
    organization_name = models.CharField(max_length=255, db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "blog_api_key"
        verbose_name = "Blog API Key"
        verbose_name_plural = "Blog API Keys"

    def __str__(self):
        return f"{self.name} ({self.prefix}...)"
