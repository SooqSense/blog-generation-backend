"""
Serializers for Knowledge Base API.
"""

from rest_framework import serializers
from .models import Directory, PDFDocument


class DirectorySerializer(serializers.ModelSerializer):
    """Serializer for Directory model."""
    
    document_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Directory
        fields = [
            'id', 
            'name', 
            'description', 
            'is_default', 
            'created_by_user_id',
            'organization_id',
            'organization_name',
            'document_count',
            'created_at', 
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'document_count']
    
    def get_document_count(self, obj):
        """Get the count of documents in this directory."""
        return obj.documents.count()


class PDFDocumentSerializer(serializers.ModelSerializer):
    """Serializer for PDFDocument model."""
    
    directory_name = serializers.CharField(source='directory.name', read_only=True)
    
    class Meta:
        model = PDFDocument
        fields = [
            'id',
            'directory',
            'directory_name',
            'user_id',
            'username',
            'email',
            'organization_id',
            'organization_name',
            'file_name',
            'file_type',
            'content',
            'uploaded_url',
            'processing_status',
            'pinecone_indexed',
            'pinecone_index_id',
            'pinecone_namespace',
            'file_size',
            'word_count',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'directory_name',
            'organization_id',
            'organization_name',
            'processing_status',
            'pinecone_indexed',
            'pinecone_index_id',
            'pinecone_namespace',
            'created_at',
            'updated_at'
        ]


class PDFDocumentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing documents (without full content)."""
    
    directory_name = serializers.CharField(source='directory.name', read_only=True)
    
    class Meta:
        model = PDFDocument
        fields = [
            'id',
            'directory',
            'directory_name',
            'user_id',
            'username',
            'organization_id',
            'organization_name',
            'file_name',
            'file_type',
            'uploaded_url',
            'processing_status',
            'pinecone_indexed',
            'file_size',
            'word_count',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'directory_name', 'organization_id', 'organization_name', 'created_at', 'updated_at']

