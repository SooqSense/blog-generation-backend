from rest_framework import serializers
import re
import os
from urllib.parse import urlparse
from drf_spectacular.utils import extend_schema_field


@extend_schema_field({
    'type': 'array',
    'items': {
        'type': 'object',
        'properties': {
            'keyword': {
                'type': 'string',
                'description': 'The keyword to use in the blog'
            },
            'count': {
                'type': 'integer',
                'minimum': 1,
                'maximum': 50,
                'description': 'How many times to use this keyword'
            }
        },
        'required': ['keyword', 'count']
    },
    'example': [
        {
            "keyword": "string",
            "count": 4
        }
    ],
    'description': 'Array of keyword objects. Each object has a keyword string and its usage count (1-50).'
})
class KeywordWithCountField(serializers.Field):
    """
    Custom field to handle keywords with counts in multiple formats:
    1. List of dictionaries: [{"keyword1": 3}, {"keyword2": 5}, {"keyword3": 1}]
    2. String format: "keyword1:3, keyword2:5, keyword3" 
    3. List of strings: ["keyword1:3", "keyword2:5", "keyword3"]
    """
    
    def to_representation(self, value):
        """Convert internal value to external representation"""
        if isinstance(value, list):
            return value
        return []
    
    def to_internal_value(self, data):
        """Convert external representation to internal value"""
        if not isinstance(data, list):
            raise serializers.ValidationError("Keywords must be provided as an array of objects.")
            
        processed_keywords = []
        
        for item in data:
            if not isinstance(item, dict):
                raise serializers.ValidationError("Each item in keywords array must be an object.")
                
            if 'keyword' not in item or 'count' not in item:
                raise serializers.ValidationError("Each keyword object must have 'keyword' and 'count' properties.")
                
            keyword = item['keyword']
            count = item['count']
            
            # Validate keyword
            if not isinstance(keyword, str) or not keyword.strip():
                raise serializers.ValidationError("Keyword must be a non-empty string.")
                
            # Validate count
            if not isinstance(count, int):
                raise serializers.ValidationError(f"Count for keyword '{keyword}' must be an integer.")
            if count <= 0:
                raise serializers.ValidationError(f"Count for keyword '{keyword}' must be a positive integer.")
            if count > 50:
                raise serializers.ValidationError(f"Count for keyword '{keyword}' cannot exceed 50.")
                
            processed_keywords.append({
                'keyword': keyword.strip(),
                'count': count
            })
            
        return processed_keywords


