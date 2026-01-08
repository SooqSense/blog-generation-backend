from rest_framework import serializers

class ApiKeyCreateRequestSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=255, 
        required=True, 
        help_text="A descriptive name for the API key (e.g., 'WordPress Integration')"
    )

class ApiKeyCreateResponseSerializer(serializers.Serializer):
    name = serializers.CharField()
    prefix = serializers.CharField()
    full_key = serializers.CharField(help_text="The full API key. This is ONLY shown once upon creation.")
    organization_name = serializers.CharField()
    created_at = serializers.DateTimeField()
    message = serializers.CharField(default="API key generated successfully. Please store it securely as it will not be shown again.")
