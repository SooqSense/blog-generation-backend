import json
import os
import sys
import re
from django.conf import settings
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiResponse
import logging

# Import models
from .models import BlogGeneral
from .serializers import (
    BlogRequestSerializer, BlogResponseSerializer, ErrorResponseSerializer,
    BlogListSerializer, BlogDetailSerializer, BlogDeleteSerializer
)

# Import organization access control
from management_app.authentication.services.access_control import require_organization_access, get_user_selected_organization

# Set up logging
logger = logging.getLogger(__name__)

# Import local service
from .service.blog_writing.blog_writer import BlogWriter


def convert_markdown_to_json(markdown_content):
    """
    Convert markdown content to a structured JSON format.
    This function parses markdown and creates a hierarchical structure.
    """
    if not markdown_content:
        return {}
    
    # Split content into lines
    lines = markdown_content.split('\n')
    
    # Initialize the structure
    structure = {
        'title': '',
        'sections': [],
        'metadata': {
            'word_count': len(markdown_content.split()),
            'line_count': len(lines)
        }
    }
    
    current_section = None
    current_subsection = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check for title (first H1)
        if line.startswith('# ') and not structure['title']:
            structure['title'] = line[2:].strip()
            continue
            
        # Check for main sections (H2)
        if line.startswith('## '):
            if current_section:
                structure['sections'].append(current_section)
            
            current_section = {
                'title': line[3:].strip(),
                'content': '',
                'subsections': [],
                'type': 'section'
            }
            current_subsection = None
            continue
            
        # Check for subsections (H3)
        if line.startswith('### '):
            if current_subsection:
                current_section['subsections'].append(current_subsection)
            
            current_subsection = {
                'title': line[4:].strip(),
                'content': '',
                'type': 'subsection'
            }
            continue
            
        # Add content to current section or subsection
        if current_subsection:
            current_subsection['content'] += line + '\n'
        elif current_section:
            current_section['content'] += line + '\n'
        else:
            # Content before any sections
            if not structure.get('introduction'):
                structure['introduction'] = line + '\n'
            else:
                structure['introduction'] += line + '\n'
    
    # Add the last section/subsection
    if current_subsection and current_section:
        current_section['subsections'].append(current_subsection)
    if current_section:
        structure['sections'].append(current_section)
    
    return structure


