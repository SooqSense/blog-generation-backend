from rest_framework import serializers
import re
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
    tone = serializers.ChoiceField(
        choices=["professional", "creative", "casual", "informative", "persuasive"],
        required=False,
        default="professional",
        help_text="The tone of the blog post."
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
        help_text="Whether to generate image prompts based on blog headings."
    )
    max_image_prompts = serializers.IntegerField(
        required=False,
        default=5,
        min_value=1,
        max_value=15,
        help_text="Maximum number of image prompts to generate (1-15). Default is 5."
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
            
        return data

class BlogResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    topic = serializers.CharField()
    keywords = serializers.JSONField(required=False, default=list, help_text="Keywords with their usage counts")
    sample_blog_url = serializers.URLField(required=False, allow_blank=True, help_text="Sample blog URL used for style analysis")
    sample_blog_analysis = serializers.CharField(required=False, allow_blank=True, allow_null=True, help_text="Analysis of the sample blog style")
    tone = serializers.CharField(required=False)
    length_min = serializers.IntegerField(required=False)
    length_max = serializers.IntegerField(required=False)
    introduction = serializers.BooleanField(required=False)
    table_of_content = serializers.BooleanField(required=False)
    faq = serializers.BooleanField(required=False)
    cta = serializers.BooleanField(required=False)
    conclusion = serializers.BooleanField(required=False)
    target_audience = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    generate_image_prompts = serializers.BooleanField(required=False)
    max_image_prompts = serializers.IntegerField(required=False)
    image_prompts = serializers.ListField(child=serializers.CharField(), required=False, default=list, help_text="Generated image prompts based on blog headings")
    prompts_count = serializers.IntegerField(required=False, default=0, help_text="Number of generated image prompts")
    content = serializers.JSONField(help_text="Structured JSON representation of the blog content")
    raw_content = serializers.CharField(required=False, help_text="Original markdown content of the blog")

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
    image_style = serializers.CharField(help_text="Style of generated images (e.g., professional_cinematic)")
    generation_method = serializers.CharField(help_text="Method used for generation (e.g., sora_style)")
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

class DailyAINewsResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    country = serializers.CharField()
    country_name = serializers.CharField()
    keywords = serializers.ListField(child=serializers.CharField())
    news_date = serializers.DateField()
    articles_count = serializers.IntegerField()
    content = serializers.JSONField(help_text="Structured JSON representation of the news content")
    raw_content = serializers.CharField(help_text="Original markdown content of the news")

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