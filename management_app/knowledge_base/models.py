from django.db import models
from django.utils import timezone


class Directory(models.Model):
    """Model for managing knowledge base directories"""
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    is_default = models.BooleanField(default=False)  # For default directories like artilence_projects, client_projects
    created_by_user_id = models.IntegerField(null=True, blank=True)  # User who created this directory
    
    # Organization-based isolation
    organization_id = models.CharField(max_length=255, null=True, blank=True, help_text="Clerk organization ID")
    organization_name = models.CharField(max_length=255, null=True, blank=True, help_text="Organization name/slug")
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'knowledge_base_directories'
        ordering = ['name']
        verbose_name_plural = 'Directories'
        # Ensure unique directory names within each organization
        unique_together = ['name', 'organization_id']
        indexes = [
            models.Index(fields=['organization_id', 'name']),
            models.Index(fields=['organization_name', 'name']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.organization_name or 'No Org'})"


class PDFDocument(models.Model):
    FILE_TYPE_CHOICES = [
        ('pdf', 'PDF'),
        ('docx', 'Word Document'),
        ('md', 'Markdown'),
        ('txt', 'Text File'),
    ]
    
    PROCESSING_STATUS_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('extracting', 'Extracting Content'),
        ('indexing', 'Indexing to Pinecone'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    # Directory relationship - nullable for migration compatibility
    directory = models.ForeignKey(
        Directory, 
        on_delete=models.CASCADE, 
        related_name='documents',
        help_text="Directory where this document is stored",
        null=True,  # Allow null for migration, will be populated by data migration
        blank=True
    )
    
    # User information
    user_id = models.IntegerField()
    username = models.CharField(max_length=150, default='')
    email = models.EmailField(default='')
    
    # Organization-based isolation
    organization_id = models.CharField(max_length=255, null=True, blank=True, help_text="Clerk organization ID")
    organization_name = models.CharField(max_length=255, null=True, blank=True, help_text="Organization name/slug")
    
    # File information
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES)
    content = models.TextField()  # Extracted text content
    
    # Storage URLs - Now supporting directory-based storage
    uploaded_url = models.URLField(max_length=500)  # S3 bucket URL with directory path
    
    # Processing status
    processing_status = models.CharField(max_length=20, choices=PROCESSING_STATUS_CHOICES, default='uploaded')
    
    # Pinecone integration
    pinecone_indexed = models.BooleanField(default=False)  # Track if indexed in Pinecone
    pinecone_index_id = models.CharField(max_length=100, blank=True, null=True)  # Pinecone vector ID prefix
    pinecone_namespace = models.CharField(max_length=100, blank=True, null=True)  # Pinecone namespace (always PDFS)
    
    # Metadata
    file_size = models.IntegerField(default=0)  # File size in bytes
    word_count = models.IntegerField(default=0)  # Number of words in content
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pdf_documents'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['directory', '-created_at']),
            models.Index(fields=['user_id', 'directory']),
            models.Index(fields=['organization_id', 'directory']),
            models.Index(fields=['organization_name', 'directory']),
            models.Index(fields=['organization_id', '-created_at']),
        ]

    def __str__(self):
        return f"{self.file_name} ({self.file_type}) - {self.directory.name}"
    
    def get_s3_key(self):
        """Get the S3 key for this document"""
        # Extract key from URL (assumes URL format: https://bucket-name.s3.region.amazonaws.com/key)
        if self.uploaded_url:
            try:
                parts = self.uploaded_url.split('.com/')
                if len(parts) > 1:
                    return parts[1]
            except:
                pass
        return None
