from django.db import models
from django.utils import timezone


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
    
    user_id = models.IntegerField()
    username = models.CharField(max_length=150, default='')
    email = models.EmailField(default='')
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES)
    content = models.TextField()  # Extracted text content
    uploaded_url = models.URLField(max_length=500)  # S3 bucket URL
    processing_status = models.CharField(max_length=20, choices=PROCESSING_STATUS_CHOICES, default='uploaded')
    pinecone_indexed = models.BooleanField(default=False)  # Track if indexed in Pinecone
    pinecone_index_id = models.CharField(max_length=100, blank=True, null=True)  # Pinecone vector ID
    file_size = models.IntegerField(default=0)  # File size in bytes
    word_count = models.IntegerField(default=0)  # Number of words in content
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pdf_documents'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.file_name} ({self.file_type})"