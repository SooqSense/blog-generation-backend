from rest_framework import serializers
import re
from urllib.parse import urlparse
from drf_spectacular.utils import extend_schema_field
class KeywordWithCountField(serializers.Field):
    """
    Custom field to handle keywords with counts in the format:
    ["keyword1:3", "keyword2:5", "keyword3"] where numbers indicate usage count
    """
    
    def to_representation(self, value):
        """Convert internal value to external representation"""
        if isinstance(value, list):
            return value
        return []
    
    def to_internal_value(self, data):
        """Convert external representation to internal value"""
        # Handle both string and list formats
        if isinstance(data, str):
            # Split comma-separated string into list
            if not data.strip():
                return []
            items = [item.strip() for item in data.split(',') if item.strip()]
        elif isinstance(data, list):
            items = data
        else:
            raise serializers.ValidationError("Keywords must be provided as a string (comma-separated) or a list.")
        
        processed_keywords = []
        for item in items:
            if not isinstance(item, str):
                raise serializers.ValidationError("Each keyword must be a string.")
            
            # Check if keyword has count format (keyword:count)
            if ':' in item:
                parts = item.split(':')
                if len(parts) == 2:
                    keyword, count_str = parts
                    keyword = keyword.strip()
                    
                    # Validate count is a positive integer
                    try:
                        count = int(count_str.strip())
                        if count <= 0:
                            raise serializers.ValidationError(f"Count for keyword '{keyword}' must be a positive integer.")
                        if count > 50:  # Reasonable upper limit
                            raise serializers.ValidationError(f"Count for keyword '{keyword}' cannot exceed 50.")
                        
                        processed_keywords.append({
                            'keyword': keyword,
                            'count': count
                        })
                    except ValueError:
                        raise serializers.ValidationError(f"Invalid count format for keyword '{item}'. Use 'keyword:count' format.")
                else:
                    raise serializers.ValidationError(f"Invalid keyword format '{item}'. Use 'keyword:count' or just 'keyword'.")
            else:
                # Keyword without count (default count = 1)
                processed_keywords.append({
                    'keyword': item.strip(),
                    'count': 1
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
        help_text="Optional keywords with usage counts. Accepts string (comma-separated) or array format. String: 'keyword1:3, keyword2:5, keyword3' or Array: ['keyword1:3', 'keyword2:5', 'keyword3'] where numbers indicate how many times to use the keyword."
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
    sample_blog_analysis = serializers.CharField(required=False, allow_blank=True, help_text="Analysis of the sample blog style")
    tone = serializers.CharField(required=False)
    length_min = serializers.IntegerField(required=False)
    length_max = serializers.IntegerField(required=False)
    introduction = serializers.BooleanField(required=False)
    table_of_content = serializers.BooleanField(required=False)
    faq = serializers.BooleanField(required=False)
    cta = serializers.BooleanField(required=False)
    conclusion = serializers.BooleanField(required=False)
    target_audience = serializers.ListField(child=serializers.CharField(), required=False, default=list)
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
        help_text="The main prompt for image generation. Optional."
    )
    keywords = serializers.CharField(
        required=False, 
        allow_blank=True, 
        help_text="Optional comma-separated keywords to enhance the image prompt."
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

class ImageGenerationResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    prompt_used = serializers.CharField()
    enhanced_prompt = serializers.CharField()
    image_file = serializers.CharField()

# Serializers for Related Topics API
class RelatedTopicsRequestSerializer(serializers.Serializer):
    keywords = serializers.ListField(
        child=serializers.CharField(max_length=255),
        help_text="A list of keywords to find related topics for.",
        min_length=1,
        max_length=10 # Optional: limit the number of keywords per request
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
        default=10,
        min_value=1,
        max_value=25, # Pytrends usually returns around 20-25 max for each category
        help_text="Maximum number of topics to return per category for each keyword. Default is 10."
    )

class TopicItemSerializer(serializers.Serializer):
    title = serializers.CharField()
    type = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    value = serializers.FloatField()
    # trend_type is removed as it's now part of the structure

class ProcessedKeywordTopicsSerializer(serializers.Serializer):
    keyword = serializers.CharField()
    id = serializers.IntegerField(required=False, allow_null=True) # Database ID after saving
    rising_topics = serializers.ListField(child=TopicItemSerializer())
    top_topics = serializers.ListField(child=TopicItemSerializer())
    error = serializers.CharField(required=False, allow_null=True, allow_blank=True)

class RelatedTopicsResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    processed_keywords = serializers.ListField(child=ProcessedKeywordTopicsSerializer())

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

class QueryItemSerializer(serializers.Serializer):
    query = serializers.CharField()
    value = serializers.FloatField()
    trend_type = serializers.CharField()

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
class LinkedinAnalyticsRequestSerializer(serializers.Serializer):
    linkedin_profile_id = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="LinkedIn profile ID (optional, will be fetched from token if not provided)"
    )

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