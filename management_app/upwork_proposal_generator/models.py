from django.db import models
from django.contrib.auth import get_user_model
import json

User = get_user_model()

class UpworkProposal(models.Model):
    """Model to store Upwork proposal generation requests and results."""
    
    # Input parameters
    client_name = models.CharField(max_length=255, blank=True, null=True, help_text="Name of the client contact person (optional)")
    company_name = models.CharField(max_length=255, blank=True, null=True, help_text="Name of the client's company (optional)")
    title = models.CharField(max_length=500)
    requirements = models.TextField()
    company_website_links = models.JSONField(default=list)  # List of website URLs
    
    # Personal information fields
    your_name = models.CharField(max_length=255, blank=True, null=True, help_text="Your full name for the proposal signature")
    upwork_profile_link = models.URLField(blank=True, null=True, help_text="Your Upwork profile URL")
    contact_information = models.TextField(blank=True, null=True, help_text="Your contact details (email, phone, etc.)")
    
    # Generated content
    proposal_content = models.TextField(blank=True, null=True)
    
    # Metadata
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Status tracking
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('generating', 'Generating'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'upwork_proposals'
        ordering = ['-created_at']
    
    def __str__(self):
        company_part = self.company_name if self.company_name else "Unknown Company"
        return f"{company_part} - {self.title[:50]}..."
    
    def set_website_links(self, links):
        """Helper method to set website links from a list."""
        if isinstance(links, list):
            self.company_website_links = links
        elif isinstance(links, str):
            # Handle single string or comma-separated strings
            self.company_website_links = [link.strip() for link in links.split(',') if link.strip()]
        else:
            self.company_website_links = []
    
    def get_website_links(self):
        """Helper method to get website links as a list."""
        return self.company_website_links or []
