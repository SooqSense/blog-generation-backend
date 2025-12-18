import json
import asyncio
import logging
from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.conf import settings
import redis

from management_app.blog_generator.service.blog_writing.blog_writer import BlogWriter
from management_app.blog_generator.models import BlogGeneral

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, soft_time_limit=1800, time_limit=2000)
def generate_blog_parallel_task(
    self,
    task_id,
    user_id,
    username='Anonymous',
    email='',
    organization_id='',
    organization_name='',
    topic='',
    blog_type='News',
    length_min=800,
    length_max=1500,
    keywords=None,
    target_audience=None,
    generate_images=True,
    use_custom_llm=False,
    max_image_prompts=5,
    **kwargs
):
    """
    Celery task that runs the BlogWriter and broadcasts updates via Channels Groups.
    It also publishes tokens to Redis for real-time streaming to WebSocket.
    """
    channel_layer = get_channel_layer()
    group_name = f"blog_{task_id}"

    async def run_writing():
        writer = BlogWriter(
            topic=topic,
            task_id=task_id,
            blog_type=blog_type,
            length_min=length_min,
            length_max=length_max,
            keywords=keywords or [],
            target_audience=target_audience or [],
            use_custom_llm=use_custom_llm,
            generate_images=generate_images,
            max_image_prompts=max_image_prompts,
        )
        
        # BlogWriter now publishes tokens and status directly to Redis Pub/Sub
        await writer.generate_streaming_blog()
        
        # Final save to DB
        try:
            from asgiref.sync import sync_to_async
            await sync_to_async(BlogGeneral.objects.create)(
                user_id=user_id or 0,
                username=username,
                email=email,
                organization_id=organization_id,
                organization_name=organization_name,
                topic=topic,
                content=writer.blog_content,
                image_urls=writer.image_urls,
                is_ai_generated=True,
                seo_optimized=True,
                seo_keywords=keywords or [],
                tags=keywords or []
            )
        except Exception as e:
            logger.error(f"Failed to save blog to DB: {e}")

    # Kick off the async loop
    try:
        logger.info(f"🚀 Starting Blog Task {task_id}")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_writing())
        finally:
            loop.close()
            
    except Exception as e:
        logger.exception(f"Task {task_id} failed")
        # Notify of error via Channels
        async_to_sync(channel_layer.group_send)(
            group_name,
            {"type": "stream_message", "data": {"type": "error", "message": str(e)}}
        )
        # Retry if necessary
        raise self.retry(exc=e, countdown=30)

    return {"status": "success", "task_id": task_id}
