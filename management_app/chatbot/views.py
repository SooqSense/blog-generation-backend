import uuid
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiResponse
import logging

# Import models
from .models import ChatSession, ChatMessage

# Set up logging
logger = logging.getLogger(__name__)

# Import local services
from .service.agent.agent import project_chatbot


@extend_schema(
    request={
        'type': 'object',
        'properties': {
            'query': {
                'type': 'string',
                'description': 'User\'s question or query about their project portfolio documents.'
            },
            'session_id': {
                'type': 'string',
                'description': 'Chat session ID. If not provided, a new session will be created.'
            }
        },
        'required': ['query']
    },
    responses={
        200: OpenApiResponse(
            description="Chat response generated successfully.",
        ),
        400: OpenApiResponse(
            description="Bad Request - Invalid query or session."
        ),
        500: OpenApiResponse(
            description="Internal Server Error."
        ),
    },
    description="Chat with AI about uploaded documents. Provide a query and optionally a session_id. If no session_id is provided, a new chat session will be created. The AI will search through your uploaded documents and provide relevant answers with source citations.",
)
@api_view(["POST"])
def chat_api(request):
    """Chat with AI about uploaded documents."""
    try:
        query = request.data.get("query", "").strip()
        session_id = request.data.get("session_id", "").strip()

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
            logger.error(f"Chat failed: {result['message']}")
            return Response(
                {"error": result["message"]},
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
            tokens_used=result.get("tokens_used", 0),
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
            "tokens_used": result.get("tokens_used", 0),
            "model_used": result.get("model_used", "unknown"),
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
        200: OpenApiResponse(
            description="User chat sessions retrieved successfully.",
        ),
        401: OpenApiResponse(
            description="Unauthorized - Invalid or missing token."
        ),
    },
    description="Get all chat sessions for the authenticated user.",
)
@api_view(["GET"])
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
