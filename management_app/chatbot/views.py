import uuid
import json
import asyncio
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiResponse
import logging
from django.contrib.auth import get_user_model

# Import models
from .models import ChatSession, ChatMessage

# Import serializers
from .serializers import ChatRequestSerializer, ChatResponseSerializer, UserSessionsResponseSerializer

# Set up logging
# Import organization access control
from management_app.authentication.services.access_control import require_organization_access

logger = logging.getLogger(__name__)
User = get_user_model()

# Import local services
from .service.agent.agent import project_chatbot


@extend_schema(
    request=ChatRequestSerializer,
    responses={
        200: ChatResponseSerializer,
        400: OpenApiResponse(
            description="Bad Request - Invalid query or session."
        ),
        500: OpenApiResponse(
            description="Internal Server Error."
        ),
    },
    description="""Chat with AI about uploaded documents. 
    
    **Modes:**
    - **Sync Mode (default)**: Returns complete response immediately
    - **Streaming Mode**: Returns task_id for WebSocket streaming
    
    **Parameters:**
    - `query` (required): Your question
    - `session_id` (optional): Existing session ID or leave empty for new session
    - `stream` (optional): Set to `true` for streaming mode
    
    **Streaming Usage:**
    1. Call this endpoint with `stream=true`
    2. Connect to WebSocket: `ws://localhost:8000/ws/stream/`
    3. Send: `{"type": "chat_message", "task_id": "<returned_task_id>", "session_id": "<session_id>", "query": "<query>"}`
    4. Receive real-time token events
    """,
)
@api_view(["POST"])
@require_organization_access()
def chat_api(request):
    """Chat with AI about uploaded documents (supports both sync and streaming modes)."""
    try:
        query = request.data.get("query", "").strip()
        session_id = request.data.get("session_id", "").strip()
        stream = request.data.get("stream", False)  # New parameter

        if not query:
            return Response(
                {"error": "Query is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # STREAMING MODE: Return task_id for WebSocket
        if stream:
            import time
            task_id = f"chat_{int(time.time() * 1000)}"
            
            if not session_id:
                session_id = str(uuid.uuid4())

            logger.info(f"Initiating streaming chat: task_id={task_id}, session_id={session_id}")

            return Response({
                "status": "success",
                "mode": "streaming",
                "message": "Streaming task initiated. Connect to WebSocket with this task_id.",
                "task_id": task_id,
                "session_id": session_id,
                "query": query,
                "websocket_url": "ws://localhost:8000/ws/stream/",
                "instructions": {
                    "step1": "Connect to WebSocket URL",
                    "step2": f"Send: {{\"type\": \"chat_message\", \"task_id\": \"{task_id}\", \"session_id\": \"{session_id}\", \"query\": \"{query}\"}}",
                    "step3": "Listen for events: status, token, context_found, complete, error"
                }
            }, status=status.HTTP_200_OK)

        # SYNC MODE: Original behavior (complete response)
        logger.info(f"Starting sync chat for user: {request.user.username}, query: {query[:50]}...")

        if not query:
            return Response(
                {"error": "Query is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info(f"Starting chat for user: {request.user.username}, query: {query[:50]}...")

        # Get or create chat session with proper user isolation
        if session_id:
            try:
                # Try to find existing session
                chat_session = ChatSession.objects.get(
                    session_id=session_id, 
                    user_id=request.user.id,
                    is_active=True
                )
                logger.info(f"Using existing chat session: {session_id} for user: {request.user.username}")
            except ChatSession.DoesNotExist:
                # Create new session with the provided session_id
                chat_session = ChatSession(
                    session_id=session_id,
                    user_id=request.user.id,
                    username=request.user.username,
                    email=request.user.email,
                    is_active=True,
                    created_at=timezone.now(),
                )
                chat_session.save()
                logger.info(f"Created new chat session with provided ID: {session_id} for user: {request.user.username}")
        else:
            # Create new session for the authenticated user
            session_id = str(uuid.uuid4())
            chat_session = ChatSession(
                session_id=session_id,
                user_id=request.user.id,
                username=request.user.username,
                email=request.user.email,
                is_active=True,
                created_at=timezone.now(),
            )
            chat_session.save()
            logger.info(f"Created new chat session: {session_id} for user: {request.user.username}")

        # Save user message
        user_message = ChatMessage(
            session_id=chat_session,
            message_type="user",
            content=query,
            created_at=timezone.now(),
        )
        user_message.save()

        # Get AI response using the service
        result = project_chatbot.ask(query)
        
        if not result["success"]:
            # The new agent.py returns "response" for errors, not "message"
            error_msg = result.get("response") or result.get("error", "Unknown error")
            logger.error(f"Chat failed: {error_msg}")
            return Response(
                {"error": error_msg, "status": "error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info(f"Successfully generated chat response for session: {session_id}")

        # Save assistant message
        assistant_message = ChatMessage(
            session_id=chat_session,
            message_type="assistant",
            content=result["response"],
            created_at=timezone.now(),
            processing_time=result.get("processing_time", 0),
            tokens_used=0,  # New sync-only agent doesn't provide token count
        )
        assistant_message.save()

        # Update session
        chat_session.total_messages += 2  # User + Assistant messages
        chat_session.updated_at = timezone.now()
        chat_session.save()

        return Response({
            "status": "success",
            "message": "Chat response generated successfully!",
            "session_id": session_id,
            "is_new_session": not bool(request.data.get("session_id")),
            "response": result["response"],
            "processing_time": result.get("processing_time", 0),
            "tokens_used": 0,  # New sync-only agent doesn't provide token count
            "model_used": project_chatbot.config.model,  # Get model from config
            "total_messages": chat_session.total_messages,
            "documents_found": result.get("documents_found", 0),
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Unexpected error in chat: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        return Response(
            {"error": f"An unexpected error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )



@extend_schema(
    responses={
        200: UserSessionsResponseSerializer,
        401: OpenApiResponse(
            description="Unauthorized - Invalid or missing token."
        ),
    },
    description="Get all chat sessions for the authenticated user.",
)
@api_view(["GET"])
@require_organization_access()
def get_user_sessions_api(request):
    """Get all chat sessions for the authenticated user"""
    try:
        # Get all active sessions for the user
        sessions = ChatSession.objects.filter(
            user_id=request.user.id,
            is_active=True
        ).order_by('-updated_at')
        
        sessions_data = []
        for session in sessions:
            # Get message count for each session using the ForeignKey relationship
            message_count = ChatMessage.objects.filter(session_id=session).count()
            
            sessions_data.append({
                'session_id': session.session_id,
                'title': f"Chat Session {session.session_id[:8]}...",
                'created_at': session.created_at.isoformat(),
                'updated_at': session.updated_at.isoformat(),
                'message_count': message_count,
                'total_messages': session.total_messages,
            })
        
        logger.info(f"Retrieved {len(sessions_data)} sessions for user: {request.user.username}")
        
        return Response({
            "status": "success",
            "message": f"Retrieved {len(sessions_data)} chat sessions",
            "sessions": sessions_data,
            "total_sessions": len(sessions_data),
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error retrieving user sessions: {type(e).__name__} - {e}")
        return Response(
            {"error": f"An unexpected error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