class BlogRequestSerializer(serializers.Serializer):
    topic = serializers.CharField(
        max_length=255,
        help_text="The main topic for the blog post."
    )
    keywords = KeywordWithCountField(
        required=False,
        default=list,
        help_text="Array of keyword objects. Each object must have 'keyword' (string) and 'count' (number 1-50) properties."
    )
    sample_blog_url = serializers.URLField(
        required=False,
        allow_blank=True,
        help_text="Optional URL of a sample blog to analyze and replicate the style (without plagiarism)."
    )
    blog_type = serializers.ChoiceField(
        choices=["News", "Comparison"],
        required=False,
        default="News",
        help_text="The type of blog post to generate. 'News' creates a news-style blog with current information and reporting format. 'Comparison' creates a comparative analysis blog with structured comparison between subjects."
    )
    length_min = serializers.IntegerField(
        required=False,
        default=800,
        min_value=300,
        max_value=5000,
        help_text="Minimum word count for the blog post."
    )
    length_max = serializers.IntegerField(
        required=False,
        default=1500,
        min_value=500,
        max_value=10000,
        help_text="Maximum word count for the blog post."
    )
    introduction = serializers.BooleanField(
        required=False,
        default=True,
        help_text="Whether to include an introduction section."
    )
    table_of_content = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Whether to include a table of contents."
    )
    faq = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Whether to include a FAQ section."
    )
    cta = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Whether to include a call to action section."
    )
    conclusion = serializers.BooleanField(
        required=False,
        default=True,
        help_text="Whether to include a conclusion section."
    )
    target_audience = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text="Optional target audience specifications."
    )
    generate_image_prompts = serializers.BooleanField(
        required=False,
        default=True,
        help_text="Whether to generate image prompts for blog sections. If False, no image prompts will be created. Default is True."
    )
    generate_images = serializers.BooleanField(
        required=False,
        default=True,
        help_text="Whether to actually generate images from the prompts. If True and generate_image_prompts is also True, generates 5 section-specific images (Banner, Main Content, Supporting Details, Evidence, Conclusion) and embeds them in markdown. If False, only generates prompts without actual images. Default is True."
    )
    
    # Add validation to ensure length_min is less than length_max and validate sample_blog_url
    def validate(self, data):
        length_min = data.get('length_min', 800)
        length_max = data.get('length_max', 1500)
        
        if length_min >= length_max:
            raise serializers.ValidationError("length_min must be less than length_max")
        
        # Validate sample_blog_url if provided
        sample_blog_url = data.get('sample_blog_url')
        if sample_blog_url:
            parsed_url = urlparse(sample_blog_url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise serializers.ValidationError("sample_blog_url must be a valid URL with http:// or https://")
            
            # Check if URL scheme is http or https
            if parsed_url.scheme not in ['http', 'https']:
                raise serializers.ValidationError("sample_blog_url must use http:// or https:// protocol")
        
        # Validate image generation flags
        generate_image_prompts = data.get('generate_image_prompts', True)
        generate_images = data.get('generate_images', True)
        
        if generate_images and not generate_image_prompts:
            raise serializers.ValidationError("Cannot generate images without generating image prompts. If generate_images is True, generate_image_prompts must also be True.")
            
        return data


class SourceSerializer(serializers.Serializer):
    url = serializers.URLField()
    title = serializers.CharField()
    type = serializers.CharField(default="research_source")


class BlogResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    topic = serializers.CharField()
    keywords = serializers.JSONField(required=False, default=list, help_text="Keywords with their usage counts")
    sample_blog_url = serializers.URLField(required=False, allow_blank=True, help_text="Sample blog URL used for style analysis")
    sample_blog_analysis = serializers.CharField(required=False, allow_blank=True, allow_null=True, help_text="Analysis of the sample blog style")
    blog_type = serializers.CharField(required=False, help_text="The type of blog generated (News or Comparison)")
    length_min = serializers.IntegerField(required=False)
    length_max = serializers.IntegerField(required=False)
    introduction = serializers.BooleanField(required=False)
    table_of_content = serializers.BooleanField(required=False)
    faq = serializers.BooleanField(required=False)
    cta = serializers.BooleanField(required=False)
    conclusion = serializers.BooleanField(required=False)
    target_audience = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    generate_image_prompts = serializers.BooleanField(required=False, help_text="Whether image prompts were generated for blog sections")
    generate_images = serializers.BooleanField(required=False, help_text="Whether actual images were generated from the prompts")
    image_prompts = serializers.ListField(child=serializers.CharField(), required=False, default=list, help_text="Generated image prompts for each section (deprecated, use section_images)")
    prompts_count = serializers.IntegerField(required=False, default=0, help_text="Number of generated image prompts (deprecated, use image_urls length)")
    image_urls = serializers.ListField(child=serializers.URLField(), required=False, default=list, help_text="S3 bucket URLs of generated section-specific images (Banner, Main Content, Supporting Details, Evidence, Conclusion)")
    section_images = serializers.JSONField(required=False, default=dict, help_text="Section-specific image data with prompts, URLs, and metadata")
    images_count = serializers.IntegerField(required=False, default=0, help_text="Number of successfully generated section images")
    research_sources = serializers.ListField(child=SourceSerializer(), required=False, default=list, help_text="Research sources discovered using SERPER API")
    sources_count = serializers.IntegerField(required=False, default=0, help_text="Number of research sources found")
    content = serializers.JSONField(help_text="Structured JSON representation of the blog content")
    raw_content = serializers.CharField(required=False, help_text="Clean markdown content of the blog with embedded images, optimized for copying and pasting into markdown viewers")


class ErrorResponseSerializer(serializers.Serializer):
    error = serializers.CharField()
