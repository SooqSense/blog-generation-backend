import logging
from django.db import models
from rest_framework import status, permissions
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse

from management_app.blog_generator.models import BlogGeneral
from .services.authentication.api_key_auth import ExternalAPIKeyAuthentication, generate_api_key
from .serializers.external_blog_serializers import ExternalBlogSerializer
from .serializers.api_key_serializers import ApiKeyCreateRequestSerializer, ApiKeyCreateResponseSerializer
from management_app.authentication.services.access_control import require_organization_access, get_user_selected_organization

logger = logging.getLogger(__name__)

@extend_schema(
    request=ApiKeyCreateRequestSerializer,
    responses={
        201: OpenApiResponse(
            response=ApiKeyCreateResponseSerializer, 
            description="API Key generated successfully."
        ),
        400: OpenApiResponse(description="Invalid request data."),
        401: OpenApiResponse(description="Unauthorized - Session expired."),
        403: OpenApiResponse(description="Forbidden - Organization access required."),
    },
    description="Generate a new secure API Key for external integrations. The key is automatically tied to your active organization.",
)
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
@require_organization_access()
def generate_api_key_api(request):
    """
    Generate a new API Key for the user's currently selected organization.
    """
    try:
        serializer = ApiKeyCreateRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        name = serializer.validated_data.get('name')
        organization_name = get_user_selected_organization(request)

        if not organization_name:
            return Response({
                'error': 'No organization selected. Please select an organization context.'
            }, status=status.HTTP_400_BAD_REQUEST)

        raw_key, key_obj = generate_api_key(name=name, organization_name=organization_name)

        response_data = {
            "name": key_obj.name,
            "prefix": key_obj.prefix,
            "full_key": raw_key,
            "organization_name": key_obj.organization_name,
            "created_at": key_obj.created_at
        }

        return Response(response_data, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"API Key generation error: {str(e)}", exc_info=True)
        return Response({
            'error': 'Internal server error during key generation'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    responses={
        200: OpenApiResponse(
            response=ExternalBlogSerializer(many=True), 
            description="List of blogs for the organization."
        ),
        401: OpenApiResponse(
            description="Unauthorized - Invalid API Key."
        ),
    },
    description="External API to list all blogs for an organization using an API Key.",
)
@api_view(["GET"])
@authentication_classes([ExternalAPIKeyAuthentication])
@permission_classes([permissions.AllowAny])
def external_blog_list_api(request):
    """
    List all blogs for the organization associated with the API Key.
    """
    try:
        organization_name = getattr(request, 'organization_name', None)
        if not organization_name:
            return Response({
                'error': 'Organization context missing from API Key'
            }, status=status.HTTP_401_UNAUTHORIZED)

        blogs = BlogGeneral.objects.filter(
            organization_name=organization_name,
            is_published=True
        ).order_by('-created_at')

        serializer = ExternalBlogSerializer(blogs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"External API list error: {str(e)}", exc_info=True)
        return Response({
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    responses={
        200: OpenApiResponse(
            response=ExternalBlogSerializer, 
            description="Detailed blog content."
        ),
        404: OpenApiResponse(
            description="Blog not found."
        ),
    },
    description="External API to fetch a specific blog's details using an API Key.",
)
@api_view(["GET"])
@authentication_classes([ExternalAPIKeyAuthentication])
@permission_classes([permissions.AllowAny])
def external_blog_detail_api(request, blog_id):
    """
    Fetch a single blog detail by ID or slug.
    """
    try:
        organization_name = getattr(request, 'organization_name', None)
        
        query = models.Q(organization_name=organization_name, is_published=True)
        if str(blog_id).isdigit():
            query &= models.Q(id=blog_id)
        else:
            query &= models.Q(seo_slug=blog_id)

        blog = BlogGeneral.objects.filter(query).first()

        if not blog:
            return Response({
                'error': 'Blog post not found'
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = ExternalBlogSerializer(blog)
        return Response(serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"External API detail error: {str(e)}", exc_info=True)
        return Response({
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
