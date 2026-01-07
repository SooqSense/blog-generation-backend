import base64
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .services.analytics_service import AnalyticsService
from .models import BlogAggregate

# 1x1 transparent GIF
PIXEL_GIF_DATA = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")

class TrackingPixelView(View):
    """
    Serves a transparent 1x1 GIF and records a view.
    Usage: <img src="/api/analytics/pixel/<blog_id>/?session_key=<uuid>" />
    """
    def get(self, request, blog_id):
        session_key = request.GET.get('session_key')
        if session_key:
            remote_addr = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            session = AnalyticsService.get_or_create_session(session_key, remote_addr, user_agent)
            AnalyticsService.record_event(blog_id, session, 'pixel_load')

        return HttpResponse(PIXEL_GIF_DATA, content_type="image/gif")

@method_decorator(csrf_exempt, name='dispatch')
class CollectEventView(APIView):
    """
    Receives JSON events (heartbeat, scroll).
    Payload: { "blog_id": 1, "session_key": "uuid", "event_type": "scroll", "scroll_percent": 50 }
    """
    authentication_classes = [] # Allow public tracking
    permission_classes = []

    def post(self, request):
        data = request.data
        blog_id = data.get('blog_id')
        session_key = data.get('session_key')
        event_type = data.get('event_type')
        
        if not all([blog_id, session_key, event_type]):
            return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

        remote_addr = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        session = AnalyticsService.get_or_create_session(session_key, remote_addr, user_agent)
        
        AnalyticsService.record_event(
            blog_id=blog_id,
            session=session,
            event_type=event_type,
            scroll_percent=data.get('scroll_percent', 0),
            time_delta_ms=data.get('time_delta_ms', 0)
        )
        
        return Response({"status": "recorded"}, status=status.HTTP_200_OK)

class BlogStatsView(APIView):
    """Returns aggregated stats for a blog."""
    def get(self, request, blog_id):
        # Refresh aggregates on demand for now (can be optimized with cache/cron)
        try:
            aggregate = AnalyticsService.calculate_aggregates(blog_id)
            return Response({
                "blog_id": blog_id,
                "total_views": aggregate.total_views,
                "unique_views": aggregate.unique_views,
                "engaged_reads": aggregate.engaged_reads,
                "avg_scroll_depth": f"{round(aggregate.avg_scroll_depth, 1)}%",
                "avg_time_on_page": f"{round(aggregate.avg_time_on_page_sec, 1)}s"
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
