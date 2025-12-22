"""
Celery task for async chatbot streaming.

This task runs the ChatbotStreamer in an async event loop and broadcasts
updates via Django Channels Groups.
"""

import asyncio
import logging
from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone

from management_app.chatbot.service.agent.chatbot_streamer import ChatbotStreamer
from management_app.chatbot.models import ChatSession, ChatMessage

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, soft_time_limit=300, time_limit=360)
def generate_chat_response_task(
    self,
    task_id,
    session_id,
    user_id,
    username='Anonymous',
    email='',
    query='',
    top_k=10,
    **kwargs
):
    """
    Celery task that runs ChatbotStreamer and broadcasts updates via Channels Groups.
    
    Args:
        task_id: Unique task identifier for WebSocket group
        session_id: Chat session ID
        user_id: User ID
        username: Username
        email: User email
        query: User's query
        top_k: Number of documents to retrieve
    
    Returns:
        dict: Task result with status and metadata
    """
    channel_layer = get_channel_layer()
    group_name = f"chat_{task_id}"

    async def run_streaming():
        """Async function to run the streaming chatbot."""
        # Initialize streamer
        streamer = ChatbotStreamer(
            query=query,
            session_id=session_id,
            task_id=task_id,
            user_id=user_id,
            username=username,
            email=email,
            top_k=top_k,
        )

        # Run streaming generation
        await streamer.generate_streaming_response()

        # Save to database after streaming completes
        try:
            await save_chat_to_database(
                session_id=session_id,
                user_id=user_id,
                username=username,
                email=email,
                query=query,
                metadata=streamer.get_metadata()
            )
        except Exception as e:
            logger.error(f"Failed to save chat to database: {e}", exc_info=True)

        return streamer.get_metadata()

    # Run async event loop
    try:
        logger.info(f"🚀 Starting Chat Task {task_id} for session {session_id}")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(run_streaming())
            logger.info(f"✅ Chat Task {task_id} completed successfully")
            return {"status": "success", "task_id": task_id, **result}
        finally:
            loop.close()

    except Exception as e:
        logger.exception(f"❌ Chat Task {task_id} failed: {e}")
        
        # Notify of error via Channels
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "stream_message",
                "data": {
                    "type": "error",
                    "session_id": session_id,
                    "message": f"Chat generation failed: {str(e)}"
                }
            }
        )
        
        # Retry if necessary
        raise self.retry(exc=e, countdown=30)


async def save_chat_to_database(
    session_id: str,
    user_id: int,
    username: str,
    email: str,
    query: str,
    metadata: dict
):
    """
    Save chat messages to database after streaming completes.
    
    Args:
        session_id: Chat session ID
        user_id: User ID
        username: Username
        email: User email
        query: User's query
        metadata: Response metadata from ChatbotStreamer
    """
    from asgiref.sync import sync_to_async

    try:
        # Get or create chat session
        chat_session, created = await sync_to_async(ChatSession.objects.get_or_create)(
            session_id=session_id,
            defaults={
                'user_id': user_id,
                'username': username,
                'email': email,
                'is_active': True,
                'created_at': timezone.now(),
            }
        )

        if created:
            logger.info(f"Created new chat session: {session_id}")
        else:
            logger.info(f"Using existing chat session: {session_id}")

        # Save user message
        await sync_to_async(ChatMessage.objects.create)(
            session_id=chat_session,
            message_type='user',
            content=query,
            created_at=timezone.now(),
        )

        # Save assistant message
        await sync_to_async(ChatMessage.objects.create)(
            session_id=chat_session,
            message_type='assistant',
            content=metadata.get('response', ''),
            created_at=timezone.now(),
            processing_time=metadata.get('processing_time', 0.0),
            tokens_used=metadata.get('tokens_generated', 0),
            relevant_documents=metadata.get('relevant_docs', []),
        )

        # Update session
        chat_session.total_messages += 2  # User + Assistant
        chat_session.updated_at = timezone.now()
        await sync_to_async(chat_session.save)()

        logger.info(
            f"💾 Saved chat to database: session={session_id}, "
            f"tokens={metadata.get('tokens_generated', 0)}, "
            f"docs={metadata.get('documents_found', 0)}"
        )

    except Exception as e:
        logger.error(f"Database save failed for session {session_id}: {e}", exc_info=True)
        raise
