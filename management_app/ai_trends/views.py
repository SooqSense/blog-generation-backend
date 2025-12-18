from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiResponse
import logging

# Import models
from .models import TrendingTopics

# Set up logging
# Import organization access control
from management_app.authentication.services.access_control import require_organization_access, get_user_selected_organization

# Import serializers
from .serializers import (
    TrendingTopicsListSerializer, TrendingTopicsDetailSerializer, 
    TrendingTopicsDeleteSerializer, ErrorResponseSerializer
)

logger = logging.getLogger(__name__)

# Import local services
from .service.trending_queries import fetch_trending_queries


@extend_schema(
    request={
        'type': 'object',
        'properties': {
            'topic': {
                'type': 'string',
                'description': 'The main topic to find trending queries for.'
            },
            'region': {
                'type': 'string',
                'description': 'The region code (e.g., \'US\', \'GB\'). Default is worldwide.'
            },
            'limit': {
                'type': 'integer',
                'description': 'Maximum number of trending queries to return. Default is 30.'
            }
        },
        'required': ['topic']
    },
    responses={
        200: OpenApiResponse(
            description="Trending queries fetched and saved successfully.",
        ),
        400: OpenApiResponse(
            description="Bad Request - Invalid input."
        ),
        500: OpenApiResponse(
            description="Internal Server Error or error during trending queries fetching."
        ),
    },
    description="Fetch trending queries related to a given topic using Serper API and save to database. Fetches 30 trending queries worldwide related to the topic from the past 30 days.",
)
@api_view(["POST"])
@require_organization_access()
def fetch_and_save_related_topics(request):
    """Fetch trending queries related to a given topic using Serper API and save to database."""
    try:
        topic = request.data.get("topic", "").strip()
        region = request.data.get("region", "").strip()
        limit = request.data.get("limit", 30)

        if not topic:
            return Response(
                {"error": "Topic is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info(f"Starting trending queries fetch for topic: '{topic}', region: '{region}'")

        # Fetch trending queries using the service
        result = fetch_trending_queries(topic=topic, region=region, limit=limit)
        
        if not result["success"]:
            logger.error(f"Trending queries fetch failed: {result['message']}")
            return Response(
                {"error": result["message"]},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info(f"Successfully fetched trending queries for topic: '{topic}'")

        # Save to database
        trending_topics = TrendingTopics(
            keyword=topic,
            rising_topics=result.get("rising_queries", []),
            top_topics=result.get("top_queries", []),
            user_id=request.user.id,
            username=request.user.username,
            email=request.user.email,
            created_at=timezone.now(),
        )
        trending_topics.save()
        logger.info(f"Saved trending topics to database with ID: {trending_topics.id}")

        return Response({
            "status": "success",
            "message": f"Trending queries fetched and saved successfully for '{topic}'!",
            "topic": topic,
            "region": region,
            "rising_queries": result.get("rising_queries", []),
            "top_queries": result.get("top_queries", []),
            "total_queries": len(result.get("rising_queries", [])) + len(result.get("top_queries", [])),
            "database_record_id": trending_topics.id,
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Unexpected error in trending queries fetch: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        return Response(
            {"error": f"An unexpected error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# List and Management Views for AI Trends
@extend_schema(
    responses={
        200: OpenApiResponse(
            response=TrendingTopicsListSerializer(many=True),
            description="Trending topics retrieved successfully."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error."
        ),
    },
    description="Get list of all trending topics for the authenticated user's organization.",
)
@api_view(["GET"])
@require_organization_access()
def list_trending_topics_api(request):
    """List all trending topics for the user's organization."""
    try:
        user = request.user
        organization_name = get_user_selected_organization(request)
        
        # Filter by organization
        trending_topics = TrendingTopics.objects.filter(
            organization_name=organization_name
        ).order_by('-created_at')
        
        serializer = TrendingTopicsListSerializer(trending_topics, many=True)
        
        return Response({
            'success': True,
            'message': f'Retrieved {len(trending_topics)} trending topics',
            'data': serializer.data,
            'count': len(trending_topics)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error listing trending topics: {str(e)}")
        return Response({
            'error': 'Failed to retrieve trending topics'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    responses={
        200: OpenApiResponse(
            response=TrendingTopicsDetailSerializer,
            description="Trending topics details retrieved successfully."
        ),
        404: OpenApiResponse(
            response=ErrorResponseSerializer, description="Trending topics not found."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error."
        ),
    },
    description="Get detailed information about a specific trending topics entry.",
)
@api_view(["GET"])
@require_organization_access()
def get_trending_topics_api(request, topic_id):
    """Get detailed information about a specific trending topics entry."""
    try:
        user = request.user
        organization_name = get_user_selected_organization(request)
        
        # Get trending topics with organization filter
        try:
            trending_topics = TrendingTopics.objects.get(
                id=topic_id,
                organization_name=organization_name
            )
        except TrendingTopics.DoesNotExist:
            return Response({
                'error': 'Trending topics not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = TrendingTopicsDetailSerializer(trending_topics)
        
        return Response({
            'success': True,
            'message': 'Trending topics retrieved successfully',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error retrieving trending topics {topic_id}: {str(e)}")
        return Response({
            'error': 'Failed to retrieve trending topics'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    responses={
        200: OpenApiResponse(
            response=TrendingTopicsDeleteSerializer,
            description="Trending topics deleted successfully."
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer, description="Bad Request."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error."
        ),
    },
    description="Delete one or more trending topics entries. Provide topic_id for single deletion or topic_ids array for bulk deletion.",
)
@api_view(["DELETE"])
@require_organization_access()
def delete_trending_topics_api(request):
    """Delete one or more trending topics entries."""
    try:
        user = request.user
        organization_name = get_user_selected_organization(request)
        
        # Get topic IDs from request
        topic_id = request.data.get('topic_id')
        topic_ids = request.data.get('topic_ids', [])
        
        if topic_id:
            topic_ids = [topic_id]
        elif not topic_ids:
            return Response({
                'error': 'Either topic_id or topic_ids must be provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Filter by organization and delete
        deleted_count = 0
        for topic_id in topic_ids:
            try:
                trending_topics = TrendingTopics.objects.get(
                    id=topic_id,
                    organization_name=organization_name
                )
                trending_topics.delete()
                deleted_count += 1
            except TrendingTopics.DoesNotExist:
                continue
        
        return Response({
            'success': True,
            'message': f'Successfully deleted {deleted_count} trending topics entry(ies)',
            'deleted_count': deleted_count
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error deleting trending topics: {str(e)}")
        return Response({
            'error': 'Failed to delete trending topics'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