@extend_schema(
    request=BlogRequestSerializer,
    responses={
        200: OpenApiResponse(
            response=BlogResponseSerializer, description="Blog generated successfully."
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer, description="Bad Request - Invalid input."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error."
        ),
    },
    description="Generate a detailed blog post based on the given topic and optional parameters for customization. Set 'generate_image_prompts' to true (default) to include 5 section-specific images, or false for text-only blog content.",
)
@extend_schema(
    request=BlogRequestSerializer,
    responses={
        200: OpenApiResponse(
            response=BlogResponseSerializer, description="Blog generated successfully."
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer, description="Bad Request - Invalid input."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error."
        ),
    },
    description="Generate a blog post by specifying topic, blog_type, word count range, and optional image generation flag.",
)
@api_view(["POST"])
@require_organization_access()
def generate_blog_api(request):
    """
    Generate a blog using minimal input fields:
    - topic (required)
    - blog_type (optional, default='News')
    - length_min / length_max (optional)
    - generate_images (optional)
    """
    serializer = BlogRequestSerializer(data=request.data)
    if not serializer.is_valid():
        logger.warning(f"Invalid input for blog generation: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        topic = serializer.validated_data["topic"]
        blog_type = serializer.validated_data.get("blog_type", "News")
        length_min = serializer.validated_data.get("length_min", 800)
        length_max = serializer.validated_data.get("length_max", 1500)
        generate_images = serializer.validated_data.get("generate_images", True)

        logger.info(f"Generating {blog_type} blog on '{topic}' (words: {length_min}-{length_max}, images: {generate_images})")

        # Initialize BlogWriter with minimal params
        writer = BlogWriter(
            topic=topic,
            blog_type=blog_type,
            length_min=length_min,
            length_max=length_max,
            generate_images=generate_images,
        )

        result = writer.generate_blog()
        blog_content = result.get("content", "")
        structured_content = convert_markdown_to_json(blog_content)

        clean_blog_content = blog_content.strip()
        image_urls = result.get("images", [])
        research_sources = result.get("sources", [])

        # Save blog
        organization_name = get_user_selected_organization(request)
        organization_id = getattr(request.user, "organization_id", None)

        blog = BlogGeneral.objects.create(
            user_id=request.user.id,
            username=request.user.username,
            email=request.user.email,
            topic=topic,
            content=clean_blog_content,
            image_urls=image_urls,
            organization_id=organization_id,
            organization_name=organization_name,
            created_at=timezone.now(),
        )

        logger.info(f"✅ Saved blog '{topic}' with {len(image_urls)} images and {len(research_sources)} sources")

        response_data = {
            "status": "success",
            "message": f"{blog_type} blog generated successfully.",
            "topic": topic,
            "blog_type": blog_type,
            "length_min": length_min,
            "length_max": length_max,
            "generate_images": generate_images,
            "image_urls": image_urls,
            "images_count": len(image_urls),
            "research_sources": research_sources,
            "sources_count": len(research_sources),
            "content": structured_content,
            "raw_content": clean_blog_content,
        }

        response_serializer = BlogResponseSerializer(data=response_data)
        if response_serializer.is_valid():
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        else:
            logger.error(f"Serialization error: {response_serializer.errors}")
            return Response({"error": "Response serialization failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# List and Management Views
@extend_schema(
    responses={
        200: OpenApiResponse(
            response=BlogListSerializer(many=True),
            description="Blog posts retrieved successfully."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error."
        ),
    },
    description="Get list of all blog posts for the authenticated user's organization.",
)
@api_view(["GET"])
@require_organization_access()
def list_blog_posts_api(request):
    """List all blog posts for the user's organization."""
    try:
        user = request.user
        organization_name = get_user_selected_organization(request)
        
        # Filter by organization
        blog_posts = BlogGeneral.objects.filter(
            organization_name=organization_name
        ).order_by('-created_at')
        
        serializer = BlogListSerializer(blog_posts, many=True)
        
        return Response({
            'success': True,
            'message': f'Retrieved {len(blog_posts)} blog posts',
            'data': serializer.data,
            'count': len(blog_posts)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error listing blog posts: {str(e)}")
        return Response({
            'error': 'Failed to retrieve blog posts'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    responses={
        200: OpenApiResponse(
            response=BlogDetailSerializer,
            description="Blog post details retrieved successfully."
        ),
        404: OpenApiResponse(
            response=ErrorResponseSerializer, description="Blog post not found."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error."
        ),
    },
    description="Get detailed information about a specific blog post.",
)
@api_view(["GET"])
@require_organization_access()
def get_blog_post_api(request, blog_id):
    """Get detailed information about a specific blog post."""
    try:
        user = request.user
        organization_name = get_user_selected_organization(request)
        
        # Get blog post with organization filter
        try:
            blog_post = BlogGeneral.objects.get(
                id=blog_id,
                organization_name=organization_name
            )
        except BlogGeneral.DoesNotExist:
            return Response({
                'error': 'Blog post not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = BlogDetailSerializer(blog_post)
        
        return Response({
            'success': True,
            'message': 'Blog post retrieved successfully',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error retrieving blog post {blog_id}: {str(e)}")
        return Response({
            'error': 'Failed to retrieve blog post'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    responses={
        200: OpenApiResponse(
            response=BlogDeleteSerializer,
            description="Blog post(s) deleted successfully."
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer, description="Bad Request."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error."
        ),
    },
    description="Delete one or more blog posts. Provide blog_id for single deletion or blog_ids array for bulk deletion.",
)
@api_view(["DELETE"])
@require_organization_access()
def delete_blog_posts_api(request):
    """Delete one or more blog posts."""
    try:
        user = request.user
        organization_name = get_user_selected_organization(request)
        
        # Get blog IDs from request
        blog_id = request.data.get('blog_id')
        blog_ids = request.data.get('blog_ids', [])
        
        if blog_id:
            blog_ids = [blog_id]
        elif not blog_ids:
            return Response({
                'error': 'Either blog_id or blog_ids must be provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Filter by organization and delete
        deleted_count = 0
        for blog_id in blog_ids:
            try:
                blog_post = BlogGeneral.objects.get(
                    id=blog_id,
                    organization_name=organization_name
                )
                blog_post.delete()
                deleted_count += 1
            except BlogGeneral.DoesNotExist:
                continue
        
        return Response({
            'success': True,
            'message': f'Successfully deleted {deleted_count} blog post(s)',
            'deleted_count': deleted_count
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error deleting blog posts: {str(e)}")
        return Response({
            'error': 'Failed to delete blog posts'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

