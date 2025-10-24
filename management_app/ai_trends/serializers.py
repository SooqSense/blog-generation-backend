from rest_framework import serializers
from .models import TrendingTopics


# AI Trends Serializers
class TrendingTopicsListSerializer(serializers.ModelSerializer):
    """Serializer for listing trending topics with basic information."""
    
    class Meta:
        model = TrendingTopics
        fields = [
            'id', 'keyword', 'username', 'email', 'organization_id', 'organization_name',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class TrendingTopicsDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed trending topics information."""
    
    class Meta:
        model = TrendingTopics
        fields = [
            'id', 'user_id', 'username', 'email', 'keyword', 'rising_topics', 'top_topics',
            'organization_id', 'organization_name', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class TrendingTopicsDeleteSerializer(serializers.Serializer):
    """Serializer for trending topics deletion response."""
    success = serializers.BooleanField()
    message = serializers.CharField()
    deleted_count = serializers.IntegerField(required=False)


class ErrorResponseSerializer(serializers.Serializer):
    """Generic error response serializer."""
    error = serializers.CharField()
