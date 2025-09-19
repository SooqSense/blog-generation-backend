from rest_framework import serializers
import re
import os
from urllib.parse import urlparse
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.openapi import AutoSchema
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

class LinkedInPostRequestSerializer(serializers.Serializer):
    topic = serializers.CharField(
        max_length=200,
        help_text="The topic for the LinkedIn post."
    )
    keywords = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text="Optional keywords to guide LinkedIn post generation."
    )

class LinkedInPostResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    topic = serializers.CharField()
    linkedin_post = serializers.CharField()
    keywords = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )

# It's also good practice to have a generic error serializer if you have consistent error responses
class ErrorResponseSerializer(serializers.Serializer):
    error = serializers.CharField()

# Serializers for Blog Generation API
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

# Serializers for Trending Keywords API
class TrendingKeywordsRequestSerializer(serializers.Serializer):
    topic = serializers.CharField(
        max_length=255,
        help_text="The main topic to find related trending keywords for."
    )
    region = serializers.CharField(
        required=False,
        max_length=10,
        allow_blank=True,
        help_text="The region code (e.g., 'US', 'GB'). Default is worldwide."
    )
    limit = serializers.IntegerField(
        required=False,
        default=10,
        min_value=1,
        max_value=50,
        help_text="Maximum number of keywords to return. Default is 10."
    )

class KeywordItemSerializer(serializers.Serializer):
    keyword = serializers.CharField()
    score = serializers.IntegerField()
    raw_value = serializers.IntegerField()

class TrendingKeywordsResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    topic = serializers.CharField()
    region = serializers.CharField(allow_blank=True)
    keywords = serializers.ListField(child=KeywordItemSerializer())

# Serializers for Image Generation API
class ImageGenerationRequestSerializer(serializers.Serializer):
    prompt = serializers.CharField(
        required=False, 
        allow_blank=True,
        help_text="The main prompt for professional, cinematic-style image generation. Optional."
    )
    keywords = serializers.CharField(
        required=False, 
        allow_blank=True, 
        help_text="Optional comma-separated keywords to enhance the image prompt for better visual relevance."
    )
    count = serializers.IntegerField(
        required=False,
        default=1,
        min_value=1,
        max_value=10,
        help_text="Number of professional images to generate (1-10). Default is 1."
    )
    model = serializers.ChoiceField(
        choices=[
            ("flux_dev", "FLUX Dev - High Quality (28 steps)"),
            ("flux_schnell", "FLUX Schnell - Fast Generation (4 steps)")
        ],
        required=False,
        default="flux_dev",
        help_text="FLUX AI model to use. 'flux_dev' for high-quality detailed images with 28 inference steps, 'flux_schnell' for faster generation with 4 steps. Default is 'flux_dev'."
    )

    # Add validation to ensure at least one field is provided
    def validate(self, data):
        prompt = data.get('prompt')
        keywords = data.get('keywords')
        if not prompt and not keywords:
            raise serializers.ValidationError("Either 'prompt' or 'keywords' (or both) must be provided.")
        if (prompt and not prompt.strip()) and (keywords and not keywords.strip()):
             raise serializers.ValidationError("Provided prompt or keywords cannot be empty or just whitespace.")
        return data

class GeneratedImageSerializer(serializers.Serializer):
    image_url = serializers.CharField()
    enhanced_prompt = serializers.CharField()
    image_number = serializers.IntegerField()

class ImageGenerationResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    prompt_used = serializers.CharField()
    count = serializers.IntegerField()
    model = serializers.CharField(help_text="FLUX AI model used ('flux_dev' or 'flux_schnell')")
    generation_method = serializers.CharField(help_text="Generation method used (deprecated, use 'model' field)")
    image_style = serializers.CharField(help_text="Style of generated images (e.g., 'FLUX Dev', 'FLUX Schnell')")
    images = serializers.ListField(child=GeneratedImageSerializer())
    total_generated = serializers.IntegerField()
    failed_generations = serializers.IntegerField()
    database_record_id = serializers.IntegerField(help_text="Database record ID for the image generation session")
    stored_image_urls = serializers.ListField(child=serializers.CharField(), help_text="All image URLs stored in database")
    stored_images_count = serializers.IntegerField(help_text="Number of images stored in database")

