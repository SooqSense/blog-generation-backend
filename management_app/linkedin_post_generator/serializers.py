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


# Request Serializers
class GenerateLinkedinPostRequestSerializer(serializers.Serializer):
    """Serializer for generate LinkedIn post request."""
    topic = serializers.CharField(max_length=500, help_text="The topic for the LinkedIn post")
    keywords = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Optional keywords to guide LinkedIn post generation"
    )
    generate_images = serializers.BooleanField(
        default=False,
        required=False,
        help_text="Whether to also generate images for the post"
    )
    image_count = serializers.IntegerField(
        default=1,
        min_value=1,
        max_value=5,
        required=False,
        help_text="How many images to generate (1-5)"
    )
    image_size = serializers.CharField(
        default='1920x1080',
        required=False,
        help_text="Target image size (e.g., 1920x1080)"
    )


class PostOnLinkedinRequestSerializer(serializers.Serializer):
    """Serializer for post on LinkedIn request."""
    content = serializers.CharField(help_text="The content to post on LinkedIn")
    image_urls = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        help_text="Optional list of image URLs to include with the post"
    )


class DeleteLinkedinPostsRequestSerializer(serializers.Serializer):
    """Serializer for delete LinkedIn posts request."""
    post_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Single LinkedIn post ID to delete"
    )
    post_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_null=True,
        default=list,
        help_text="Array of LinkedIn post IDs to delete (e.g., [1, 2, 3])"
    )

    def validate(self, data):
        if not data.get('post_id') and not data.get('post_ids'):
            raise serializers.ValidationError("Either post_id or post_ids must be provided")
        return data


class DeleteLinkedinPostingContentRequestSerializer(serializers.Serializer):
    """Serializer for delete LinkedIn posting content request."""
    content_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Single LinkedIn posting content ID to delete"
    )
    content_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_null=True,
        default=list,
        help_text="Array of LinkedIn posting content IDs to delete (e.g., [1, 2, 3])"
    )

    def validate(self, data):
        if not data.get('content_id') and not data.get('content_ids'):
            raise serializers.ValidationError("Either content_id or content_ids must be provided")
        return data
