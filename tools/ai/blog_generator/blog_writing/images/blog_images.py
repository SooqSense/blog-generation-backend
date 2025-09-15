import os
from datetime import datetime
from ..prompts.prompts import BlogWriterPrompts
from ....image_generation.image_generator import generate_image_with_flux, generate_image_with_flux_schnell


def extract_blog_sections_for_images(blog_content):
    """
    Extract relevant sections from blog content for image generation context
    
    Args:
        blog_content (str): The full blog content in markdown
        
    Returns:
        dict: Dictionary with section names as keys and content as values
    """
    sections = {}
    
    # Split content by markdown headers
    lines = blog_content.split('\n')
    current_section = None
    current_content = []
    
    for line in lines:
        line = line.strip()
        if line.startswith('## '):
            # Save previous section
            if current_section and current_content:
                sections[current_section] = '\n'.join(current_content).strip()
            
            # Start new section
            current_section = line[3:].lower().strip()
            current_content = []
        elif line.startswith('# '):
            # This is the title, save as introduction context
            if not current_section:
                current_section = 'introduction'
                current_content = [line[2:].strip()]
        else:
            if current_section:
                current_content.append(line)
    
    # Save the last section
    if current_section and current_content:
        sections[current_section] = '\n'.join(current_content).strip()
    
    # Map section names to our standardized keys
    section_mapping = {
        'introduction': 'introduction',
        'main content': 'main_content',
        'list': 'main_content',
        'current trends': 'main_content',
        'key developments and trends': 'main_content',
        'supporting details': 'supporting_details',
        'additional context': 'supporting_details',
        'evidence and data sources': 'evidence',
        'evidence (data sources)': 'evidence',
        'data sources': 'evidence',
        'conclusion': 'conclusion'
    }
    
    mapped_sections = {}
    for section_name, content in sections.items():
        for key, mapped_key in section_mapping.items():
            if key in section_name:
                mapped_sections[mapped_key] = content
                break
    
    return mapped_sections


def generate_section_image_prompts_only(topic, blog_type, blog_content):
    """
    Generate only image prompts for specific blog sections without generating actual images
    
    Args:
        topic (str): The blog topic
        blog_type (str): The type of blog (News, Comparison, etc.)
        blog_content (str): The full blog content in markdown
        
    Returns:
        dict: Dictionary with section names as keys and prompt data as values
        {
            'banner': {'prompt': 'prompt', 'section': 'banner'},
            'main_content': {'prompt': 'prompt', 'section': 'main_content'},
            ...
        }
    """
    # Extract sections from blog content for context
    content_sections = extract_blog_sections_for_images(blog_content)
    
    # Get section-specific prompts
    section_prompts = BlogWriterPrompts.get_section_image_prompts(topic, blog_type, content_sections)
    
    # Section order for prompt generation
    sections = ['banner', 'main_content', 'supporting_details', 'evidence', 'conclusion']
    
    generated_prompts = {}
    
    for section in sections:
        prompt = section_prompts.get(section, f"Professional image for {section} section about {topic}")
        generated_prompts[section] = {
            'prompt': prompt,
            'enhanced_prompt': prompt,  # Same as prompt since no AI optimization without actual generation
            'section': section,
            'image_url': None,  # No image generated
            'generation_method': None
        }
        print(f"Generated prompt for {section}: {prompt[:100]}...")
    
    return generated_prompts


def generate_section_specific_images(topic, blog_type, blog_content, generation_method="flux", output_dir="blog_images"):
    """
    Generate images for specific blog sections using FLUX AI models via fal.ai and upload to S3
    
    Args:
        topic (str): The blog topic
        blog_type (str): The type of blog (News, Comparison, etc.)
        blog_content (str): The full blog content in markdown
        generation_method (str): Generation method to use ("flux" or "flux_schnell")
        output_dir (str): Directory prefix for S3 storage
        
    Returns:
        dict: Dictionary with section names as keys and image data as values
        {
            'banner': {'image_url': 'url', 'prompt': 'prompt'},
            'main_content': {'image_url': 'url', 'prompt': 'prompt'},
            ...
        }
    """
    # Extract sections from blog content for context
    content_sections = extract_blog_sections_for_images(blog_content)
    
    # Get section-specific prompts
    section_prompts = BlogWriterPrompts.get_section_image_prompts(topic, blog_type, content_sections)
    
    # Section order for image generation
    sections = ['banner', 'main_content', 'supporting_details', 'evidence', 'conclusion']
    
    generated_images = {}
    
    for section in sections:
        try:
            print(f"Generating {section} image for blog topic: {topic}")
            
            # Get the prompt for this section
            prompt = section_prompts.get(section, f"Professional image for {section} section about {topic}")
            
            # Generate image using FLUX AI models via fal.ai
            if generation_method == "flux_schnell":
                images_data, total_generated, failed_generations = generate_image_with_flux_schnell(
                    prompt=prompt,
                    size="1024x1024",
                    output_dir=f"{output_dir}/{section}",
                    topic=topic,
                    keywords=None,
                    image_type=section,
                    count=1
                )
            else:  # flux (default)
                images_data, total_generated, failed_generations = generate_image_with_flux(
                    prompt=prompt,
                    size="1024x1024",
                    output_dir=f"{output_dir}/{section}",
                    topic=topic,
                    keywords=None,
                    image_type=section,
                    count=1
                )
            
            # Store the result
            if images_data and len(images_data) > 0:
                generated_images[section] = {
                    'image_url': images_data[0]['image_url'],
                    'prompt': prompt,
                    'enhanced_prompt': images_data[0].get('enhanced_prompt', prompt),
                    'generation_method': generation_method,
                    'section': section
                }
                print(f"Successfully generated {section} image: {images_data[0]['image_url']}")
            else:
                print(f"Failed to generate {section} image")
                generated_images[section] = {
                    'image_url': None,
                    'prompt': prompt,
                    'enhanced_prompt': prompt,
                    'generation_method': generation_method,
                    'section': section,
                    'error': 'Image generation failed'
                }
                
        except Exception as e:
            print(f"Error generating {section} image: {str(e)}")
            generated_images[section] = {
                'image_url': None,
                'prompt': section_prompts.get(section, f"Professional image for {section} section about {topic}"),
                'enhanced_prompt': None,
                'generation_method': generation_method,
                'section': section,
                'error': str(e)
            }
    
    return generated_images


def embed_images_in_blog_content(blog_content, section_images):
    """
    Embed image URLs into the blog content at the END of their respective sections
    
    CRITICAL: Images must be placed at the END of section content, NOT immediately after headers
    
    Args:
        blog_content (str): The original blog content in markdown
        section_images (dict): Dictionary with section names and their image data
        
    Returns:
        str: Updated blog content with embedded images
    """
    # Create section mapping for embedding - CRITICAL: Images go at END of sections
    section_headers = {
        'banner': '# ',  # After the main title content
        'main_content': ['## Main Content', '## List', '## Current Trends', '## Key Developments and Trends'],  # After ALL main content  
        'supporting_details': ['## Supporting Details', '## Supporting Details:', '## Additional Context', '## Supporting Information'],  # CRITICAL: At END of Supporting Details section, NOT after header
        'evidence': ['## Evidence and Data Sources', '## Evidence (Data Sources)', '## Data Sources', '## Evidence', '## Sources and Methodology'],
        'conclusion': ['## Conclusion']
    }
    
    # CRITICAL REWRITE: Completely new approach for accurate section-end placement
    lines = blog_content.split('\n')
    
    # Step 1: Find all section headers and their positions
    section_positions = {}
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        for section, headers in section_headers.items():
            if section not in section_images:
                continue
                
            if isinstance(headers, list):
                header_matches = any(line_stripped.startswith(header) for header in headers)
            else:
                header_matches = line_stripped.startswith(headers)
                
            if header_matches:
                section_positions[section] = i
                print(f"CRITICAL: Found {section} header at line {i}: {line_stripped[:50]}")
                break
    
    # Step 2: Process content and insert images at section ends
    result_lines = []
    processed_sections = set()
    
    for i, line in enumerate(lines):
        result_lines.append(line)
        
        # Check if we need to insert an image after this line
        for section, header_pos in section_positions.items():
            if section in processed_sections or section not in section_images:
                continue
                
            # Determine if this is the end of the section
            is_section_end = False
            
            # We're at section end if:
            # 1. Next line is another ## header, OR
            # 2. We're at the very last line of content
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line.startswith('##') and i > header_pos:
                    is_section_end = True
            else:
                # Last line of content - check if we're in this section
                if i > header_pos:
                    is_section_end = True
            
            if is_section_end:
                image_data = section_images[section]
                image_url = image_data.get('image_url')
                
                if image_url:
                    result_lines.append('')
                    result_lines.append(f'![{section.replace("_", " ").title()} Image]({image_url})')
                    result_lines.append('')
                    processed_sections.add(section)
                    print(f"CRITICAL SUCCESS: Placed {section} image at END of section after line {i}")
    
    return '\n'.join(result_lines)


def get_section_image_urls_list(section_images):
    """
    Extract list of image URLs from section images data for database storage
    
    Args:
        section_images (dict): Dictionary with section names and their image data
        
    Returns:
        list: List of image URLs in order [banner, main_content, supporting_details, evidence, conclusion]
    """
    sections_order = ['banner', 'main_content', 'supporting_details', 'evidence', 'conclusion']
    urls = []
    
    for section in sections_order:
        if section in section_images:
            image_url = section_images[section].get('image_url')
            if image_url:
                urls.append(image_url)
            else:
                urls.append(None)  # Keep position but mark as None
        else:
            urls.append(None)
    
    # Remove trailing None values but keep the structure for existing images
    while urls and urls[-1] is None:
        urls.pop()
    
    return [url for url in urls if url is not None]  # Return only valid URLs
