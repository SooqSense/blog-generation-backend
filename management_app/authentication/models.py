from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class User(AbstractUser):
    """Custom User model with Clerk integration only"""
    
    # Remove fields that don't exist in the database
    first_name = None
    last_name = None
    date_joined = None
    
    # Clerk specific fields only
    clerk_user_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    
    # Essential timestamp fields
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'users'
    
    def __str__(self):
        return f"{self.username} ({self.clerk_user_id})"