# Serializers for Related Topics API (Updated for Trending Queries)
class RelatedTopicsRequestSerializer(serializers.Serializer):
    topic = serializers.CharField(
        max_length=255,
        help_text="The main topic to find trending queries for."
    )
    region = serializers.CharField(
        required=False,
        max_length=10,
        allow_blank=True,
        default='',
        help_text="The region code (e.g., 'US', 'GB'). Default is worldwide."
    )
    limit = serializers.IntegerField(
        required=False,
        default=30,
        min_value=10,
        max_value=50,
        help_text="Maximum number of trending queries to return. Default is 30."
    )

class QueryItemSerializer(serializers.Serializer):
    query = serializers.CharField()
    value = serializers.FloatField()
    trend_type = serializers.CharField()

class RelatedTopicsResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    topic = serializers.CharField()
    region = serializers.CharField(allow_blank=True)
    rising_queries = serializers.ListField(child=QueryItemSerializer())
    top_queries = serializers.ListField(child=QueryItemSerializer())
    total_queries = serializers.IntegerField()
    database_record_id = serializers.IntegerField(required=False, allow_null=True)

# Serializers for Related Queries API (Added for completeness)
class RelatedQueriesRequestSerializer(serializers.Serializer):
    topic = serializers.CharField(
        max_length=255,
        help_text="The main keyword to find related queries for."
    )
    region = serializers.CharField(
        required=False,
        max_length=10,
        allow_blank=True,
        help_text="The region code (e.g., 'US', 'GB'). Default is worldwide."
    )
    limit = serializers.IntegerField(
        required=False,
        default=10,
        min_value=1,
        max_value=50,
        help_text="Maximum number of queries to return. Default is 10."
    )

class RelatedQueriesResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    topic = serializers.CharField()
    region = serializers.CharField(allow_blank=True)
    related_queries = serializers.ListField(child=QueryItemSerializer())

# Serializers for Trending Searches API (Added for completeness)
class TrendingSearchesRequestSerializer(serializers.Serializer):
    region = serializers.CharField(
        required=False,
        max_length=20,
        allow_blank=True,
        default="united_states",
        help_text="The region code for trending searches (e.g., 'united_states', 'uk'). Default is 'united_states'."
    )
    limit = serializers.IntegerField(
        required=False,
        default=10,
        min_value=1,
        max_value=50,
        help_text="Maximum number of trending searches to return. Default is 10."
    )

class TrendingSearchesResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    region = serializers.CharField()
    trending_searches = serializers.ListField(child=serializers.CharField())

# Serializers for Regional Interest API (Added for completeness)
class RegionalInterestRequestSerializer(serializers.Serializer):
    topic = serializers.CharField(
        max_length=255,
        help_text="The main keyword to find regional interest for."
    )
    region = serializers.CharField(
        required=False,
        max_length=10,
        allow_blank=True,
        help_text="The region code to limit results (e.g., 'US', 'GB'). Default is worldwide."
    )
    resolution = serializers.CharField(
        required=False,
        default="COUNTRY",
        help_text="Geographic resolution ('COUNTRY', 'REGION', 'CITY', 'DMA'). Default is 'COUNTRY'."
    )
    limit = serializers.IntegerField(
        required=False,
        default=10,
        min_value=1,
        max_value=50,
        help_text="Maximum number of regions to return. Default is 10."
    )

class RegionItemSerializer(serializers.Serializer):
    region = serializers.CharField()
    value = serializers.FloatField()

class RegionalInterestResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    topic = serializers.CharField()
    region = serializers.CharField(allow_blank=True)
    resolution = serializers.CharField()
    regional_interest = serializers.ListField(child=RegionItemSerializer())

