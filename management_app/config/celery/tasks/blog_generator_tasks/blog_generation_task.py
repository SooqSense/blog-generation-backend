"""
Celery tasks for parallel blog generation with Redis Pub/Sub progress updates.

This module provides production-ready blog generation tasks that:
- Run in separate Celery worker processes (scalable)
- Publish real-time progress via Redis Pub/Sub
- Support automatic retry on failure
- Persist task results in Redis backend
"""

import json
import logging
import time
from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import redis
from django.conf import settings

logger = logging.getLogger(__name__)

# Redis client for Pub/Sub
redis_client = redis.Redis(
    host=settings.REDIS_HOST if hasattr(settings, 'REDIS_HOST') else 'localhost',
    port=settings.REDIS_PORT if hasattr(settings, 'REDIS_PORT') else 6379,
    db=0,
    decode_responses=True
)


@shared_task(bind=True, max_retries=3, soft_time_limit=1800, time_limit=2000)
def generate_blog_parallel_task(
    self,
    task_id,
    user_id,
    topic,
    blog_type='News',
    length_min=800,
    length_max=1500,
    keywords=None,
    target_audience=None,
    generate_images=True,
    use_custom_llm=False,
    max_image_prompts=5,
    organization_id=None,
    organization_name=None,
    username=None,
    user_email=None,
    **kwargs
):
    """
    Celery task for parallel blog generation with real-time progress updates.
    
    This task runs in a separate worker process and publishes progress updates
    via Redis Pub/Sub, which are then forwarded to WebSocket clients.
    
    Args:
        task_id: Unique task identifier for tracking
        user_id: User ID requesting the blog
        topic: Blog topic
        blog_type: Type of blog (Guide, News, Tutorial, Analysis)
        length_min: Minimum blog length
        length_max: Maximum blog length
        keywords: List of keywords
        target_audience: List of target audience
        generate_images: Whether to generate images
        use_custom_llm: Use custom LLM (Gemini) instead of OpenAI
        max_image_prompts: Maximum number of images to generate
        
    Returns:
        dict: Blog generation result with content, sections, images, sources
    """
    from management_app.blog_generator.service.blog_writing.blog_writer import BlogWriter
    from management_app.blog_generator.models import BlogGeneral

    
    start_time = time.time()
    channel_layer = get_channel_layer()
    
    def publish_to_redis(event_type, data):
        """Publish progress update to Redis Pub/Sub channel"""
        try:
            message = json.dumps({
                'type': event_type,
                'task_id': task_id,
                'data': data
            })
            redis_client.publish(f'blog_progress_{task_id}', message)
            logger.info(f"📡 Published to Redis: {event_type} for task {task_id}")
        except Exception as e:
            logger.error(f"Failed to publish to Redis: {e}")
    
    def publish_progress(event_type, data):
        """Publish to Redis Pub/Sub only (Channels layer not needed)"""
        publish_to_redis(event_type, data)
    
    # Callback functions for BlogWriter (all must be async)
    async def on_status(stage, message):
        publish_progress('status', {
            'stage': stage,
            'message': message,
            'task_id': task_id
        })
    
    async def on_toc(section_metadata):
        publish_progress('toc', {
            'sections': section_metadata,
            'total_sections': len(section_metadata),
            'task_id': task_id
        })
    
    async def on_section_start(section_title, index, section_id):
        publish_progress('section_start', {
            'section_id': section_id,
            'section_title': section_title,
            'index': index,
            'task_id': task_id
        })
    
    async def on_section_progress(section_id, section_title, stage, progress_message):
        publish_progress('section_progress', {
            'section_id': section_id,
            'section_title': section_title,
            'stage': stage,
            'message': progress_message,
            'task_id': task_id
        })
    
    async def on_section_token(token, section_id):
        publish_progress('section_token', {
            'section_id': section_id,
            'content': token,
            'task_id': task_id
        })
    
    async def on_image(section_title, image_data, section_id):
        publish_progress('image', {
            'section_id': section_id,
            'section_title': section_title,
            'image_url': image_data.get('image_url'),
            'image_data': image_data,
            'task_id': task_id
        })
    
    async def on_section_complete(section_title, content, section_id, image_url):
        publish_progress('section_complete', {
            'section_id': section_id,
            'section_title': section_title,
            'has_image': image_url is not None,
            'image_url': image_url,
            'task_id': task_id
        })
    
    async def on_batch_status(completed, total, failed):
        publish_progress('batch_status', {
            'completed': completed,
            'total': total,
            'in_progress': total - completed - failed,
            'failed': failed,
            'task_id': task_id
        })
    
    async def on_section_error(section_id, section_title, error, retry_attempt, max_retries, will_retry):
        publish_progress('section_error', {
            'section_id': section_id,
            'section_title': section_title,
            'error': error,
            'retry_attempt': retry_attempt,
            'max_retries': max_retries,
            'will_retry': will_retry,
            'task_id': task_id
        })
    
    async def on_complete(result_data):
        total_time = time.time() - start_time
        result_data['total_time_seconds'] = round(total_time, 2)
        result_data['task_id'] = task_id
        
        # Save to database
        try:
            # Use sync_to_async or ensure we are safe. 
            # Since on_complete is async but we are inside run_generation which is run_until_complete,
            # we need to be careful with ORM access.
            # Ideally, save it after the loop closes or use asgiref.sync.sync_to_async
            pass 
        except Exception as e:
            logger.error(f"Failed to save blog to database: {e}")

        publish_progress('complete', {
            'message': '✅ Blog generation completed successfully!',
            'data': result_data,
            'task_id': task_id
        })
    
    async def on_error(error_message):
        publish_progress('error', {
            'message': f'Blog generation failed: {error_message}',
            'task_id': task_id
        })
    
    try:
        logger.info(f"🚀 Starting blog generation task {task_id} for topic: {topic}")
        
        # Initialize BlogWriter
        generator = BlogWriter(
            topic=topic,
            blog_type=blog_type,
            length_min=length_min,
            length_max=length_max,
            keywords=keywords or [],
            target_audience=target_audience or [],
            use_custom_llm=use_custom_llm,
            generate_images=generate_images,
            max_image_prompts=max_image_prompts,
        )
        
        # Run async blog generation in sync context
        import asyncio
        
        async def run_generation():
            return await generator.generate_streaming_blog(
                on_status=on_status,
                on_toc=on_toc,
                on_section_start=on_section_start,
                on_section_progress=on_section_progress,
                on_section_token=on_section_token,
                on_image=on_image,
                on_section_complete=on_section_complete,
                on_batch_status=on_batch_status,
                on_section_error=on_section_error,
                on_complete=on_complete,
                on_error=on_error,
                max_parallel_sections=3,
                max_retries=2
            )
        
        # Run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_generation())
        finally:
            loop.close()
        
        # Return result (stored in Celery result backend)
        result = {
            'task_id': task_id,
            'status': 'completed',
            'topic': topic,
            'content': generator.blog_content,
            'sections': len(generator.section_images),
            'images': generator.image_urls,
            'total_time': round(time.time() - start_time, 2)
        }
        
        # Save to database (Sync operation is safe here as we are out of the async loop)
        try:
            blog = BlogGeneral.objects.create(
                user_id=user_id if user_id else 0,
                username=username or 'Anonymous',
                email=user_email or '',
                organization_id=organization_id,
                organization_name=organization_name,
                topic=topic,
                content=generator.blog_content,
                image_urls=generator.image_urls,
                is_ai_generated=True,
                seo_optimized=True,
                seo_keywords=keywords or [],
                tags=keywords or [] # using keywords as tags for now
            )
            logger.info(f"✅ Saved generated blog {blog.id} to database for user {username}")
        except Exception as e:
            logger.error(f"❌ Failed to save blog to database: {e}")

        
        logger.info(f"✅ Blog generation task {task_id} completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"❌ Blog generation task {task_id} failed: {e}", exc_info=True)
        
        # Publish error
        on_error(str(e))
        
        # Retry if not max retries
        if self.request.retries < self.max_retries:
            logger.info(f"🔄 Retrying task {task_id} (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        
        # Max retries exceeded
        raise
