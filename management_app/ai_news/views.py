import re
from datetime import datetime
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiResponse
import logging

# Import models
from .models import BlogAiNews
from .serializers import DailyAINewsRequestSerializer, DailyAINewsResponseSerializer, ErrorResponseSerializer

# Set up logging
# Import organization access control
from management_app.authentication.services.access_control import require_sooqsense_organization

logger = logging.getLogger(__name__)


def convert_markdown_to_json(markdown_content):
    """
    Convert markdown content to a structured JSON format.
    This function parses markdown and creates a hierarchical structure.
    """
    if not markdown_content:
        return {}
    
    # Split content into lines
    lines = markdown_content.split('\n')
    
    # Initialize the structure
    structure = {
        'title': '',
        'sections': [],
        'metadata': {
            'word_count': len(markdown_content.split()),
            'line_count': len(lines)
        }
    }
    
    current_section = None
    current_subsection = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check for title (first H1)
        if line.startswith('# ') and not structure['title']:
            structure['title'] = line[2:].strip()
            continue
            
        # Check for main sections (H2)
        if line.startswith('## '):
            if current_section:
                structure['sections'].append(current_section)
            
            current_section = {
                'title': line[3:].strip(),
                'content': '',
                'subsections': [],
                'type': 'section'
            }
            current_subsection = None
            continue
            
        # Check for subsections (H3)
        if line.startswith('### '):
            if current_subsection:
                current_section['subsections'].append(current_subsection)
            
            current_subsection = {
                'title': line[4:].strip(),
                'content': '',
                'type': 'subsection'
            }
            continue
            
        # Add content to current section or subsection
        if current_subsection:
            current_subsection['content'] += line + '\n'
        elif current_section:
            current_section['content'] += line + '\n'
        else:
            # Content before any sections
            if not structure.get('introduction'):
                structure['introduction'] = line + '\n'
            else:
                structure['introduction'] += line + '\n'
    
    # Add the last section/subsection
    if current_subsection and current_section:
        current_section['subsections'].append(current_subsection)
    if current_section:
        structure['sections'].append(current_section)
    
    return structure


@extend_schema(
    request=DailyAINewsRequestSerializer,
    responses={
        200: OpenApiResponse(
            response=DailyAINewsResponseSerializer,
            description="Daily AI news generated successfully.",
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer, description="Bad Request - Invalid input."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error."
        ),
    },
    description="Fetch and generate daily AI news from specified country and keywords using Serper API.",
)
@api_view(["POST"])
@require_sooqsense_organization
def generate_daily_ai_news(request):
    """
    Generate daily AI news based on country and keywords.

    This endpoint fetches the latest AI news from specified countries using Serper API,
    processes the information using AI, and returns structured content.
    The result is saved to the database.
    """
    # Validate request data using the serializer
    serializer = DailyAINewsRequestSerializer(data=request.data)
    if not serializer.is_valid():
        logger.warning(f"Invalid input for daily AI news: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    country = serializer.validated_data.get("country", "us")
    keywords = serializer.validated_data.get("keywords", ["artificial intelligence", "machine learning"])
    num_results = serializer.validated_data.get("num_results", 10)

    try:
        logger.info(f"Starting daily AI news generation for country: {country}, keywords: {keywords}")

        # Import the AI daily news service
        from .service.ai_daily_news import AIDailyNewsService
        
        # Initialize the service
        news_service = AIDailyNewsService()
        
        # Get daily AI news
        news_result = news_service.get_daily_ai_news(keywords, country, num_results)
        
        if not news_result["success"]:
            logger.error(f"Daily AI news generation failed: {news_result['message']}")
            return Response(
                {"error": news_result["message"]},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info(f"Successfully generated daily AI news for {country}")

        # Clean and properly format the news content for proper markdown rendering
        clean_news_content = news_result["content"]
        if isinstance(clean_news_content, str):
            # Handle various escape sequences that might come from AI service or JSON serialization
            # First handle double newlines to preserve paragraph breaks
            clean_news_content = clean_news_content.replace('\\n\\n', '\n\n')
            # Then handle single newlines
            clean_news_content = clean_news_content.replace('\\n', '\n')
            # Handle tabs
            clean_news_content = clean_news_content.replace('\\t', '\t')
            # Handle other common escape sequences
            clean_news_content = clean_news_content.replace('\\r', '\r')
            # Handle escaped quotes and backslashes if they exist
            clean_news_content = clean_news_content.replace('\\"', '"')
            clean_news_content = clean_news_content.replace("\\'", "'")
            # Remove any remaining double backslashes
            clean_news_content = clean_news_content.replace('\\\\', '\\')
            # Strip leading/trailing whitespace
            clean_news_content = clean_news_content.strip()
            
            # Additional cleaning: ensure proper markdown structure
            # Split by lines and clean each line
            lines = clean_news_content.split('\n')
            cleaned_lines = []
            for line in lines:
                # Remove any remaining escape characters that might affect rendering
                cleaned_line = line.replace('\\n', '').replace('\\t', '\t').strip()
                cleaned_lines.append(cleaned_line)
            
            # Rejoin with proper newlines
            clean_news_content = '\n'.join(cleaned_lines)
            
            # Ensure proper spacing around headers and sections
            # Fix spacing around headers
            clean_news_content = re.sub(r'\n(#{1,6}\s)', r'\n\n\1', clean_news_content)
            clean_news_content = re.sub(r'(#{1,6}[^\n]*)\n([^\n#])', r'\1\n\n\2', clean_news_content)
            # Remove excessive empty lines (more than 2 consecutive)
            clean_news_content = re.sub(r'\n{3,}', '\n\n', clean_news_content)
            # Final strip
            clean_news_content = clean_news_content.strip()
        
        # Convert markdown content to JSON structure
        structured_content = convert_markdown_to_json(clean_news_content)

        # Save to database
        news_blog = BlogAiNews(
            user_id=request.user.id,
            username=request.user.username,
            email=request.user.email,
            news_date=datetime.now().date(),
            country=country,
            keywords=keywords,
            summary=news_result["summary"],
            content=clean_news_content,
            sources=news_result.get("sources", []),
            created_at=timezone.now(),
        )
        news_blog.save()
        logger.info(f"Saved daily AI news to database with ID: {news_blog.id}")

        # Get country name for response
        country_name = news_service._get_country_name(country)

        response_data = {
            "status": "success",
            "message": f"Daily AI news generated successfully for {country_name}!",
            "country": country,
            "country_name": country_name,
            "keywords": keywords,
            "news_date": datetime.now().date(),
            "articles_count": news_result["articles_count"],
            "sources": news_result.get("sources", []),
            "content": structured_content,
            "raw_content": clean_news_content,
        }

        # Serialize the successful response
        response_serializer = DailyAINewsResponseSerializer(data=response_data)
        if response_serializer.is_valid():
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        else:
            logger.error(f"Error serializing daily AI news response: {response_serializer.errors}")
            return Response(
                {"error": "Internal server error during response serialization."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    except Exception as e:
        logger.error(f"Unexpected error in daily AI news generation: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        return Response(
            {"error": f"An unexpected error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )