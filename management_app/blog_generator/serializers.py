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
    blog_id = serializers.IntegerField(required=False, help_text="ID of the generated blog post")
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
            "image_urls", "created_at", "seo_optimized"
        ]
        read_only_fields = ["id", "created_at"]


class BlogDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogGeneral
        fields = [
            "id", "user_id", "username", "email",
            "topic", "content", "image_urls",
            "organization_id", "organization_name", "created_at",
            # SEO fields
            "seo_title", "seo_meta_description", "seo_keywords", "seo_slug", "canonical_url",
            "reading_time_minutes", "word_count", "content_hash",
            "html_content", "og_title", "og_description", "og_image_url", "twitter_card_type",
            "structured_data", "seo_optimized", "is_published", "published_at",
            "robots_index", "is_ai_generated", "tags", "categories", "updated_at"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class BlogDeleteSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    deleted_count = serializers.IntegerField(required=False)


class SEOHTMLResponseSerializer(serializers.Serializer):
    """Serializer for SEO HTML generation response."""
    status = serializers.CharField()
    message = serializers.CharField()
    blog_id = serializers.IntegerField()
    html_content = serializers.CharField(help_text="SEO-optimized HTML body content")
    full_html = serializers.CharField(help_text="Complete HTML document with head section")
    seo_metadata = serializers.DictField(help_text="SEO metadata (title, description, keywords, etc.)")
    structured_data = serializers.DictField(help_text="JSON-LD structured data schemas")
    social_metadata = serializers.DictField(help_text="Open Graph and Twitter Card metadata")
    html_validation = serializers.DictField(help_text="HTML structure validation results")
    optimization_applied = serializers.DictField(help_text="Details of optimizations applied")
    seo_score = serializers.IntegerField(help_text="Overall SEO score (0-100)")
