from rest_framework import serializers
from .models import BlogAiNews


class DailyAINewsRequestSerializer(serializers.Serializer):
    country = serializers.CharField(
        max_length=10,
        required=False,
        default="us",
        help_text="Country code for news filtering (e.g., 'us', 'uk', 'in', 'ca'). Default is 'us'."
    )
    keywords = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=lambda: ["artificial intelligence", "machine learning"],
        help_text="List of keywords to search for AI news. Default includes 'artificial intelligence' and 'machine learning'."
    )
    num_results = serializers.IntegerField(
        required=False,
        default=10,
        min_value=5,
        max_value=20,
        help_text="Number of news articles to fetch (5-20). Default is 10."
    )


class NewsSourceSerializer(serializers.Serializer):
    title = serializers.CharField(help_text="Title of the news article")
    source = serializers.CharField(help_text="Source publication name")
    link = serializers.CharField(help_text="URL to the original article")
    snippet = serializers.CharField(help_text="Brief description/snippet of the article")
    date = serializers.CharField(required=False, allow_blank=True, help_text="Publication date")
    position = serializers.IntegerField(required=False, default=0, help_text="Position in search results")


class DailyAINewsResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    country = serializers.CharField()
    country_name = serializers.CharField()
    keywords = serializers.ListField(child=serializers.CharField())
    news_date = serializers.DateField()
    articles_count = serializers.IntegerField()
    sources = serializers.ListField(child=NewsSourceSerializer(), help_text="Source articles used for generating the news")
    content = serializers.JSONField(help_text="Structured JSON representation of the news content")
    raw_content = serializers.CharField(help_text="Clean markdown content of the news, optimized for copying and pasting into markdown viewers")


class ErrorResponseSerializer(serializers.Serializer):
    error = serializers.CharField()


# List and Management Serializers for AI News
class AINewsListSerializer(serializers.ModelSerializer):
    """Serializer for listing AI news with basic information."""
    
    class Meta:
        model = BlogAiNews
        fields = [
            'id', 'news_date', 'country', 'username', 'email', 'organization_id', 'organization_name',
            'keywords', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class AINewsDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed AI news information."""
    
    class Meta:
        model = BlogAiNews
        fields = [
            'id', 'user_id', 'username', 'email', 'news_date', 'country', 'keywords',
            'summary', 'content', 'sources', 'organization_id', 'organization_name', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class AINewsDeleteSerializer(serializers.Serializer):
    """Serializer for AI news deletion response."""
    success = serializers.BooleanField()
    message = serializers.CharField()
    deleted_count = serializers.IntegerField(required=False)


