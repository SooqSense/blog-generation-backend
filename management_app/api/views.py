import json
import os
import sys
from django.conf import settings
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
import logging
from django.utils import timezone
from datetime import datetime
import re

# Import models
from .models import (
    BlogGeneral,
    BlogAiNews,
    LinkedinPost,
    ImageGeneration,
    TrendingTopics,
    LinkedinAnalytics,
)

# Set up logging
logger = logging.getLogger(__name__)

# Add tools directory to sys.path
if settings.TOOLS_DIR not in sys.path:
    sys.path.insert(0, settings.TOOLS_DIR)
if os.path.dirname(settings.TOOLS_DIR) not in sys.path:
    sys.path.insert(0, os.path.dirname(settings.TOOLS_DIR))

from tools.ai.blog_generator.blog_writer import BlogWriter, generate_image

# Import the new LinkedInPostGenerator service
from tools.ai.linkedin_post_generator.linkedin_post_generator import (
    LinkedInPostGenerator,
)

# Import the PyTrends service
from tools.ai.trends_ai.pytrends_api import fetch_related_topics

# Import the LinkedIn Analytics service
from tools.ai.linkedin_analytics.linkedin_analytics_service import fetch_linkedin_analytics

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
    LinkedinAnalyticsRequestSerializer,
    LinkedinAnalyticsResponseSerializer,
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
    description="Generate a detailed blog post based on the given topic and optional parameters for customization.",
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
        tone = serializer.validated_data.get("tone", "professional")
        length_min = serializer.validated_data.get("length_min", 800)
        length_max = serializer.validated_data.get("length_max", 1500)
        introduction = serializer.validated_data.get("introduction", True)
        table_of_content = serializer.validated_data.get("table_of_content", False)
        faq = serializer.validated_data.get("faq", False)
        cta = serializer.validated_data.get("cta", False)
        conclusion = serializer.validated_data.get("conclusion", True)
        target_audience = serializer.validated_data.get("target_audience", [])
        
        # Process keywords if they come as a string (e.g., "War:10, Pakistan:20, India:3")
        if isinstance(keywords, str) and keywords.strip():
            processed_keywords = []
            for kw_pair in keywords.split(','):
                kw_pair = kw_pair.strip()
                if ':' in kw_pair:
                    keyword, count = kw_pair.split(':', 1)
                    processed_keywords.append({
                        "keyword": keyword.strip(),
                        "count": int(count.strip())
                    })
                else:
                    processed_keywords.append({
                        "keyword": kw_pair.strip(),
                        "count": 1
                    })
            keywords = processed_keywords

        try:
            logger.info(
                f"Starting blog generation for topic: '{topic}' with customized parameters"
            )

            blog_writer_instance = BlogWriter(
                topic=topic,
                keywords=keywords,
                tone=tone,
                length_min=length_min,
                length_max=length_max,
                introduction=introduction,
                table_of_content=table_of_content,
                faq=faq,
                cta=cta,
                conclusion=conclusion,
                target_audience=target_audience,
                sample_blog_url=sample_blog_url if sample_blog_url else None,
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

            # Save to database (still save the markdown version)
            blog = BlogGeneral(
                user_id=request.user.id,  # Use authenticated user's ID
                username=request.user.username,  # Use authenticated user's username
                email=request.user.email,  # Use authenticated user's email
                topic=topic,
                content=blog_content,
                sample_blog_url=sample_blog_url if sample_blog_url else None,
                created_at=timezone.now(),
            )
            blog.save()
            logger.info(f"Saved blog to database with ID: {blog.id}")

            response_data = {
                "status": "success",
                "message": "Blog generated successfully!",
                "topic": topic,
                "keywords": keywords,
                "sample_blog_url": sample_blog_url,
                "sample_blog_analysis": getattr(blog_writer_instance, 'sample_blog_analysis', None),
                "tone": tone,
                "length_min": length_min,
                "length_max": length_max,
                "introduction": introduction,
                "table_of_content": table_of_content,
                "faq": faq,
                "cta": cta,
                "conclusion": conclusion,
                "target_audience": target_audience,
                "content": structured_content,
                "raw_content": blog_content,  # Include the original markdown as well
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
        except ImportError as e:
            return Response(
                {"error": f"Server configuration error (ImportError): {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
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
    description="Automatically generates a blog about the latest trends and news of this week.",
    responses={200: None},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def generate_weekly_news_blog(request):
    """
    Generate a weekly news blog about the latest trends and developments.

    This endpoint automatically creates a blog about this week's news and trends.
    The result is saved to the database.
    No parameters needed - just click Execute!
    """
    try:
        logger.info("Starting weekly news blog generation")

        topic = "Latest Trends and News This Week: Technology, Business, and Culture"
        date_str = datetime.now().strftime("%Y-%m-%d")

        blog_writer_instance = BlogWriter(topic=topic)

        # Generate the blog content without saving to file
        blog_content = blog_writer_instance.generate_blog(topic=topic)

        if not blog_content:
            logger.error("Weekly news blog generation failed.")
            return Response(
                {"error": "Weekly news blog generation failed."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info("Successfully generated weekly news blog")

        # Convert markdown content to JSON structure
        structured_content = convert_markdown_to_json(blog_content)

        # Save to database (still save the markdown version)
        news_blog = BlogAiNews(
            news_week_start=datetime.now().date(),
            username=request.user.username,  # Use authenticated user's username
            email=request.user.email,  # Use authenticated user's email
            summary=topic,  # Using the topic as a summary
            content=blog_content,
            created_at=timezone.now(),
        )
        news_blog.save()
        logger.info(f"Saved weekly news blog to database with ID: {news_blog.id}")

        response_data = {
            "status": "success",
            "message": "Weekly news blog generated successfully!",
            "topic": topic,
            "date": date_str,
            "content": structured_content,
            "raw_content": blog_content,  # Include the original markdown as well
        }

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(
            f"Unexpected error in weekly news blog generation: {type(e).__name__} - {e}"
        )
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
            description="Image generated successfully.",
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer, description="Bad Request - Invalid input."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="Internal Server Error / Image Generation Failed.",
        ),
    },
    description="Generate an image based on a prompt and/or keywords using DALL-E 3.",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_image_api(request):
    """
    Generate an image based on a prompt and/or keywords using DALL-E 3.
    """
    serializer = ImageGenerationRequestSerializer(data=request.data)
    if not serializer.is_valid():
        logger.warning(f"Invalid input for image generation: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    prompt = serializer.validated_data.get("prompt", "")
    keywords = serializer.validated_data.get("keywords", [])
    aspect_ratio = serializer.validated_data.get("aspect_ratio", "1024x1024")
    size = serializer.validated_data.get("size", "1024x1024")

    logger.info(
        f"Received image generation request for prompt: '{prompt}' with keywords: {keywords}, aspect_ratio: {aspect_ratio}, size: {size}"
    )

    final_prompt = prompt
    if keywords:
        final_prompt += " " + " ".join(keywords)

    try:
        # Call generate_image with correct parameters (prompt, size, output_dir, topic)
        image_url, optimized_prompt = generate_image(
            prompt=final_prompt, size=size, output_dir="blog_images"
        )

        if image_url:
            # Save to database
            image_record = ImageGeneration(
                user_id=request.user.id,
                username=request.user.username,
                email=request.user.email,
                prompt=final_prompt,
                image_url=image_url,
                created_at=timezone.now(),
            )
            image_record.save()
            logger.info(f"Saved image generation details for prompt: '{final_prompt}'")

            response_serializer = ImageGenerationResponseSerializer(
                data={
                    "status": "success",
                    "message": "Image generated successfully!",
                    "prompt_used": final_prompt,
                    "enhanced_prompt": optimized_prompt,
                    "image_file": image_url,
                }
            )
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
                f"Image generation failed for prompt: '{final_prompt}'. No URL returned."
            )
            return Response(
                {"error": "Image generation failed. Please try again."},
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
            description="Related topics fetched and saved successfully for all keywords.",
        ),
        202: OpenApiResponse(
            response=RelatedTopicsResponseSerializer,
            description="Related topics processing initiated; some keywords might have failed.",
        ),  # For partial success
        400: OpenApiResponse(
            response=ErrorResponseSerializer, description="Bad Request - Invalid input."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="Internal Server Error or error during topic fetching.",
        ),
    },
    description="Fetch topics related to a list of given keywords using Google Trends data and save to database.",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def fetch_and_save_related_topics(request):
    """
    Fetches topics related to a list of given keywords using Google Trends and saves to database.

    Input is a JSON object with:
    - "keywords" (required list of strings): Main keywords to find related topics for.
    - "region" (optional string): Region code for trends (e.g., 'US'). Defaults to worldwide.
    - "limit" (optional int): Max topics per category (top/rising) per keyword. Default 10.
    """
    serializer = RelatedTopicsRequestSerializer(data=request.data)
    if not serializer.is_valid():
        logger.warning(f"Invalid input for related topics: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    keywords_list = serializer.validated_data["keywords"]
    region = serializer.validated_data.get("region", "")
    limit = serializer.validated_data.get("limit", 10)

    processed_keywords_data = []
    overall_status_code = status.HTTP_200_OK
    errors_occurred = False

    for keyword in keywords_list:
        try:
            logger.info(
                f"Starting related topics fetch for keyword: '{keyword}', region: '{region}', limit: {limit}"
            )

            # Use the updated fetch_related_topics from pytrends_api.py
            # This function is expected to be imported at the top of views.py
            related_topics_data = fetch_related_topics(
                topic=keyword, region=region, limit=limit
            )

            rising_topics = related_topics_data.get("rising", [])
            top_topics = related_topics_data.get("top", [])

            record_id = None
            if rising_topics or top_topics:
                # Save to database
                db_record, created = TrendingTopics.objects.update_or_create(
                    keyword=keyword,
                    defaults={
                        "rising_topics": rising_topics,
                        "top_topics": top_topics,
                        "created_at": timezone.now(),  # Update timestamp on modification
                    },
                )
                record_id = db_record.id
                action = "updated" if not created else "created"
                logger.info(
                    f"Successfully {action} and saved {len(rising_topics)} rising and {len(top_topics)} top topics for keyword '{keyword}' with ID: {record_id}"
                )
            else:
                logger.warning(
                    f"No rising or top topics found for keyword: '{keyword}'. Not saving to DB."
                )

            processed_keywords_data.append(
                {
                    "keyword": keyword,
                    "id": record_id,
                    "rising_topics": rising_topics,
                    "top_topics": top_topics,
                }
            )

        except Exception as e:
            logger.error(
                f"Error processing keyword '{keyword}': {type(e).__name__} - {str(e)}"
            )
            errors_occurred = True
            processed_keywords_data.append(
                {
                    "keyword": keyword,
                    "id": None,
                    "rising_topics": [],
                    "top_topics": [],
                    "error": f"Failed to fetch/save topics: {str(e)}",
                }
            )
            # If any keyword fails, we might want to indicate partial success.
            overall_status_code = status.HTTP_202_ACCEPTED

    response_message = "Related topics processed."
    if errors_occurred:
        response_message = "Related topics processed with some errors."
    elif not processed_keywords_data:
        response_message = "No keywords provided or processed."
        overall_status_code = (
            status.HTTP_400_BAD_REQUEST
        )  # Or keep 200 if an empty list is valid

    final_response_data = {
        "status": "success" if not errors_occurred else "partial_success",
        "message": response_message,
        "processed_keywords": processed_keywords_data,
    }

    # Serialize the successful/partial response
    response_serializer = RelatedTopicsResponseSerializer(data=final_response_data)
    if response_serializer.is_valid():
        return Response(response_serializer.data, status=overall_status_code)
    else:
        logger.error(
            f"Error serializing response for related topics: {response_serializer.errors}"
        )
        # Fallback response if serialization itself fails
        return Response(
            {
                "status": "error",
                "message": "Internal server error during response serialization.",
                "details": response_serializer.errors,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    parameters=[
        OpenApiParameter(
            name='linkedin_profile_id',
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            description='LinkedIn profile ID (optional, will be fetched from token if not provided)'
        ),
        OpenApiParameter(
            name='force_scraping',
            type=bool,
            location=OpenApiParameter.QUERY,
            required=False,
            description='Force scraping attempt if API returns limited data (⚠️ WARNING: Risky and may violate ToS)'
        ),
        OpenApiParameter(
            name='Authorization',
            type=str,
            location=OpenApiParameter.HEADER,
            required=True,
            description='JWT token in format: Bearer <jwt_token>'
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=LinkedinAnalyticsResponseSerializer,
            description="LinkedIn analytics fetched successfully.",
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer, description="Bad Request - Invalid input."
        ),
        401: OpenApiResponse(
            response=ErrorResponseSerializer, description="Unauthorized - Invalid access token."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error."
        ),
    },
    description="Fetch LinkedIn profile analytics including followers, posts, and engagement metrics using stored LinkedIn access token from user profile.",
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
    
    Usage:
    GET /api/linkedin-analytics/
    Headers:
        Authorization: Bearer <your_jwt_token>
    
    Query Parameters:
        linkedin_profile_id (optional): LinkedIn profile ID
    """
    
    # Get LinkedIn access token from authenticated user's profile
    user = request.user
    linkedin_access_token = user.linkedin_access_token
    
    if not linkedin_access_token:
        logger.warning(f"No LinkedIn access token found for user {user.id}")
        return Response(
            {"error": "No LinkedIn access token found. Please login with LinkedIn first to connect your account."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    # Check if token is expired
    if user.linkedin_token_expires_at and user.linkedin_token_expires_at < timezone.now():
        logger.warning(f"LinkedIn access token expired for user {user.id}")
        return Response(
            {"error": "LinkedIn access token has expired. Please login with LinkedIn again to refresh your token."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Get optional parameters from query
    linkedin_profile_id = request.query_params.get('linkedin_profile_id', None)
    force_scraping = request.query_params.get('force_scraping', 'false').lower() == 'true'

    logger.info(f"Received LinkedIn analytics request for profile: {linkedin_profile_id or 'auto-detect'}, force_scraping: {force_scraping}")

    try:
        # Import the hybrid function that tries API first, then scraping
        from tools.ai.linkedin_analytics.linkedin_analytics_service import hybrid_linkedin_analytics
        
        # Use hybrid approach: tries API first, then considers scraping
        analytics_data = hybrid_linkedin_analytics(linkedin_access_token, linkedin_profile_id)
        
        # Check if we got an error response (indicating API failed and scraping not recommended)
        if analytics_data.get('error'):
            logger.warning(f"LinkedIn analytics returned error: {analytics_data.get('message', 'Unknown error')}")
            
            # If user explicitly wants to force scraping despite warnings
            if force_scraping:
                logger.warning("🚨 User requested force scraping - attempting despite risks!")
                from tools.ai.linkedin_analytics.linkedin_analytics_service import scrape_linkedin_analytics
                try:
                    scraping_data = scrape_linkedin_analytics(linkedin_access_token)
                    if scraping_data and not scraping_data.get('error'):
                        analytics_data = scraping_data
                        analytics_data['data_source'] = 'scraping_forced'
                        logger.warning("⚠️ Using scraped data - this may violate LinkedIn ToS!")
                    else:
                        logger.error(f"Scraping also failed: {scraping_data.get('error', 'Unknown scraping error')}")
                        # Fall back to API data if available
                        if analytics_data.get('api_data'):
                            analytics_data = analytics_data['api_data']
                            analytics_data['data_source'] = 'api_limited'
                        else:
                            return Response(
                                {
                                    "error": "Both API and scraping failed",
                                    "api_error": analytics_data.get('message', 'API failed'),
                                    "scraping_error": scraping_data.get('error', 'Scraping failed'),
                                    "recommendation": "Please check your LinkedIn permissions or try again later"
                                },
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            )
                except Exception as scraping_error:
                    logger.error(f"Scraping attempt failed with exception: {scraping_error}")
                    # Fall back to API data if available
                    if analytics_data.get('api_data'):
                        analytics_data = analytics_data['api_data']
                        analytics_data['data_source'] = 'api_limited'
                    else:
                        return Response(
                            {
                                "error": "Both API and scraping failed",
                                "api_error": analytics_data.get('message', 'API failed'),
                                "scraping_error": str(scraping_error),
                                "recommendation": "Please check your LinkedIn permissions or try again later"
                            },
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        )
            else:
                # If API failed but we have some basic data, use it
                if analytics_data.get('api_data'):
                    analytics_data = analytics_data['api_data']
                    analytics_data['data_source'] = 'api_limited'
                else:
                    return Response(
                        {
                            "error": analytics_data.get('message', 'Failed to fetch LinkedIn analytics data'),
                            "recommendation": analytics_data.get('recommendation', 'Please check your access token and permissions.'),
                            "scraping_option": "Add ?force_scraping=true to attempt scraping (⚠️ WARNING: Risky and may violate ToS)"
                        },
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )
        
        if not analytics_data:
            logger.error("Failed to fetch LinkedIn analytics data")
            return Response(
                {"error": "Failed to fetch LinkedIn analytics data. Please check your access token and permissions."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Save or update analytics data in database
        linkedin_analytics, created = LinkedinAnalytics.objects.update_or_create(
            user_id=request.user.id,
            linkedin_profile_id=analytics_data['linkedin_profile_id'],
            defaults={
                'username': request.user.username,
                'email': request.user.email,
                'total_followers': analytics_data.get('total_followers', 0),
                'total_posts': analytics_data.get('total_posts', 0),
                'posts_analytics': analytics_data.get('posts_analytics', []),
                'total_reactions': analytics_data.get('total_reactions', 0),
                'total_comments': analytics_data.get('total_comments', 0),
                'total_reposts': analytics_data.get('total_reposts', 0),
                'total_impressions': analytics_data.get('total_impressions', 0),
                'total_engagement': analytics_data.get('total_engagement', 0),
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
            "data_source": analytics_data.get('data_source', 'official_api'),
            "data_quality": analytics_data.get('data_quality', 'unknown'),
            "available_scopes": analytics_data.get('available_scopes', []),
            "api_limitations": analytics_data.get('api_limitations', []),
            "total_followers": analytics_data.get('total_followers', 0),
            "total_posts": analytics_data.get('total_posts', 0),
            "posts_analytics": analytics_data.get('posts_analytics', []),
            "total_reactions": analytics_data.get('total_reactions', 0),
            "total_comments": analytics_data.get('total_comments', 0),
            "total_reposts": analytics_data.get('total_reposts', 0),
            "total_impressions": analytics_data.get('total_impressions', 0),
            "total_engagement": analytics_data.get('total_engagement', 0),
            "last_updated": linkedin_analytics.last_updated,
            "created_at": linkedin_analytics.created_at,
        }
        
        # Add warnings if using scraped data
        if analytics_data.get('data_source') == 'scraping_forced':
            response_data['warnings'] = analytics_data.get('warnings', [])
            response_data['scraping_method'] = analytics_data.get('scraping_method', 'unknown')
            response_data['scraped_at'] = analytics_data.get('scraped_at')

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

    except ValueError as e:
        logger.error(f"ValueError in LinkedIn analytics: {str(e)}")
        return Response(
            {"error": f"Invalid request: {str(e)}"},
            status=status.HTTP_400_BAD_REQUEST,
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
    responses={
        200: OpenApiResponse(
            description="Debug information about LinkedIn token storage.",
        ),
        401: OpenApiResponse(
            response=ErrorResponseSerializer, description="Unauthorized - User not authenticated."
        ),
    },
    description="Debug endpoint to check LinkedIn token storage in database.",
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def debug_linkedin_token(request):
    """
    Debug endpoint to check LinkedIn token storage and retrieval.
    
    Usage:
    GET /api/debug-linkedin-token/
    Headers:
        Authorization: Bearer <your_jwt_token>
    """
    
    user = request.user
    
    # Get all user data for debugging
    debug_info = {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "has_linkedin_access_token": bool(user.linkedin_access_token),
        "linkedin_access_token_length": len(user.linkedin_access_token) if user.linkedin_access_token else 0,
        "linkedin_access_token_preview": user.linkedin_access_token[:20] + "..." if user.linkedin_access_token else None,
        "linkedin_profile_id": user.linkedin_profile_id,
        "linkedin_token_expires_at": user.linkedin_token_expires_at,
        "token_expired": user.linkedin_token_expires_at < timezone.now() if user.linkedin_token_expires_at else None,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }
    
    # Check if fields exist in model
    debug_info["model_fields"] = {
        "has_linkedin_access_token_field": hasattr(user, 'linkedin_access_token'),
        "has_linkedin_profile_id_field": hasattr(user, 'linkedin_profile_id'),
        "has_linkedin_token_expires_at_field": hasattr(user, 'linkedin_token_expires_at'),
    }
    
    # Check database connection
    from django.db import connection
    debug_info["database"] = {
        "name": connection.settings_dict.get('NAME', 'Unknown'),
        "connection_alive": connection.is_usable(),
    }
    
    # Try to fetch user again from database to ensure fresh data
    from authentication.models import User
    fresh_user = User.objects.get(id=user.id)
    debug_info["fresh_fetch"] = {
        "has_linkedin_access_token": bool(fresh_user.linkedin_access_token),
        "linkedin_access_token_length": len(fresh_user.linkedin_access_token) if fresh_user.linkedin_access_token else 0,
        "linkedin_access_token_preview": fresh_user.linkedin_access_token[:20] + "..." if fresh_user.linkedin_access_token else None,
        "linkedin_profile_id": fresh_user.linkedin_profile_id,
        "linkedin_token_expires_at": fresh_user.linkedin_token_expires_at,
    }
    
    return Response({
        "status": "success",
        "message": "Debug information retrieved successfully",
        "debug_info": debug_info
    }, status=status.HTTP_200_OK)
