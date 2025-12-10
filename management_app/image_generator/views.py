import os
import sys
from django.conf import settings
from django.utils import timezone
from rest_framework.decorators import api_view, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema, OpenApiResponse
import logging

# Import models
from .models import ImageGeneration, ImageEditing
from .serializers import (
    ImageGenerationRequestSerializer, 
    ImageGenerationResponseSerializer,
    ImageEditingRequestSerializer,
    ImageEditingResponseSerializer,
    ErrorResponseSerializer
)

# Set up logging
# Import organization access control
from management_app.authentication.services.access_control import require_organization_access

logger = logging.getLogger(__name__)

# Import local services
from .service.image_generator import generate_image
from .service.edit_images import edit_image_with_flux, convert_image_to_base64


@extend_schema(
    request=ImageGenerationRequestSerializer,
    responses={
        200: OpenApiResponse(
            response=ImageGenerationResponseSerializer,
            description="Images generated successfully.",
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer, description="Bad Request - Invalid input."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="Internal Server Error / Image Generation Failed.",
        ),
    },
    description="Generate one or more professional images using FLUX AI generation models. Choose between FLUX Dev (28 steps, high quality) or FLUX Schnell (4 steps, fast generation) models for detailed, artistic image generation.",
)
@api_view(["POST"])
@require_organization_access()
def generate_image_api(request):
    """
    Generate one or more professional images using FLUX AI generation models.
    
    Supports two FLUX AI models:
    - 'flux_dev': FLUX Dev - High quality detailed images with 28 inference steps
    - 'flux_schnell': FLUX Schnell - Fast generation with 4 inference steps
    
    Both models use AI-optimized prompts tailored to FLUX AI's strengths.
    """
    serializer = ImageGenerationRequestSerializer(data=request.data)
    if not serializer.is_valid():
        logger.warning(f"Invalid input for image generation: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    prompt = serializer.validated_data.get("prompt", "")
    keywords = serializer.validated_data.get("keywords", "")
    count = serializer.validated_data.get("count", 1)
    model = serializer.validated_data.get("model", "flux_dev")
    
    # Map model to generation method for backward compatibility
    generation_method = "flux" if model == "flux_dev" else "flux_schnell"
    
    # Set default values
    image_type = "content"  # Default to content type for professional images
    size = "1920x1080"

    try:
        logger.info(f"Starting image generation with model: {model}, count: {count}")
        
        # Generate images using the service
        images_data, total_generated, failed_generations = generate_image(
            prompt=prompt,
            keywords=keywords,
            count=count,
            generation_method=generation_method,
            image_type=image_type,
            size=size
        )
        
        if total_generated == 0:
            error_msg = f"Failed to generate any images. {failed_generations} failed attempts."
            logger.error(error_msg)
            return Response(
                {"error": error_msg},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info(f"Successfully generated {total_generated} images")

        # Get organization information
        from management_app.authentication.services.access_control import get_user_selected_organization
        organization_name = get_user_selected_organization(request)
        organization_id = getattr(request.user, 'organization_id', None)
        
        # Save to database
        image_generation = ImageGeneration(
            user_id=request.user.id,
            username=request.user.username,
            email=request.user.email,
            prompt=prompt,
            image_urls=[img["image_url"] for img in images_data],
            images_count=total_generated,
            enhanced_prompts=[img["enhanced_prompt"] for img in images_data],
            generation_method=generation_method,
            image_style=model,
            organization_id=organization_id,
            organization_name=organization_name,
            created_at=timezone.now(),
        )
        image_generation.save()
        logger.info(f"Saved image generation to database with ID: {image_generation.id}")

        response_data = {
            "status": "success",
            "message": f"Successfully generated {total_generated} professional images using {model}!",
            "prompt_used": prompt,
            "count": count,
            "model": model,
            "generation_method": generation_method,
            "image_style": model,
            "images": images_data,
            "total_generated": total_generated,
            "failed_generations": failed_generations,
            "database_record_id": image_generation.id,
            "stored_image_urls": [img["image_url"] for img in images_data],
            "stored_images_count": total_generated,
        }

        # Serialize the successful response
        response_serializer = ImageGenerationResponseSerializer(data=response_data)
        if response_serializer.is_valid():
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        else:
            logger.error(f"Error serializing image generation response: {response_serializer.errors}")
            return Response(
                {"error": "Internal server error during response serialization."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    except Exception as e:
        logger.error(f"Unexpected error in image generation: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        return Response(
            {"error": f"An unexpected error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    request={
        'multipart/form-data': {
            'type': 'object',
            'properties': {
                'prompt': {
                    'type': 'string',
                    'description': 'The editing instruction/prompt describing what changes to make to the image.',
                    'maxLength': 1000
                },
                'keywords': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': 'Optional keywords to guide the editing process.',
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
    },
    responses={
        200: OpenApiResponse(
            response=ImageEditingResponseSerializer,
            description="Image edited successfully using FLUX AI.",
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer, description="Bad Request - Invalid input or image format."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="Internal Server Error / Image Editing Failed.",
        ),
    },
    description="Edit an uploaded image using FLUX AI based on the provided prompt and optional keywords. Upload an image file and provide editing instructions to transform the image using advanced AI editing capabilities.",
)
@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
@require_organization_access()
def edit_image_api(request):
    """Edit an uploaded image using FLUX AI based on the provided prompt and optional keywords."""
    try:
        # Validate request data using the serializer
        serializer = ImageEditingRequestSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"Invalid input for image editing: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        prompt = serializer.validated_data["prompt"]
        keywords = serializer.validated_data.get("keywords", [])
        image_file = serializer.validated_data["image"]

        logger.info(f"Starting image editing with prompt: {prompt[:50]}...")

        # Convert image to base64
        image_base64 = convert_image_to_base64(image_file)
        
        # Edit image using the service
        success, edited_image_url, enhanced_prompt, error_msg = edit_image_with_flux(
            prompt=prompt,
            keywords=keywords,
            image_base64=image_base64
        )
        
        if not success:
            logger.error(f"Image editing failed: {error_msg}")
            return Response(
                {"error": error_msg},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info("Successfully edited image")

        # Get organization information
        from management_app.authentication.services.access_control import get_user_selected_organization
        organization_name = get_user_selected_organization(request)
        organization_id = getattr(request.user, 'organization_id', None)
        
        # Save to database
        image_editing = ImageEditing(
            user_id=request.user.id,
            username=request.user.username,
            email=request.user.email,
            prompt=prompt,
            keywords=", ".join(keywords) if keywords else "",
            uploaded_image=image_base64,
            image_url=edited_image_url,
            enhanced_prompt=enhanced_prompt,
            edit_status="success",
            organization_id=organization_id,
            organization_name=organization_name,
            created_at=timezone.now(),
        )
        image_editing.save()
        logger.info(f"Saved image editing to database with ID: {image_editing.id}")

        response_data = {
            "status": "success",
            "message": "Image edited successfully using FLUX AI!",
            "prompt_used": prompt,
            "enhanced_prompt": enhanced_prompt,
            "keywords": ", ".join(keywords) if keywords else "",
            "original_image_size": image_file.size,
            "edited_image_url": edited_image_url,
            "database_record_id": image_editing.id,
            "edit_status": "success",
            "processing_time": 0,  # Could be calculated if needed
            "created_at": image_editing.created_at,
        }

        # Serialize the successful response
        response_serializer = ImageEditingResponseSerializer(data=response_data)
        if response_serializer.is_valid():
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        else:
            logger.error(f"Error serializing image editing response: {response_serializer.errors}")
            return Response(
                {"error": "Internal server error during response serialization."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    except Exception as e:
        logger.error(f"Unexpected error in image editing: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        return Response(
            {"error": f"An unexpected error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    description="List all generated images for the authenticated user's organization",
    responses={
        200: OpenApiResponse(description="List of generated images"),
        401: OpenApiResponse(description="Authentication required"),
        403: OpenApiResponse(description="Organization access required"),
    },
)
@api_view(['GET'])
@require_organization_access()
def list_images_api(request):
    """List all generated images for the user's organization"""
    try:
        # Get images for the user's organization
        images = ImageGeneration.objects.filter(
            organization_id=request.user.organization_id
        ).order_by('-created_at')
        
        # Serialize the data
        image_data = []
        for image in images:
            image_data.append({
                'id': image.id,
                'title': image.prompt[:50] + "..." if len(image.prompt) > 50 else image.prompt,
                'prompt': image.prompt,
                'image_urls': image.image_urls if image.image_urls else [],
                'images_count': image.images_count,
                'generation_method': image.generation_method,
                'image_style': image.image_style,
                'created_at': image.created_at.isoformat(),
                'username': request.user.username,
                'organization_name': request.user.organization_name,
            })
        
        return Response({
            'success': True,
            'data': image_data,
            'message': f'Found {len(image_data)} images'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error listing images: {str(e)}")
        return Response(
            {"error": f"Failed to list images: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'ids': {
                    'type': 'array',
                    'items': {'type': 'integer'},
                    'description': 'Array of image IDs to delete',
                    'example': [1, 2, 3]
                }
            },
            'required': ['ids']
        }
    },
    responses={
        200: OpenApiResponse(
            description="Images deleted successfully",
            examples={
                'application/json': {
                    'success': True,
                    'message': 'Successfully deleted 3 images',
                    'deleted_count': 3
                }
            }
        ),
        400: OpenApiResponse(
            description="Invalid request data",
            examples={
                'application/json': {
                    'error': 'No image IDs provided'
                }
            }
        ),
        401: OpenApiResponse(description="Authentication required"),
        403: OpenApiResponse(description="Organization access required"),
    },
    description="Delete multiple images by providing an array of image IDs. Only images belonging to the user's organization can be deleted."
)
@api_view(['DELETE'])
@require_organization_access()
def delete_images_api(request):
    """Delete multiple images by IDs"""
    try:
        image_ids = request.data.get('ids', [])
        
        if not image_ids:
            return Response(
                {"error": "No image IDs provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        # Get images for the user's organization
        images = ImageGeneration.objects.filter(
            id__in=image_ids,
            organization_id=request.user.organization_id
        )
        
        deleted_count = images.count()
        images.delete()
        
        return Response({
            'success': True,
            'message': f'Successfully deleted {deleted_count} images',
            'deleted_count': deleted_count
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error deleting images: {str(e)}")
        return Response(
            {"error": f"Failed to delete images: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

