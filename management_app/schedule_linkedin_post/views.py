from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiResponse
import logging

# Import models
from .models import SchedulePosts

# Set up logging
logger = logging.getLogger(__name__)

# Import local services
from .service.tasks import schedule_linkedin_post_task


@extend_schema(
    request={
        'type': 'object',
        'properties': {
            'content': {
                'type': 'array',
                'items': {'type': 'string'},
                'description': 'Array of LinkedIn post content to be scheduled.'
            },
            'scheduled_date': {
                'type': 'string',
                'format': 'date',
                'description': 'The date when the posts should be published (YYYY-MM-DD format).'
            },
            'scheduled_time': {
                'type': 'string',
                'format': 'time',
                'description': 'The time when the posts should be published (HH:MM:SS format).'
            },
            'timezone': {
                'type': 'string',
                'description': 'Timezone for the scheduled time.'
            },
            'image_urls': {
                'type': 'array',
                'items': {'type': 'string'},
                'description': 'Optional list of image URLs to include with the posts.'
            },
            'delay_between_posts': {
                'type': 'integer',
                'description': 'Delay in minutes between each post if multiple posts are scheduled.'
            }
        },
        'required': ['content', 'scheduled_date', 'scheduled_time']
    },
    responses={
        200: OpenApiResponse(
            description="LinkedIn posts scheduled successfully.",
        ),
        400: OpenApiResponse(
            description="Bad Request - Invalid input or missing LinkedIn access token."
        ),
        401: OpenApiResponse(
            description="Unauthorized - Invalid or expired LinkedIn access token."
        ),
        500: OpenApiResponse(
            description="Internal Server Error."
        ),
    },
    description="Schedule multiple LinkedIn posts to be published at a specific date and time with delays between posts. Requires LinkedIn authentication and validates the scheduled time is in the future.",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def schedule_linkedin_post_api(request):
    """Schedule multiple LinkedIn posts to be published at a specific date and time."""
    try:
        content = request.data.get("content", [])
        scheduled_date = request.data.get("scheduled_date")
        scheduled_time = request.data.get("scheduled_time")
        timezone_str = request.data.get("timezone", "UTC")
        image_urls = request.data.get("image_urls", [])
        delay_between_posts = request.data.get("delay_between_posts", 5)

        if not content:
            return Response(
                {"error": "Content is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not scheduled_date or not scheduled_time:
            return Response(
                {"error": "Scheduled date and time are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get user's LinkedIn token
        user = request.user
        if not user.linkedin_access_token:
            return Response(
                {"error": "LinkedIn access token not found. Please authenticate with LinkedIn first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info(f"Starting LinkedIn post scheduling for user: {user.username}")

        # Schedule posts using the service
        result = schedule_linkedin_post_task.delay(
            user_id=user.id,
            content=content,
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time,
            timezone_str=timezone_str,
            image_urls=image_urls,
            delay_between_posts=delay_between_posts
        )

        logger.info(f"Successfully scheduled LinkedIn posts for user: {user.username}")

        return Response({
            "status": "success",
            "message": f"Successfully scheduled {len(content)} LinkedIn posts!",
            "schedule_id": result.id,
            "content": content,
            "total_posts": len(content),
            "scheduled_datetime": f"{scheduled_date} {scheduled_time}",
            "timezone": timezone_str,
            "linkedin_profile_id": user.linkedin_profile_id,
            "linkedin_username": user.username,
            "post_type": "image" if image_urls else "text",
            "images_count": len(image_urls),
            "delay_between_posts": delay_between_posts,
            "celery_task_id": result.id,
            "created_at": timezone.now(),
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Unexpected error in LinkedIn post scheduling: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        return Response(
            {"error": f"An unexpected error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    responses={
        200: OpenApiResponse(
            description="Scheduled posts retrieved successfully.",
        ),
        500: OpenApiResponse(
            description="Internal Server Error."
        ),
    },
    description="Get all scheduled LinkedIn posts for the authenticated user, including their status and details.",
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_scheduled_posts_api(request):
    """Get all scheduled LinkedIn posts for the authenticated user."""
    try:
        user = request.user
        logger.info(f"Retrieving scheduled posts for user: {user.username}")

        # Get scheduled posts from database
        scheduled_posts = SchedulePosts.objects.filter(user_id=user.id).order_by('-scheduled_datetime')

        posts_data = []
        for post in scheduled_posts:
            posts_data.append({
                "schedule_id": post.id,
                "content": post.content,
                "content_preview": post.content[0][:100] + "..." if post.content else "",
                "total_posts": len(post.content),
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
                "error_message": post.error_message,
            })

        logger.info(f"Retrieved {len(posts_data)} scheduled posts for user: {user.username}")

        return Response({
            "status": "success",
            "message": f"Retrieved {len(posts_data)} scheduled posts successfully!",
            "total_scheduled": len(posts_data),
            "scheduled_posts": posts_data,
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Unexpected error in retrieving scheduled posts: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        return Response(
            {"error": f"An unexpected error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    responses={
        200: OpenApiResponse(
            description="Scheduled post cancelled successfully.",
        ),
        400: OpenApiResponse(
            description="Bad Request - Invalid schedule ID or post cannot be cancelled."
        ),
        404: OpenApiResponse(
            description="Not Found - Scheduled post not found."
        ),
        500: OpenApiResponse(
            description="Internal Server Error."
        ),
    },
    description="Cancel a scheduled LinkedIn post. Only posts with 'scheduled' status can be cancelled.",
)
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def cancel_scheduled_post_api(request, schedule_id):
    """Cancel a scheduled LinkedIn post."""
    try:
        user = request.user
        logger.info(f"Cancelling scheduled post {schedule_id} for user: {user.username}")

        # Get scheduled post
        try:
            scheduled_post = SchedulePosts.objects.get(id=schedule_id, user_id=user.id)
        except SchedulePosts.DoesNotExist:
            return Response(
                {"error": "Scheduled post not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if post can be cancelled
        if scheduled_post.status not in ['scheduled']:
            return Response(
                {"error": f"Cannot cancel post with status '{scheduled_post.status}'. Only 'scheduled' posts can be cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        previous_status = scheduled_post.status

        # Cancel the Celery task if it exists
        if scheduled_post.celery_task_id:
            from celery import current_app
            current_app.control.revoke(scheduled_post.celery_task_id, terminate=True)

        # Update post status
        scheduled_post.status = 'cancelled'
        scheduled_post.save()

        logger.info(f"Successfully cancelled scheduled post {schedule_id} for user: {user.username}")

        return Response({
            "status": "success",
            "message": f"Scheduled post {schedule_id} cancelled successfully!",
            "schedule_id": schedule_id,
            "previous_status": previous_status,
            "current_status": scheduled_post.status,
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Unexpected error in cancelling scheduled post: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        return Response(
            {"error": f"An unexpected error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
