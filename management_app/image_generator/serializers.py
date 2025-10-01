from rest_framework import serializers


class ImageGenerationRequestSerializer(serializers.Serializer):
    prompt = serializers.CharField(
        required=False, 
        allow_blank=True,
        help_text="The main prompt for professional, cinematic-style image generation. Optional."
    )
    keywords = serializers.CharField(
        required=False, 
        allow_blank=True, 
        help_text="Optional comma-separated keywords to enhance the image prompt for better visual relevance."
    )
    count = serializers.IntegerField(
        required=False,
        default=1,
        min_value=1,
        max_value=10,
        help_text="Number of professional images to generate (1-10). Default is 1."
    )
    model = serializers.ChoiceField(
        choices=[
            ("flux_dev", "FLUX Dev - High Quality (28 steps)"),
            ("flux_schnell", "FLUX Schnell - Fast Generation (4 steps)")
        ],
        required=False,
        default="flux_dev",
        help_text="FLUX AI model to use. 'flux_dev' for high-quality detailed images with 28 inference steps, 'flux_schnell' for faster generation with 4 steps. Default is 'flux_dev'."
    )

    # Add validation to ensure at least one field is provided
    def validate(self, data):
        prompt = data.get('prompt')
        keywords = data.get('keywords')
        if not prompt and not keywords:
            raise serializers.ValidationError("Either 'prompt' or 'keywords' (or both) must be provided.")
        if (prompt and not prompt.strip()) and (keywords and not keywords.strip()):
             raise serializers.ValidationError("Provided prompt or keywords cannot be empty or just whitespace.")
        return data


class GeneratedImageSerializer(serializers.Serializer):
    image_url = serializers.CharField()
    enhanced_prompt = serializers.CharField()
    image_number = serializers.IntegerField()


class ImageGenerationResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    prompt_used = serializers.CharField()
    count = serializers.IntegerField()
    model = serializers.CharField(help_text="FLUX AI model used ('flux_dev' or 'flux_schnell')")
    generation_method = serializers.CharField(help_text="Generation method used (deprecated, use 'model' field)")
    image_style = serializers.CharField(help_text="Style of generated images (e.g., 'FLUX Dev', 'FLUX Schnell')")
    images = serializers.ListField(child=GeneratedImageSerializer())
    total_generated = serializers.IntegerField()
    failed_generations = serializers.IntegerField()
    database_record_id = serializers.IntegerField(help_text="Database record ID for the image generation session")
    stored_image_urls = serializers.ListField(child=serializers.CharField(), help_text="All image URLs stored in database")
    stored_images_count = serializers.IntegerField(help_text="Number of images stored in database")


class ImageEditingRequestSerializer(serializers.Serializer):
    prompt = serializers.CharField(
        max_length=1000,
        help_text="The editing instruction/prompt describing what changes to make to the image."
    )
    keywords = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text="Optional array of keywords to guide the editing process."
    )
    image = serializers.ImageField(
        help_text="The image file to be edited. Supported formats: JPEG, PNG, WebP. Maximum size: 10MB.",
        allow_empty_file=False
    )
    
    class Meta:
        swagger_schema_fields = {
            'type': 'object',
            'properties': {
                'prompt': {
                    'type': 'string',
                    'maxLength': 1000,
                    'description': 'The editing instruction/prompt describing what changes to make to the image.'
                },
                'keywords': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': 'Optional array of keywords to guide the editing process.',
                    'default': []
                },
                'image': {
                    'type': 'string',
                    'format': 'binary',
                    'description': 'The image file to edit. Supported formats: JPEG, PNG, WebP. Maximum size: 10MB.'
                }
            },
            'required': ['prompt', 'image']
        }


class ImageEditingResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    prompt_used = serializers.CharField(help_text="The original editing prompt provided")
    enhanced_prompt = serializers.CharField(help_text="The AI-optimized editing prompt used")
    keywords = serializers.CharField(required=False, allow_blank=True, help_text="Keywords used in the editing")
    original_image_size = serializers.IntegerField(help_text="Size of the original uploaded image in bytes")
    edited_image_url = serializers.URLField(help_text="URL of the edited result image")
    database_record_id = serializers.IntegerField(help_text="Database record ID for the editing session")
    edit_status = serializers.CharField(help_text="Status of the editing process")
    processing_time = serializers.FloatField(required=False, help_text="Time taken to process the editing in seconds")
    created_at = serializers.DateTimeField(help_text="When the editing was performed")


class ErrorResponseSerializer(serializers.Serializer):
    error = serializers.CharField()
