import markdown
from rest_framework import serializers
from management_app.blog_generator.models import BlogGeneral

class ExternalBlogSerializer(serializers.ModelSerializer):
    """
    Serializer for external API consumption moved to shared app.
    Strictly follows the requested 'Example Formate'.
    """
    id = serializers.SerializerMethodField()
    title = serializers.CharField(source="topic")
    slug = serializers.CharField(source="seo_slug")
    content_markdown = serializers.CharField(source="content")
    content_html = serializers.SerializerMethodField()
    author = serializers.SerializerMethodField()
    seo = serializers.SerializerMethodField()
    source = serializers.SerializerMethodField()

    class Meta:
        model = BlogGeneral
        fields = [
            "id", "title", "slug", "content_markdown", "content_html",
            "author", "tags", "categories", "seo",
            "published_at", "updated_at", "source"
        ]

    def get_id(self, obj):
        return f"post_{obj.id}"

    def get_content_html(self, obj):
        if obj.html_content:
            return obj.html_content
        if obj.content:
            return markdown.markdown(obj.content)
        return ""

    def get_author(self, obj):
        return {
            "name": obj.username or "Sohaib",
            "id": f"author_{obj.user_id}" if obj.user_id else "author_1"
        }

    def get_seo(self, obj):
        return {
            "meta_title": obj.seo_title or obj.topic,
            "meta_description": obj.seo_meta_description or "",
            "canonical_url": obj.canonical_url or ""
        }

    def get_source(self, obj):
        return "blog_generation_service"
