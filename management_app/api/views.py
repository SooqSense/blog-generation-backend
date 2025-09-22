import json
import os
import sys
import requests
from django.conf import settings
from django.http import HttpResponse
from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
import logging
from django.utils import timezone
from datetime import datetime
import re
import urllib.parse
from rest_framework.parsers import MultiPartParser, FormParser

# Import models
from .models import (
    BlogGeneral,
    BlogAiNews,
    LinkedinPost,
    LinkedinPostingContent,
    ImageGeneration,
    TrendingTopics,
    LinkedinAnalytics,
    SchedulePosts,
    ImageEditing,
)

# Set up logging
logger = logging.getLogger(__name__)

# Add tools directory to sys.path
if settings.TOOLS_DIR not in sys.path:
    sys.path.insert(0, settings.TOOLS_DIR)
if os.path.dirname(settings.TOOLS_DIR) not in sys.path:
    sys.path.insert(0, os.path.dirname(settings.TOOLS_DIR))

from tools.ai.blog_generator.blog_writing.blog_writer import BlogWriter
from tools.ai.image_generation.image_generator import generate_image

# Import the new LinkedInPostGenerator service
from tools.ai.linkedin_post_generator.linkedin_post_generator import (
    LinkedInPostGenerator,
)

# Import the Trending Queries service (using Serper API)
from tools.ai.trends_ai.trending_queries import fetch_trending_queries

# Import the image editing functionality
from tools.ai.image_generation.edit_images import (
    edit_image_with_flux,
    convert_image_to_base64,
)

# Import serializers
from .serializers import (
    LinkedInPostRequestSerializer,
    LinkedInPostResponseSerializer,
    ErrorResponseSerializer,
    BlogRequestSerializer,
    BlogResponseSerializer,
    ImageGenerationRequestSerializer,
    ImageGenerationResponseSerializer,
    TrendingKeywordsRequestSerializer,
    TrendingKeywordsResponseSerializer,
    RelatedTopicsRequestSerializer,
    RelatedTopicsResponseSerializer,
    LinkedinAnalyticsResponseSerializer,
    DailyAINewsRequestSerializer,
    DailyAINewsResponseSerializer,
    LinkedinPostingRequestSerializer,
    LinkedinPostingResponseSerializer,
    ScheduleLinkedinPostRequestSerializer,
    ScheduleLinkedinPostResponseSerializer,
    ScheduledPostsListResponseSerializer,
    CancelScheduledPostResponseSerializer,
    ImageEditingRequestSerializer,
    ImageEditingResponseSerializer,
)

def convert_markdown_to_json(markdown_content):
    """
    Convert markdown blog content to a structured JSON format.
    
    Args:
        markdown_content (str): The markdown content to convert
    
    Returns:
        dict: A structured JSON representation of the blog
    """
    # Initialize result structure
    result = {
        "title": "",
        "sections": []
    }
    
    # Split content into lines for processing
    lines = markdown_content.strip().split('\n')
    
    current_section = None
    current_subsection = None
    current_content = []
    
    for line in lines:
        line = line.rstrip()
        
        # Handle main title (# Title)
        if line.startswith('# '):
            result['title'] = line[2:].strip()
            
        # Handle section headers (## Section)
        elif line.startswith('## '):
            # Save previous section if exists
            if current_section:
                # Add any remaining content to the current section or subsection
                if current_content:
                    if current_subsection:
                        current_subsection['content'] = '\n'.join(current_content).strip()
                        current_content = []
                    else:
                        current_section['content'] = '\n'.join(current_content).strip()
                        current_content = []
            
            # Create new section
            section_title = line[3:].strip()
            current_section = {
                'title': section_title,
                'type': 'section',
                'content': '',
                'subsections': []
            }
            
            # Add qa_pairs array for FAQ section
            if any(faq_keyword in section_title.lower() for faq_keyword in ['faq', 'frequently asked questions', 'questions']):
                current_section['qa_pairs'] = []
                
            current_subsection = None
            current_content = []
            result['sections'].append(current_section)
            
        # Handle subsection headers (### Subsection)
        elif line.startswith('### '):
            # Save content to previous subsection if exists
            if current_subsection and current_content:
                current_subsection['content'] = '\n'.join(current_content).strip()
                current_content = []
            
            # Create new subsection
            subsection_title = line[4:].strip()
            current_subsection = {
                'title': subsection_title,
                'type': 'subsection',
                'content': ''
            }
            if current_section:
                current_section['subsections'].append(current_subsection)
                
                # If this is a FAQ section, add question to qa_pairs
                if 'qa_pairs' in current_section:
                    current_section['qa_pairs'].append({
                        'question': subsection_title,
                        'answer': ''  # Will be populated when we process the content
                    })
                    
            current_content = []
            
        # Handle bold headers that might be sections (**Section**)
        elif line.startswith('**') and line.endswith('**') and len(line.strip()) > 4:
            # Save previous section if exists
            if current_section:
                if current_content:
                    if current_subsection:
                        current_subsection['content'] = '\n'.join(current_content).strip()
                        current_content = []
                    else:
                        current_section['content'] = '\n'.join(current_content).strip()
                        current_content = []
            
            # Create new section from bold text
            section_title = line.strip()[2:-2].strip()  # Remove ** from both ends
            current_section = {
                'title': section_title,
                'type': 'section',
                'content': '',
                'subsections': []
            }
            
            # Add qa_pairs array for FAQ section
            if any(faq_keyword in section_title.lower() for faq_keyword in ['faq', 'frequently asked questions', 'questions']):
                current_section['qa_pairs'] = []
                
            current_subsection = None
            current_content = []
            result['sections'].append(current_section)
            
        # Handle bullet points and other content
        else:
            # Only add non-empty lines
            if line.strip():
                current_content.append(line)
    
    # Add any remaining content
    if current_content:
        if current_subsection:
            current_subsection['content'] = '\n'.join(current_content).strip()
            
            # If this is a FAQ section, update the answer in qa_pairs
            if current_section and 'qa_pairs' in current_section:
                for qa_pair in current_section['qa_pairs']:
                    if qa_pair['question'] == current_subsection['title']:
                        qa_pair['answer'] = '\n'.join(current_content).strip()
                        
        elif current_section:
            current_section['content'] = '\n'.join(current_content).strip()
    
    # Process FAQ content if it's not in subsections format (might be in list format)
    for section in result['sections']:
        if 'qa_pairs' in section and not section['qa_pairs']:
            # If the FAQ section uses numbered lists or other format instead of subsections, try to extract Q&A
            content_lines = section['content'].split('\n')
            question = None
            answer_lines = []
            
            for content_line in content_lines:
                # Check if this line is a question (bold, numbered, or starts with Q:)
                if (content_line.strip().startswith('**') or 
                    re.match(r'^\d+\.', content_line.strip()) or
                    content_line.strip().lower().startswith('q:') or
                    content_line.strip().lower().startswith('question')):
                    
                    # If we have a previous question, save it
                    if question and answer_lines:
                        section['qa_pairs'].append({
                            'question': question,
                            'answer': '\n'.join(answer_lines).strip()
                        })
                        answer_lines = []
                    
                    # Extract new question
                    question = content_line.strip()
                    # Remove formatting from question
                    question = re.sub(r'^\d+\.\s*', '', question)  # Remove numbers
                    question = re.sub(r'\*\*|\*', '', question)  # Remove asterisks
                    question = re.sub(r'^q:\s*', '', question, flags=re.IGNORECASE)  # Remove Q:
                    question = re.sub(r'^question\s*\d*:?\s*', '', question, flags=re.IGNORECASE)  # Remove Question
                    question = question.strip()
                else:
                    # This is part of the answer
                    if question and content_line.strip():
                        answer_lines.append(content_line)
            
            # Add the last Q&A pair
            if question and answer_lines:
                section['qa_pairs'].append({
                    'question': question,
                    'answer': '\n'.join(answer_lines).strip()
                })
        
        # Extract bullet points for Call to Action section
        if 'call to action' in section['title'].lower() or 'cta' in section['title'].lower():
            # Extract bullet points from content using regex
            bullet_points = []
            content_lines = section['content'].split('\n')
            
            for line in content_lines:
                # Match both asterisk, dash, and numbered bullet points
                if re.match(r'^\s*[\*\-\d+\.]\s+', line.strip()):
                    bullet_text = re.sub(r'^\s*[\*\-\d+\.]\s+', '', line.strip())
                    if bullet_text:
                        bullet_points.append(bullet_text)
            
            # Only add bullet_points array if we found bullet points
            if bullet_points:
                section['bullet_points'] = bullet_points
    
    return result

