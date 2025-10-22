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
from .serializers import BlogRequestSerializer, BlogResponseSerializer, ErrorResponseSerializer

# Import organization access control
from management_app.authentication.services.access_control import require_sooqsense_organization

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
@api_view(["POST"])
@require_sooqsense_organization
def generate_blog_api(request):
    """
    Generate a detailed blog post from a given topic and optional parameters.
    Input is a JSON object with "topic" (required) and various optional parameters
    for customizing the blog format and style.
    """
    # Validate request data using the serializer
    serializer = BlogRequestSerializer(data=request.data)
    if serializer.is_valid():
        topic = serializer.validated_data["topic"]
        keywords = serializer.validated_data.get("keywords", [])
        sample_blog_url = serializer.validated_data.get("sample_blog_url", "")
        blog_type = serializer.validated_data.get("blog_type", "News")
        length_min = serializer.validated_data.get("length_min", 800)
        length_max = serializer.validated_data.get("length_max", 1500)
        introduction = serializer.validated_data.get("introduction", True)
        table_of_content = serializer.validated_data.get("table_of_content", False)
        faq = serializer.validated_data.get("faq", False)
        cta = serializer.validated_data.get("cta", False)
        conclusion = serializer.validated_data.get("conclusion", True)
        target_audience = serializer.validated_data.get("target_audience", [])
        generate_image_prompts = serializer.validated_data.get("generate_image_prompts", True)
        generate_images = serializer.validated_data.get("generate_images", True)

        try:
            logger.info(
                f"Starting blog generation for topic: '{topic}' with blog type: '{blog_type}' and research-based workflow"
            )

            blog_writer_instance = BlogWriter(
                topic=topic,
                keywords=keywords,
                blog_type=blog_type,
                length_min=length_min,
                length_max=length_max,
                introduction=introduction,
                table_of_content=table_of_content,
                faq=faq,
                cta=cta,
                conclusion=conclusion,
                target_audience=target_audience,
                sample_blog_url=sample_blog_url if sample_blog_url else None,
                generate_image_prompts=generate_image_prompts,
                generate_images=generate_images,
            )

            # Generate the blog content without saving to file
            blog_content = blog_writer_instance.generate_blog(
                topic=topic,
                sample_blog_url=sample_blog_url if sample_blog_url else None
            )

            if not blog_content:
                logger.error(f"Blog generation failed for topic: '{topic}'")
                return Response(
                    {"error": "Blog generation failed."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            logger.info(f"Successfully generated blog on '{topic}'")
            
            # Convert markdown content to JSON structure
            structured_content = convert_markdown_to_json(blog_content)

            # Get generated image prompts (legacy support)
            image_prompts = getattr(blog_writer_instance, 'image_prompts', [])
            prompts_count = len(image_prompts)
            
            # Get section-specific image data
            section_images = getattr(blog_writer_instance, 'section_images', {})
            image_urls = getattr(blog_writer_instance, 'image_urls', [])
            images_count = len([img for img in section_images.values() if img.get('image_url')])
            
            # Debug logging for images
            logger.info(f"Section-specific images generated: {images_count}")
            logger.info(f"S3 URLs stored: {len(image_urls)}")
            for section, img_data in section_images.items():
                if img_data.get('image_url'):
                    logger.info(f"Section '{section}' image: {img_data['image_url']}")
            
            # Get research sources
            research_sources = getattr(blog_writer_instance, 'research_sources', [])
            sources_count = len(research_sources)
            
            # Clean and properly format the blog content for proper markdown rendering
            clean_blog_content = blog_content
            if isinstance(clean_blog_content, str):
                # Handle various escape sequences that might come from CrewAI or JSON serialization
                # First handle double newlines to preserve paragraph breaks
                clean_blog_content = clean_blog_content.replace('\\n\\n', '\n\n')
                # Then handle single newlines
                clean_blog_content = clean_blog_content.replace('\\n', '\n')
                # Handle tabs
                clean_blog_content = clean_blog_content.replace('\\t', '\t')
                # Handle other common escape sequences
                clean_blog_content = clean_blog_content.replace('\\r', '\r')
                # Handle escaped quotes and backslashes if they exist
                clean_blog_content = clean_blog_content.replace('\\"', '"')
                clean_blog_content = clean_blog_content.replace("\\'", "'")
                # Remove any remaining double backslashes
                clean_blog_content = clean_blog_content.replace('\\\\', '\\')
                # Strip leading/trailing whitespace
                clean_blog_content = clean_blog_content.strip()
                
                # Additional cleaning: ensure proper markdown structure
                # Split by lines and clean each line
                lines = clean_blog_content.split('\n')
                cleaned_lines = []
                for line in lines:
                    # Remove any remaining escape characters that might affect rendering
                    cleaned_line = line.replace('\\n', '').replace('\\t', '\t').strip()
                    cleaned_lines.append(cleaned_line)
                
                # Rejoin with proper newlines
                clean_blog_content = '\n'.join(cleaned_lines)
                
                # Ensure proper spacing around headers and sections
                # Fix spacing around headers
                clean_blog_content = re.sub(r'\n(#{1,6}\s)', r'\n\n\1', clean_blog_content)
                clean_blog_content = re.sub(r'(#{1,6}[^\n]*)\n([^\n#])', r'\1\n\n\2', clean_blog_content)
                # Remove excessive empty lines (more than 2 consecutive)
                clean_blog_content = re.sub(r'\n{3,}', '\n\n', clean_blog_content)
                # Final strip
                clean_blog_content = clean_blog_content.strip()
            
            # Save to database with section-specific image URLs
            blog = BlogGeneral(
                user_id=request.user.id,
                username=request.user.username,
                email=request.user.email,
                topic=topic,
                content=clean_blog_content,
                sample_blog_url=sample_blog_url if sample_blog_url else None,
                image_prompts=image_prompts,
                prompts_count=prompts_count,
                image_urls=image_urls,
                created_at=timezone.now(),
            )
            blog.save()
            logger.info(f"Saved blog to database with ID: {blog.id} with {images_count} section images and {sources_count} research sources")

            response_data = {
                "status": "success",
                "message": f"Research-based {blog_type.lower()} blog generated successfully with {images_count} section-specific images!",
                "topic": topic,
                "keywords": keywords,
                "sample_blog_url": sample_blog_url,
                "sample_blog_analysis": getattr(blog_writer_instance, 'sample_blog_analysis', None) if hasattr(blog_writer_instance, 'sample_blog_analysis') else None,
                "blog_type": blog_type,
                "length_min": length_min,
                "length_max": length_max,
                "introduction": introduction,
                "table_of_content": table_of_content,
                "faq": faq,
                "cta": cta,
                "conclusion": conclusion,
                "target_audience": target_audience,
                "generate_image_prompts": generate_image_prompts,
                "generate_images": generate_images,
                "image_prompts": image_prompts,
                "prompts_count": prompts_count,
                "image_urls": image_urls,
                "section_images": section_images,
                "images_count": images_count,
                "research_sources": research_sources,
                "sources_count": sources_count,
                "content": structured_content,
                "raw_content": clean_blog_content,
            }

            # Serialize the successful response
            response_serializer = BlogResponseSerializer(data=response_data)
            if response_serializer.is_valid():
                return Response(response_serializer.data, status=status.HTTP_200_OK)
            else:
                logger.error(
                    f"Error serializing successful response for blog: {response_serializer.errors}"
                )
                return Response(
                    {"error": "Internal server error during response serialization."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(
                f"Unexpected error in blog generation: {type(e).__name__} - {e}"
            )
            import traceback
            traceback.print_exc()
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    else:
        # If serializer validation fails
        logger.warning(f"Invalid input for blog generation: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)