# Serializers for LinkedIn Analytics API
class PostAnalyticsSerializer(serializers.Serializer):
    post_id = serializers.CharField()
    post_content = serializers.CharField(required=False, allow_blank=True)
    post_date = serializers.DateTimeField(required=False, allow_null=True)
    reactions = serializers.IntegerField(default=0)
    comments = serializers.IntegerField(default=0)
    reposts = serializers.IntegerField(default=0)
    impressions = serializers.IntegerField(default=0)
    engagement = serializers.IntegerField(default=0)

class LinkedinAnalyticsResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    linkedin_profile_id = serializers.CharField()
    
    # Data source and quality information
    data_source = serializers.CharField(required=False, default='official_api', help_text="Source of the data (e.g., official_api)")
    data_quality = serializers.CharField(required=False, default='enhanced', help_text="Quality of the data (enhanced, basic, error)")
    available_scopes = serializers.ListField(child=serializers.CharField(), required=False, default=list, help_text="Available LinkedIn API scopes")
    api_limitations = serializers.ListField(child=serializers.CharField(), required=False, default=list, help_text="Any API limitations encountered")
    
    # Re-authentication guidance
    needs_reauth = serializers.BooleanField(required=False, help_text="Whether user needs to re-authenticate for better permissions")
    reauth_reason = serializers.CharField(required=False, help_text="Reason why re-authentication is needed")
    reauth_instructions = serializers.DictField(required=False, help_text="Step-by-step instructions for re-authentication")
    current_limitations = serializers.ListField(child=serializers.CharField(), required=False, help_text="Current API limitations")
    scope_status = serializers.DictField(required=False, help_text="Current scope detection status and data quality")
    
    # Profile Analytics
    total_followers = serializers.IntegerField()
    total_posts = serializers.IntegerField()
    
    # Post Analytics
    posts_analytics = serializers.ListField(child=PostAnalyticsSerializer())
    
    # Summary metrics
    total_reactions = serializers.IntegerField()
    total_comments = serializers.IntegerField()
    total_reposts = serializers.IntegerField()
    total_impressions = serializers.IntegerField()
    total_engagement = serializers.IntegerField()
    
    # Metadata
    last_updated = serializers.DateTimeField()
    created_at = serializers.DateTimeField()

# Serializers for Daily AI News API
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

# Serializers for LinkedIn Posting API
class LinkedinPostingRequestSerializer(serializers.Serializer):
    content = serializers.CharField(
        help_text="The content to post on LinkedIn. Can be text, with optional formatting."
    )
    image_urls = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        default=list,
        max_length=9,  # LinkedIn supports up to 9 images per post
        help_text="Optional list of S3 image URLs to include with the post. Maximum 9 images. URLs should be publicly accessible."
    )
    
    def validate_content(self, value):
        """Validate the content field"""
        if not value or not value.strip():
            raise serializers.ValidationError("Content cannot be empty.")
        
        # LinkedIn has a character limit of around 3000 characters for posts
        if len(value) > 3000:
            raise serializers.ValidationError("Content exceeds LinkedIn's character limit of 3000 characters.")
            
        return value.strip()
    
    def validate_image_urls(self, value):
        """Validate the image URLs"""
        if not value:
            return value
            
        # Check maximum number of images
        if len(value) > 9:
            raise serializers.ValidationError("LinkedIn supports a maximum of 9 images per post.")
        
        # Validate each URL
        for url in value:
            if not url.strip():
                raise serializers.ValidationError("Image URLs cannot be empty.")
            
            # Basic validation for S3 URLs (you can make this more specific)
            if not any(domain in url.lower() for domain in ['amazonaws.com', 's3.', 'cloudfront.net']):
                raise serializers.ValidationError(f"Image URL should be from a supported cloud storage service: {url}")
        
        return [url.strip() for url in value]

class LinkedinPostingResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    profile_id = serializers.CharField(help_text="LinkedIn profile ID")
    username = serializers.CharField(help_text="LinkedIn profile username")
    content = serializers.CharField(help_text="The content that was posted")
    post_date = serializers.DateTimeField(help_text="When the post was made")
    linkedin_post_id = serializers.CharField(required=False, allow_null=True, help_text="LinkedIn's post ID if available")
    database_record_id = serializers.IntegerField(help_text="Database record ID for the posted content")
    image_urls = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        default=list,
        help_text="List of image URLs that were posted with the content"
    )
    images_count = serializers.IntegerField(
        required=False,
        default=0,
        help_text="Number of images posted with the content"
    )
    post_type = serializers.CharField(
        required=False,
        default="text",
        help_text="Type of post: 'text' for text-only, 'image' for posts with images"
    )


