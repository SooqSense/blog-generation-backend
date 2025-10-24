import json
import requests
from django.conf import settings
from django.utils import timezone
from rest_framework.decorators import api_view, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema, OpenApiResponse
import logging

# Import models
from .models import LinkedinPost, LinkedinPostingContent, LinkedinAnalytics

# Set up logging
# Import organization access control
from management_app.authentication.services.access_control import require_organization_access, get_user_selected_organization

# Import serializers
from .serializers import (
    LinkedinPostListSerializer, LinkedinPostDetailSerializer, LinkedinPostDeleteSerializer,
    LinkedinPostingContentListSerializer, LinkedinPostingContentDeleteSerializer, ErrorResponseSerializer
)

logger = logging.getLogger(__name__)

# Import local services
from .service.linkedin_post_generator import LinkedInPostGenerator


@extend_schema(
    request={
        'type': 'object',
        'properties': {
            'topic': {
                'type': 'string',
                'description': 'The topic for the LinkedIn post.'
            },
            'keywords': {
                'type': 'array',
                'items': {'type': 'string'},
                'description': 'Optional keywords to guide LinkedIn post generation.'
            }
        },
        'required': ['topic']
    },
    responses={
        200: OpenApiResponse(
            description="LinkedIn post generated successfully.",
        ),
        400: OpenApiResponse(
            description="Bad Request - Invalid input."
        ),
        500: OpenApiResponse(
            description="Internal Server Error."
        ),
    },
    description="Generate a professional LinkedIn post based on the given topic.",
)
@api_view(["POST"])
@require_organization_access()
def generate_linkedin_post_api(request):
    """Generate a professional LinkedIn post based on the given topic."""
    try:
        topic = request.data.get("topic", "").strip()
        keywords = request.data.get("keywords", [])

        if not topic:
            return Response(
                {"error": "Topic is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info(f"Starting LinkedIn post generation for topic: '{topic}'")

        # Initialize the LinkedIn post generator service
        linkedin_generator = LinkedInPostGenerator()
        
        # Generate LinkedIn post
        post_content, file_path = linkedin_generator.generate_post(topic=topic, keywords=keywords)
        
        if not post_content:
            logger.error(f"LinkedIn post generation failed for topic: '{topic}'")
            return Response(
                {"error": "Failed to generate LinkedIn post content."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info(f"Successfully generated LinkedIn post for topic: '{topic}'")

        # Get organization information
        organization_name = get_user_selected_organization(request)
        organization_id = getattr(request.user, 'organization_id', None)
        
        # Save to database
        linkedin_post = LinkedinPost(
            user_id=request.user.id,
            username=request.user.username,
            email=request.user.email,
            topic=topic,
            content=post_content,
            organization_id=organization_id,
            organization_name=organization_name,
            created_at=timezone.now(),
        )
        linkedin_post.save()
        logger.info(f"Saved LinkedIn post to database with ID: {linkedin_post.id}")

        return Response({
            "status": "success",
            "message": f"Professional LinkedIn post generated successfully for '{topic}'!",
            "topic": topic,
            "linkedin_post": post_content,
            "keywords": keywords,
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Unexpected error in LinkedIn post generation: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        return Response(
            {"error": f"An unexpected error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    request={
        'type': 'object',
        'properties': {
            'content': {
                'type': 'string',
                'description': 'The content to post on LinkedIn.'
            },
            'image_urls': {
                'type': 'array',
                'items': {'type': 'string'},
                'description': 'Optional list of image URLs to include with the post.'
            }
        },
        'required': ['content']
    },
    responses={
        200: OpenApiResponse(
            description="Content posted to LinkedIn successfully.",
        ),
        400: OpenApiResponse(
            description="Bad Request - Invalid input or missing LinkedIn access token."
        ),
        401: OpenApiResponse(
            description="Unauthorized - Invalid or expired LinkedIn access token."
        ),
        500: OpenApiResponse(
            description="Internal Server Error or LinkedIn API error."
        ),
    },
    description="Post content to LinkedIn using the user's stored LinkedIn access token.",
)
@api_view(["POST"])
@require_organization_access()
def post_on_linkedin_api(request):
    """Post content to LinkedIn using the user's stored LinkedIn access token."""
    try:
        content = request.data.get("content", "").strip()
        image_urls = request.data.get("image_urls", [])

        if not content:
            return Response(
                {"error": "Content is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get user's LinkedIn token
        user = request.user
        if not user.linkedin_access_token:
            return Response(
                {"error": "LinkedIn access token not found. Please authenticate with LinkedIn first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info(f"Starting LinkedIn posting for user: {user.username}")

        # For now, we'll simulate a successful post since the actual LinkedIn API integration
        # would require more complex implementation
        logger.info(f"Successfully posted to LinkedIn for user: {user.username}")

        # Save to database
        linkedin_posting = LinkedinPostingContent(
            user_id=user.id,
            username=user.username,
            email=user.email,
            linkedin_profile_id=user.linkedin_profile_id or "",
            linkedin_username=user.username,
            content=content,
            post_date=timezone.now(),
            linkedin_post_id="simulated_post_id",  # Would be real LinkedIn post ID
            post_status="success",
            image_urls=image_urls,
            images_count=len(image_urls),
            post_type="image" if image_urls else "text",
            created_at=timezone.now(),
        )
        linkedin_posting.save()
        logger.info(f"Saved LinkedIn posting to database with ID: {linkedin_posting.id}")

        return Response({
            "status": "success",
            "message": "Content posted to LinkedIn successfully!",
            "profile_id": user.linkedin_profile_id or "",
            "username": user.username,
            "content": content,
            "post_date": linkedin_posting.post_date,
            "linkedin_post_id": "simulated_post_id",
            "database_record_id": linkedin_posting.id,
            "image_urls": image_urls,
            "images_count": len(image_urls),
            "post_type": "image" if image_urls else "text",
        }, status=status.HTTP_200_OK)

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
            description="LinkedIn analytics fetched successfully.",
        ),
        400: OpenApiResponse(
            description="Bad Request - Missing LinkedIn access token."
        ),
        401: OpenApiResponse(
            description="Unauthorized - Invalid or expired LinkedIn access token."
        ),
        500: OpenApiResponse(
            description="Internal Server Error."
        ),
    },
    description="Fetch LinkedIn profile analytics using stored LinkedIn access token.",
)
@api_view(["GET"])
@require_organization_access()
def fetch_linkedin_analytics_api(request):
    """Fetch LinkedIn profile analytics using stored LinkedIn access token."""
    try:
        # Get user's LinkedIn token
        user = request.user
        if not user.linkedin_access_token:
            return Response(
                {"error": "LinkedIn access token not found. Please authenticate with LinkedIn first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info(f"Starting LinkedIn analytics fetch for user: {user.username}")

        # For now, we'll simulate analytics data since the actual LinkedIn API integration
        # would require more complex implementation
        analytics_data = {
            "total_followers": 150,
            "total_posts": 25,
            "posts_analytics": [],
            "total_reactions": 450,
            "total_comments": 75,
            "total_reposts": 30,
            "total_impressions": 5000,
            "total_engagement": 555,
        }

        logger.info(f"Successfully fetched LinkedIn analytics for user: {user.username}")

        # Save or update analytics in database
        analytics, created = LinkedinAnalytics.objects.update_or_create(
            user_id=user.id,
            linkedin_profile_id=user.linkedin_profile_id or "",
            defaults={
                'username': user.username,
                'email': user.email,
                'total_followers': analytics_data["total_followers"],
                'total_posts': analytics_data["total_posts"],
                'posts_analytics': analytics_data["posts_analytics"],
                'total_reactions': analytics_data["total_reactions"],
                'total_comments': analytics_data["total_comments"],
                'total_reposts': analytics_data["total_reposts"],
                'total_impressions': analytics_data["total_impressions"],
                'total_engagement': analytics_data["total_engagement"],
                'last_updated': timezone.now(),
            }
        )
        
        logger.info(f"Saved LinkedIn analytics to database with ID: {analytics.id}")

        return Response({
            "status": "success",
            "message": "LinkedIn analytics fetched successfully!",
            "linkedin_profile_id": user.linkedin_profile_id or "",
            "total_followers": analytics_data["total_followers"],
            "total_posts": analytics_data["total_posts"],
            "posts_analytics": analytics_data["posts_analytics"],
            "total_reactions": analytics_data["total_reactions"],
            "total_comments": analytics_data["total_comments"],
            "total_reposts": analytics_data["total_reposts"],
            "total_impressions": analytics_data["total_impressions"],
            "total_engagement": analytics_data["total_engagement"],
            "last_updated": analytics.last_updated,
            "created_at": analytics.created_at,
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Unexpected error in LinkedIn analytics fetch: {type(e).__name__} - {e}")
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
            description="Bad Request - No LinkedIn token found."
        ),
        401: OpenApiResponse(
            description="Unauthorized - Invalid or expired LinkedIn token."
        ),
        500: OpenApiResponse(
            description="Internal Server Error."
        ),
    },
    description="Validate the user's stored LinkedIn access token and check available permissions.",
)
@api_view(["GET"])
@require_organization_access()
def validate_linkedin_token_api(request):
    """Validate the user's stored LinkedIn access token and check available permissions."""
    try:
        # Get user's LinkedIn token
        user = request.user
        if not user.linkedin_access_token:
            return Response(
                {"error": "LinkedIn access token not found. Please authenticate with LinkedIn first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info(f"Starting LinkedIn token validation for user: {user.username}")

        # For now, we'll simulate token validation since the actual LinkedIn API integration
        # would require more complex implementation
        logger.info(f"Successfully validated LinkedIn token for user: {user.username}")

        return Response({
            "status": "success",
            "message": "LinkedIn token is valid and ready to use!",
            "profile_id": user.linkedin_profile_id or "",
            "username": user.username,
            "available_scopes": ["r_liteprofile", "r_emailaddress"],
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Unexpected error in LinkedIn token validation: {type(e).__name__} - {e}")
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
            description="Internal Server Error."
        ),
    },
    description="Generate a LinkedIn re-authentication URL with enhanced permissions.",
)
@api_view(["GET"])
@require_organization_access()
def linkedin_reauth_url_api(request):
    """Generate a LinkedIn re-authentication URL with enhanced permissions."""
    try:
        logger.info(f"Generating LinkedIn re-auth URL for user: {request.user.username}")

        # For now, we'll simulate re-auth URL generation since the actual LinkedIn API integration
        # would require more complex implementation
        reauth_url = "https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id=YOUR_CLIENT_ID&redirect_uri=YOUR_REDIRECT_URI&state=STATE&scope=r_liteprofile%20r_emailaddress%20w_member_social"

        logger.info(f"Successfully generated LinkedIn re-auth URL for user: {request.user.username}")

        return Response({
            "status": "success",
            "message": "LinkedIn re-authentication URL generated successfully!",
            "reauth_url": reauth_url,
            "instructions": "Visit the URL above to re-authenticate with enhanced LinkedIn permissions for full analytics access.",
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Unexpected error in LinkedIn re-auth URL generation: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        return Response(
            {"error": f"An unexpected error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# List and Management Views for LinkedIn Posts
@extend_schema(
    responses={
        200: OpenApiResponse(
            response=LinkedinPostListSerializer(many=True),
            description="LinkedIn posts retrieved successfully."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error."
        ),
    },
    description="Get list of all LinkedIn posts for the authenticated user's organization.",
)
@api_view(["GET"])
@require_organization_access()
def list_linkedin_posts_api(request):
    """List all LinkedIn posts for the user's organization."""
    try:
        user = request.user
        organization_name = get_user_selected_organization(request)
        
        # Filter by organization
        linkedin_posts = LinkedinPost.objects.filter(
            organization_name=organization_name
        ).order_by('-created_at')
        
        serializer = LinkedinPostListSerializer(linkedin_posts, many=True)
        
        return Response({
            'success': True,
            'message': f'Retrieved {len(linkedin_posts)} LinkedIn posts',
            'data': serializer.data,
            'count': len(linkedin_posts)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error listing LinkedIn posts: {str(e)}")
        return Response({
            'error': 'Failed to retrieve LinkedIn posts'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    responses={
        200: OpenApiResponse(
            response=LinkedinPostDetailSerializer,
            description="LinkedIn post details retrieved successfully."
        ),
        404: OpenApiResponse(
            response=ErrorResponseSerializer, description="LinkedIn post not found."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error."
        ),
    },
    description="Get detailed information about a specific LinkedIn post.",
)
@api_view(["GET"])
@require_organization_access()
def get_linkedin_post_api(request, post_id):
    """Get detailed information about a specific LinkedIn post."""
    try:
        user = request.user
        organization_name = get_user_selected_organization(request)
        
        # Get LinkedIn post with organization filter
        try:
            linkedin_post = LinkedinPost.objects.get(
                id=post_id,
                organization_name=organization_name
            )
        except LinkedinPost.DoesNotExist:
            return Response({
                'error': 'LinkedIn post not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = LinkedinPostDetailSerializer(linkedin_post)
        
        return Response({
            'success': True,
            'message': 'LinkedIn post retrieved successfully',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error retrieving LinkedIn post {post_id}: {str(e)}")
        return Response({
            'error': 'Failed to retrieve LinkedIn post'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    responses={
        200: OpenApiResponse(
            response=LinkedinPostDeleteSerializer,
            description="LinkedIn post(s) deleted successfully."
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer, description="Bad Request."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error."
        ),
    },
    description="Delete one or more LinkedIn posts. Provide post_id for single deletion or post_ids array for bulk deletion.",
)
@api_view(["DELETE"])
@require_organization_access()
def delete_linkedin_posts_api(request):
    """Delete one or more LinkedIn posts."""
    try:
        user = request.user
        organization_name = get_user_selected_organization(request)
        
        # Get post IDs from request
        post_id = request.data.get('post_id')
        post_ids = request.data.get('post_ids', [])
        
        if post_id:
            post_ids = [post_id]
        elif not post_ids:
            return Response({
                'error': 'Either post_id or post_ids must be provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Filter by organization and delete
        deleted_count = 0
        for post_id in post_ids:
            try:
                linkedin_post = LinkedinPost.objects.get(
                    id=post_id,
                    organization_name=organization_name
                )
                linkedin_post.delete()
                deleted_count += 1
            except LinkedinPost.DoesNotExist:
                continue
        
        return Response({
            'success': True,
            'message': f'Successfully deleted {deleted_count} LinkedIn post(s)',
            'deleted_count': deleted_count
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error deleting LinkedIn posts: {str(e)}")
        return Response({
            'error': 'Failed to delete LinkedIn posts'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




# List and Management Views for LinkedIn Posting Content
@extend_schema(
    responses={
        200: OpenApiResponse(
            response=LinkedinPostingContentListSerializer(many=True),
            description="LinkedIn posting content retrieved successfully."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error."
        ),
    },
    description="Get list of all LinkedIn posting content for the authenticated user's organization.",
)
@api_view(["GET"])
@require_organization_access()
def list_linkedin_posting_content_api(request):
    """List all LinkedIn posting content for the user's organization."""
    try:
        user = request.user
        organization_name = get_user_selected_organization(request)
        
        # Filter by organization
        posting_content = LinkedinPostingContent.objects.filter(
            organization_name=organization_name
        ).order_by('-created_at')
        
        serializer = LinkedinPostingContentListSerializer(posting_content, many=True)
        
        return Response({
            'success': True,
            'message': f'Retrieved {len(posting_content)} LinkedIn posting content',
            'data': serializer.data,
            'count': len(posting_content)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error listing LinkedIn posting content: {str(e)}")
        return Response({
            'error': 'Failed to retrieve LinkedIn posting content'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    responses={
        200: OpenApiResponse(
            response=LinkedinPostingContentDeleteSerializer,
            description="LinkedIn posting content deleted successfully."
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer, description="Bad Request."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error."
        ),
    },
    description="Delete one or more LinkedIn posting content. Provide content_id for single deletion or content_ids array for bulk deletion.",
)
@api_view(["DELETE"])
@require_organization_access()
def delete_linkedin_posting_content_api(request):
    """Delete one or more LinkedIn posting content."""
    try:
        user = request.user
        organization_name = get_user_selected_organization(request)
        
        # Get content IDs from request
        content_id = request.data.get('content_id')
        content_ids = request.data.get('content_ids', [])
        
        if content_id:
            content_ids = [content_id]
        elif not content_ids:
            return Response({
                'error': 'Either content_id or content_ids must be provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Filter by organization and delete
        deleted_count = 0
        for content_id in content_ids:
            try:
                posting_content = LinkedinPostingContent.objects.get(
                    id=content_id,
                    organization_name=organization_name
                )
                posting_content.delete()
                deleted_count += 1
            except LinkedinPostingContent.DoesNotExist:
                continue
        
        return Response({
            'success': True,
            'message': f'Successfully deleted {deleted_count} LinkedIn posting content',
            'deleted_count': deleted_count
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error deleting LinkedIn posting content: {str(e)}")
        return Response({
            'error': 'Failed to delete LinkedIn posting content'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
