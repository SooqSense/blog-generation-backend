from rest_framework import serializers
from .models import LinkedinPost, LinkedinPostingContent, LinkedinAnalytics


# LinkedIn Post Serializers
class LinkedinPostListSerializer(serializers.ModelSerializer):
    """Serializer for listing LinkedIn posts with basic information."""
    
    class Meta:
        model = LinkedinPost
        fields = [
            'id', 'topic', 'username', 'email', 'organization_id', 'organization_name',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class LinkedinPostDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed LinkedIn post information."""
    
    class Meta:
        model = LinkedinPost
        fields = [
            'id', 'user_id', 'username', 'email', 'topic', 'content',
            'organization_id', 'organization_name', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class LinkedinPostDeleteSerializer(serializers.Serializer):
    """Serializer for LinkedIn post deletion response."""
    success = serializers.BooleanField()
    message = serializers.CharField()
    deleted_count = serializers.IntegerField(required=False)


class LinkedinPostDownloadSerializer(serializers.Serializer):
    """Serializer for LinkedIn post download response."""
    success = serializers.BooleanField()
    message = serializers.CharField()
    download_url = serializers.URLField(required=False)
    file_name = serializers.CharField(required=False)


# LinkedIn Posting Content Serializers
class LinkedinPostingContentListSerializer(serializers.ModelSerializer):
    """Serializer for listing LinkedIn posting content with basic information."""
    
    class Meta:
        model = LinkedinPostingContent
        fields = [
            'id', 'linkedin_username', 'post_status', 'post_type', 'images_count',
            'organization_id', 'organization_name', 'post_date', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class LinkedinPostingContentDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed LinkedIn posting content information."""
    
    class Meta:
        model = LinkedinPostingContent
        fields = [
            'id', 'user_id', 'username', 'email', 'linkedin_profile_id', 'linkedin_username',
            'content', 'post_date', 'linkedin_post_id', 'post_status', 'image_urls',
            'images_count', 'post_type', 'organization_id', 'organization_name', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class LinkedinPostingContentDeleteSerializer(serializers.Serializer):
    """Serializer for LinkedIn posting content deletion response."""
    success = serializers.BooleanField()
    message = serializers.CharField()
    deleted_count = serializers.IntegerField(required=False)


class LinkedinPostingContentDownloadSerializer(serializers.Serializer):
    """Serializer for LinkedIn posting content download response."""
    success = serializers.BooleanField()
    message = serializers.CharField()
    download_url = serializers.URLField(required=False)
    file_name = serializers.CharField(required=False)


# LinkedIn Analytics Serializers
class LinkedinAnalyticsListSerializer(serializers.ModelSerializer):
    """Serializer for listing LinkedIn analytics with basic information."""
    
    class Meta:
        model = LinkedinAnalytics
        fields = [
            'id', 'linkedin_profile_id', 'total_followers', 'total_posts',
            'total_reactions', 'total_comments', 'total_reposts', 'total_impressions',
            'organization_id', 'organization_name', 'last_updated', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class LinkedinAnalyticsDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed LinkedIn analytics information."""
    
    class Meta:
        model = LinkedinAnalytics
        fields = [
            'id', 'user_id', 'username', 'email', 'linkedin_profile_id',
            'total_followers', 'total_posts', 'posts_analytics', 'total_reactions',
            'total_comments', 'total_reposts', 'total_impressions', 'total_engagement',
            'organization_id', 'organization_name', 'last_updated', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class LinkedinAnalyticsDeleteSerializer(serializers.Serializer):
    """Serializer for LinkedIn analytics deletion response."""
    success = serializers.BooleanField()
    message = serializers.CharField()
    deleted_count = serializers.IntegerField(required=False)


class ErrorResponseSerializer(serializers.Serializer):
    """Generic error response serializer."""
    error = serializers.CharField()
