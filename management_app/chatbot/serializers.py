from rest_framework import serializers


class ChatRequestSerializer(serializers.Serializer):
    """Serializer for chat request"""
    query = serializers.CharField(
        required=True,
        help_text="User's question or query about their project portfolio documents.",
        style={'base_template': 'textarea.html'}
    )
    session_id = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Chat session ID. If not provided, a new session will be created."
    )


class ChatResponseSerializer(serializers.Serializer):
    """Serializer for chat response"""
    status = serializers.CharField()
    message = serializers.CharField()
    session_id = serializers.CharField()
    is_new_session = serializers.BooleanField()
    response = serializers.CharField()
    processing_time = serializers.FloatField()
    tokens_used = serializers.IntegerField()
    model_used = serializers.CharField()
    total_messages = serializers.IntegerField()
    documents_found = serializers.IntegerField()


class ChatSessionSerializer(serializers.Serializer):
    """Serializer for chat session"""
    session_id = serializers.CharField()
    title = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    message_count = serializers.IntegerField()
    total_messages = serializers.IntegerField()


class UserSessionsResponseSerializer(serializers.Serializer):
    """Serializer for user sessions response"""
    status = serializers.CharField()
    message = serializers.CharField()
    sessions = ChatSessionSerializer(many=True)
    total_sessions = serializers.IntegerField()
