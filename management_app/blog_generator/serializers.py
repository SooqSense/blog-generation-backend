from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from urllib.parse import urlparse
from .models import BlogGeneral


class BlogRequestSerializer(serializers.Serializer):
    topic = serializers.CharField(
        max_length=255,
        help_text="The main topic for the blog post."
    )
    blog_type = serializers.ChoiceField(
        choices=["News", "Comparison"],
        default="News",
        help_text="Choose 'News' for news-style blogs or 'Comparison' for analytical comparisons."
    )
    length_min = serializers.IntegerField(
        default=800,
        min_value=300,
        max_value=5000,
        help_text="Minimum word count for the blog."
    )
    length_max = serializers.IntegerField(
        default=1500,
        min_value=500,
        max_value=10000,
        help_text="Maximum word count for the blog."
    )
    generate_images = serializers.BooleanField(
        default=True,
        help_text="Set to true to generate contextual section images for the blog."
    )

    def validate(self, data):
        if data["length_min"] >= data["length_max"]:
            raise serializers.ValidationError("length_min must be less than length_max.")
        return data


class SourceSerializer(serializers.Serializer):
    url = serializers.URLField()
    title = serializers.CharField()
    type = serializers.CharField(default="research_source")


class BlogResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    topic = serializers.CharField()
    blog_type = serializers.CharField()
    length_min = serializers.IntegerField()
    length_max = serializers.IntegerField()
    generate_images = serializers.BooleanField()
    image_urls = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        default=list,
        help_text="S3 URLs of generated blog section images."
    )
    images_count = serializers.IntegerField(default=0)
    research_sources = serializers.ListField(
        child=SourceSerializer(),
        required=False,
        default=list
    )
    sources_count = serializers.IntegerField(default=0)
    content = serializers.JSONField(help_text="Structured JSON representation of the blog.")
    raw_content = serializers.CharField(help_text="Markdown blog content with embedded images.")


class ErrorResponseSerializer(serializers.Serializer):
    error = serializers.CharField()


class BlogListSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogGeneral
        fields = [
            "id", "topic", "username", "email",
            "organization_id", "organization_name",
            "image_urls", "created_at"
        ]
        read_only_fields = ["id", "created_at"]


class BlogDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogGeneral
        fields = [
            "id", "user_id", "username", "email",
            "topic", "content", "image_urls",
            "organization_id", "organization_name", "created_at"
        ]
        read_only_fields = ["id", "created_at"]


class BlogDeleteSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    deleted_count = serializers.IntegerField(required=False)