@extend_schema(
    request=BlogRequestSerializer,
    responses={
        200: OpenApiResponse(
            response=BlogResponseSerializer, description="Blog generated successfully."
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer, description="Bad Request - Invalid input."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error."
        ),
    },
    description="Generate a detailed blog post based on the given topic and optional parameters for customization. Set 'generate_image_prompts' to true (default) to include 5 section-specific images, or false for text-only blog content.",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_blog_api(request):
    """
    Generate a detailed blog post from a given topic and optional parameters.
    Input is a JSON object with "topic" (required) and various optional parameters
    for customizing the blog format and style.
    """
    # Validate request data using the serializer
    serializer = BlogRequestSerializer(data=request.data)
    if serializer.is_valid():
        topic = serializer.validated_data["topic"]
        keywords = serializer.validated_data.get("keywords", [])
        sample_blog_url = serializer.validated_data.get("sample_blog_url", "")
        blog_type = serializer.validated_data.get("blog_type", "News")  # Changed from tone to blog_type
        length_min = serializer.validated_data.get("length_min", 800)
        length_max = serializer.validated_data.get("length_max", 1500)
        introduction = serializer.validated_data.get("introduction", True)
        table_of_content = serializer.validated_data.get("table_of_content", False)
        faq = serializer.validated_data.get("faq", False)
        cta = serializer.validated_data.get("cta", False)
        conclusion = serializer.validated_data.get("conclusion", True)
        target_audience = serializer.validated_data.get("target_audience", [])
        generate_image_prompts = serializer.validated_data.get("generate_image_prompts", True)
        generate_images = serializer.validated_data.get("generate_images", True)
        
        # Keywords are already processed by the serializer into the correct format
        # No additional processing needed as KeywordWithCountField handles all formats:
        # 1. List of dictionaries: [{"keyword1": 3}, {"keyword2": 5}]
        # 2. String format: "keyword1:3, keyword2:5"  
        # 3. List of strings: ["keyword1:3", "keyword2:5"]

        try:
            logger.info(
                f"Starting blog generation for topic: '{topic}' with blog type: '{blog_type}' and research-based workflow"
            )

            blog_writer_instance = BlogWriter(
                topic=topic,
                keywords=keywords,
                blog_type=blog_type,  # Changed from tone to blog_type
                length_min=length_min,
                length_max=length_max,
                introduction=introduction,
                table_of_content=table_of_content,
                faq=faq,
                cta=cta,
                conclusion=conclusion,
                target_audience=target_audience,
                sample_blog_url=sample_blog_url if sample_blog_url else None,
                generate_image_prompts=generate_image_prompts,
                generate_images=generate_images,
            )

            # Generate the blog content without saving to file
            blog_content = blog_writer_instance.generate_blog(
                topic=topic,
                sample_blog_url=sample_blog_url if sample_blog_url else None
            )

            if not blog_content:
                logger.error(f"Blog generation failed for topic: '{topic}'")
                return Response(
                    {"error": "Blog generation failed."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            logger.info(f"Successfully generated blog on '{topic}'")
            
            # Convert markdown content to JSON structure
            structured_content = convert_markdown_to_json(blog_content)

            # Get generated image prompts (legacy support)
            image_prompts = getattr(blog_writer_instance, 'image_prompts', [])
            prompts_count = len(image_prompts)
            
            # Get section-specific image data
            section_images = getattr(blog_writer_instance, 'section_images', {})
            image_urls = getattr(blog_writer_instance, 'image_urls', [])
            images_count = len([img for img in section_images.values() if img.get('image_url')])
            
            # Debug logging for images
            logger.info(f"Section-specific images generated: {images_count}")
            logger.info(f"S3 URLs stored: {len(image_urls)}")
            for section, img_data in section_images.items():
                if img_data.get('image_url'):
                    logger.info(f"Section '{section}' image: {img_data['image_url']}")
            
            # Get research sources
            research_sources = getattr(blog_writer_instance, 'research_sources', [])
            sources_count = len(research_sources)
            
            # Clean and properly format the blog content for proper markdown rendering
            clean_blog_content = blog_content
            if isinstance(clean_blog_content, str):
                # Handle various escape sequences that might come from CrewAI or JSON serialization
                # First handle double newlines to preserve paragraph breaks
                clean_blog_content = clean_blog_content.replace('\\n\\n', '\n\n')
                # Then handle single newlines
                clean_blog_content = clean_blog_content.replace('\\n', '\n')
                # Handle tabs
                clean_blog_content = clean_blog_content.replace('\\t', '\t')
                # Handle other common escape sequences
                clean_blog_content = clean_blog_content.replace('\\r', '\r')
                # Handle escaped quotes and backslashes if they exist
                clean_blog_content = clean_blog_content.replace('\\"', '"')
                clean_blog_content = clean_blog_content.replace("\\'", "'")
                # Remove any remaining double backslashes
                clean_blog_content = clean_blog_content.replace('\\\\', '\\')
                # Strip leading/trailing whitespace
                clean_blog_content = clean_blog_content.strip()
                
                # Additional cleaning: ensure proper markdown structure
                # Split by lines and clean each line
                lines = clean_blog_content.split('\n')
                cleaned_lines = []
                for line in lines:
                    # Remove any remaining escape characters that might affect rendering
                    cleaned_line = line.replace('\\n', '').replace('\\t', '\t').strip()
                    cleaned_lines.append(cleaned_line)
                
                # Rejoin with proper newlines
                clean_blog_content = '\n'.join(cleaned_lines)
                
                # Ensure proper spacing around headers and sections
                # Fix spacing around headers
                clean_blog_content = re.sub(r'\n(#{1,6}\s)', r'\n\n\1', clean_blog_content)
                clean_blog_content = re.sub(r'(#{1,6}[^\n]*)\n([^\n#])', r'\1\n\n\2', clean_blog_content)
                # Remove excessive empty lines (more than 2 consecutive)
                clean_blog_content = re.sub(r'\n{3,}', '\n\n', clean_blog_content)
                # Final strip
                clean_blog_content = clean_blog_content.strip()
            
            # Save to database with section-specific image URLs
            blog = BlogGeneral(
                user_id=request.user.id,  # Use authenticated user's ID
                username=request.user.username,  # Use authenticated user's username
                email=request.user.email,  # Use authenticated user's email
                topic=topic,
                content=clean_blog_content,  # This now includes embedded images
                sample_blog_url=sample_blog_url if sample_blog_url else None,
                image_prompts=image_prompts,  # Legacy field for backward compatibility
                prompts_count=prompts_count,  # Legacy field
                image_urls=image_urls,  # New field: list of S3 URLs
                created_at=timezone.now(),
            )
            blog.save()
            logger.info(f"Saved blog to database with ID: {blog.id} with {images_count} section images and {sources_count} research sources")

            response_data = {
                "status": "success",
                "message": f"Research-based {blog_type.lower()} blog generated successfully with {images_count} section-specific images!",
                "topic": topic,
                "keywords": keywords,
                "sample_blog_url": sample_blog_url,
                "sample_blog_analysis": getattr(blog_writer_instance, 'sample_blog_analysis', None) if hasattr(blog_writer_instance, 'sample_blog_analysis') else None,
                "blog_type": blog_type,  # Changed from tone to blog_type
                "length_min": length_min,
                "length_max": length_max,
                "introduction": introduction,
                "table_of_content": table_of_content,
                "faq": faq,
                "cta": cta,
                "conclusion": conclusion,
                "target_audience": target_audience,
                "generate_image_prompts": generate_image_prompts,
                "generate_images": generate_images,
                "image_prompts": image_prompts,  # Legacy field for backward compatibility
                "prompts_count": prompts_count,  # Legacy field
                "image_urls": image_urls,  # New: S3 URLs of section-specific images
                "section_images": section_images,  # New: Complete section image data with prompts and metadata
                "images_count": images_count,  # New: Number of successfully generated images
                "research_sources": research_sources,  # Include research sources
                "sources_count": sources_count,  # Include sources count
                "content": structured_content,
                "raw_content": clean_blog_content,  # Include the properly formatted markdown with embedded images
            }

            # Serialize the successful response
            response_serializer = BlogResponseSerializer(data=response_data)
            if response_serializer.is_valid():
                return Response(response_serializer.data, status=status.HTTP_200_OK)
            else:
                logger.error(
                    f"Error serializing successful response for blog: {response_serializer.errors}"
                )
                return Response(
                    {"error": "Internal server error during response serialization."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        # Exception handling for the main try block
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(
                f"Unexpected error in blog generation: {type(e).__name__} - {e}"
            )
            import traceback

            traceback.print_exc()
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    else:
        # If serializer validation fails
        logger.warning(f"Invalid input for blog generation: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
@permission_classes([IsAuthenticated])
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
        from tools.ai.daily_news.ai_daily_news import AIDailyNewsService
        
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


# New endpoints will be added below


@extend_schema(
    request=ImageGenerationRequestSerializer,
    responses={
        200: OpenApiResponse(
            response=ImageGenerationResponseSerializer,
            description="Images generated successfully.",
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer, description="Bad Request - Invalid input."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="Internal Server Error / Image Generation Failed.",
        ),
    },
    description="Generate one or more professional images using FLUX AI generation models. Choose between FLUX Dev (28 steps, high quality) or FLUX Schnell (4 steps, fast generation) models for detailed, artistic image generation.",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_image_api(request):
    """
    Generate one or more professional images using FLUX AI generation models.
    
    Supports two FLUX AI models:
    - 'flux_dev': FLUX Dev - High quality detailed images with 28 inference steps
    - 'flux_schnell': FLUX Schnell - Fast generation with 4 inference steps
    
    Both models use AI-optimized prompts tailored to FLUX AI's strengths.
    """
    serializer = ImageGenerationRequestSerializer(data=request.data)
    if not serializer.is_valid():
        logger.warning(f"Invalid input for image generation: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    prompt = serializer.validated_data.get("prompt", "")
    keywords = serializer.validated_data.get("keywords", "")
    count = serializer.validated_data.get("count", 1)
    model = serializer.validated_data.get("model", "flux_dev")
    
    # Map model to generation method for backward compatibility
    generation_method = "flux" if model == "flux_dev" else "flux_schnell"
    
    # Set default values
    image_type = "content"  # Default to content type for professional images
    size = "1920x1080"  # Default size - Full HD resolution

    logger.info(
        f"Received image generation request for prompt: '{prompt}' with keywords: '{keywords}', count: {count}, model: {model}"
    )

    # Build final prompt
    final_prompt = prompt
    if keywords and keywords.strip():
        # Split keywords by comma and join them
        keyword_list = [kw.strip() for kw in keywords.split(',') if kw.strip()]
        if keyword_list:
            final_prompt += " " + " ".join(keyword_list)

    # Enhance prompt based on selected model
    if model == "flux_schnell":
        if final_prompt and not any(style_word in final_prompt.lower() for style_word in ['fast', 'quick', 'detailed', 'artistic']):
            final_prompt = f"Create a detailed, artistic image about: {final_prompt}. Use intricate details, rich colors, and high-quality artistic composition."
        method_description = "FLUX Schnell"
        model_description = "FLUX Schnell - Fast Generation (4 steps)"
    else:  # flux_dev
        if final_prompt and not any(style_word in final_prompt.lower() for style_word in ['artistic', 'detailed', 'intricate', 'high-quality']):
            final_prompt = f"Create a detailed, artistic image about: {final_prompt}. Use intricate details, rich colors, and high-quality artistic composition."
        method_description = "FLUX Dev"
        model_description = "FLUX Dev - High Quality (28 steps)"

    try:
        # Call generate_image with the selected generation method
        images_data, total_generated, failed_generations = generate_image(
            prompt=final_prompt, 
            size=size, 
            output_dir="blog_images",
            topic=None,
            image_type=image_type,
            count=count,
            keywords=keywords.split(',') if keywords else None,
            generation_method=generation_method
        )

        if total_generated > 0:
            # Prepare data for database storage
            all_image_urls = [img['image_url'] for img in images_data]
            all_enhanced_prompts = [img.get('enhanced_prompt', final_prompt) for img in images_data]
            first_image_url = all_image_urls[0] if all_image_urls else ""
            
            # Save the image generation session to database
            image_record = ImageGeneration(
                user_id=request.user.id,
                username=request.user.username,
                email=request.user.email,
                prompt=final_prompt,
                image_url=first_image_url,  # Keep first image for backward compatibility
                image_urls=all_image_urls,  # Store all image URLs
                images_count=total_generated,  # Store count of generated images
                enhanced_prompts=all_enhanced_prompts,  # Store all enhanced prompts
                generation_method=model,  # Store the selected model
                image_style=method_description,
                created_at=timezone.now(),
            )
            image_record.save()
            logger.info(f"Saved image generation session with {total_generated} images using {model} model for prompt: '{final_prompt}' with ID: {image_record.id}")

            # Determine response message
            if failed_generations == 0:
                message = f"All {total_generated} {method_description} images generated successfully!"
            else:
                message = f"{total_generated} {method_description} images generated successfully, {failed_generations} failed."

            response_data = {
                "status": "success",
                "message": message,
                "prompt_used": final_prompt,
                "count": count,
                "model": model,
                "generation_method": generation_method,  # Keep for backward compatibility
                "image_style": method_description,
                "images": images_data,
                "total_generated": total_generated,
                "failed_generations": failed_generations,
                "database_record_id": image_record.id,  # Include database record ID
                "stored_image_urls": all_image_urls,  # Include all stored URLs
                "stored_images_count": total_generated,  # Include stored count
            }

            response_serializer = ImageGenerationResponseSerializer(data=response_data)
            if response_serializer.is_valid():
                return Response(response_serializer.data, status=status.HTTP_200_OK)
            else:
                logger.error(
                    f"Error serializing successful response for image generation: {response_serializer.errors}"
                )
                return Response(
                    {"error": "Internal server error during response serialization."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        else:
            logger.error(
                f"All image generations failed for prompt: '{final_prompt}' using {model} model. No images generated."
            )
            return Response(
                {"error": f"All {count} image generation attempts failed using {model} model. Please try again with a different prompt."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    except ValueError as e:
        logger.error(f"Error in image generation: {str(e)}")
        return Response(
            {"error": f"An error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    except Exception as e:
        logger.error(f"Unexpected error in image generation: {type(e).__name__} - {e}")
        import traceback

        traceback.print_exc()
        return Response(
            {"error": f"An unexpected error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    request=LinkedInPostRequestSerializer,
    responses={
        200: OpenApiResponse(
            response=LinkedInPostResponseSerializer,
            description="LinkedIn post generated successfully.",
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer, description="Bad Request - Invalid input."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error."
        ),
    },
    description="Generate a professional LinkedIn post based on the given topic.",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_linkedin_post_api(request):
    """
    Generates a professional LinkedIn post for a given topic.
    Input is a JSON object with a "topic" field.
    """
    # Validate request data using the serializer
    serializer = LinkedInPostRequestSerializer(data=request.data)
    if serializer.is_valid():
        topic = serializer.validated_data["topic"]
        keywords = serializer.validated_data.get("keywords", [])

        try:
            logger.info(
                f"Starting LinkedIn post generation for topic: '{topic}' with keywords: {keywords}"
            )

            linkedin_generator = LinkedInPostGenerator(topic=topic, keywords=keywords)
            linkedin_post_content, _ = linkedin_generator.generate_post(
                topic=topic, keywords=keywords
            )

            if linkedin_post_content:
                # Save to database
                linkedin_post = LinkedinPost(
                    user_id=request.user.id,  # Use authenticated user's ID
                    username=request.user.username,  # Use authenticated user's username
                    email=request.user.email,  # Use authenticated user's email
                    topic=topic,
                    content=linkedin_post_content,
                    created_at=timezone.now(),
                )
                linkedin_post.save()
                logger.info(
                    f"Saved LinkedIn post to database with ID: {linkedin_post.id}"
                )

                response_data = {
                    "status": "success",
                    "message": "LinkedIn post generated successfully!",
                    "topic": topic,
                    "keywords": keywords,
                    "linkedin_post": linkedin_post_content,
                }

                # Serialize the successful response
                response_serializer = LinkedInPostResponseSerializer(data=response_data)
                if response_serializer.is_valid():
                    logger.info(
                        f"Successfully generated LinkedIn post for topic: '{topic}'"
                    )
                    return Response(response_serializer.data, status=status.HTTP_200_OK)
                else:
                    logger.error(
                        f"Error serializing successful response: {response_serializer.errors}"
                    )
                    return Response(
                        {
                            "error": "Internal server error during response serialization."
                        },
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )
            else:
                logger.error(f"LinkedIn post generation failed for topic: '{topic}'")
                return Response(
                    {"error": "LinkedIn post generation failed. Check server logs."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        except Exception as e:
            logger.error(
                f"Unexpected error in LinkedIn post generation API: {type(e).__name__} - {e}"
            )
            import traceback

            traceback.print_exc()
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    else:
        # If serializer validation fails, return errors
        logger.warning(
            f"Invalid input for LinkedIn post generation: {serializer.errors}"
        )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    request=RelatedTopicsRequestSerializer,
    responses={
        200: OpenApiResponse(
            response=RelatedTopicsResponseSerializer,
            description="Trending queries fetched and saved successfully.",
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer, description="Bad Request - Invalid input."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="Internal Server Error or error during trending queries fetching.",
        ),
    },
    description="Fetch trending queries related to a given topic using Serper API and save to database. Fetches 30 trending queries worldwide related to the topic from the past 30 days.",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def fetch_and_save_related_topics(request):
    """
    Fetches trending queries related to a given topic using Serper API and saves to database.
    Fetches 30 trending queries worldwide related to the topic from the past 30 days.

    Input is a JSON object with:
    - "topic" (required string): Main topic to find trending queries for.
    - "region" (optional string): Region code for trends (e.g., 'US'). Defaults to worldwide.
    - "limit" (optional int): Max queries to return. Default 30.
    """
    serializer = RelatedTopicsRequestSerializer(data=request.data)
    if not serializer.is_valid():
        logger.warning(f"Invalid input for trending queries: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    topic = serializer.validated_data["topic"]
    region = serializer.validated_data.get("region", "")
    limit = serializer.validated_data.get("limit", 30)

    try:
        logger.info(
            f"Starting trending queries fetch for topic: '{topic}', region: '{region}', limit: {limit}"
        )

        # Use the updated fetch_trending_queries from trending_queries.py
        trending_queries_data = fetch_trending_queries(
            topic=topic, region=region, limit=limit
        )

        rising_queries = trending_queries_data.get("rising", [])
        top_queries = trending_queries_data.get("top", [])
        total_queries = len(rising_queries) + len(top_queries)

        record_id = None
        if rising_queries or top_queries:
            # Save to database using the keyword field for the topic
            db_record, created = TrendingTopics.objects.update_or_create(
                keyword=topic,  # Using keyword field to store the topic
                defaults={
                    "rising_topics": rising_queries,  # Store as rising_topics
                    "top_topics": top_queries,        # Store as top_topics
                    "created_at": timezone.now(),     # Update timestamp on modification
                },
            )
            record_id = db_record.id
            action = "updated" if not created else "created"
            logger.info(
                f"Successfully {action} and saved {len(rising_queries)} rising and {len(top_queries)} top trending queries for topic '{topic}' with ID: {record_id}"
            )
        else:
            logger.warning(
                f"No trending queries found for topic: '{topic}'. Not saving to DB."
            )

        response_data = {
            "status": "success",
            "message": f"Trending queries fetched and saved successfully for topic '{topic}'.",
            "topic": topic,
            "region": region,
            "rising_queries": rising_queries,
            "top_queries": top_queries,
            "total_queries": total_queries,
            "database_record_id": record_id,
        }

        # Serialize the successful response
        response_serializer = RelatedTopicsResponseSerializer(data=response_data)
        if response_serializer.is_valid():
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        else:
            logger.error(
                f"Error serializing response for trending queries: {response_serializer.errors}"
            )
            return Response(
                {
                    "status": "error",
                    "message": "Internal server error during response serialization.",
                    "details": response_serializer.errors,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    except Exception as e:
        logger.error(
            f"Error processing topic '{topic}': {type(e).__name__} - {str(e)}"
        )
        return Response(
            {
                "status": "error",
                "message": f"Failed to fetch trending queries for topic '{topic}': {str(e)}",
                "topic": topic,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    responses={
        200: OpenApiResponse(
            response=LinkedinAnalyticsResponseSerializer,
            description="LinkedIn analytics fetched successfully.",
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer, description="Bad Request - Missing LinkedIn access token."
        ),
        401: OpenApiResponse(
            response=ErrorResponseSerializer, description="Unauthorized - Invalid or expired LinkedIn access token."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error."
        ),
    },
    description="Fetch LinkedIn profile analytics including followers, posts, and engagement metrics using stored LinkedIn access token from user profile. No parameters required - automatically uses authenticated user's LinkedIn token.",
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def fetch_linkedin_analytics_api(request):
    """
    Fetch LinkedIn profile analytics including:
    - Total number of followers
    - Total number of posts
    - Per post analytics (reactions, comments, reposts, impressions, engagement)
    
    Uses the LinkedIn access token stored in the user's profile from OAuth login.
    No parameters required - automatically fetches analytics for the authenticated user.
    
    Usage:
    GET /api/linkedin-analytics/
    Headers:
        Authorization: Bearer <your_jwt_token>
    """
    
    # Get the authenticated user
    user = request.user
    
    # Check if user has LinkedIn access token
    linkedin_access_token = getattr(user, 'linkedin_access_token', None)
    
    if not linkedin_access_token:
        logger.warning(f"No LinkedIn access token found for user {user.id}")
        return Response(
            {"error": "No LinkedIn access token found. Please login with LinkedIn first to connect your account."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    # Check if token is expired
    if hasattr(user, 'linkedin_token_expires_at') and user.linkedin_token_expires_at and user.linkedin_token_expires_at < timezone.now():
        logger.warning(f"LinkedIn access token expired for user {user.id}")
        return Response(
            {"error": "LinkedIn access token has expired. Please login with LinkedIn again to refresh your token."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Get stored LinkedIn profile ID from user
    linkedin_profile_id = getattr(user, 'linkedin_profile_id', None)

    logger.info(f"Fetching LinkedIn analytics for user {user.id} with profile ID: {linkedin_profile_id}")

    try:
        # Initialize analytics data structure
        analytics_data = {
            'linkedin_profile_id': linkedin_profile_id or 'unknown',
            'total_followers': 0,
            'total_posts': 0,
            'posts_analytics': [],
            'total_reactions': 0,
            'total_comments': 0,
            'total_reposts': 0,
            'total_impressions': 0,
            'total_engagement': 0,
            'available_scopes': ['openid', 'profile', 'email'],
            'api_limitations': [],
            'data_quality': 'basic'
        }

        # Get stored LinkedIn scopes from user model
        stored_scopes = getattr(user, 'linkedin_scopes', '') or ''
        if stored_scopes:
            # Parse stored scopes - LinkedIn can return them comma-separated or space-separated
            if ',' in stored_scopes:
                # Handle comma-separated scopes: "email,openid,profile,w_member_social"
                scope_list = [scope.strip() for scope in stored_scopes.split(',')]
            else:
                # Handle space-separated scopes: "openid profile w_member_social email"
                scope_list = stored_scopes.split()
            
            analytics_data['available_scopes'] = scope_list
            logger.info(f"Using stored LinkedIn scopes: {scope_list}")
            logger.info(f"Raw stored scopes: '{stored_scopes}'")
        else:
            logger.warning("No stored LinkedIn scopes found, using default scopes")
            
        # Additional debug: Try to get current token info from LinkedIn
        logger.info("Attempting to verify current token scopes with LinkedIn...")
        try:
            # Test what the current token can actually access
            token_test_url = "https://api.linkedin.com/v2/me"
            token_headers = {
                'Authorization': f'Bearer {linkedin_access_token}',
                'X-Restli-Protocol-Version': '2.0.0'
            }
            
            token_response = requests.get(token_test_url, headers=token_headers, timeout=10)
            logger.info(f"Token test with /v2/me endpoint: {token_response.status_code}")
            
            if token_response.status_code == 200:
                me_data = token_response.json()
                logger.info(f"Successfully accessed /v2/me endpoint: {me_data}")
            else:
                logger.warning(f"Failed to access /v2/me endpoint: {token_response.status_code} - {token_response.text}")
                
        except Exception as e:
            logger.warning(f"Error testing token with /v2/me: {str(e)}")

        # Check if w_member_social scope is available
        has_w_member_social = 'w_member_social' in analytics_data['available_scopes']
        logger.info(f"w_member_social scope available: {has_w_member_social}")
        logger.info(f"All available scopes: {analytics_data['available_scopes']}")
        
        # Set up headers for LinkedIn API calls (define early so it's available for all subsequent code)
        headers = {
            'Authorization': f'Bearer {linkedin_access_token}',
            'Content-Type': 'application/json',
        }
        
        # Debug: Test w_member_social scope with a simple endpoint
        if has_w_member_social:
            logger.info("Testing w_member_social scope with a simple endpoint...")
            test_headers = headers.copy()
            test_headers['X-Restli-Protocol-Version'] = '2.0.0'
            
            try:
                # Test with a simpler endpoint that should work with w_member_social
                test_url = "https://api.linkedin.com/v2/people/~"
                test_response = requests.get(test_url, headers=test_headers, timeout=10)
                logger.info(f"Simple people endpoint test: {test_response.status_code}")
                
                if test_response.status_code == 200:
                    logger.info("✅ w_member_social scope is working with basic people endpoint")
                else:
                    logger.warning(f"❌ w_member_social scope test failed: {test_response.status_code} - {test_response.text}")
                    
            except Exception as e:
                logger.warning(f"Error testing w_member_social scope: {str(e)}")

        # Step 1: Get profile information using userinfo endpoint
        logger.info("Fetching LinkedIn profile information...")
        profile_url = "https://api.linkedin.com/v2/userinfo"
        
        try:
            profile_response = requests.get(profile_url, headers=headers, timeout=30)
            
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                
                # Extract profile ID if not stored
                if not linkedin_profile_id:
                    linkedin_profile_id = profile_data.get('sub', profile_data.get('id', ''))
                    analytics_data['linkedin_profile_id'] = linkedin_profile_id
                    logger.info(f"Auto-detected LinkedIn profile ID: {linkedin_profile_id}")
                
                logger.info("Successfully fetched LinkedIn profile information")
                
            else:
                logger.warning(f"Failed to fetch profile info: {profile_response.status_code}")
                analytics_data['api_limitations'].append('Profile information access limited')
                
        except Exception as e:
            logger.warning(f"Error fetching profile info: {str(e)}")
            analytics_data['api_limitations'].append('Profile information access failed')

        # Step 2: Scope detection is now handled above using stored scopes from user model
        # No need to test API endpoints since we have the granted scopes stored

        # Step 3: Connection fetching is now handled in Step 5 with correct LinkedIn API endpoints

        # Step 4: Get posts data with w_member_social scope
        logger.info("Attempting to fetch posts data...")
        try:
            if has_w_member_social and linkedin_profile_id:
                # URL encode the URN parameters as required by LinkedIn API v2
                encoded_person_urn = urllib.parse.quote(f"urn:li:person:{linkedin_profile_id}", safe='')
                
                # Use the correct LinkedIn API format for fetching posts with URL encoding
                posts_endpoints = [
                    f"https://api.linkedin.com/v2/ugcPosts?q=authors&authors={encoded_person_urn}",
                    f"https://api.linkedin.com/v2/shares?q=owners&owners={encoded_person_urn}",
                ]
                
                # Add required headers for LinkedIn API v2
                api_headers = headers.copy()
                api_headers['X-Restli-Protocol-Version'] = '2.0.0'
                
                posts_found = False
                for endpoint in posts_endpoints:
                    try:
                        logger.info(f"Trying posts endpoint: {endpoint}")
                        posts_response = requests.get(endpoint, headers=api_headers, timeout=30)
                        
                        logger.info(f"Posts endpoint {endpoint} response: {posts_response.status_code}")
                        if posts_response.status_code == 200:
                            posts_data = posts_response.json()
                            posts = posts_data.get('elements', [])
                            
                            logger.info(f"Posts data received: {len(posts)} posts")
                            logger.info(f"Sample posts data: {posts_data}")
                            
                            analytics_data['total_posts'] = len(posts)
                            logger.info(f"✅ Successfully fetched {len(posts)} posts from {endpoint}")
                            
                            # Process posts for analytics
                            for i, post in enumerate(posts[:20]):  # Process up to 20 posts
                                post_analytics = {
                                    'post_id': post.get('id', f'post_{i}'),
                                    'post_content': str(post.get('text', post.get('commentary', post.get('specificContent', {}).get('com.linkedin.ugc.ShareContent', {}).get('shareCommentary', {}).get('text', ''))))[:200],
                                    'post_date': post.get('created', {}).get('time') if isinstance(post.get('created'), dict) else None,
                                    'reactions': 0,
                                    'comments': 0,
                                    'reposts': 0,
                                    'impressions': 0,
                                    'engagement': 0
                                }
                                
                                # Try to extract engagement data from different possible locations
                                # UGC Posts format
                                if 'socialDetail' in post:
                                    social = post['socialDetail']
                                    if 'totalSocialActivityCounts' in social:
                                        counts = social['totalSocialActivityCounts']
                                        post_analytics['reactions'] = counts.get('numLikes', 0)
                                        post_analytics['comments'] = counts.get('numComments', 0)
                                        post_analytics['reposts'] = counts.get('numShares', 0)
                                
                                # Shares format
                                elif 'totalSocialActivityCounts' in post:
                                    counts = post['totalSocialActivityCounts']
                                    post_analytics['reactions'] = counts.get('numLikes', 0)
                                    post_analytics['comments'] = counts.get('numComments', 0)
                                    post_analytics['reposts'] = counts.get('numShares', 0)
                                
                                # Calculate total engagement
                                post_analytics['engagement'] = (
                                    post_analytics['reactions'] + 
                                    post_analytics['comments'] + 
                                    post_analytics['reposts']
                                )
                                
                                analytics_data['posts_analytics'].append(post_analytics)
                                
                                # Add to totals
                                analytics_data['total_reactions'] += post_analytics['reactions']
                                analytics_data['total_comments'] += post_analytics['comments']
                                analytics_data['total_reposts'] += post_analytics['reposts']
                                analytics_data['total_engagement'] += post_analytics['engagement']
                            
                            posts_found = True
                            break
                        elif posts_response.status_code == 403:
                            logger.warning(f"Posts endpoint {endpoint} failed: 403 - Access denied. This indicates the LinkedIn app needs approval for r_member_social permission.")
                            analytics_data['api_limitations'].append('Posts data requires LinkedIn app approval for r_member_social permission')
                            continue
                        else:
                            logger.warning(f"Posts endpoint {endpoint} failed: {posts_response.status_code} - {posts_response.text}")
                            continue
                            
                    except Exception as e:
                        logger.debug(f"Posts endpoint {endpoint} failed: {str(e)}")
                        continue
                
                if not posts_found:
                    if 'Posts data requires LinkedIn app approval for r_member_social permission' not in analytics_data['api_limitations']:
                        analytics_data['api_limitations'].append('Posts data not available - API access denied')
                        
            else:
                analytics_data['api_limitations'].append('Posts data requires w_member_social scope')
                
        except Exception as e:
            logger.warning(f"Error fetching posts: {str(e)}")
            analytics_data['api_limitations'].append('Posts data access failed')

        # Step 5: Get connections count using correct LinkedIn API endpoints
        logger.info("Attempting to fetch connections count with correct endpoints...")
        try:
            connections_found = False
            
            if has_w_member_social and linkedin_profile_id:
                # URL encode the URN parameters as required by LinkedIn API v2
                encoded_person_urn = urllib.parse.quote(f"urn:li:person:{linkedin_profile_id}", safe='')
                
                # Try the correct LinkedIn API endpoints for connections with URL encoding
                connection_endpoints = [
                    f"https://api.linkedin.com/v2/people/{encoded_person_urn}?projection=(id,numConnections,numConnectionsDisplay)",
                    "https://api.linkedin.com/v2/people/~?projection=(id,numConnections,numConnectionsDisplay)",
                    "https://api.linkedin.com/v2/networkSizes?edgeType=FIRST_DEGREE_CONNECTIONS",
                ]
                
                # Add required headers for LinkedIn API v2
                api_headers = headers.copy()
                api_headers['X-Restli-Protocol-Version'] = '2.0.0'
                
                for endpoint in connection_endpoints:
                    try:
                        logger.info(f"Trying connection endpoint: {endpoint}")
                        conn_response = requests.get(endpoint, headers=api_headers, timeout=30)
                        
                        logger.info(f"Connection endpoint {endpoint} response: {conn_response.status_code}")
                        if conn_response.status_code == 200:
                            conn_data = conn_response.json()
                            logger.info(f"Connection endpoint data: {conn_data}")
                            
                            # Extract connection count from different possible fields
                            connections = (
                                conn_data.get('numConnections', 0) or
                                conn_data.get('connectionCount', 0) or
                                conn_data.get('numConnectionsDisplay', 0) or
                                conn_data.get('firstDegreeSize', 0) or
                                conn_data.get('elements', [{}])[0].get('firstDegreeSize', 0) if conn_data.get('elements') else 0
                            )
                            
                            if connections > 0:
                                analytics_data['total_followers'] = connections
                                logger.info(f"✅ Successfully fetched connections count: {connections}")
                                connections_found = True
                                break
                        elif conn_response.status_code == 403:
                            logger.warning(f"Connection endpoint {endpoint} failed: 403 - Access denied. This indicates the LinkedIn app needs approval for r_member_social permission.")
                            analytics_data['api_limitations'].append('Connection data requires LinkedIn app approval for r_member_social permission')
                            continue
                        else:
                            logger.warning(f"Connection endpoint {endpoint} failed: {conn_response.status_code} - {conn_response.text}")
                            continue
                            
                    except Exception as e:
                        logger.debug(f"Connection endpoint {endpoint} failed: {str(e)}")
                        continue
                        
            if not connections_found:
                if has_w_member_social:
                    analytics_data['api_limitations'].append('Connections count not available - API access denied')
                else:
                    analytics_data['api_limitations'].append('Connections count requires w_member_social scope')
                
        except Exception as e:
            logger.warning(f"Error fetching connections: {str(e)}")
            analytics_data['api_limitations'].append('Connections data access failed')

        # Determine data quality based on available data and scope
        if has_w_member_social and len(analytics_data['api_limitations']) <= 1:
            analytics_data['data_quality'] = 'enhanced'
        elif analytics_data['total_followers'] > 0 or analytics_data['total_posts'] > 0:
            analytics_data['data_quality'] = 'partial'
        else:
            analytics_data['data_quality'] = 'limited'

        # Check if user needs to re-authenticate for w_member_social scope
        needs_reauth = False
        reauth_reason = ""
        
        # Check if the issue is LinkedIn app approval rather than scope
        app_approval_needed = any('LinkedIn app approval' in limitation for limitation in analytics_data['api_limitations'])
        
        if app_approval_needed:
            needs_reauth = False  # Re-auth won't help, app needs approval
            reauth_reason = "Your LinkedIn app needs approval for r_member_social permission. Re-authentication won't resolve this issue."
        elif not has_w_member_social:
            needs_reauth = True
            reauth_reason = "Your LinkedIn token doesn't have the 'w_member_social' scope required for posts and engagement data."
        elif len(analytics_data['api_limitations']) > 2:
            needs_reauth = True
            reauth_reason = "Your LinkedIn token has w_member_social scope but API responses are limited. Re-authentication might help refresh permissions."
        else:
            needs_reauth = False
            reauth_reason = "Your token has the required scopes but LinkedIn API access is limited."
        
        # Save or update analytics data in database
        linkedin_analytics, created = LinkedinAnalytics.objects.update_or_create(
            user_id=user.id,
            linkedin_profile_id=analytics_data['linkedin_profile_id'],
            defaults={
                'username': user.username,
                'email': user.email,
                'total_followers': analytics_data['total_followers'],
                'total_posts': analytics_data['total_posts'],
                'posts_analytics': analytics_data['posts_analytics'],
                'total_reactions': analytics_data['total_reactions'],
                'total_comments': analytics_data['total_comments'],
                'total_reposts': analytics_data['total_reposts'],
                'total_impressions': analytics_data['total_impressions'],
                'total_engagement': analytics_data['total_engagement'],
                'last_updated': timezone.now(),
            }
        )

        action = "updated" if not created else "created"
        logger.info(f"Successfully {action} LinkedIn analytics for profile {analytics_data['linkedin_profile_id']} with ID: {linkedin_analytics.id}")

        # Prepare response data
        response_data = {
            "status": "success",
            "message": f"LinkedIn analytics {action} successfully!",
            "linkedin_profile_id": analytics_data['linkedin_profile_id'],
            "data_source": "official_api",
            "data_quality": analytics_data['data_quality'],
            "available_scopes": analytics_data['available_scopes'],
            "api_limitations": analytics_data['api_limitations'],
            "total_followers": analytics_data['total_followers'],
            "total_posts": analytics_data['total_posts'],
            "posts_analytics": analytics_data['posts_analytics'],
            "total_reactions": analytics_data['total_reactions'],
            "total_comments": analytics_data['total_comments'],
            "total_reposts": analytics_data['total_reposts'],
            "total_impressions": analytics_data['total_impressions'],
            "total_engagement": analytics_data['total_engagement'],
            "last_updated": linkedin_analytics.last_updated,
            "created_at": linkedin_analytics.created_at,
        }

        # Add re-authentication guidance if needed
        if needs_reauth:
            response_data.update({
                "needs_reauth": True,
                "reauth_reason": reauth_reason,
                "reauth_instructions": {
                    "step1": "Visit the LinkedIn login endpoint to re-authenticate",
                    "step2": "Grant the 'w_member_social' permission when prompted",
                    "step3": "This will enable access to posts, engagement data, and connections",
                    "endpoint": "/auth/linkedin/login/",
                    "required_scopes": ["openid", "profile", "w_member_social", "email"],
                    "benefits": [
                        "Access to your LinkedIn posts and their engagement metrics",
                        "Detailed analytics including reactions, comments, and reposts",
                        "Connection count and follower information",
                        "Enhanced data quality for better insights"
                    ]
                },
                "current_limitations": analytics_data['api_limitations']
            })
        elif app_approval_needed:
            response_data.update({
                "needs_reauth": False,
                "reauth_reason": reauth_reason,
                "linkedin_app_approval_required": True,
                "app_approval_instructions": {
                    "issue": "Your LinkedIn app needs approval for restricted permissions",
                    "required_permissions": ["r_member_social", "w_member_social"],
                    "explanation": "The r_member_social permission is restricted and only available to approved LinkedIn apps",
                    "solution_steps": [
                        "Contact LinkedIn Developer Support to request approval for r_member_social permission",
                        "Provide business justification for needing access to member's posts and connections",
                        "Wait for LinkedIn's approval process to complete",
                        "Once approved, the existing token with w_member_social scope should work"
                    ],
                    "alternative": "Use the posting functionality which works with w_member_social scope",
                    "documentation": "https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api"
                },
                "current_limitations": analytics_data['api_limitations'],
                "working_features": [
                    "LinkedIn posting (w_member_social scope)",
                    "Basic profile information (openid, profile scopes)",
                    "Token validation and management"
                ]
            })
        else:
            response_data.update({
                "needs_reauth": False,
                "reauth_reason": reauth_reason,
                "scope_status": {
                    "has_w_member_social": has_w_member_social,
                    "detected_scopes": analytics_data['available_scopes'],
                    "data_quality": analytics_data['data_quality'],
                    "note": "Token has required scopes but LinkedIn API access may be limited by app permissions"
                }
            })

        # Serialize the successful response
        response_serializer = LinkedinAnalyticsResponseSerializer(data=response_data)
        if response_serializer.is_valid():
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        else:
            logger.error(f"Error serializing LinkedIn analytics response: {response_serializer.errors}")
            return Response(
                {"error": "Internal server error during response serialization."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error during LinkedIn API call: {str(e)}")
        return Response(
            {"error": f"Network error while communicating with LinkedIn API: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    except Exception as e:
        logger.error(f"Unexpected error in LinkedIn analytics: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        return Response(
            {"error": f"An unexpected error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    request=LinkedinPostingRequestSerializer,
    responses={
        200: OpenApiResponse(
            response=LinkedinPostingResponseSerializer,
            description="Content posted to LinkedIn successfully.",
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer, description="Bad Request - Invalid input or missing LinkedIn access token."
        ),
        401: OpenApiResponse(
            response=ErrorResponseSerializer, description="Unauthorized - Invalid or expired LinkedIn access token."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error or LinkedIn API error."
        ),
    },
    description="Post content to LinkedIn using the user's stored LinkedIn access token. Supports both text-only posts and posts with images (up to 9 images from S3 URLs). Validates the token, retrieves profile information, uploads images if provided, and posts the content.",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def post_on_linkedin_api(request):
    """
    Post content to LinkedIn using the user's stored LinkedIn access token.
    
    This endpoint:
    1. Validates the user's LinkedIn access token from the users table
    2. Retrieves the user's LinkedIn profile information
    3. Uploads images to LinkedIn if provided (up to 9 images from S3 URLs)
    4. Posts the provided content with or without images to LinkedIn
    5. Saves the post details to the database
    
    Usage:
    POST /api/post-on-linkedin/
    Headers:
        Authorization: Bearer <your_jwt_token>
    Body:
        {
            "content": "Your LinkedIn post content here...",
            "image_urls": ["https://s3.amazonaws.com/bucket/image1.jpg", "https://s3.amazonaws.com/bucket/image2.jpg"]  // Optional
        }
    
    Supported features:
    - Text-only posts
    - Posts with up to 9 images from S3 URLs
    - Automatic image upload to LinkedIn
    - Post type detection (text/image)
    - Comprehensive error handling
    
    Note: Content should be properly escaped JSON. If you're copying from another response,
    make sure to escape quotes and handle newlines properly. Image URLs must be publicly accessible S3 URLs.
    """
    
    # Get the authenticated user
    user = request.user
    
    # Check if user has LinkedIn access token
    linkedin_access_token = getattr(user, 'linkedin_access_token', None)
    
    if not linkedin_access_token:
        logger.warning(f"No LinkedIn access token found for user {user.id}")
        return Response(
            {"error": "No LinkedIn access token found. Please login with LinkedIn first to connect your account."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    # Check if token is expired
    if hasattr(user, 'linkedin_token_expires_at') and user.linkedin_token_expires_at and user.linkedin_token_expires_at < timezone.now():
        logger.warning(f"LinkedIn access token expired for user {user.id}")
        return Response(
            {"error": "LinkedIn access token has expired. Please login with LinkedIn again to refresh your token."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Enhanced error handling for JSON parsing issues
    try:
        # Check if request.data is available and has content
        if not hasattr(request, 'data') or not request.data:
            logger.error("No request data received")
            return Response(
                {
                    "error": "No request data received. Please provide content in JSON format.",
                    "example": {
                        "content": "Your LinkedIn post content here...",
                        "image_urls": ["https://s3.amazonaws.com/bucket/image1.jpg", "https://s3.amazonaws.com/bucket/image2.jpg"]  // Optional
                    },
                    "tip": "Make sure to escape quotes in your content. Use \\\" instead of \" inside the content string."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        # Check if content field exists
        if 'content' not in request.data:
            logger.error("Missing 'content' field in request data")
            return Response(
                {
                    "error": "Missing 'content' field in request data.",
                    "received_fields": list(request.data.keys()) if request.data else [],
                    "expected_format": {
                        "content": "Your LinkedIn post content here...",
                        "image_urls": ["https://s3.amazonaws.com/bucket/image1.jpg", "https://s3.amazonaws.com/bucket/image2.jpg"]  // Optional
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    except Exception as json_error:
        logger.error(f"JSON parsing error: {str(json_error)}")
        return Response(
            {
                "error": "JSON parsing error. Please check your request format.",
                "details": str(json_error),
                "tip": "Common issues: unescaped quotes, missing commas, or invalid JSON structure. Use a JSON validator to check your request.",
                "correct_format": {
                    "content": "Your content here with properly escaped quotes like \\\"this\\\""
                }
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validate request data
    serializer = LinkedinPostingRequestSerializer(data=request.data)
    if not serializer.is_valid():
        logger.warning(f"Invalid request data for LinkedIn posting: {serializer.errors}")
        
        # Provide more helpful error messages
        error_details = {}
        for field, errors in serializer.errors.items():
            error_details[field] = errors
            
        return Response(
            {
                "error": "Invalid request data", 
                "details": error_details,
                "tips": {
                    "content": "Content must be a non-empty string with max 3000 characters",
                    "image_urls": "Optional list of S3 image URLs (max 9 images)",
                    "json_format": "Ensure your JSON is properly formatted with escaped quotes"
                }
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Get and clean the content
    content = serializer.validated_data['content']
    image_urls = serializer.validated_data.get('image_urls', [])
    
    # Determine post type
    post_type = 'image' if image_urls else 'text'
    images_count = len(image_urls)
    
    logger.info(f"Received LinkedIn posting request for user {user.id} with content length: {len(content)}, images: {images_count}")

    # Clean and normalize the content
    try:
        # Remove any potential duplicate content (sometimes copy-paste creates duplicates)
        content_lines = content.split('\n')
        seen_lines = set()
        cleaned_lines = []
        
        for line in content_lines:
            line_stripped = line.strip()
            if line_stripped and line_stripped not in seen_lines:
                cleaned_lines.append(line)
                seen_lines.add(line_stripped)
            elif not line_stripped:  # Keep empty lines for formatting
                cleaned_lines.append(line)
        
        content = '\n'.join(cleaned_lines)
        
        # Final validation
        if len(content.strip()) == 0:
            return Response(
                {"error": "Content cannot be empty after cleaning."},
                status=status.HTTP_400_BAD_REQUEST,
            )
            
    except Exception as content_error:
        logger.error(f"Error processing content: {str(content_error)}")
        return Response(
            {"error": f"Error processing content: {str(content_error)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    logger.info(f"Received LinkedIn posting request for user {user.id} with content length: {len(content)}, images: {images_count}")

    try:
        # First, validate the LinkedIn access token and get user profile information
        # Use the userinfo endpoint which works with OpenID Connect scope
        profile_url = "https://api.linkedin.com/v2/userinfo"
        headers = {
            'Authorization': f'Bearer {linkedin_access_token}',
            'Content-Type': 'application/json',
        }
        
        profile_response = requests.get(profile_url, headers=headers)
        
        if profile_response.status_code != 200:
            logger.error(f"Failed to fetch LinkedIn profile: {profile_response.status_code} - {profile_response.text}")
            
            # Check if it's a permission error
            if profile_response.status_code == 403:
                error_data = {}
                try:
                    error_data = profile_response.json()
                except:
                    pass
                
                return Response(
                    {
                        "error": "LinkedIn access token lacks required permissions.",
                        "details": "The stored LinkedIn token doesn't have sufficient permissions to access profile information.",
                        "linkedin_error": error_data.get('message', 'Access denied'),
                        "solution": "Please re-authenticate with LinkedIn to grant the required permissions.",
                        "required_scopes": ["openid", "profile", "w_member_social", "email"],
                        "current_error": f"Status {profile_response.status_code}: {error_data.get('message', 'Access denied')}"
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            else:
                return Response(
                    {
                        "error": "Failed to validate LinkedIn access token or fetch profile information.",
                        "linkedin_error": f"Status {profile_response.status_code}: {profile_response.text[:200]}...",
                        "suggestion": "Please try re-authenticating with LinkedIn."
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )
        
        profile_data = profile_response.json()
        
        # Extract profile information from userinfo endpoint (OpenID Connect format)
        linkedin_profile_id = profile_data.get('sub', '')  # 'sub' is the standard user ID in OpenID Connect
        linkedin_username = profile_data.get('name', '')
        
        # If we don't have the profile ID, try to extract it from the user's stored data
        if not linkedin_profile_id and hasattr(user, 'linkedin_profile_id') and user.linkedin_profile_id:
            linkedin_profile_id = user.linkedin_profile_id
            logger.info(f"Using stored LinkedIn profile ID: {linkedin_profile_id}")
        
        if not linkedin_profile_id:
            logger.error("Could not determine LinkedIn profile ID")
            return Response(
                {
                    "error": "Could not determine LinkedIn profile ID.",
                    "details": "The LinkedIn token validation succeeded but profile ID is missing.",
                    "suggestion": "Please re-authenticate with LinkedIn to ensure proper profile access."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        logger.info(f"Retrieved LinkedIn profile - ID: {linkedin_profile_id}, Username: {linkedin_username}")

        # Helper function to upload image to LinkedIn
        def upload_image_to_linkedin(image_url, linkedin_access_token, linkedin_profile_id):
            """Upload an image from S3 URL to LinkedIn and return the asset URN"""
            try:
                # Step 1: Register upload for image
                register_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
                register_headers = {
                    'Authorization': f'Bearer {linkedin_access_token}',
                    'Content-Type': 'application/json',
                    'X-Restli-Protocol-Version': '2.0.0'
                }
                
                register_data = {
                    "registerUploadRequest": {
                        "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                        "owner": f"urn:li:person:{linkedin_profile_id}",
                        "serviceRelationships": [
                            {
                                "relationshipType": "OWNER",
                                "identifier": "urn:li:userGeneratedContent"
                            }
                        ]
                    }
                }
                
                register_response = requests.post(register_url, headers=register_headers, json=register_data)
                
                if register_response.status_code != 200:
                    logger.error(f"Failed to register image upload: {register_response.status_code} - {register_response.text}")
                    return None
                
                register_result = register_response.json()
                upload_url = register_result['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
                asset_urn = register_result['value']['asset']
                
                # Step 2: Download image from S3
                image_response = requests.get(image_url, timeout=30)
                if image_response.status_code != 200:
                    logger.error(f"Failed to download image from S3: {image_response.status_code}")
                    return None
                
                # Step 3: Upload image to LinkedIn
                upload_headers = {
                    'Authorization': f'Bearer {linkedin_access_token}',
                }
                
                upload_response = requests.put(upload_url, headers=upload_headers, data=image_response.content)
                
                if upload_response.status_code not in [200, 201]:
                    logger.error(f"Failed to upload image to LinkedIn: {upload_response.status_code} - {upload_response.text}")
                    return None
                
                logger.info(f"Successfully uploaded image to LinkedIn: {asset_urn}")
                return asset_urn
                
            except Exception as e:
                logger.error(f"Error uploading image to LinkedIn: {str(e)}")
                return None

        # Upload images to LinkedIn if provided
        uploaded_assets = []
        if image_urls:
            logger.info(f"Uploading {len(image_urls)} images to LinkedIn...")
            for i, image_url in enumerate(image_urls):
                logger.info(f"Uploading image {i+1}/{len(image_urls)}: {image_url}")
                asset_urn = upload_image_to_linkedin(image_url, linkedin_access_token, linkedin_profile_id)
                if asset_urn:
                    uploaded_assets.append(asset_urn)
                else:
                    logger.warning(f"Failed to upload image {i+1}: {image_url}")
            
            logger.info(f"Successfully uploaded {len(uploaded_assets)}/{len(image_urls)} images")

        # Now post the content to LinkedIn using UGC Posts API
        post_url = "https://api.linkedin.com/v2/ugcPosts"
        
        # Prepare the post data according to LinkedIn API v2 format
        if uploaded_assets:
            # Post with images
            media_list = []
            for asset_urn in uploaded_assets:
                media_list.append({
                    "status": "READY",
                    "description": {
                        "text": ""
                    },
                    "media": asset_urn,
                    "title": {
                        "text": ""
                    }
                })
            
            post_data = {
                "author": f"urn:li:person:{linkedin_profile_id}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": content
                        },
                        "shareMediaCategory": "IMAGE",
                        "media": media_list
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
        else:
            # Text-only post
            post_data = {
                "author": f"urn:li:person:{linkedin_profile_id}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": content
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
        
        post_response = requests.post(post_url, headers=headers, json=post_data)
        
        if post_response.status_code not in [200, 201]:
            logger.error(f"Failed to post to LinkedIn: {post_response.status_code} - {post_response.text}")
            
            # Parse LinkedIn error response
            linkedin_error = "Unknown error"
            try:
                error_data = post_response.json()
                linkedin_error = error_data.get('message', error_data.get('error_description', 'Unknown error'))
            except:
                linkedin_error = post_response.text[:200] + "..." if len(post_response.text) > 200 else post_response.text
            
            # Save failed post attempt to database
            linkedin_post = LinkedinPostingContent.objects.create(
                user_id=user.id,
                username=user.username,
                email=user.email,
                linkedin_profile_id=linkedin_profile_id,
                linkedin_username=linkedin_username,
                content=content,
                post_date=timezone.now(),
                post_status='failed',
                image_urls=image_urls,
                images_count=images_count,
                post_type=post_type,
            )
            
            # Provide specific error messages based on status code
            if post_response.status_code == 403:
                error_message = "LinkedIn posting permission denied. Your token may not have 'w_member_social' scope."
            elif post_response.status_code == 401:
                error_message = "LinkedIn access token is invalid or expired."
            elif post_response.status_code == 422:
                error_message = "LinkedIn rejected the post content. Please check content format and length."
            else:
                error_message = f"LinkedIn API error (Status {post_response.status_code})"
            
            return Response(
                {
                    "error": error_message,
                    "linkedin_error": linkedin_error,
                    "status_code": post_response.status_code,
                    "database_record_id": linkedin_post.id,
                    "image_urls": image_urls,
                    "images_count": images_count,
                    "post_type": post_type,
                    "suggestion": "Please re-authenticate with LinkedIn if the token is expired or lacks permissions."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        
        # Extract LinkedIn post ID from response
        post_response_data = post_response.json()
        linkedin_post_id = post_response_data.get('id', '')
        
        logger.info(f"Successfully posted to LinkedIn - Post ID: {linkedin_post_id}, Type: {post_type}, Images: {images_count}")

        # Save successful post to database
        linkedin_post = LinkedinPostingContent.objects.create(
            user_id=user.id,
            username=user.username,
            email=user.email,
            linkedin_profile_id=linkedin_profile_id,
            linkedin_username=linkedin_username,
            content=content,
            post_date=timezone.now(),
            linkedin_post_id=linkedin_post_id,
            post_status='success',
            image_urls=image_urls,
            images_count=images_count,
            post_type=post_type,
        )

        logger.info(f"Successfully saved LinkedIn post to database with ID: {linkedin_post.id}")

        # Prepare response data
        response_data = {
            "status": "success",
            "message": f"Content posted to LinkedIn successfully! ({post_type} post with {images_count} images)" if images_count > 0 else "Content posted to LinkedIn successfully!",
            "profile_id": linkedin_profile_id,
            "username": linkedin_username,
            "content": content,
            "post_date": linkedin_post.post_date,
            "linkedin_post_id": linkedin_post_id,
            "database_record_id": linkedin_post.id,
            "image_urls": image_urls,
            "images_count": images_count,
            "post_type": post_type,
        }

        # Serialize the successful response
        response_serializer = LinkedinPostingResponseSerializer(data=response_data)
        if response_serializer.is_valid():
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        else:
            logger.error(f"Error serializing LinkedIn posting response: {response_serializer.errors}")
            return Response(
                {"error": "Internal server error during response serialization."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error during LinkedIn API call: {str(e)}")
        return Response(
            {"error": f"Network error while communicating with LinkedIn API: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    except Exception as e:
        logger.error(f"Unexpected error in LinkedIn posting: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        return Response(
            {"error": f"An unexpected error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    responses={
        200: OpenApiResponse(
            description="LinkedIn re-authentication URL generated successfully.",
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error."
        ),
    },
    description="Generate a LinkedIn re-authentication URL with w_member_social scope to enable full analytics access. This endpoint helps users upgrade their LinkedIn token permissions.",
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def linkedin_reauth_url_api(request):
    """
    Generate a LinkedIn re-authentication URL with w_member_social scope.
    
    This endpoint helps users who have basic LinkedIn tokens to re-authenticate
    and get enhanced permissions for accessing posts, engagement data, and connections.
    
    Usage:
    GET /api/linkedin-reauth-url/
    Headers:
        Authorization: Bearer <your_jwt_token>
    
    Returns:
        {
            "auth_url": "https://www.linkedin.com/oauth/v2/authorization?...",
            "required_scopes": ["openid", "profile", "w_member_social", "email"],
            "benefits": ["Access to posts data", "Engagement metrics", "Connection count"],
            "instructions": "Click the auth_url to re-authenticate with enhanced permissions"
        }
    """
    
    try:
        import hashlib
        import os
        from django.conf import settings
        
        # Get LinkedIn OAuth settings
        LINKEDIN_CLIENT_ID = os.environ.get('LINKEDIN_CLIENT_ID', '')
        LINKEDIN_REDIRECT_URI = os.environ.get('LINKEDIN_REDIRECT_URI', '')
        
        if not LINKEDIN_CLIENT_ID or not LINKEDIN_REDIRECT_URI:
            logger.error("LinkedIn OAuth settings not configured")
            return Response(
                {
                    "error": "LinkedIn OAuth not configured",
                    "details": "LINKEDIN_CLIENT_ID or LINKEDIN_REDIRECT_URI not set in environment variables"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        
        # Generate state parameter for security
        state = hashlib.sha256(os.urandom(32).hex().encode()).hexdigest()
        
        # Construct LinkedIn OAuth URL with w_member_social scope
        linkedin_auth_url = "https://www.linkedin.com/oauth/v2/authorization"
        params = {
            "client_id": LINKEDIN_CLIENT_ID,
            "redirect_uri": LINKEDIN_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid profile w_member_social email",  # Include w_member_social
            "state": state
        }
        
        # Construct full URL with parameters
        auth_url = f"{linkedin_auth_url}?{'&'.join([f'{key}={value}' for key, value in params.items()])}"
        
        logger.info(f"Generated LinkedIn re-auth URL for user {request.user.id}")
        
        return Response({
            "status": "success",
            "message": "LinkedIn re-authentication URL generated successfully",
            "auth_url": auth_url,
            "required_scopes": ["openid", "profile", "w_member_social", "email"],
            "current_user": {
                "id": request.user.id,
                "username": request.user.username,
                "email": request.user.email,
                "has_linkedin_token": bool(getattr(request.user, 'linkedin_access_token', None))
            },
            "benefits": [
                "Access to your LinkedIn posts and their content",
                "Detailed engagement metrics (reactions, comments, reposts)",
                "Connection count and follower information",
                "Enhanced analytics data quality",
                "Full social media insights"
            ],
            "instructions": {
                "step1": "Click the 'auth_url' to open LinkedIn authorization page",
                "step2": "Login to LinkedIn if not already logged in",
                "step3": "Review and accept the requested permissions",
                "step4": "You'll be redirected back to the application",
                "step5": "Your token will be automatically updated with new permissions",
                "note": "This will replace your existing LinkedIn token with an enhanced one"
            },
            "what_happens_next": [
                "Your existing LinkedIn token will be replaced",
                "You'll have access to enhanced analytics features",
                "Posts and engagement data will be available",
                "Connection count will be accessible"
            ]
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error generating LinkedIn re-auth URL: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        return Response(
            {"error": f"An unexpected error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    responses={
        200: OpenApiResponse(
            description="LinkedIn token validation successful.",
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer, description="Bad Request - No LinkedIn token found."
        ),
        401: OpenApiResponse(
            response=ErrorResponseSerializer, description="Unauthorized - Invalid or expired LinkedIn token."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error."
        ),
    },
    description="Validate the user's stored LinkedIn access token and check available permissions. Useful for debugging token issues before posting content.",
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def validate_linkedin_token_api(request):
    """
    Validate the user's stored LinkedIn access token and check available permissions.
    
    This endpoint helps debug token issues by:
    1. Checking if a LinkedIn token exists for the user
    2. Validating the token with LinkedIn's API
    3. Retrieving available scopes/permissions
    4. Checking token expiration
    
    Usage:
    GET /api/validate-linkedin-token/
    Headers:
        Authorization: Bearer <your_jwt_token>
    """
    
    # Get the authenticated user
    user = request.user
    
    # Check if user has LinkedIn access token
    linkedin_access_token = getattr(user, 'linkedin_access_token', None)
    
    if not linkedin_access_token:
        logger.warning(f"No LinkedIn access token found for user {user.id}")
        return Response(
            {
                "valid": False,
                "error": "No LinkedIn access token found.",
                "details": "User has not connected their LinkedIn account.",
                "solution": "Please login with LinkedIn first to connect your account.",
                "user_id": user.id,
                "username": user.username
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    # Check if token is expired (if we have expiration info)
    token_expired = False
    if hasattr(user, 'linkedin_token_expires_at') and user.linkedin_token_expires_at:
        if user.linkedin_token_expires_at < timezone.now():
            token_expired = True
    
    try:
        # Test the token with LinkedIn's userinfo endpoint
        profile_url = "https://api.linkedin.com/v2/userinfo"
        headers = {
            'Authorization': f'Bearer {linkedin_access_token}',
            'Content-Type': 'application/json',
        }
        
        profile_response = requests.get(profile_url, headers=headers)
        
        # Prepare response data
        response_data = {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "token_exists": True,
            "token_length": len(linkedin_access_token),
            "token_preview": linkedin_access_token[:20] + "..." if len(linkedin_access_token) > 20 else linkedin_access_token,
            "token_expired_by_date": token_expired,
            "token_expires_at": user.linkedin_token_expires_at if hasattr(user, 'linkedin_token_expires_at') else None,
            "stored_linkedin_profile_id": getattr(user, 'linkedin_profile_id', None),
        }
        
        if profile_response.status_code == 200:
            # Token is valid
            profile_data = profile_response.json()
            
            response_data.update({
                "valid": True,
                "status": "success",
                "message": "LinkedIn token is valid and working!",
                "profile_data": {
                    "linkedin_id": profile_data.get('sub', ''),
                    "name": profile_data.get('name', ''),
                    "email": profile_data.get('email', ''),
                    "picture": profile_data.get('picture', ''),
                },
                "available_endpoints": {
                    "userinfo": "✅ Working",
                    "posting": "✅ Should work (requires w_member_social scope)"
                },
                "recommendations": [
                    "Token is working correctly",
                    "You can proceed with posting content to LinkedIn"
                ]
            })
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        elif profile_response.status_code == 403:
            # Permission denied
            error_data = {}
            try:
                error_data = profile_response.json()
            except:
                pass
            
            response_data.update({
                "valid": False,
                "status": "permission_denied",
                "message": "LinkedIn token lacks required permissions.",
                "error": error_data.get('message', 'Access denied'),
                "linkedin_error_code": error_data.get('serviceErrorCode', 'Unknown'),
                "available_endpoints": {
                    "userinfo": "❌ Permission denied",
                    "posting": "❌ Likely to fail"
                },
                "required_scopes": ["openid", "profile", "w_member_social", "email"],
                "recommendations": [
                    "Re-authenticate with LinkedIn to grant required permissions",
                    "Ensure your LinkedIn app has the correct scopes configured",
                    "Check if your LinkedIn app is approved for the required permissions"
                ]
            })
            
            return Response(response_data, status=status.HTTP_401_UNAUTHORIZED)
            
        elif profile_response.status_code == 401:
            # Token invalid or expired
            response_data.update({
                "valid": False,
                "status": "invalid_or_expired",
                "message": "LinkedIn token is invalid or expired.",
                "linkedin_response": profile_response.text[:200] + "..." if len(profile_response.text) > 200 else profile_response.text,
                "available_endpoints": {
                    "userinfo": "❌ Unauthorized",
                    "posting": "❌ Will fail"
                },
                "recommendations": [
                    "Re-authenticate with LinkedIn to get a fresh token",
                    "Check if the token has expired",
                    "Verify LinkedIn app credentials"
                ]
            })
            
            return Response(response_data, status=status.HTTP_401_UNAUTHORIZED)
            
        else:
            # Other error
            response_data.update({
                "valid": False,
                "status": "api_error",
                "message": f"LinkedIn API returned unexpected status: {profile_response.status_code}",
                "linkedin_response": profile_response.text[:200] + "..." if len(profile_response.text) > 200 else profile_response.text,
                "available_endpoints": {
                    "userinfo": f"❌ Error {profile_response.status_code}",
                    "posting": "❌ Likely to fail"
                },
                "recommendations": [
                    "Check LinkedIn API status",
                    "Try re-authenticating with LinkedIn",
                    "Contact support if the issue persists"
                ]
            })
            
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error during LinkedIn token validation: {str(e)}")
        return Response(
            {
                "valid": False,
                "status": "network_error",
                "message": "Network error while validating LinkedIn token.",
                "error": str(e),
                "recommendations": [
                    "Check your internet connection",
                    "Try again in a few moments",
                    "Contact support if the issue persists"
                ]
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    except Exception as e:
        logger.error(f"Unexpected error in LinkedIn token validation: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        return Response(
            {
                "valid": False,
                "status": "unexpected_error",
                "message": "An unexpected error occurred during token validation.",
                "error": str(e),
                "recommendations": [
                    "Try again in a few moments",
                    "Contact support if the issue persists"
                ]
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# Schedule LinkedIn Post Endpoints

@extend_schema(
    request=ScheduleLinkedinPostRequestSerializer,
    responses={
        200: OpenApiResponse(
            response=ScheduleLinkedinPostResponseSerializer,
            description="LinkedIn posts scheduled successfully.",
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer, description="Bad Request - Invalid input or missing LinkedIn access token."
        ),
        401: OpenApiResponse(
            response=ErrorResponseSerializer, description="Unauthorized - Invalid or expired LinkedIn access token."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error."
        ),
    },
    description="Schedule multiple LinkedIn posts to be published at a specific date and time with delays between posts. Requires LinkedIn authentication and validates the scheduled time is in the future.",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def schedule_linkedin_post_api(request):
    """
    Schedule multiple LinkedIn posts to be published at a specific date and time.
    
    This endpoint:
    1. Validates the user has LinkedIn authentication
    2. Validates the scheduled time is in the future
    3. Creates a scheduled post record in the database with multiple content
    4. Schedules a Celery task to post at the specified time with delays between posts
    
    Body Parameters:
    - content: Array of LinkedIn post content (each max 3000 characters, max 10 posts)
    - scheduled_date: Date to publish (YYYY-MM-DD format)
    - scheduled_time: Time to publish (HH:MM:SS format)
    - timezone: Timezone for the scheduled time (optional, default: UTC)
    - image_urls: Optional list of image URLs to distribute across posts
    - delay_between_posts: Delay in minutes between each post (default: 5 minutes)
    
    Returns:
    - schedule_id: Unique ID for the scheduled post batch
    - total_posts: Number of posts scheduled
    - scheduled_datetime: When the first post will be published
    - celery_task_id: Task ID for tracking/cancellation
    """
    
    # Get the authenticated user
    user = request.user
    
    # Check if user has LinkedIn access token
    linkedin_access_token = getattr(user, 'linkedin_access_token', None)
    linkedin_profile_id = getattr(user, 'linkedin_profile_id', None)
    
    if not linkedin_access_token or not linkedin_profile_id:
        logger.warning(f"No LinkedIn access token found for user {user.id}")
        return Response(
            {
                "error": "LinkedIn authentication required.",
                "details": "User has not connected their LinkedIn account.",
                "solution": "Please login with LinkedIn first to connect your account."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    # Validate request data
    serializer = ScheduleLinkedinPostRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"error": "Invalid input data.", "details": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    validated_data = serializer.validated_data
    
    try:
        # Get LinkedIn username (optional, for display purposes)
        linkedin_username = ""
        try:
            profile_url = "https://api.linkedin.com/v2/userinfo"
            headers = {
                'Authorization': f'Bearer {linkedin_access_token}',
                'Content-Type': 'application/json',
            }
            profile_response = requests.get(profile_url, headers=headers)
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                linkedin_username = profile_data.get('name', '')
        except:
            pass  # Continue without username if API call fails
        
        # Get multiple content posts
        content_array = validated_data['content']
        total_posts = len(content_array)
        delay_between_posts = validated_data.get('delay_between_posts', 5)
        
        # Determine post type
        post_type = 'image' if validated_data.get('image_urls') else 'text'
        images_count = len(validated_data.get('image_urls', []))
        
        # Create scheduled post record with array content
        scheduled_post = SchedulePosts.objects.create(
            user_id=user.id,
            username=user.username,
            email=user.email,
            linkedin_profile_id=linkedin_profile_id,
            linkedin_username=linkedin_username,
            content=content_array,  # Now storing as array
            image_urls=validated_data.get('image_urls', []),
            images_count=images_count,
            post_type=post_type,
            scheduled_datetime=validated_data['scheduled_datetime'],
            user_timezone=validated_data.get('timezone', 'UTC'),
            status='scheduled'
        )
        
        # Schedule Celery task
        from tools.ai.schedule_linkedin_post.tasks import schedule_linkedin_post_batch_task
        from celery import current_app
        
        # Calculate ETA (when to execute the task)
        eta = validated_data['scheduled_datetime']
        
        # Schedule the batch task with delay information
        task = schedule_linkedin_post_batch_task.apply_async(
            args=[scheduled_post.id, delay_between_posts],
            eta=eta
        )
        
        # Save the Celery task ID for potential cancellation
        scheduled_post.celery_task_id = task.id
        scheduled_post.save()
        
        logger.info(f"Scheduled LinkedIn post batch {scheduled_post.id} with {total_posts} posts for user {user.id} at {eta}")
        
        # Prepare response
        response_data = {
            "status": "success",
            "message": f"{total_posts} LinkedIn posts scheduled successfully starting at {validated_data['scheduled_datetime'].strftime('%Y-%m-%d %H:%M:%S %Z')}",
            "schedule_id": scheduled_post.id,
            "content": scheduled_post.content,
            "total_posts": total_posts,
            "scheduled_datetime": scheduled_post.scheduled_datetime,
            "timezone": scheduled_post.user_timezone,
            "linkedin_profile_id": scheduled_post.linkedin_profile_id,
            "linkedin_username": scheduled_post.linkedin_username,
            "post_type": scheduled_post.post_type,
            "images_count": scheduled_post.images_count,
            "delay_between_posts": delay_between_posts,
            "celery_task_id": scheduled_post.celery_task_id,
            "created_at": scheduled_post.created_at
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error scheduling LinkedIn post for user {user.id}: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response(
            {
                "error": "Failed to schedule LinkedIn post.",
                "details": str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    responses={
        200: OpenApiResponse(
            response=ScheduledPostsListResponseSerializer,
            description="Scheduled posts retrieved successfully.",
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error."
        ),
    },
    description="Get all scheduled LinkedIn posts for the authenticated user, including their status and details.",
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_scheduled_posts_api(request):
    """
    Get all scheduled LinkedIn posts for the authenticated user.
    
    Returns a list of all scheduled posts with their current status:
    - scheduled: Waiting to be posted
    - posted: Successfully posted
    - failed: Failed to post
    - cancelled: Cancelled by user
    """
    
    user = request.user
    
    try:
        # Get all scheduled posts for the user
        scheduled_posts = SchedulePosts.objects.filter(user_id=user.id).order_by('-scheduled_datetime')
        
        # Prepare response data
        posts_data = []
        for post in scheduled_posts:
            # Handle both array and single content for backward compatibility
            content = post.content
            if isinstance(content, list):
                total_posts = len(content)
                content_preview = content[0][:100] + "..." if content and len(content[0]) > 100 else (content[0] if content else "")
            else:
                total_posts = 1
                content_preview = content[:100] + "..." if content and len(content) > 100 else content
            
            posts_data.append({
                "schedule_id": post.id,
                "content": post.content,
                "content_preview": content_preview,
                "total_posts": total_posts,
                "scheduled_datetime": post.scheduled_datetime,
                "timezone": post.user_timezone,
                "status": post.status,
                "linkedin_profile_id": post.linkedin_profile_id,
                "linkedin_username": post.linkedin_username,
                "post_type": post.post_type,
                "images_count": post.images_count,
                "created_at": post.created_at,
                "posted_at": post.posted_at,
                "linkedin_post_id": post.linkedin_post_id,
                "error_message": post.error_message
            })
        
        response_data = {
            "status": "success",
            "message": f"Retrieved {len(posts_data)} scheduled posts",
            "total_scheduled": len(posts_data),
            "scheduled_posts": posts_data
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error retrieving scheduled posts for user {user.id}: {str(e)}")
        return Response(
            {
                "error": "Failed to retrieve scheduled posts.",
                "details": str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    responses={
        200: OpenApiResponse(
            response=CancelScheduledPostResponseSerializer,
            description="Scheduled post cancelled successfully.",
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer, description="Bad Request - Invalid schedule ID or post cannot be cancelled."
        ),
        404: OpenApiResponse(
            response=ErrorResponseSerializer, description="Not Found - Scheduled post not found."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error."
        ),
    },
    description="Cancel a scheduled LinkedIn post. Only posts with 'scheduled' status can be cancelled.",
)
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def cancel_scheduled_post_api(request, schedule_id):
    """
    Cancel a scheduled LinkedIn post.
    
    Path Parameters:
    - schedule_id: The ID of the scheduled post to cancel
    
    Only posts with 'scheduled' status can be cancelled.
    This will also revoke the associated Celery task.
    """
    
    user = request.user
    
    try:
        # Get the scheduled post
        try:
            scheduled_post = SchedulePosts.objects.get(id=schedule_id, user_id=user.id)
        except SchedulePosts.DoesNotExist:
            return Response(
                {
                    "error": "Scheduled post not found.",
                    "details": f"No scheduled post found with ID {schedule_id} for this user."
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        
        # Check if post can be cancelled
        if scheduled_post.status != 'scheduled':
            return Response(
                {
                    "error": "Post cannot be cancelled.",
                    "details": f"Post status is '{scheduled_post.status}'. Only 'scheduled' posts can be cancelled.",
                    "current_status": scheduled_post.status
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        previous_status = scheduled_post.status
        
        # Cancel the Celery task if it exists
        if scheduled_post.celery_task_id:
            try:
                from celery import current_app
                current_app.control.revoke(scheduled_post.celery_task_id, terminate=True)
                logger.info(f"Revoked Celery task {scheduled_post.celery_task_id} for scheduled post {schedule_id}")
            except Exception as e:
                logger.warning(f"Failed to revoke Celery task {scheduled_post.celery_task_id}: {str(e)}")
        
        # Update post status
        scheduled_post.status = 'cancelled'
        scheduled_post.save()
        
        logger.info(f"Cancelled scheduled post {schedule_id} for user {user.id}")
        
        response_data = {
            "status": "success",
            "message": f"Scheduled post {schedule_id} cancelled successfully",
            "schedule_id": scheduled_post.id,
            "previous_status": previous_status,
            "current_status": scheduled_post.status
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error cancelling scheduled post {schedule_id} for user {user.id}: {str(e)}")
        return Response(
            {
                "error": "Failed to cancel scheduled post.",
                "details": str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    request={
        'multipart/form-data': {
            'type': 'object',
            'properties': {
                'prompt': {
                    'type': 'string',
                    'description': 'The editing instruction/prompt describing what changes to make to the image.',
                    'maxLength': 1000
                },
                'keywords': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': 'Optional keywords to guide the editing process.',
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
    },
    responses={
        200: OpenApiResponse(
            response=ImageEditingResponseSerializer,
            description="Image edited successfully using FLUX AI.",
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer, description="Bad Request - Invalid input or image format."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="Internal Server Error / Image Editing Failed.",
        ),
    },
    description="Edit an uploaded image using FLUX AI based on the provided prompt and optional keywords. Upload an image file and provide editing instructions to transform the image using advanced AI editing capabilities.",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def edit_image_api(request):
    """
    Edit an uploaded image using FLUX AI based on the provided prompt and keywords.
    
    This endpoint:
    1. Accepts multipart form data with prompt, keywords, and image file
    2. Converts the image to base64 format
    3. Optimizes the editing prompt using AI
    4. Sends the image and prompt to FLUX AI for editing
    5. Downloads and uploads the edited result to S3
    6. Saves the editing session to the database
    
    Request format:
    - Multipart form data with prompt (string), keywords (array), and image (file)
    """
    import json
    
    # Extract prompt and keywords from form data
    prompt = request.data.get('prompt')
    keywords = request.data.get('keywords', [])
    
    # Handle keywords if sent as JSON string
    if isinstance(keywords, str):
        try:
            keywords = json.loads(keywords)
        except json.JSONDecodeError:
            # If not valid JSON, treat as comma-separated string
            keywords = [k.strip() for k in keywords.split(',') if k.strip()]
    
    # Validate prompt
    if not prompt or not prompt.strip():
        return Response(
            {"error": "Missing or empty 'prompt'. Please provide an editing instruction."},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate prompt length
    if len(prompt) > 1000:
        return Response(
            {"error": "Prompt exceeds maximum length of 1000 characters."},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Convert keywords array to string for processing
    if isinstance(keywords, list):
        keywords_str = ", ".join(keywords) if keywords else ""
    else:
        keywords_str = str(keywords) if keywords else ""
    
    # Validate keywords length if provided
    if keywords_str and len(keywords_str) > 500:
        return Response(
            {"error": "Keywords exceed maximum length of 500 characters."},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate the image file
    uploaded_image = request.FILES.get('image')
    if not uploaded_image:
        return Response(
            {"error": "Missing image file. Please upload an image file."},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate image file
    if uploaded_image.size > 10 * 1024 * 1024:
        return Response(
            {"error": "Image file size cannot exceed 10MB."},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    allowed_formats = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
    if uploaded_image.content_type not in allowed_formats:
        return Response(
            {"error": "Unsupported image format. Please use JPEG, PNG, or WebP."},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    logger.info(
        f"Received image editing request for prompt: '{prompt}' with keywords: '{keywords_str}', image size: {uploaded_image.size} bytes"
    )

    start_time = timezone.now()

    try:
        # Convert uploaded image to base64
        image_base64 = convert_image_to_base64(uploaded_image)
        if not image_base64:
            logger.error("Failed to convert uploaded image to base64")
            return Response(
                {"error": "Failed to process the uploaded image. Please ensure it's a valid image file."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Edit the image using FLUX AI
        success, edited_image_url, enhanced_prompt, error_message = edit_image_with_flux(
            prompt=prompt,
            image_base64=image_base64,
            keywords=keywords_str,
            output_dir="edited_images"
        )

        # Calculate processing time
        processing_time = (timezone.now() - start_time).total_seconds()

        if success and edited_image_url:
            # Save the image editing session to database
            image_editing_record = ImageEditing(
                user_id=request.user.id,
                username=request.user.username,
                email=request.user.email,
                prompt=prompt,
                keywords=keywords_str,
                uploaded_image=image_base64,  # Store base64 of original image
                image_url=edited_image_url,
                enhanced_prompt=enhanced_prompt,
                edit_status='success',
                created_at=timezone.now(),
            )
            image_editing_record.save()
            
            logger.info(f"Successfully edited image for prompt: '{prompt}' with ID: {image_editing_record.id}")

            response_data = {
                "status": "success", 
                "message": "Image edited successfully using FLUX AI!",
                "prompt_used": prompt,
                "enhanced_prompt": enhanced_prompt,
                "keywords": keywords_str,
                "original_image_size": uploaded_image.size,
                "edited_image_url": edited_image_url,
                "database_record_id": image_editing_record.id,
                "edit_status": "success",
                "processing_time": processing_time,
                "created_at": image_editing_record.created_at,
            }

            response_serializer = ImageEditingResponseSerializer(data=response_data)
            if response_serializer.is_valid():
                return Response(response_serializer.data, status=status.HTTP_200_OK)
            else:
                logger.error(
                    f"Error serializing successful response for image editing: {response_serializer.errors}"
                )
                return Response(
                    {"error": "Internal server error during response serialization."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        else:
            # Save failed editing attempt to database
            image_editing_record = ImageEditing(
                user_id=request.user.id,
                username=request.user.username,
                email=request.user.email,
                prompt=prompt,
                keywords=keywords_str,
                uploaded_image=image_base64,
                image_url="",  # No result URL for failed attempts
                enhanced_prompt=enhanced_prompt or prompt,
                edit_status='failed',
                created_at=timezone.now(),
            )
            image_editing_record.save()
            
            logger.error(f"Image editing failed for prompt: '{prompt}'. Error: {error_message}")
            return Response(
                {
                    "error": f"Image editing failed: {error_message}",
                    "database_record_id": image_editing_record.id,
                    "edit_status": "failed",
                    "processing_time": processing_time,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    except Exception as e:
        processing_time = (timezone.now() - start_time).total_seconds()
        logger.error(f"Unexpected error in image editing: {type(e).__name__} - {e}")
        
        # Try to save error to database
        try:
            image_editing_record = ImageEditing(
                user_id=request.user.id,
                username=request.user.username,
                email=request.user.email,
                prompt=prompt,
                keywords=keywords,
                uploaded_image="",  # Don't store image on error
                image_url="",
                enhanced_prompt=prompt,
                edit_status='failed',
                created_at=timezone.now(),
            )
            image_editing_record.save()
            record_id = image_editing_record.id
        except:
            record_id = None
            
        import traceback
        traceback.print_exc()
        return Response(
            {
                "error": f"An unexpected error occurred: {str(e)}",
                "database_record_id": record_id,
                "edit_status": "failed", 
                "processing_time": processing_time,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    request=LinkedInPostRequestSerializer,
    responses={
        200: OpenApiResponse(
            response=LinkedInPostResponseSerializer,
            description="LinkedIn post generated successfully.",
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer, description="Bad Request - Invalid input."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error."
        ),
    },
    description="Generate a professional LinkedIn post based on the given topic.",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_linkedin_post_api(request):
    """
    Generates a professional LinkedIn post for a given topic.
    Input is a JSON object with a "topic" field.
    """
    # Validate request data using the serializer
    serializer = LinkedInPostRequestSerializer(data=request.data)
    if serializer.is_valid():
        topic = serializer.validated_data["topic"]
        keywords = serializer.validated_data.get("keywords", [])

        try:
            logger.info(
                f"Starting LinkedIn post generation for topic: '{topic}' with keywords: {keywords}"
            )

            linkedin_generator = LinkedInPostGenerator(topic=topic, keywords=keywords)
            linkedin_post_content, _ = linkedin_generator.generate_post(
                topic=topic, keywords=keywords
            )

            if linkedin_post_content:
                # Save to database
                linkedin_post = LinkedinPost(
                    user_id=request.user.id,  # Use authenticated user's ID
                    username=request.user.username,  # Use authenticated user's username
                    email=request.user.email,  # Use authenticated user's email
                    topic=topic,
                    content=linkedin_post_content,
                    created_at=timezone.now(),
                )
                linkedin_post.save()
                logger.info(
                    f"Saved LinkedIn post to database with ID: {linkedin_post.id}"
                )

                response_data = {
                    "status": "success",
                    "message": "LinkedIn post generated successfully!",
                    "topic": topic,
                    "keywords": keywords,
                    "linkedin_post": linkedin_post_content,
                }

                # Serialize the successful response
                response_serializer = LinkedInPostResponseSerializer(data=response_data)
                if response_serializer.is_valid():
                    logger.info(
                        f"Successfully generated LinkedIn post for topic: '{topic}'"
                    )
                    return Response(response_serializer.data, status=status.HTTP_200_OK)
                else:
                    logger.error(
                        f"Error serializing successful response: {response_serializer.errors}"
                    )
                    return Response(
                        {
                            "error": "Internal server error during response serialization."
                        },
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )
            else:
                logger.error(f"LinkedIn post generation failed for topic: '{topic}'")
                return Response(
                    {"error": "LinkedIn post generation failed. Check server logs."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        except Exception as e:
            logger.error(
                f"Unexpected error in LinkedIn post generation API: {type(e).__name__} - {e}"
            )
            import traceback

            traceback.print_exc()
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    else:
        # If serializer validation fails, return errors
        logger.warning(
            f"Invalid input for LinkedIn post generation: {serializer.errors}"
        )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    request=RelatedTopicsRequestSerializer,
    responses={
        200: OpenApiResponse(
            response=RelatedTopicsResponseSerializer,
            description="Trending queries fetched and saved successfully.",
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer, description="Bad Request - Invalid input."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="Internal Server Error or error during trending queries fetching.",
        ),
    },
    description="Fetch trending queries related to a given topic using Serper API and save to database. Fetches 30 trending queries worldwide related to the topic from the past 30 days.",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def fetch_and_save_related_topics(request):
    """
    Fetches trending queries related to a given topic using Serper API and saves to database.
    Fetches 30 trending queries worldwide related to the topic from the past 30 days.

    Input is a JSON object with:
    - "topic" (required string): Main topic to find trending queries for.
    - "region" (optional string): Region code for trends (e.g., 'US'). Defaults to worldwide.
    - "limit" (optional int): Max queries to return. Default 30.
    """
    serializer = RelatedTopicsRequestSerializer(data=request.data)
    if not serializer.is_valid():
        logger.warning(f"Invalid input for trending queries: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    topic = serializer.validated_data["topic"]
    region = serializer.validated_data.get("region", "")
    limit = serializer.validated_data.get("limit", 30)

    try:
        logger.info(
            f"Starting trending queries fetch for topic: '{topic}', region: '{region}', limit: {limit}"
        )

        # Use the updated fetch_trending_queries from trending_queries.py
        trending_queries_data = fetch_trending_queries(
            topic=topic, region=region, limit=limit
        )

        rising_queries = trending_queries_data.get("rising", [])
        top_queries = trending_queries_data.get("top", [])
        total_queries = len(rising_queries) + len(top_queries)

        record_id = None
        if rising_queries or top_queries:
            # Save to database using the keyword field for the topic
            db_record, created = TrendingTopics.objects.update_or_create(
                keyword=topic,  # Using keyword field to store the topic
                defaults={
                    "rising_topics": rising_queries,  # Store as rising_topics
                    "top_topics": top_queries,        # Store as top_topics
                    "created_at": timezone.now(),     # Update timestamp on modification
                },
            )
            record_id = db_record.id
            action = "updated" if not created else "created"
            logger.info(
                f"Successfully {action} and saved {len(rising_queries)} rising and {len(top_queries)} top trending queries for topic '{topic}' with ID: {record_id}"
            )
        else:
            logger.warning(
                f"No trending queries found for topic: '{topic}'. Not saving to DB."
            )

        response_data = {
            "status": "success",
            "message": f"Trending queries fetched and saved successfully for topic '{topic}'.",
            "topic": topic,
            "region": region,
            "rising_queries": rising_queries,
            "top_queries": top_queries,
            "total_queries": total_queries,
            "database_record_id": record_id,
        }

        # Serialize the successful response
        response_serializer = RelatedTopicsResponseSerializer(data=response_data)
        if response_serializer.is_valid():
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        else:
            logger.error(
                f"Error serializing response for trending queries: {response_serializer.errors}"
            )
            return Response(
                {
                    "status": "error",
                    "message": "Internal server error during response serialization.",
                    "details": response_serializer.errors,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    except Exception as e:
        logger.error(
            f"Error processing topic '{topic}': {type(e).__name__} - {str(e)}"
        )
        return Response(
            {
                "status": "error",
                "message": f"Failed to fetch trending queries for topic '{topic}': {str(e)}",
                "topic": topic,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    responses={
        200: OpenApiResponse(
            response=LinkedinAnalyticsResponseSerializer,
            description="LinkedIn analytics fetched successfully.",
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer, description="Bad Request - Missing LinkedIn access token."
        ),
        401: OpenApiResponse(
            response=ErrorResponseSerializer, description="Unauthorized - Invalid or expired LinkedIn access token."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error."
        ),
    },
    description="Fetch LinkedIn profile analytics including followers, posts, and engagement metrics using stored LinkedIn access token from user profile. No parameters required - automatically uses authenticated user's LinkedIn token.",
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def fetch_linkedin_analytics_api(request):
    """
    Fetch LinkedIn profile analytics including:
    - Total number of followers
    - Total number of posts
    - Per post analytics (reactions, comments, reposts, impressions, engagement)
    
    Uses the LinkedIn access token stored in the user's profile from OAuth login.
    No parameters required - automatically fetches analytics for the authenticated user.
    
    Usage:
    GET /api/linkedin-analytics/
    Headers:
        Authorization: Bearer <your_jwt_token>
    """
    
    # Get the authenticated user
    user = request.user
    
    # Check if user has LinkedIn access token
    linkedin_access_token = getattr(user, 'linkedin_access_token', None)
    
    if not linkedin_access_token:
        logger.warning(f"No LinkedIn access token found for user {user.id}")
        return Response(
            {"error": "No LinkedIn access token found. Please login with LinkedIn first to connect your account."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    # Check if token is expired
    if hasattr(user, 'linkedin_token_expires_at') and user.linkedin_token_expires_at and user.linkedin_token_expires_at < timezone.now():
        logger.warning(f"LinkedIn access token expired for user {user.id}")
        return Response(
            {"error": "LinkedIn access token has expired. Please login with LinkedIn again to refresh your token."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Get stored LinkedIn profile ID from user
    linkedin_profile_id = getattr(user, 'linkedin_profile_id', None)

    logger.info(f"Fetching LinkedIn analytics for user {user.id} with profile ID: {linkedin_profile_id}")

    try:
        # Initialize analytics data structure
        analytics_data = {
            'linkedin_profile_id': linkedin_profile_id or 'unknown',
            'total_followers': 0,
            'total_posts': 0,
            'posts_analytics': [],
            'total_reactions': 0,
            'total_comments': 0,
            'total_reposts': 0,
            'total_impressions': 0,
            'total_engagement': 0,
            'available_scopes': ['openid', 'profile', 'email'],
            'api_limitations': [],
            'data_quality': 'basic'
        }

        # Get stored LinkedIn scopes from user model
        stored_scopes = getattr(user, 'linkedin_scopes', '') or ''
        if stored_scopes:
            # Parse stored scopes - LinkedIn can return them comma-separated or space-separated
            if ',' in stored_scopes:
                # Handle comma-separated scopes: "email,openid,profile,w_member_social"
                scope_list = [scope.strip() for scope in stored_scopes.split(',')]
            else:
                # Handle space-separated scopes: "openid profile w_member_social email"
                scope_list = stored_scopes.split()
            
            analytics_data['available_scopes'] = scope_list
            logger.info(f"Using stored LinkedIn scopes: {scope_list}")
            logger.info(f"Raw stored scopes: '{stored_scopes}'")
        else:
            logger.warning("No stored LinkedIn scopes found, using default scopes")
            
        # Additional debug: Try to get current token info from LinkedIn
        logger.info("Attempting to verify current token scopes with LinkedIn...")
        try:
            # Test what the current token can actually access
            token_test_url = "https://api.linkedin.com/v2/me"
            token_headers = {
                'Authorization': f'Bearer {linkedin_access_token}',
                'X-Restli-Protocol-Version': '2.0.0'
            }
            
            token_response = requests.get(token_test_url, headers=token_headers, timeout=10)
            logger.info(f"Token test with /v2/me endpoint: {token_response.status_code}")
            
            if token_response.status_code == 200:
                me_data = token_response.json()
                logger.info(f"Successfully accessed /v2/me endpoint: {me_data}")
            else:
                logger.warning(f"Failed to access /v2/me endpoint: {token_response.status_code} - {token_response.text}")
                
        except Exception as e:
            logger.warning(f"Error testing token with /v2/me: {str(e)}")

        # Check if w_member_social scope is available
        has_w_member_social = 'w_member_social' in analytics_data['available_scopes']
        logger.info(f"w_member_social scope available: {has_w_member_social}")
        logger.info(f"All available scopes: {analytics_data['available_scopes']}")
        
        # Set up headers for LinkedIn API calls (define early so it's available for all subsequent code)
        headers = {
            'Authorization': f'Bearer {linkedin_access_token}',
            'Content-Type': 'application/json',
        }
        
        # Debug: Test w_member_social scope with a simple endpoint
        if has_w_member_social:
            logger.info("Testing w_member_social scope with a simple endpoint...")
            test_headers = headers.copy()
            test_headers['X-Restli-Protocol-Version'] = '2.0.0'
            
            try:
                # Test with a simpler endpoint that should work with w_member_social
                test_url = "https://api.linkedin.com/v2/people/~"
                test_response = requests.get(test_url, headers=test_headers, timeout=10)
                logger.info(f"Simple people endpoint test: {test_response.status_code}")
                
                if test_response.status_code == 200:
                    logger.info("✅ w_member_social scope is working with basic people endpoint")
                else:
                    logger.warning(f"❌ w_member_social scope test failed: {test_response.status_code} - {test_response.text}")
                    
            except Exception as e:
                logger.warning(f"Error testing w_member_social scope: {str(e)}")

        # Step 1: Get profile information using userinfo endpoint
        logger.info("Fetching LinkedIn profile information...")
        profile_url = "https://api.linkedin.com/v2/userinfo"
        
        try:
            profile_response = requests.get(profile_url, headers=headers, timeout=30)
            
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                
                # Extract profile ID if not stored
                if not linkedin_profile_id:
                    linkedin_profile_id = profile_data.get('sub', profile_data.get('id', ''))
                    analytics_data['linkedin_profile_id'] = linkedin_profile_id
                    logger.info(f"Auto-detected LinkedIn profile ID: {linkedin_profile_id}")
                
                logger.info("Successfully fetched LinkedIn profile information")
                
            else:
                logger.warning(f"Failed to fetch profile info: {profile_response.status_code}")
                analytics_data['api_limitations'].append('Profile information access limited')
                
        except Exception as e:
            logger.warning(f"Error fetching profile info: {str(e)}")
            analytics_data['api_limitations'].append('Profile information access failed')

        # Step 2: Scope detection is now handled above using stored scopes from user model
        # No need to test API endpoints since we have the granted scopes stored

        # Step 3: Connection fetching is now handled in Step 5 with correct LinkedIn API endpoints

        # Step 4: Get posts data with w_member_social scope
        logger.info("Attempting to fetch posts data...")
        try:
            if has_w_member_social and linkedin_profile_id:
                # URL encode the URN parameters as required by LinkedIn API v2
                encoded_person_urn = urllib.parse.quote(f"urn:li:person:{linkedin_profile_id}", safe='')
                
                # Use the correct LinkedIn API format for fetching posts with URL encoding
                posts_endpoints = [
                    f"https://api.linkedin.com/v2/ugcPosts?q=authors&authors={encoded_person_urn}",
                    f"https://api.linkedin.com/v2/shares?q=owners&owners={encoded_person_urn}",
                ]
                
                # Add required headers for LinkedIn API v2
                api_headers = headers.copy()
                api_headers['X-Restli-Protocol-Version'] = '2.0.0'
                
                posts_found = False
                for endpoint in posts_endpoints:
                    try:
                        logger.info(f"Trying posts endpoint: {endpoint}")
                        posts_response = requests.get(endpoint, headers=api_headers, timeout=30)
                        
                        logger.info(f"Posts endpoint {endpoint} response: {posts_response.status_code}")
                        if posts_response.status_code == 200:
                            posts_data = posts_response.json()
                            posts = posts_data.get('elements', [])
                            
                            logger.info(f"Posts data received: {len(posts)} posts")
                            logger.info(f"Sample posts data: {posts_data}")
                            
                            analytics_data['total_posts'] = len(posts)
                            logger.info(f"✅ Successfully fetched {len(posts)} posts from {endpoint}")
                            
                            # Process posts for analytics
                            for i, post in enumerate(posts[:20]):  # Process up to 20 posts
                                post_analytics = {
                                    'post_id': post.get('id', f'post_{i}'),
                                    'post_content': str(post.get('text', post.get('commentary', post.get('specificContent', {}).get('com.linkedin.ugc.ShareContent', {}).get('shareCommentary', {}).get('text', ''))))[:200],
                                    'post_date': post.get('created', {}).get('time') if isinstance(post.get('created'), dict) else None,
                                    'reactions': 0,
                                    'comments': 0,
                                    'reposts': 0,
                                    'impressions': 0,
                                    'engagement': 0
                                }
                                
                                # Try to extract engagement data from different possible locations
                                # UGC Posts format
                                if 'socialDetail' in post:
                                    social = post['socialDetail']
                                    if 'totalSocialActivityCounts' in social:
                                        counts = social['totalSocialActivityCounts']
                                        post_analytics['reactions'] = counts.get('numLikes', 0)
                                        post_analytics['comments'] = counts.get('numComments', 0)
                                        post_analytics['reposts'] = counts.get('numShares', 0)
                                
                                # Shares format
                                elif 'totalSocialActivityCounts' in post:
                                    counts = post['totalSocialActivityCounts']
                                    post_analytics['reactions'] = counts.get('numLikes', 0)
                                    post_analytics['comments'] = counts.get('numComments', 0)
                                    post_analytics['reposts'] = counts.get('numShares', 0)
                                
                                # Calculate total engagement
                                post_analytics['engagement'] = (
                                    post_analytics['reactions'] + 
                                    post_analytics['comments'] + 
                                    post_analytics['reposts']
                                )
                                
                                analytics_data['posts_analytics'].append(post_analytics)
                                
                                # Add to totals
                                analytics_data['total_reactions'] += post_analytics['reactions']
                                analytics_data['total_comments'] += post_analytics['comments']
                                analytics_data['total_reposts'] += post_analytics['reposts']
                                analytics_data['total_engagement'] += post_analytics['engagement']
                            
                            posts_found = True
                            break
                        elif posts_response.status_code == 403:
                            logger.warning(f"Posts endpoint {endpoint} failed: 403 - Access denied. This indicates the LinkedIn app needs approval for r_member_social permission.")
                            analytics_data['api_limitations'].append('Posts data requires LinkedIn app approval for r_member_social permission')
                            continue
                        else:
                            logger.warning(f"Posts endpoint {endpoint} failed: {posts_response.status_code} - {posts_response.text}")
                            continue
                            
                    except Exception as e:
                        logger.debug(f"Posts endpoint {endpoint} failed: {str(e)}")
                        continue
                
                if not posts_found:
                    if 'Posts data requires LinkedIn app approval for r_member_social permission' not in analytics_data['api_limitations']:
                        analytics_data['api_limitations'].append('Posts data not available - API access denied')
                        
            else:
                analytics_data['api_limitations'].append('Posts data requires w_member_social scope')
                
        except Exception as e:
            logger.warning(f"Error fetching posts: {str(e)}")
            analytics_data['api_limitations'].append('Posts data access failed')

        # Step 5: Get connections count using correct LinkedIn API endpoints
        logger.info("Attempting to fetch connections count with correct endpoints...")
        try:
            connections_found = False
            
            if has_w_member_social and linkedin_profile_id:
                # URL encode the URN parameters as required by LinkedIn API v2
                encoded_person_urn = urllib.parse.quote(f"urn:li:person:{linkedin_profile_id}", safe='')
                
                # Try the correct LinkedIn API endpoints for connections with URL encoding
                connection_endpoints = [
                    f"https://api.linkedin.com/v2/people/{encoded_person_urn}?projection=(id,numConnections,numConnectionsDisplay)",
                    "https://api.linkedin.com/v2/people/~?projection=(id,numConnections,numConnectionsDisplay)",
                    "https://api.linkedin.com/v2/networkSizes?edgeType=FIRST_DEGREE_CONNECTIONS",
                ]
                
                # Add required headers for LinkedIn API v2
                api_headers = headers.copy()
                api_headers['X-Restli-Protocol-Version'] = '2.0.0'
                
                for endpoint in connection_endpoints:
                    try:
                        logger.info(f"Trying connection endpoint: {endpoint}")
                        conn_response = requests.get(endpoint, headers=api_headers, timeout=30)
                        
                        logger.info(f"Connection endpoint {endpoint} response: {conn_response.status_code}")
                        if conn_response.status_code == 200:
                            conn_data = conn_response.json()
                            logger.info(f"Connection endpoint data: {conn_data}")
                            
                            # Extract connection count from different possible fields
                            connections = (
                                conn_data.get('numConnections', 0) or
                                conn_data.get('connectionCount', 0) or
                                conn_data.get('numConnectionsDisplay', 0) or
                                conn_data.get('firstDegreeSize', 0) or
                                conn_data.get('elements', [{}])[0].get('firstDegreeSize', 0) if conn_data.get('elements') else 0
                            )
                            
                            if connections > 0:
                                analytics_data['total_followers'] = connections
                                logger.info(f"✅ Successfully fetched connections count: {connections}")
                                connections_found = True
                                break
                        elif conn_response.status_code == 403:
                            logger.warning(f"Connection endpoint {endpoint} failed: 403 - Access denied. This indicates the LinkedIn app needs approval for r_member_social permission.")
                            analytics_data['api_limitations'].append('Connection data requires LinkedIn app approval for r_member_social permission')
                            continue
                        else:
                            logger.warning(f"Connection endpoint {endpoint} failed: {conn_response.status_code} - {conn_response.text}")
                            continue
                            
                    except Exception as e:
                        logger.debug(f"Connection endpoint {endpoint} failed: {str(e)}")
                        continue
                        
            if not connections_found:
                if has_w_member_social:
                    analytics_data['api_limitations'].append('Connections count not available - API access denied')
                else:
                    analytics_data['api_limitations'].append('Connections count requires w_member_social scope')
                
        except Exception as e:
            logger.warning(f"Error fetching connections: {str(e)}")
            analytics_data['api_limitations'].append('Connections data access failed')

        # Determine data quality based on available data and scope
        if has_w_member_social and len(analytics_data['api_limitations']) <= 1:
            analytics_data['data_quality'] = 'enhanced'
        elif analytics_data['total_followers'] > 0 or analytics_data['total_posts'] > 0:
            analytics_data['data_quality'] = 'partial'
        else:
            analytics_data['data_quality'] = 'limited'

        # Check if user needs to re-authenticate for w_member_social scope
        needs_reauth = False
        reauth_reason = ""
        
        # Check if the issue is LinkedIn app approval rather than scope
        app_approval_needed = any('LinkedIn app approval' in limitation for limitation in analytics_data['api_limitations'])
        
        if app_approval_needed:
            needs_reauth = False  # Re-auth won't help, app needs approval
            reauth_reason = "Your LinkedIn app needs approval for r_member_social permission. Re-authentication won't resolve this issue."
        elif not has_w_member_social:
            needs_reauth = True
            reauth_reason = "Your LinkedIn token doesn't have the 'w_member_social' scope required for posts and engagement data."
        elif len(analytics_data['api_limitations']) > 2:
            needs_reauth = True
            reauth_reason = "Your LinkedIn token has w_member_social scope but API responses are limited. Re-authentication might help refresh permissions."
        else:
            needs_reauth = False
            reauth_reason = "Your token has the required scopes but LinkedIn API access is limited."
        
        # Save or update analytics data in database
        linkedin_analytics, created = LinkedinAnalytics.objects.update_or_create(
            user_id=user.id,
            linkedin_profile_id=analytics_data['linkedin_profile_id'],
            defaults={
                'username': user.username,
                'email': user.email,
                'total_followers': analytics_data['total_followers'],
                'total_posts': analytics_data['total_posts'],
                'posts_analytics': analytics_data['posts_analytics'],
                'total_reactions': analytics_data['total_reactions'],
                'total_comments': analytics_data['total_comments'],
                'total_reposts': analytics_data['total_reposts'],
                'total_impressions': analytics_data['total_impressions'],
                'total_engagement': analytics_data['total_engagement'],
                'last_updated': timezone.now(),
            }
        )

        action = "updated" if not created else "created"
        logger.info(f"Successfully {action} LinkedIn analytics for profile {analytics_data['linkedin_profile_id']} with ID: {linkedin_analytics.id}")

        # Prepare response data
        response_data = {
            "status": "success",
            "message": f"LinkedIn analytics {action} successfully!",
            "linkedin_profile_id": analytics_data['linkedin_profile_id'],
            "data_source": "official_api",
            "data_quality": analytics_data['data_quality'],
            "available_scopes": analytics_data['available_scopes'],
            "api_limitations": analytics_data['api_limitations'],
            "total_followers": analytics_data['total_followers'],
            "total_posts": analytics_data['total_posts'],
            "posts_analytics": analytics_data['posts_analytics'],
            "total_reactions": analytics_data['total_reactions'],
            "total_comments": analytics_data['total_comments'],
            "total_reposts": analytics_data['total_reposts'],
            "total_impressions": analytics_data['total_impressions'],
            "total_engagement": analytics_data['total_engagement'],
            "last_updated": linkedin_analytics.last_updated,
            "created_at": linkedin_analytics.created_at,
        }

        # Add re-authentication guidance if needed
        if needs_reauth:
            response_data.update({
                "needs_reauth": True,
                "reauth_reason": reauth_reason,
                "reauth_instructions": {
                    "step1": "Visit the LinkedIn login endpoint to re-authenticate",
                    "step2": "Grant the 'w_member_social' permission when prompted",
                    "step3": "This will enable access to posts, engagement data, and connections",
                    "endpoint": "/auth/linkedin/login/",
                    "required_scopes": ["openid", "profile", "w_member_social", "email"],
                    "benefits": [
                        "Access to your LinkedIn posts and their engagement metrics",
                        "Detailed analytics including reactions, comments, and reposts",
                        "Connection count and follower information",
                        "Enhanced data quality for better insights"
                    ]
                },
                "current_limitations": analytics_data['api_limitations']
            })
        elif app_approval_needed:
            response_data.update({
                "needs_reauth": False,
                "reauth_reason": reauth_reason,
                "linkedin_app_approval_required": True,
                "app_approval_instructions": {
                    "issue": "Your LinkedIn app needs approval for restricted permissions",
                    "required_permissions": ["r_member_social", "w_member_social"],
                    "explanation": "The r_member_social permission is restricted and only available to approved LinkedIn apps",
                    "solution_steps": [
                        "Contact LinkedIn Developer Support to request approval for r_member_social permission",
                        "Provide business justification for needing access to member's posts and connections",
                        "Wait for LinkedIn's approval process to complete",
                        "Once approved, the existing token with w_member_social scope should work"
                    ],
                    "alternative": "Use the posting functionality which works with w_member_social scope",
                    "documentation": "https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api"
                },
                "current_limitations": analytics_data['api_limitations'],
                "working_features": [
                    "LinkedIn posting (w_member_social scope)",
                    "Basic profile information (openid, profile scopes)",
                    "Token validation and management"
                ]
            })
        else:
            response_data.update({
                "needs_reauth": False,
                "reauth_reason": reauth_reason,
                "scope_status": {
                    "has_w_member_social": has_w_member_social,
                    "detected_scopes": analytics_data['available_scopes'],
                    "data_quality": analytics_data['data_quality'],
                    "note": "Token has required scopes but LinkedIn API access may be limited by app permissions"
                }
            })

        # Serialize the successful response
        response_serializer = LinkedinAnalyticsResponseSerializer(data=response_data)
        if response_serializer.is_valid():
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        else:
            logger.error(f"Error serializing LinkedIn analytics response: {response_serializer.errors}")
            return Response(
                {"error": "Internal server error during response serialization."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error during LinkedIn API call: {str(e)}")
        return Response(
            {"error": f"Network error while communicating with LinkedIn API: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    except Exception as e:
        logger.error(f"Unexpected error in LinkedIn analytics: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        return Response(
            {"error": f"An unexpected error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    request=LinkedinPostingRequestSerializer,
    responses={
        200: OpenApiResponse(
            response=LinkedinPostingResponseSerializer,
            description="Content posted to LinkedIn successfully.",
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer, description="Bad Request - Invalid input or missing LinkedIn access token."
        ),
        401: OpenApiResponse(
            response=ErrorResponseSerializer, description="Unauthorized - Invalid or expired LinkedIn access token."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error or LinkedIn API error."
        ),
    },
    description="Post content to LinkedIn using the user's stored LinkedIn access token. Supports both text-only posts and posts with images (up to 9 images from S3 URLs). Validates the token, retrieves profile information, uploads images if provided, and posts the content.",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def post_on_linkedin_api(request):
    """
    Post content to LinkedIn using the user's stored LinkedIn access token.
    
    This endpoint:
    1. Validates the user's LinkedIn access token from the users table
    2. Retrieves the user's LinkedIn profile information
    3. Uploads images to LinkedIn if provided (up to 9 images from S3 URLs)
    4. Posts the provided content with or without images to LinkedIn
    5. Saves the post details to the database
    
    Usage:
    POST /api/post-on-linkedin/
    Headers:
        Authorization: Bearer <your_jwt_token>
    Body:
        {
            "content": "Your LinkedIn post content here...",
            "image_urls": ["https://s3.amazonaws.com/bucket/image1.jpg", "https://s3.amazonaws.com/bucket/image2.jpg"]  // Optional
        }
    
    Supported features:
    - Text-only posts
    - Posts with up to 9 images from S3 URLs
    - Automatic image upload to LinkedIn
    - Post type detection (text/image)
    - Comprehensive error handling
    
    Note: Content should be properly escaped JSON. If you're copying from another response,
    make sure to escape quotes and handle newlines properly. Image URLs must be publicly accessible S3 URLs.
    """
    
    # Get the authenticated user
    user = request.user
    
    # Check if user has LinkedIn access token
    linkedin_access_token = getattr(user, 'linkedin_access_token', None)
    
    if not linkedin_access_token:
        logger.warning(f"No LinkedIn access token found for user {user.id}")
        return Response(
            {"error": "No LinkedIn access token found. Please login with LinkedIn first to connect your account."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    # Check if token is expired
    if hasattr(user, 'linkedin_token_expires_at') and user.linkedin_token_expires_at and user.linkedin_token_expires_at < timezone.now():
        logger.warning(f"LinkedIn access token expired for user {user.id}")
        return Response(
            {"error": "LinkedIn access token has expired. Please login with LinkedIn again to refresh your token."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Enhanced error handling for JSON parsing issues
    try:
        # Check if request.data is available and has content
        if not hasattr(request, 'data') or not request.data:
            logger.error("No request data received")
            return Response(
                {
                    "error": "No request data received. Please provide content in JSON format.",
                    "example": {
                        "content": "Your LinkedIn post content here...",
                        "image_urls": ["https://s3.amazonaws.com/bucket/image1.jpg", "https://s3.amazonaws.com/bucket/image2.jpg"]  // Optional
                    },
                    "tip": "Make sure to escape quotes in your content. Use \\\" instead of \" inside the content string."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        # Check if content field exists
        if 'content' not in request.data:
            logger.error("Missing 'content' field in request data")
            return Response(
                {
                    "error": "Missing 'content' field in request data.",
                    "received_fields": list(request.data.keys()) if request.data else [],
                    "expected_format": {
                        "content": "Your LinkedIn post content here...",
                        "image_urls": ["https://s3.amazonaws.com/bucket/image1.jpg", "https://s3.amazonaws.com/bucket/image2.jpg"]  // Optional
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    except Exception as json_error:
        logger.error(f"JSON parsing error: {str(json_error)}")
        return Response(
            {
                "error": "JSON parsing error. Please check your request format.",
                "details": str(json_error),
                "tip": "Common issues: unescaped quotes, missing commas, or invalid JSON structure. Use a JSON validator to check your request.",
                "correct_format": {
                    "content": "Your content here with properly escaped quotes like \\\"this\\\""
                }
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validate request data
    serializer = LinkedinPostingRequestSerializer(data=request.data)
    if not serializer.is_valid():
        logger.warning(f"Invalid request data for LinkedIn posting: {serializer.errors}")
        
        # Provide more helpful error messages
        error_details = {}
        for field, errors in serializer.errors.items():
            error_details[field] = errors
            
        return Response(
            {
                "error": "Invalid request data", 
                "details": error_details,
                "tips": {
                    "content": "Content must be a non-empty string with max 3000 characters",
                    "image_urls": "Optional list of S3 image URLs (max 9 images)",
                    "json_format": "Ensure your JSON is properly formatted with escaped quotes"
                }
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Get and clean the content
    content = serializer.validated_data['content']
    image_urls = serializer.validated_data.get('image_urls', [])
    
    # Determine post type
    post_type = 'image' if image_urls else 'text'
    images_count = len(image_urls)
    
    logger.info(f"Received LinkedIn posting request for user {user.id} with content length: {len(content)}, images: {images_count}")

    # Clean and normalize the content
    try:
        # Remove any potential duplicate content (sometimes copy-paste creates duplicates)
        content_lines = content.split('\n')
        seen_lines = set()
        cleaned_lines = []
        
        for line in content_lines:
            line_stripped = line.strip()
            if line_stripped and line_stripped not in seen_lines:
                cleaned_lines.append(line)
                seen_lines.add(line_stripped)
            elif not line_stripped:  # Keep empty lines for formatting
                cleaned_lines.append(line)
        
        content = '\n'.join(cleaned_lines)
        
        # Final validation
        if len(content.strip()) == 0:
            return Response(
                {"error": "Content cannot be empty after cleaning."},
                status=status.HTTP_400_BAD_REQUEST,
            )
            
    except Exception as content_error:
        logger.error(f"Error processing content: {str(content_error)}")
        return Response(
            {"error": f"Error processing content: {str(content_error)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    logger.info(f"Received LinkedIn posting request for user {user.id} with content length: {len(content)}, images: {images_count}")

    try:
        # First, validate the LinkedIn access token and get user profile information
        # Use the userinfo endpoint which works with OpenID Connect scope
        profile_url = "https://api.linkedin.com/v2/userinfo"
        headers = {
            'Authorization': f'Bearer {linkedin_access_token}',
            'Content-Type': 'application/json',
        }
        
        profile_response = requests.get(profile_url, headers=headers)
        
        if profile_response.status_code != 200:
            logger.error(f"Failed to fetch LinkedIn profile: {profile_response.status_code} - {profile_response.text}")
            
            # Check if it's a permission error
            if profile_response.status_code == 403:
                error_data = {}
                try:
                    error_data = profile_response.json()
                except:
                    pass
                
                return Response(
                    {
                        "error": "LinkedIn access token lacks required permissions.",
                        "details": "The stored LinkedIn token doesn't have sufficient permissions to access profile information.",
                        "linkedin_error": error_data.get('message', 'Access denied'),
                        "solution": "Please re-authenticate with LinkedIn to grant the required permissions.",
                        "required_scopes": ["openid", "profile", "w_member_social", "email"],
                        "current_error": f"Status {profile_response.status_code}: {error_data.get('message', 'Access denied')}"
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            else:
                return Response(
                    {
                        "error": "Failed to validate LinkedIn access token or fetch profile information.",
                        "linkedin_error": f"Status {profile_response.status_code}: {profile_response.text[:200]}...",
                        "suggestion": "Please try re-authenticating with LinkedIn."
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )
        
        profile_data = profile_response.json()
        
        # Extract profile information from userinfo endpoint (OpenID Connect format)
        linkedin_profile_id = profile_data.get('sub', '')  # 'sub' is the standard user ID in OpenID Connect
        linkedin_username = profile_data.get('name', '')
        
        # If we don't have the profile ID, try to extract it from the user's stored data
        if not linkedin_profile_id and hasattr(user, 'linkedin_profile_id') and user.linkedin_profile_id:
            linkedin_profile_id = user.linkedin_profile_id
            logger.info(f"Using stored LinkedIn profile ID: {linkedin_profile_id}")
        
        if not linkedin_profile_id:
            logger.error("Could not determine LinkedIn profile ID")
            return Response(
                {
                    "error": "Could not determine LinkedIn profile ID.",
                    "details": "The LinkedIn token validation succeeded but profile ID is missing.",
                    "suggestion": "Please re-authenticate with LinkedIn to ensure proper profile access."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        logger.info(f"Retrieved LinkedIn profile - ID: {linkedin_profile_id}, Username: {linkedin_username}")

        # Helper function to upload image to LinkedIn
        def upload_image_to_linkedin(image_url, linkedin_access_token, linkedin_profile_id):
            """Upload an image from S3 URL to LinkedIn and return the asset URN"""
            try:
                # Step 1: Register upload for image
                register_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
                register_headers = {
                    'Authorization': f'Bearer {linkedin_access_token}',
                    'Content-Type': 'application/json',
                    'X-Restli-Protocol-Version': '2.0.0'
                }
                
                register_data = {
                    "registerUploadRequest": {
                        "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                        "owner": f"urn:li:person:{linkedin_profile_id}",
                        "serviceRelationships": [
                            {
                                "relationshipType": "OWNER",
                                "identifier": "urn:li:userGeneratedContent"
                            }
                        ]
                    }
                }
                
                register_response = requests.post(register_url, headers=register_headers, json=register_data)
                
                if register_response.status_code != 200:
                    logger.error(f"Failed to register image upload: {register_response.status_code} - {register_response.text}")
                    return None
                
                register_result = register_response.json()
                upload_url = register_result['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
                asset_urn = register_result['value']['asset']
                
                # Step 2: Download image from S3
                image_response = requests.get(image_url, timeout=30)
                if image_response.status_code != 200:
                    logger.error(f"Failed to download image from S3: {image_response.status_code}")
                    return None
                
                # Step 3: Upload image to LinkedIn
                upload_headers = {
                    'Authorization': f'Bearer {linkedin_access_token}',
                }
                
                upload_response = requests.put(upload_url, headers=upload_headers, data=image_response.content)
                
                if upload_response.status_code not in [200, 201]:
                    logger.error(f"Failed to upload image to LinkedIn: {upload_response.status_code} - {upload_response.text}")
                    return None
                
                logger.info(f"Successfully uploaded image to LinkedIn: {asset_urn}")
                return asset_urn
                
            except Exception as e:
                logger.error(f"Error uploading image to LinkedIn: {str(e)}")
                return None

        # Upload images to LinkedIn if provided
        uploaded_assets = []
        if image_urls:
            logger.info(f"Uploading {len(image_urls)} images to LinkedIn...")
            for i, image_url in enumerate(image_urls):
                logger.info(f"Uploading image {i+1}/{len(image_urls)}: {image_url}")
                asset_urn = upload_image_to_linkedin(image_url, linkedin_access_token, linkedin_profile_id)
                if asset_urn:
                    uploaded_assets.append(asset_urn)
                else:
                    logger.warning(f"Failed to upload image {i+1}: {image_url}")
            
            logger.info(f"Successfully uploaded {len(uploaded_assets)}/{len(image_urls)} images")

        # Now post the content to LinkedIn using UGC Posts API
        post_url = "https://api.linkedin.com/v2/ugcPosts"
        
        # Prepare the post data according to LinkedIn API v2 format
        if uploaded_assets:
            # Post with images
            media_list = []
            for asset_urn in uploaded_assets:
                media_list.append({
                    "status": "READY",
                    "description": {
                        "text": ""
                    },
                    "media": asset_urn,
                    "title": {
                        "text": ""
                    }
                })
            
            post_data = {
                "author": f"urn:li:person:{linkedin_profile_id}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": content
                        },
                        "shareMediaCategory": "IMAGE",
                        "media": media_list
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
        else:
            # Text-only post
            post_data = {
                "author": f"urn:li:person:{linkedin_profile_id}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": content
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
        
        post_response = requests.post(post_url, headers=headers, json=post_data)
        
        if post_response.status_code not in [200, 201]:
            logger.error(f"Failed to post to LinkedIn: {post_response.status_code} - {post_response.text}")
            
            # Parse LinkedIn error response
            linkedin_error = "Unknown error"
            try:
                error_data = post_response.json()
                linkedin_error = error_data.get('message', error_data.get('error_description', 'Unknown error'))
            except:
                linkedin_error = post_response.text[:200] + "..." if len(post_response.text) > 200 else post_response.text
            
            # Save failed post attempt to database
            linkedin_post = LinkedinPostingContent.objects.create(
                user_id=user.id,
                username=user.username,
                email=user.email,
                linkedin_profile_id=linkedin_profile_id,
                linkedin_username=linkedin_username,
                content=content,
                post_date=timezone.now(),
                post_status='failed',
                image_urls=image_urls,
                images_count=images_count,
                post_type=post_type,
            )
            
            # Provide specific error messages based on status code
            if post_response.status_code == 403:
                error_message = "LinkedIn posting permission denied. Your token may not have 'w_member_social' scope."
            elif post_response.status_code == 401:
                error_message = "LinkedIn access token is invalid or expired."
            elif post_response.status_code == 422:
                error_message = "LinkedIn rejected the post content. Please check content format and length."
            else:
                error_message = f"LinkedIn API error (Status {post_response.status_code})"
            
            return Response(
                {
                    "error": error_message,
                    "linkedin_error": linkedin_error,
                    "status_code": post_response.status_code,
                    "database_record_id": linkedin_post.id,
                    "image_urls": image_urls,
                    "images_count": images_count,
                    "post_type": post_type,
                    "suggestion": "Please re-authenticate with LinkedIn if the token is expired or lacks permissions."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        
        # Extract LinkedIn post ID from response
        post_response_data = post_response.json()
        linkedin_post_id = post_response_data.get('id', '')
        
        logger.info(f"Successfully posted to LinkedIn - Post ID: {linkedin_post_id}, Type: {post_type}, Images: {images_count}")

        # Save successful post to database
        linkedin_post = LinkedinPostingContent.objects.create(
            user_id=user.id,
            username=user.username,
            email=user.email,
            linkedin_profile_id=linkedin_profile_id,
            linkedin_username=linkedin_username,
            content=content,
            post_date=timezone.now(),
            linkedin_post_id=linkedin_post_id,
            post_status='success',
            image_urls=image_urls,
            images_count=images_count,
            post_type=post_type,
        )

        logger.info(f"Successfully saved LinkedIn post to database with ID: {linkedin_post.id}")

        # Prepare response data
        response_data = {
            "status": "success",
            "message": f"Content posted to LinkedIn successfully! ({post_type} post with {images_count} images)" if images_count > 0 else "Content posted to LinkedIn successfully!",
            "profile_id": linkedin_profile_id,
            "username": linkedin_username,
            "content": content,
            "post_date": linkedin_post.post_date,
            "linkedin_post_id": linkedin_post_id,
            "database_record_id": linkedin_post.id,
            "image_urls": image_urls,
            "images_count": images_count,
            "post_type": post_type,
        }

        # Serialize the successful response
        response_serializer = LinkedinPostingResponseSerializer(data=response_data)
        if response_serializer.is_valid():
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        else:
            logger.error(f"Error serializing LinkedIn posting response: {response_serializer.errors}")
            return Response(
                {"error": "Internal server error during response serialization."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error during LinkedIn API call: {str(e)}")
        return Response(
            {"error": f"Network error while communicating with LinkedIn API: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    except Exception as e:
        logger.error(f"Unexpected error in LinkedIn posting: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        return Response(
            {"error": f"An unexpected error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    responses={
        200: OpenApiResponse(
            description="LinkedIn re-authentication URL generated successfully.",
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error."
        ),
    },
    description="Generate a LinkedIn re-authentication URL with w_member_social scope to enable full analytics access. This endpoint helps users upgrade their LinkedIn token permissions.",
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def linkedin_reauth_url_api(request):
    """
    Generate a LinkedIn re-authentication URL with w_member_social scope.
    
    This endpoint helps users who have basic LinkedIn tokens to re-authenticate
    and get enhanced permissions for accessing posts, engagement data, and connections.
    
    Usage:
    GET /api/linkedin-reauth-url/
    Headers:
        Authorization: Bearer <your_jwt_token>
    
    Returns:
        {
            "auth_url": "https://www.linkedin.com/oauth/v2/authorization?...",
            "required_scopes": ["openid", "profile", "w_member_social", "email"],
            "benefits": ["Access to posts data", "Engagement metrics", "Connection count"],
            "instructions": "Click the auth_url to re-authenticate with enhanced permissions"
        }
    """
    
    try:
        import hashlib
        import os
        from django.conf import settings
        
        # Get LinkedIn OAuth settings
        LINKEDIN_CLIENT_ID = os.environ.get('LINKEDIN_CLIENT_ID', '')
        LINKEDIN_REDIRECT_URI = os.environ.get('LINKEDIN_REDIRECT_URI', '')
        
        if not LINKEDIN_CLIENT_ID or not LINKEDIN_REDIRECT_URI:
            logger.error("LinkedIn OAuth settings not configured")
            return Response(
                {
                    "error": "LinkedIn OAuth not configured",
                    "details": "LINKEDIN_CLIENT_ID or LINKEDIN_REDIRECT_URI not set in environment variables"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        
        # Generate state parameter for security
        state = hashlib.sha256(os.urandom(32).hex().encode()).hexdigest()
        
        # Construct LinkedIn OAuth URL with w_member_social scope
        linkedin_auth_url = "https://www.linkedin.com/oauth/v2/authorization"
        params = {
            "client_id": LINKEDIN_CLIENT_ID,
            "redirect_uri": LINKEDIN_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid profile w_member_social email",  # Include w_member_social
            "state": state
        }
        
        # Construct full URL with parameters
        auth_url = f"{linkedin_auth_url}?{'&'.join([f'{key}={value}' for key, value in params.items()])}"
        
        logger.info(f"Generated LinkedIn re-auth URL for user {request.user.id}")
        
        return Response({
            "status": "success",
            "message": "LinkedIn re-authentication URL generated successfully",
            "auth_url": auth_url,
            "required_scopes": ["openid", "profile", "w_member_social", "email"],
            "current_user": {
                "id": request.user.id,
                "username": request.user.username,
                "email": request.user.email,
                "has_linkedin_token": bool(getattr(request.user, 'linkedin_access_token', None))
            },
            "benefits": [
                "Access to your LinkedIn posts and their content",
                "Detailed engagement metrics (reactions, comments, reposts)",
                "Connection count and follower information",
                "Enhanced analytics data quality",
                "Full social media insights"
            ],
            "instructions": {
                "step1": "Click the 'auth_url' to open LinkedIn authorization page",
                "step2": "Login to LinkedIn if not already logged in",
                "step3": "Review and accept the requested permissions",
                "step4": "You'll be redirected back to the application",
                "step5": "Your token will be automatically updated with new permissions",
                "note": "This will replace your existing LinkedIn token with an enhanced one"
            },
            "what_happens_next": [
                "Your existing LinkedIn token will be replaced",
                "You'll have access to enhanced analytics features",
                "Posts and engagement data will be available",
                "Connection count will be accessible"
            ]
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error generating LinkedIn re-auth URL: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        return Response(
            {"error": f"An unexpected error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    responses={
        200: OpenApiResponse(
            description="LinkedIn token validation successful.",
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer, description="Bad Request - No LinkedIn token found."
        ),
        401: OpenApiResponse(
            response=ErrorResponseSerializer, description="Unauthorized - Invalid or expired LinkedIn token."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error."
        ),
    },
    description="Validate the user's stored LinkedIn access token and check available permissions. Useful for debugging token issues before posting content.",
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def validate_linkedin_token_api(request):
    """
    Validate the user's stored LinkedIn access token and check available permissions.
    
    This endpoint helps debug token issues by:
    1. Checking if a LinkedIn token exists for the user
    2. Validating the token with LinkedIn's API
    3. Retrieving available scopes/permissions
    4. Checking token expiration
    
    Usage:
    GET /api/validate-linkedin-token/
    Headers:
        Authorization: Bearer <your_jwt_token>
    """
    
    # Get the authenticated user
    user = request.user
    
    # Check if user has LinkedIn access token
    linkedin_access_token = getattr(user, 'linkedin_access_token', None)
    
    if not linkedin_access_token:
        logger.warning(f"No LinkedIn access token found for user {user.id}")
        return Response(
            {
                "valid": False,
                "error": "No LinkedIn access token found.",
                "details": "User has not connected their LinkedIn account.",
                "solution": "Please login with LinkedIn first to connect your account.",
                "user_id": user.id,
                "username": user.username
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    # Check if token is expired (if we have expiration info)
    token_expired = False
    if hasattr(user, 'linkedin_token_expires_at') and user.linkedin_token_expires_at:
        if user.linkedin_token_expires_at < timezone.now():
            token_expired = True
    
    try:
        # Test the token with LinkedIn's userinfo endpoint
        profile_url = "https://api.linkedin.com/v2/userinfo"
        headers = {
            'Authorization': f'Bearer {linkedin_access_token}',
            'Content-Type': 'application/json',
        }
        
        profile_response = requests.get(profile_url, headers=headers)
        
        # Prepare response data
        response_data = {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "token_exists": True,
            "token_length": len(linkedin_access_token),
            "token_preview": linkedin_access_token[:20] + "..." if len(linkedin_access_token) > 20 else linkedin_access_token,
            "token_expired_by_date": token_expired,
            "token_expires_at": user.linkedin_token_expires_at if hasattr(user, 'linkedin_token_expires_at') else None,
            "stored_linkedin_profile_id": getattr(user, 'linkedin_profile_id', None),
        }
        
        if profile_response.status_code == 200:
            # Token is valid
            profile_data = profile_response.json()
            
            response_data.update({
                "valid": True,
                "status": "success",
                "message": "LinkedIn token is valid and working!",
                "profile_data": {
                    "linkedin_id": profile_data.get('sub', ''),
                    "name": profile_data.get('name', ''),
                    "email": profile_data.get('email', ''),
                    "picture": profile_data.get('picture', ''),
                },
                "available_endpoints": {
                    "userinfo": "✅ Working",
                    "posting": "✅ Should work (requires w_member_social scope)"
                },
                "recommendations": [
                    "Token is working correctly",
                    "You can proceed with posting content to LinkedIn"
                ]
            })
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        elif profile_response.status_code == 403:
            # Permission denied
            error_data = {}
            try:
                error_data = profile_response.json()
            except:
                pass
            
            response_data.update({
                "valid": False,
                "status": "permission_denied",
                "message": "LinkedIn token lacks required permissions.",
                "error": error_data.get('message', 'Access denied'),
                "linkedin_error_code": error_data.get('serviceErrorCode', 'Unknown'),
                "available_endpoints": {
                    "userinfo": "❌ Permission denied",
                    "posting": "❌ Likely to fail"
                },
                "required_scopes": ["openid", "profile", "w_member_social", "email"],
                "recommendations": [
                    "Re-authenticate with LinkedIn to grant required permissions",
                    "Ensure your LinkedIn app has the correct scopes configured",
                    "Check if your LinkedIn app is approved for the required permissions"
                ]
            })
            
            return Response(response_data, status=status.HTTP_401_UNAUTHORIZED)
            
        elif profile_response.status_code == 401:
            # Token invalid or expired
            response_data.update({
                "valid": False,
                "status": "invalid_or_expired",
                "message": "LinkedIn token is invalid or expired.",
                "linkedin_response": profile_response.text[:200] + "..." if len(profile_response.text) > 200 else profile_response.text,
                "available_endpoints": {
                    "userinfo": "❌ Unauthorized",
                    "posting": "❌ Will fail"
                },
                "recommendations": [
                    "Re-authenticate with LinkedIn to get a fresh token",
                    "Check if the token has expired",
                    "Verify LinkedIn app credentials"
                ]
            })
            
            return Response(response_data, status=status.HTTP_401_UNAUTHORIZED)
            
        else:
            # Other error
            response_data.update({
                "valid": False,
                "status": "api_error",
                "message": f"LinkedIn API returned unexpected status: {profile_response.status_code}",
                "linkedin_response": profile_response.text[:200] + "..." if len(profile_response.text) > 200 else profile_response.text,
                "available_endpoints": {
                    "userinfo": f"❌ Error {profile_response.status_code}",
                    "posting": "❌ Likely to fail"
                },
                "recommendations": [
                    "Check LinkedIn API status",
                    "Try re-authenticating with LinkedIn",
                    "Contact support if the issue persists"
                ]
            })
            
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error during LinkedIn token validation: {str(e)}")
        return Response(
            {
                "valid": False,
                "status": "network_error",
                "message": "Network error while validating LinkedIn token.",
                "error": str(e),
                "recommendations": [
                    "Check your internet connection",
                    "Try again in a few moments",
                    "Contact support if the issue persists"
                ]
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    except Exception as e:
        logger.error(f"Unexpected error in LinkedIn token validation: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        return Response(
            {
                "valid": False,
                "status": "unexpected_error",
                "message": "An unexpected error occurred during token validation.",
                "error": str(e),
                "recommendations": [
                    "Try again in a few moments",
                    "Contact support if the issue persists"
                ]
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# Schedule LinkedIn Post Endpoints

@extend_schema(
    request=ScheduleLinkedinPostRequestSerializer,
    responses={
        200: OpenApiResponse(
            response=ScheduleLinkedinPostResponseSerializer,
            description="LinkedIn posts scheduled successfully.",
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer, description="Bad Request - Invalid input or missing LinkedIn access token."
        ),
        401: OpenApiResponse(
            response=ErrorResponseSerializer, description="Unauthorized - Invalid or expired LinkedIn access token."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error."
        ),
    },
    description="Schedule multiple LinkedIn posts to be published at a specific date and time with delays between posts. Requires LinkedIn authentication and validates the scheduled time is in the future.",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def schedule_linkedin_post_api(request):
    """
    Schedule multiple LinkedIn posts to be published at a specific date and time.
    
    This endpoint:
    1. Validates the user has LinkedIn authentication
    2. Validates the scheduled time is in the future
    3. Creates a scheduled post record in the database with multiple content
    4. Schedules a Celery task to post at the specified time with delays between posts
    
    Body Parameters:
    - content: Array of LinkedIn post content (each max 3000 characters, max 10 posts)
    - scheduled_date: Date to publish (YYYY-MM-DD format)
    - scheduled_time: Time to publish (HH:MM:SS format)
    - timezone: Timezone for the scheduled time (optional, default: UTC)
    - image_urls: Optional list of image URLs to distribute across posts
    - delay_between_posts: Delay in minutes between each post (default: 5 minutes)
    
    Returns:
    - schedule_id: Unique ID for the scheduled post batch
    - total_posts: Number of posts scheduled
    - scheduled_datetime: When the first post will be published
    - celery_task_id: Task ID for tracking/cancellation
    """
    
    # Get the authenticated user
    user = request.user
    
    # Check if user has LinkedIn access token
    linkedin_access_token = getattr(user, 'linkedin_access_token', None)
    linkedin_profile_id = getattr(user, 'linkedin_profile_id', None)
    
    if not linkedin_access_token or not linkedin_profile_id:
        logger.warning(f"No LinkedIn access token found for user {user.id}")
        return Response(
            {
                "error": "LinkedIn authentication required.",
                "details": "User has not connected their LinkedIn account.",
                "solution": "Please login with LinkedIn first to connect your account."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    # Validate request data
    serializer = ScheduleLinkedinPostRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"error": "Invalid input data.", "details": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    validated_data = serializer.validated_data
    
    try:
        # Get LinkedIn username (optional, for display purposes)
        linkedin_username = ""
        try:
            profile_url = "https://api.linkedin.com/v2/userinfo"
            headers = {
                'Authorization': f'Bearer {linkedin_access_token}',
                'Content-Type': 'application/json',
            }
            profile_response = requests.get(profile_url, headers=headers)
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                linkedin_username = profile_data.get('name', '')
        except:
            pass  # Continue without username if API call fails
        
        # Get multiple content posts
        content_array = validated_data['content']
        total_posts = len(content_array)
        delay_between_posts = validated_data.get('delay_between_posts', 5)
        
        # Determine post type
        post_type = 'image' if validated_data.get('image_urls') else 'text'
        images_count = len(validated_data.get('image_urls', []))
        
        # Create scheduled post record with array content
        scheduled_post = SchedulePosts.objects.create(
            user_id=user.id,
            username=user.username,
            email=user.email,
            linkedin_profile_id=linkedin_profile_id,
            linkedin_username=linkedin_username,
            content=content_array,  # Now storing as array
            image_urls=validated_data.get('image_urls', []),
            images_count=images_count,
            post_type=post_type,
            scheduled_datetime=validated_data['scheduled_datetime'],
            user_timezone=validated_data.get('timezone', 'UTC'),
            status='scheduled'
        )
        
        # Schedule Celery task
        from tools.ai.schedule_linkedin_post.tasks import schedule_linkedin_post_batch_task
        from celery import current_app
        
        # Calculate ETA (when to execute the task)
        eta = validated_data['scheduled_datetime']
        
        # Schedule the batch task with delay information
        task = schedule_linkedin_post_batch_task.apply_async(
            args=[scheduled_post.id, delay_between_posts],
            eta=eta
        )
        
        # Save the Celery task ID for potential cancellation
        scheduled_post.celery_task_id = task.id
        scheduled_post.save()
        
        logger.info(f"Scheduled LinkedIn post batch {scheduled_post.id} with {total_posts} posts for user {user.id} at {eta}")
        
        # Prepare response
        response_data = {
            "status": "success",
            "message": f"{total_posts} LinkedIn posts scheduled successfully starting at {validated_data['scheduled_datetime'].strftime('%Y-%m-%d %H:%M:%S %Z')}",
            "schedule_id": scheduled_post.id,
            "content": scheduled_post.content,
            "total_posts": total_posts,
            "scheduled_datetime": scheduled_post.scheduled_datetime,
            "timezone": scheduled_post.user_timezone,
            "linkedin_profile_id": scheduled_post.linkedin_profile_id,
            "linkedin_username": scheduled_post.linkedin_username,
            "post_type": scheduled_post.post_type,
            "images_count": scheduled_post.images_count,
            "delay_between_posts": delay_between_posts,
            "celery_task_id": scheduled_post.celery_task_id,
            "created_at": scheduled_post.created_at
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error scheduling LinkedIn post for user {user.id}: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response(
            {
                "error": "Failed to schedule LinkedIn post.",
                "details": str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    responses={
        200: OpenApiResponse(
            response=ScheduledPostsListResponseSerializer,
            description="Scheduled posts retrieved successfully.",
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error."
        ),
    },
    description="Get all scheduled LinkedIn posts for the authenticated user, including their status and details.",
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_scheduled_posts_api(request):
    """
    Get all scheduled LinkedIn posts for the authenticated user.
    
    Returns a list of all scheduled posts with their current status:
    - scheduled: Waiting to be posted
    - posted: Successfully posted
    - failed: Failed to post
    - cancelled: Cancelled by user
    """
    
    user = request.user
    
    try:
        # Get all scheduled posts for the user
        scheduled_posts = SchedulePosts.objects.filter(user_id=user.id).order_by('-scheduled_datetime')
        
        # Prepare response data
        posts_data = []
        for post in scheduled_posts:
            # Handle both array and single content for backward compatibility
            content = post.content
            if isinstance(content, list):
                total_posts = len(content)
                content_preview = content[0][:100] + "..." if content and len(content[0]) > 100 else (content[0] if content else "")
            else:
                total_posts = 1
                content_preview = content[:100] + "..." if content and len(content) > 100 else content
            
            posts_data.append({
                "schedule_id": post.id,
                "content": post.content,
                "content_preview": content_preview,
                "total_posts": total_posts,
                "scheduled_datetime": post.scheduled_datetime,
                "timezone": post.user_timezone,
                "status": post.status,
                "linkedin_profile_id": post.linkedin_profile_id,
                "linkedin_username": post.linkedin_username,
                "post_type": post.post_type,
                "images_count": post.images_count,
                "created_at": post.created_at,
                "posted_at": post.posted_at,
                "linkedin_post_id": post.linkedin_post_id,
                "error_message": post.error_message
            })
        
        response_data = {
            "status": "success",
            "message": f"Retrieved {len(posts_data)} scheduled posts",
            "total_scheduled": len(posts_data),
            "scheduled_posts": posts_data
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error retrieving scheduled posts for user {user.id}: {str(e)}")
        return Response(
            {
                "error": "Failed to retrieve scheduled posts.",
                "details": str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    responses={
        200: OpenApiResponse(
            response=CancelScheduledPostResponseSerializer,
            description="Scheduled post cancelled successfully.",
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer, description="Bad Request - Invalid schedule ID or post cannot be cancelled."
        ),
        404: OpenApiResponse(
            response=ErrorResponseSerializer, description="Not Found - Scheduled post not found."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error."
        ),
    },
    description="Cancel a scheduled LinkedIn post. Only posts with 'scheduled' status can be cancelled.",
)
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def cancel_scheduled_post_api(request, schedule_id):
    """
    Cancel a scheduled LinkedIn post.
    
    Path Parameters:
    - schedule_id: The ID of the scheduled post to cancel
    
    Only posts with 'scheduled' status can be cancelled.
    This will also revoke the associated Celery task.
    """
    
    user = request.user
    
    try:
        # Get the scheduled post
        try:
            scheduled_post = SchedulePosts.objects.get(id=schedule_id, user_id=user.id)
        except SchedulePosts.DoesNotExist:
            return Response(
                {
                    "error": "Scheduled post not found.",
                    "details": f"No scheduled post found with ID {schedule_id} for this user."
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        
        # Check if post can be cancelled
        if scheduled_post.status != 'scheduled':
            return Response(
                {
                    "error": "Post cannot be cancelled.",
                    "details": f"Post status is '{scheduled_post.status}'. Only 'scheduled' posts can be cancelled.",
                    "current_status": scheduled_post.status
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        previous_status = scheduled_post.status
        
        # Cancel the Celery task if it exists
        if scheduled_post.celery_task_id:
            try:
                from celery import current_app
                current_app.control.revoke(scheduled_post.celery_task_id, terminate=True)
                logger.info(f"Revoked Celery task {scheduled_post.celery_task_id} for scheduled post {schedule_id}")
            except Exception as e:
                logger.warning(f"Failed to revoke Celery task {scheduled_post.celery_task_id}: {str(e)}")
        
        # Update post status
        scheduled_post.status = 'cancelled'
        scheduled_post.save()
        
        logger.info(f"Cancelled scheduled post {schedule_id} for user {user.id}")
        
        response_data = {
            "status": "success",
            "message": f"Scheduled post {schedule_id} cancelled successfully",
            "schedule_id": scheduled_post.id,
            "previous_status": previous_status,
            "current_status": scheduled_post.status
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error cancelling scheduled post {schedule_id} for user {user.id}: {str(e)}")
        return Response(
            {
                "error": "Failed to cancel scheduled post.",
                "details": str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# PDF Upload and Chat API imports
from .models import PDFDocument, ChatSession, ChatMessage
from .serializers import (
    PDFUploadSerializer, PDFUploadResponseSerializer,
    ChatRequestSerializer, ChatResponseSerializer
)

# Import services
try:
    from tools.ai.pdf_uploader.pdf_uploader import pdf_uploader_service
    from tools.ai.chatbot.agent.agent import project_chatbot
    from management_app.pinecone_integration.service.service import pinecone_service
    PDF_CHAT_SERVICES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ PDF/Chat services not available: {e}")
    PDF_CHAT_SERVICES_AVAILABLE = False


@extend_schema(
    request={
        'multipart/form-data': {
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
    },
    responses={
        200: OpenApiResponse(
            response=PDFUploadResponseSerializer,
            description="Document uploaded and processed successfully.",
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer, description="Bad Request - Invalid file or processing error."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="Internal Server Error / Processing Failed.",
        ),
    },
    description="Upload a document (PDF, DOCX, MD, TXT), extract its content, index it in Pinecone for searchability, and store it in S3. The document will be available for querying through the chat API.",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_pdf_api(request):
    """Upload and process document files (PDF, DOCX, MD, TXT)."""
    try:
        if not PDF_CHAT_SERVICES_AVAILABLE:
            return Response({
                "error": "PDF/Chat services not available. Please check service configuration."
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        serializer = PDFUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "error": "Invalid file upload",
                "details": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        uploaded_file = serializer.validated_data['file']
        user = request.user
        
        print(f"📄 Processing file upload: {uploaded_file.name} for user {user.username}")
        
        # Read file content
        file_content = uploaded_file.read()
        
        # Process document using PDF uploader service
        processing_result = pdf_uploader_service.process_document(
            file_content=file_content,
            filename=uploaded_file.name,
            user_id=user.id,
            username=user.username,
            email=user.email
        )
        
        if not processing_result['success']:
            return Response({
                "status": "error",
                "message": f"Document processing failed: {processing_result['error']}",
                "stage": processing_result.get('stage', 'unknown')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create database record
        pdf_document = PDFDocument.objects.create(
            user_id=user.id,
            username=user.username,
            email=user.email,
            file_name=processing_result['file_name'],
            file_type=processing_result['file_type'],
            content=processing_result['content'],
            uploaded_url=processing_result['uploaded_url'],
            processing_status='extracting',
            file_size=processing_result['file_size'],
            word_count=processing_result['word_count']
        )
        
        print(f"💾 Created database record with ID: {pdf_document.id}")
        
        # Update status to indexing
        pdf_document.processing_status = 'indexing'
        pdf_document.save()
        
        # Index in Pinecone
        indexing_result = pinecone_service.index_document(
            document_id=processing_result['document_id'],
            file_name=processing_result['file_name'],
            file_type=processing_result['file_type'],
            content=processing_result['content'],
            user_id=user.id,
            username=user.username,
            file_url=processing_result['uploaded_url']
        )
        
        # Update database record with indexing results
        if indexing_result['success']:
            pdf_document.processing_status = 'completed'
            pdf_document.pinecone_indexed = True
            pdf_document.pinecone_index_id = processing_result['document_id']
            chunks_indexed = indexing_result['chunks_indexed']
            print(f"✅ Successfully indexed {chunks_indexed} chunks in Pinecone")
        else:
            pdf_document.processing_status = 'failed'
            pdf_document.pinecone_indexed = False
            chunks_indexed = 0
            print(f"❌ Pinecone indexing failed: {indexing_result['error']}")
        
        pdf_document.save()
        
        # Prepare response
        response_data = {
            "status": "success",
            "message": "Document uploaded and processed successfully",
            "document_id": processing_result['document_id'],
            "file_name": processing_result['file_name'],
            "file_type": processing_result['file_type'],
            "file_size": processing_result['file_size'],
            "word_count": processing_result['word_count'],
            "uploaded_url": processing_result['uploaded_url'],
            "content_extraction_completed": True,
            "pinecone_indexing_completed": indexing_result['success'],
            "chunks_indexed": chunks_indexed,
            "processing_status": pdf_document.processing_status,
            "extraction_method": processing_result.get('extraction_method', 'unknown'),
            "database_record_id": pdf_document.id,
            "created_at": pdf_document.created_at
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"❌ Unexpected error in upload_pdf_api: {str(e)}")
        return Response({
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    request=ChatRequestSerializer,
    responses={
        200: OpenApiResponse(
            response=ChatResponseSerializer,
            description="Chat response generated successfully.",
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer, description="Bad Request - Invalid query or session."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error."
        ),
    },
    description="Chat with AI about uploaded documents. Provide a query and optionally a session_id. If no session_id is provided, a new chat session will be created. The AI will search through your uploaded documents and provide relevant answers with source citations.",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def chat_api(request):
    """Chat with AI about uploaded documents."""
    try:
        if not PDF_CHAT_SERVICES_AVAILABLE:
            return Response({
                "error": "Chat service not available. Please check service configuration."
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        serializer = ChatRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "error": "Invalid request",
                "details": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        query = serializer.validated_data['query']
        session_id = serializer.validated_data.get('session_id', '')
        user = request.user
        
        print(f"💬 Processing chat query from user {user.username}: {query[:50]}...")
        
        # Validate query
        query_validation = project_chatbot.validate_query(query)
        if not query_validation['valid']:
            return Response({
                "status": "error",
                "message": f"Invalid query: {query_validation['error']}"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Handle session
        is_new_session = False
        
        if session_id:
            try:
                chat_session = ChatSession.objects.get(
                    session_id=session_id,
                    user_id=user.id,
                    is_active=True
                )
                print(f"📝 Using existing session: {session_id}")
            except ChatSession.DoesNotExist:
                return Response({
                    "status": "error",
                    "message": f"Chat session {session_id} not found or inactive"
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            session_id = project_chatbot.generate_session_id(user.id)
            
            chat_session = ChatSession.objects.create(
                session_id=session_id,
                user_id=user.id,
                username=user.username,
                email=user.email,
                is_active=True,
                total_messages=0
            )
            
            is_new_session = True
            print(f"🆕 Created new session: {session_id}")
        
        # Store user message
        user_message = ChatMessage.objects.create(
            session=chat_session,
            message_type='user',
            content=query
        )
        
        # Get conversation history for context
        conversation_history = []
        recent_messages = ChatMessage.objects.filter(
            session=chat_session
        ).order_by('-created_at')[:10]
        
        for msg in reversed(recent_messages):
            conversation_history.append({
                "role": "user" if msg.message_type == "user" else "assistant",
                "content": msg.content
            })
        
        # Use Enhanced RAG system with project-specific capabilities
        print(f"🚀 Using Enhanced RAG system with project-specific search capabilities")
        response_result = project_chatbot.rag_query(
            query=query,
            use_comprehensive_search=True,
            top_k=30,  # Comprehensive results with project focus
            user_id=user.id  # Pass user context for project-specific search
        )
        
        if not response_result['success']:
            return Response({
                "status": "error", 
                "message": f"Failed to generate response: {response_result['error']}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        ai_response = response_result['response']
        sources_used = response_result.get('sources_used', [])
        processing_time = response_result['processing_time']
        tokens_used = response_result.get('tokens_used', 0)
        relevant_documents = response_result.get('documents', [])
        
        # Store AI response
        assistant_message = ChatMessage.objects.create(
            session=chat_session,
            message_type='assistant',
            content=ai_response,
            relevant_documents=relevant_documents,
            sources_used=sources_used,
            processing_time=processing_time,
            tokens_used=tokens_used
        )
        
        # Update session
        chat_session.total_messages = ChatMessage.objects.filter(session=chat_session).count()
        chat_session.save()
        
        response_data = {
            "status": "success",
            "message": "Chat response generated successfully",
            "session_id": session_id,
            "is_new_session": is_new_session,
            "response": ai_response,
            "processing_time": processing_time,
            "tokens_used": tokens_used,
            "model_used": response_result.get('model_used', 'ENHANCED_RAG_RETRIEVAL'),
            "total_messages": chat_session.total_messages,
            "relevant_documents_found": len(relevant_documents),
            "project_detected": response_result.get('project_name'),
            "search_strategy": response_result.get('search_strategy', 'comprehensive')
        }
        
        print(f"✅ Chat response generated successfully for session {session_id}")
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"❌ Unexpected error in chat_api: {str(e)}")
        return Response({
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

