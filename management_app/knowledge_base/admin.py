from django.contrib import admin
from .models import Directory, PDFDocument


@admin.register(Directory)
class DirectoryAdmin(admin.ModelAdmin):
    """Admin interface for Directory model."""
    list_display = ('name', 'is_default', 'created_by_user_id', 'document_count', 'created_at')
    list_filter = ('is_default', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    
    def document_count(self, obj):
        """Display count of documents in directory."""
        return obj.documents.count()
    document_count.short_description = 'Documents'


@admin.register(PDFDocument)
class PDFDocumentAdmin(admin.ModelAdmin):
    """Admin interface for PDFDocument model."""
    list_display = ('file_name', 'directory', 'user_id', 'username', 'file_type', 'processing_status', 'pinecone_indexed', 'created_at')
    list_filter = ('directory', 'file_type', 'processing_status', 'pinecone_indexed', 'created_at')
    search_fields = ('file_name', 'username', 'email', 'content')
    readonly_fields = ('created_at', 'updated_at', 'pinecone_index_id', 'pinecone_namespace')
    
    fieldsets = (
        ('Directory & File Info', {
            'fields': ('directory', 'file_name', 'file_type', 'file_size', 'word_count')
        }),
        ('User Info', {
            'fields': ('user_id', 'username', 'email')
        }),
        ('Storage', {
            'fields': ('uploaded_url', 'processing_status')
        }),
        ('Pinecone Integration', {
            'fields': ('pinecone_indexed', 'pinecone_index_id', 'pinecone_namespace')
        }),
        ('Content', {
            'fields': ('content',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
