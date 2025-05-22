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
)


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
        tone = serializer.validated_data.get("tone", "professional")
        length_min = serializer.validated_data.get("length_min", 800)
        length_max = serializer.validated_data.get("length_max", 1500)
        introduction = serializer.validated_data.get("introduction", True)
        table_of_content = serializer.validated_data.get("table_of_content", False)
        faq = serializer.validated_data.get("faq", False)
        cta = serializer.validated_data.get("cta", False)
        conclusion = serializer.validated_data.get("conclusion", True)
        target_audience = serializer.validated_data.get("target_audience", [])

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
            )

            # Generate the blog content without saving to file
            blog_content = blog_writer_instance.generate_blog(topic=topic)

            if not blog_content:
                logger.error(f"Blog generation failed for topic: '{topic}'")
                return Response(
                    {"error": "Blog generation failed."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            logger.info(f"Successfully generated blog on '{topic}'")

            # Save to database
            blog = BlogGeneral(
                user_id=request.user.id,  # Use authenticated user's ID
                username=request.user.username,  # Use authenticated user's username
                email=request.user.email,  # Use authenticated user's email
                topic=topic,
                content=blog_content,
                created_at=timezone.now(),
            )
            blog.save()
            logger.info(f"Saved blog to database with ID: {blog.id}")

            response_data = {
                "status": "success",
                "message": "Blog generated successfully!",
                "topic": topic,
                "keywords": keywords,
                "tone": tone,
                "length_min": length_min,
                "length_max": length_max,
                "introduction": introduction,
                "table_of_content": table_of_content,
                "faq": faq,
                "cta": cta,
                "conclusion": conclusion,
                "target_audience": target_audience,
                "content": blog_content,
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

        # Save to database
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
            "content": blog_content,
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
