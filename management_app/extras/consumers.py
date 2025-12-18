import json
import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from management_app.config.celery.tasks.blog_generator_tasks.blog_generation_task import generate_blog_parallel_task


logger = logging.getLogger(__name__)

class StreamingWebSocketConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer that listens for events from Django Channels Groups and streams them to the client.
    Uses 'blog_{task_id}' group for targeted updates.
    """

    async def connect(self):
        """Handles WebSocket connection."""
        await self.accept()
        logger.info(f"WebSocket connected: {self.scope['path']}")

    async def disconnect(self, close_code):
        """Handles WebSocket disconnection."""
        logger.info(f"WebSocket disconnected ({close_code})")

    async def receive(self, text_data):
        """Handles receiving messages from the frontend."""
        try:
            data = json.loads(text_data)
            msg_type = data.get("type")
            
            if msg_type in ["generate_blog", "blog_generation"]:
                await self.handle_blog_generation(data)
            elif msg_type == "cancel":
                await self.send_json({"type": "status", "message": "Cancellation not implemented via WebSocket yet"})
        except Exception as e:
            logger.error(f"WebSocket receive error: {e}")
            await self.send_json({"type": "error", "message": "Invalid request format"})

    async def handle_blog_generation(self, data):
        """Trigger Celery task for blog generation and notify the client."""
        
        topic = data.get("topic")
        task_id = data.get("message_id") or f"blog_{int(asyncio.get_event_loop().time())}"

        if not topic:
            await self.send_json({"type": "error", "message": "Topic is missing"})
            return

        # Join the group for this specific task
        group_name = f"blog_{task_id}"
        await self.channel_layer.group_add(group_name, self.channel_name)
        logger.debug(f"Added channel {self.channel_name} to group {group_name}")

        # Trigger the Celery task to start blog generation
        user = self.scope.get('user')
        user_id = 0
        username = "Anonymous"
        email = ""
        org_id = ""
        org_name = ""

        if user and user.is_authenticated:
            user_id = user.id
            username = getattr(user, 'username', str(user))
            email = getattr(user, 'email', '')
            org_id = getattr(user, 'organization_id', '')
            org_name = getattr(user, 'organization_name', '')

        generate_blog_parallel_task.delay(
            task_id=task_id,
            user_id=user_id,
            username=username,
            email=email,
            organization_id=org_id,
            organization_name=org_name,
            topic=topic,
            blog_type=data.get("blog_type", "News"),
            keywords=data.get("keywords", []),
            target_audience=data.get("target_audience", []),
            use_custom_llm=data.get("use_custom_llm", False),
            generate_images=data.get("generate_images", True),
            length_min=data.get("length_min", 800),
            length_max=data.get("length_max", 1500)
        )

        await self.send_json({
            "type": "task_queued",
            "task_id": task_id,
            "message": "Generation task started in background..."
        })

    async def stream_message(self, event):
        """
        Handler for messages sent to the Channels Group.
        This method is called by the Channel Layer when a message is sent to the group.
        """
        # Forward the 'data' part of the event directly to the WebSocket
        await self.send(text_data=json.dumps(event["data"]))

    async def send_json(self, data):
        """Helper method to send JSON data to WebSocket."""
        await self.send(text_data=json.dumps(data))
