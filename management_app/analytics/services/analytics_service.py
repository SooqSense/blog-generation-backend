import hashlib
import logging
from django.db import models
from django.db.models import Count, Avg, Sum
from django.utils import timezone
from ..models import AnalyticSession, AnalyticEvent, BlogAggregate
from management_app.blog_generator.models import BlogGeneral

logger = logging.getLogger(__name__)

class AnalyticsService:
    @staticmethod
    def get_or_create_session(session_key, remote_addr, user_agent):
        """Get or create an analytic session based on UUID and IP hash."""
        target_ip_hash = hashlib.sha256(remote_addr.encode()).hexdigest()
        
        session, created = AnalyticSession.objects.get_or_create(
            session_key=session_key,
            defaults={
                'ip_hash': target_ip_hash,
                'user_agent': user_agent
            }
        )
        return session

    @staticmethod
    def record_event(blog_id, session, event_type, scroll_percent=0, time_delta_ms=0):
        """Record a raw event and trigger aggregate update."""
        try:
            blog = BlogGeneral.objects.get(id=blog_id)
            
            event = AnalyticEvent.objects.create(
                blog=blog,
                session=session,
                event_type=event_type,
                scroll_percent=scroll_percent,
                time_delta_ms=time_delta_ms
            )
            
            # For high performance, we'd use a background task to update aggregates
            # For now, we update them periodically or on-demand via the service
            return event
        except BlogGeneral.DoesNotExist:
            logger.error(f"Blog ID {blog_id} not found for analytics event")
            return None

    @staticmethod
    def calculate_aggregates(blog_id):
        """Calculate and save aggregates for a specific blog."""
        blog = BlogGeneral.objects.get(id=blog_id)
        
        # Total Views: pixel_load count
        total_views = AnalyticEvent.objects.filter(blog=blog, event_type='pixel_load').count()
        
        # Unique Views: distinct sessions with pixel_load
        unique_views = AnalyticEvent.objects.filter(
            blog=blog, event_type='pixel_load'
        ).values('session').distinct().count()
        
        # Avg Scroll Depth
        avg_scroll = AnalyticEvent.objects.filter(
            blog=blog, event_type='scroll'
        ).aggregate(Avg('scroll_percent'))['scroll_percent__avg'] or 0.0
        
        # Total Time Spent per Session
        session_times = AnalyticEvent.objects.filter(blog=blog).values('session').annotate(
            total_time=Sum('time_delta_ms')
        )
        
        avg_time_ms = session_times.aggregate(Avg('total_time'))['total_time__avg'] or 0
        avg_time_sec = avg_time_ms / 1000.0
        
        # Engaged Reads (Threshold: > 30s AND > 50% scroll)
        engaged_count = 0
        for s in session_times:
            if s['total_time'] > 30000: # 30s
                max_scroll = AnalyticEvent.objects.filter(
                    blog=blog, session_id=s['session'], event_type='scroll'
                ).aggregate(models.Max('scroll_percent'))['scroll_percent__max'] or 0
                if max_scroll >= 50:
                    engaged_count += 1

        aggregate, _ = BlogAggregate.objects.update_or_create(
            blog=blog,
            defaults={
                'total_views': total_views,
                'unique_views': unique_views,
                'engaged_reads': engaged_count,
                'avg_scroll_depth': avg_scroll,
                'avg_time_on_page_sec': avg_time_sec
            }
        )
        return aggregate
