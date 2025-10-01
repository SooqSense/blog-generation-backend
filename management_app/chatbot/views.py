import uuid
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
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
@permission_classes([IsAuthenticated])
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

        # Get or create chat session
        if session_id:
            try:
                chat_session = ChatSession.objects.get(session_id=session_id, user_id=request.user.id)
            except ChatSession.DoesNotExist:
                return Response(
                    {"error": "Invalid session ID."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            # Create new session
            session_id = str(uuid.uuid4())
            chat_session = ChatSession(
                session_id=session_id,
                user_id=request.user.id,
                username=request.user.username,
                email=request.user.email,
                created_at=timezone.now(),
            )
            chat_session.save()
            logger.info(f"Created new chat session: {session_id}")

        # Save user message
        user_message = ChatMessage(
            session=chat_session,
            message_type="user",
            content=query,
            created_at=timezone.now(),
        )
        user_message.save()

        # Get AI response using the service
        result = project_chatbot.chat_with_documents(query, request.user)
        
        if not result["success"]:
            logger.error(f"Chat failed: {result['message']}")
            return Response(
                {"error": result["message"]},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info(f"Successfully generated chat response for session: {session_id}")

        # Save assistant message
        assistant_message = ChatMessage(
            session=chat_session,
            message_type="assistant",
            content=result["response"],
            relevant_documents=result.get("relevant_documents", []),
            sources_used=result.get("sources_used", []),
            processing_time=result.get("processing_time", 0),
            tokens_used=result.get("tokens_used", 0),
            created_at=timezone.now(),
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
            "relevant_documents_found": len(result.get("relevant_documents", [])),
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Unexpected error in chat: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        return Response(
            {"error": f"An unexpected error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
