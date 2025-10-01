from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiResponse
import logging

# Import models
from .models import TrendingTopics

# Set up logging
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
@permission_classes([IsAuthenticated])
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