# Serializers for Schedule LinkedIn Post API
class ScheduleLinkedinPostRequestSerializer(serializers.Serializer):
    content = serializers.ListField(
        child=serializers.CharField(max_length=3000),
        min_length=1,
        max_length=10,  # Maximum 10 posts at once
        help_text="Array of LinkedIn post content to be scheduled. Each post content max 3000 characters. Maximum 10 posts at once."
    )
    scheduled_date = serializers.DateField(
        help_text="The date when the posts should be published (YYYY-MM-DD format)."
    )
    scheduled_time = serializers.TimeField(
        help_text="The time when the posts should be published (HH:MM:SS format)."
    )
    timezone = serializers.CharField(
        max_length=50,
        required=False,
        default="UTC",
        help_text="Timezone for the scheduled time (e.g., 'UTC', 'America/New_York', 'Europe/London'). Default is UTC."
    )
    image_urls = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        default=list,
        help_text="Optional list of image URLs to include with the posts. Will be distributed across posts if multiple posts are provided."
    )
    delay_between_posts = serializers.IntegerField(
        required=False,
        default=5,
        min_value=1,
        max_value=60,
        help_text="Delay in minutes between each post if multiple posts are scheduled. Default is 5 minutes."
    )
    
    def validate_content(self, value):
        """Validate each content item in the array"""
        for i, content_item in enumerate(value):
            if not content_item or not content_item.strip():
                raise serializers.ValidationError(f"Content item {i+1} cannot be empty.")
        return [content.strip() for content in value]
    
    def validate(self, data):
        from datetime import datetime, timezone as tz
        from django.utils import timezone
        
        # Combine date and time
        scheduled_datetime = datetime.combine(
            data['scheduled_date'], 
            data['scheduled_time']
        )
        
        # Make timezone aware
        if data.get('timezone', 'UTC') == 'UTC':
            scheduled_datetime = scheduled_datetime.replace(tzinfo=tz.utc)
        else:
            # For other timezones, you might want to use pytz
            import pytz
            try:
                tz_obj = pytz.timezone(data.get('timezone', 'UTC'))
                scheduled_datetime = tz_obj.localize(scheduled_datetime)
            except:
                # Fallback to UTC if timezone is invalid
                scheduled_datetime = scheduled_datetime.replace(tzinfo=tz.utc)
        
        # Check if scheduled time is in the future
        if scheduled_datetime <= timezone.now():
            raise serializers.ValidationError("Scheduled time must be in the future.")
        
        data['scheduled_datetime'] = scheduled_datetime
        return data


class ScheduleLinkedinPostResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    schedule_id = serializers.IntegerField(help_text="Unique ID for the scheduled post batch")
    content = serializers.ListField(
        child=serializers.CharField(),
        help_text="Array of scheduled post content"
    )
    total_posts = serializers.IntegerField(help_text="Total number of posts scheduled")
    scheduled_datetime = serializers.DateTimeField(help_text="When the first post is scheduled to be published")
    timezone = serializers.CharField(help_text="Timezone for the scheduled time")
    linkedin_profile_id = serializers.CharField(help_text="LinkedIn profile ID where the posts will be published")
    linkedin_username = serializers.CharField(help_text="LinkedIn profile username")
    post_type = serializers.CharField(help_text="Type of posts: 'text' or 'image'")
    images_count = serializers.IntegerField(help_text="Number of images to be posted")
    delay_between_posts = serializers.IntegerField(help_text="Delay in minutes between each post")
    celery_task_id = serializers.CharField(help_text="Celery task ID for tracking/cancellation")
    created_at = serializers.DateTimeField(help_text="When the schedule was created")


