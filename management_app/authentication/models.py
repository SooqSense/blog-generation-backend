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
    
    # Organization fields - Multiple organizations support
    organization_ids = models.JSONField(default=list, blank=True, help_text="List of Clerk organization IDs user belongs to")
    organization_names = models.JSONField(default=list, blank=True, help_text="List of organization display names (slugs)")
    organization_roles = models.JSONField(default=list, blank=True, help_text="List of user roles in each organization")
    
    # Legacy fields - kept for backward compatibility but will be deprecated
    organization_id = models.CharField(max_length=255, null=True, blank=True, help_text="[DEPRECATED] Primary organization ID")
    organization_name = models.CharField(max_length=255, null=True, blank=True, help_text="[DEPRECATED] Primary organization name")
    organization_role = models.CharField(max_length=100, null=True, blank=True, help_text="[DEPRECATED] Primary organization role")
    
    # Essential timestamp fields
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'users'
    
    def __str__(self):
        return f"{self.username} ({self.clerk_user_id})"
    
    # Organization helper methods
    def is_member_of_organization(self, organization_name: str) -> bool:
        """Check if user is a member of a specific organization by name/slug"""
        if not self.organization_names:
            return False
        return organization_name.lower() in [org.lower() for org in self.organization_names]
    
    def get_organization_role(self, organization_name: str) -> str:
        """Get user's role in a specific organization"""
        if not self.organization_names or not self.organization_roles:
            return None
        try:
            # Find index of organization
            org_index = next(
                (i for i, org in enumerate(self.organization_names) if org.lower() == organization_name.lower()),
                None
            )
            if org_index is not None and org_index < len(self.organization_roles):
                return self.organization_roles[org_index]
        except (ValueError, IndexError):
            pass
        return None
    
    def add_organization(self, org_id: str, org_name: str, org_role: str):
        """Add an organization to user's organizations"""
        if not self.organization_ids:
            self.organization_ids = []
        if not self.organization_names:
            self.organization_names = []
        if not self.organization_roles:
            self.organization_roles = []
        
        # Check if organization already exists
        if org_id not in self.organization_ids:
            self.organization_ids.append(org_id)
            self.organization_names.append(org_name)
            self.organization_roles.append(org_role)
    
    def update_organization_role(self, org_name: str, new_role: str):
        """Update user's role in a specific organization"""
        if not self.organization_names or not self.organization_roles:
            return False
        try:
            org_index = next(
                (i for i, org in enumerate(self.organization_names) if org.lower() == org_name.lower()),
                None
            )
            if org_index is not None and org_index < len(self.organization_roles):
                self.organization_roles[org_index] = new_role
                return True
        except (ValueError, IndexError):
            pass
        return False
