from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class User(AbstractUser):
    """Custom User model with Clerk integration only"""
    
    # Remove fields that don't exist in the database
    date_joined = None
    
    # Clerk specific fields only
    clerk_user_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    
    # User profile fields
    first_name = models.CharField(max_length=150, null=True, blank=True, help_text="User's first name")
    last_name = models.CharField(max_length=150, null=True, blank=True, help_text="User's last name")
    
    # Organization fields
    organization_id = models.CharField(max_length=255, null=True, blank=True, help_text="Clerk organization ID")
    organization_name = models.CharField(max_length=255, null=True, blank=True, help_text="Organization display name")
    organization_role = models.CharField(max_length=100, null=True, blank=True, help_text="User role in organization")
    
    # Essential timestamp fields
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'users'
    
    def __str__(self):
        return f"{self.username} ({self.clerk_user_id})"