class ScheduledPostListSerializer(serializers.Serializer):
    schedule_id = serializers.IntegerField()
    content = serializers.JSONField(help_text="Array of post content or single content for backward compatibility")
    content_preview = serializers.CharField(help_text="Preview of the first post content")
    total_posts = serializers.IntegerField(help_text="Total number of posts in this schedule")
    scheduled_datetime = serializers.DateTimeField()
    timezone = serializers.CharField()
    status = serializers.CharField()
    linkedin_profile_id = serializers.CharField()
    linkedin_username = serializers.CharField()
    post_type = serializers.CharField()
    images_count = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    posted_at = serializers.DateTimeField(required=False, allow_null=True)
    linkedin_post_id = serializers.CharField(required=False, allow_null=True)
    error_message = serializers.CharField(required=False, allow_null=True)


class ScheduledPostsListResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    total_scheduled = serializers.IntegerField()
    scheduled_posts = serializers.ListField(child=ScheduledPostListSerializer())


class CancelScheduledPostResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    schedule_id = serializers.IntegerField()
    previous_status = serializers.CharField()
    current_status = serializers.CharField()


# Serializers for Image Editing API
class ImageEditingRequestSerializer(serializers.Serializer):
    prompt = serializers.CharField(
        max_length=1000,
        help_text="The editing instruction/prompt describing what changes to make to the image."
    )
    keywords = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text="Optional array of keywords to guide the editing process."
    )
    image = serializers.ImageField(
        help_text="The image file to be edited. Supported formats: JPEG, PNG, WebP. Maximum size: 10MB.",
        allow_empty_file=False
    )
    
    class Meta:
        swagger_schema_fields = {
            'type': 'object',
            'properties': {
                'prompt': {
                    'type': 'string',
                    'maxLength': 1000,
                    'description': 'The editing instruction/prompt describing what changes to make to the image.'
                },
                'keywords': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': 'Optional array of keywords to guide the editing process.',
                    'default': []
                },
                'image': {
                    'type': 'string',
                    'format': 'binary',
                    'description': 'The image file to edit. Supported formats: JPEG, PNG, WebP. Maximum size: 10MB.'
                }
            },
            'required': ['prompt', 'image']
        }


class ImageEditingResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    prompt_used = serializers.CharField(help_text="The original editing prompt provided")
    enhanced_prompt = serializers.CharField(help_text="The AI-optimized editing prompt used")
    keywords = serializers.CharField(required=False, allow_blank=True, help_text="Keywords used in the editing")
    original_image_size = serializers.IntegerField(help_text="Size of the original uploaded image in bytes")
    edited_image_url = serializers.URLField(help_text="URL of the edited result image")
    database_record_id = serializers.IntegerField(help_text="Database record ID for the editing session")
    edit_status = serializers.CharField(help_text="Status of the editing process")
    processing_time = serializers.FloatField(required=False, help_text="Time taken to process the editing in seconds")
    created_at = serializers.DateTimeField(help_text="When the editing was performed")


# Serializers for PDF Upload API
class PDFUploadSerializer(serializers.Serializer):
    file = serializers.FileField(
        help_text="Document file to upload. Supported formats: PDF, DOCX, MD, TXT. Maximum size: 50MB.",
        allow_empty_file=False
    )
    
    def validate_file(self, file):
        """Validate uploaded file."""
        # Check file size (50MB limit)
        max_size = 50 * 1024 * 1024  # 50MB in bytes
        if file.size > max_size:
            raise serializers.ValidationError(
                f"File size ({file.size / (1024*1024):.2f} MB) exceeds maximum limit (50 MB)."
            )
        
        # Check file type by extension
        allowed_extensions = ['.pdf', '.docx', '.doc', '.md', '.txt']
        file_extension = os.path.splitext(file.name.lower())[1]
        
        if file_extension not in allowed_extensions:
            raise serializers.ValidationError(
                f"Unsupported file type '{file_extension}'. Allowed types: {', '.join(allowed_extensions)}"
            )
        
        return file

    class Meta:
        swagger_schema_fields = {
            'type': 'object',
            'properties': {
                'file': {
                    'type': 'string',
                    'format': 'binary',
                    'description': 'Document file to upload. Supported formats: PDF, DOCX, MD, TXT. Maximum size: 50MB.'
                }
            },
            'required': ['file']
        }


class PDFUploadResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    document_id = serializers.CharField(help_text="Unique document identifier")
    file_name = serializers.CharField(help_text="Original filename")
    file_type = serializers.CharField(help_text="Detected file type (pdf, docx, md, txt)")
    file_size = serializers.IntegerField(help_text="File size in bytes")
    word_count = serializers.IntegerField(help_text="Number of words extracted from the document")
    uploaded_url = serializers.URLField(help_text="S3 bucket URL where the file is stored")
    
    # Processing status information
    content_extraction_completed = serializers.BooleanField(help_text="Whether content extraction was successful")
    pinecone_indexing_completed = serializers.BooleanField(help_text="Whether Pinecone indexing was successful")
    chunks_indexed = serializers.IntegerField(help_text="Number of chunks indexed in Pinecone")
    processing_status = serializers.CharField(help_text="Overall processing status")
    
    # Additional metadata
    extraction_method = serializers.CharField(required=False, help_text="Method used for content extraction")
    database_record_id = serializers.IntegerField(help_text="Database record ID for the uploaded document")
    created_at = serializers.DateTimeField(help_text="When the document was uploaded and processed")


# Serializers for Chat API
class ChatRequestSerializer(serializers.Serializer):
    query = serializers.CharField(
        max_length=2000,
        help_text="User's question or query about their project portfolio documents."
    )
    session_id = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        help_text="Chat session ID. If not provided, a new session will be created."
    )
    
    def validate_query(self, query):
        """Validate the query field."""
        if not query or not query.strip():
            raise serializers.ValidationError("Query cannot be empty.")
        
        if len(query.strip()) < 3:
            raise serializers.ValidationError("Query must be at least 3 characters long.")
        
        return query.strip()


class DocumentSourceSerializer(serializers.Serializer):
    file_name = serializers.CharField()
    file_type = serializers.CharField()
    file_url = serializers.URLField()
    relevance_score = serializers.FloatField()


class ChatResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    session_id = serializers.CharField(help_text="Chat session ID")
    is_new_session = serializers.BooleanField(help_text="Whether this is a new chat session")
    
    # Response content
    response = serializers.CharField(help_text="AI-generated response to the user's query")
    
    # Processing information
    processing_time = serializers.FloatField(help_text="Time taken to process the query in seconds")
    tokens_used = serializers.IntegerField(help_text="Number of tokens used for this response")
    model_used = serializers.CharField(help_text="AI model used to generate the response")
    
    # Conversation context
    total_messages = serializers.IntegerField(help_text="Total number of messages in this session")
    relevant_documents_found = serializers.IntegerField(help_text="Number of relevant documents found for this query")


# Serializers for Chat Session Management
class ChatSessionSerializer(serializers.Serializer):
    session_id = serializers.CharField()
    is_active = serializers.BooleanField()
    total_messages = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class ChatMessageSerializer(serializers.Serializer):
    message_type = serializers.CharField()
    content = serializers.CharField()
    sources_used = serializers.JSONField(required=False)
    processing_time = serializers.FloatField(required=False)
    tokens_used = serializers.IntegerField(required=False)
    created_at = serializers.DateTimeField()


class ChatHistorySerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    session = ChatSessionSerializer()
    messages = serializers.ListField(child=ChatMessageSerializer())
    total_messages = serializers.IntegerField()


# Serializer for PDF Document List
class PDFDocumentListSerializer(serializers.Serializer):
    document_id = serializers.CharField()
    file_name = serializers.CharField()
    file_type = serializers.CharField()
    file_size = serializers.IntegerField()
    word_count = serializers.IntegerField()
    uploaded_url = serializers.URLField()
    processing_status = serializers.CharField()
    pinecone_indexed = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class PDFDocumentListResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    total_documents = serializers.IntegerField()
    documents = serializers.ListField(child=PDFDocumentListSerializer()) 