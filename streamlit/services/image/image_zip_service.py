"""
Image ZIP Service Module
Handles ZIP file creation for image downloads
"""

import io
import json
import logging
import zipfile
from typing import Dict, Any, List
import requests
from services.image.image_utils import ImageUtils

logger = logging.getLogger(__name__)


class ImageZipService:
    """Service for creating ZIP files containing images"""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.image_utils = ImageUtils()
    
    def create_images_zip(self, image_urls: List[str]) -> bytes:
        """Download multiple images and create a ZIP file"""
        try:
            if not image_urls:
                raise ValueError("No image URLs provided")
            
            # Create ZIP file in memory
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for i, image_url in enumerate(image_urls, 1):
                    try:
                        # Download image
                        response = requests.get(image_url, timeout=self.timeout)
                        response.raise_for_status()
                        
                        # Determine file extension from URL or content type
                        file_extension = self.image_utils.get_image_extension(
                            image_url, 
                            response.headers.get('content-type', '')
                        )
                        filename = f"image_{i}{file_extension}"
                        
                        # Add to ZIP
                        zip_file.writestr(filename, response.content)
                        logger.info(f"Added {filename} to ZIP file")
                        
                    except Exception as e:
                        logger.error(f"Failed to download image {i} from {image_url}: {str(e)}")
                        # Add placeholder file for failed downloads
                        zip_file.writestr(
                            f"image_{i}_failed.txt", 
                            f"Failed to download: {image_url}\nError: {str(e)}"
                        )
            
            zip_buffer.seek(0)
            return zip_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Error creating ZIP file: {str(e)}")
            raise
    
    def create_image_generation_zip(self, image_data: Dict[str, Any]) -> bytes:
        """Generate ZIP file for image generation data with metadata"""
        try:
            image_urls = image_data.get('image_urls', [])
            if not image_urls:
                raise ValueError("No images available for download")
            
            # Create ZIP file in memory
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add images
                for i, image_url in enumerate(image_urls, 1):
                    try:
                        response = requests.get(image_url, timeout=self.timeout)
                        response.raise_for_status()
                        
                        file_extension = self.image_utils.get_image_extension(
                            image_url, 
                            response.headers.get('content-type', '')
                        )
                        filename = f"image_{i}{file_extension}"
                        zip_file.writestr(filename, response.content)
                        
                    except Exception as e:
                        logger.error(f"Failed to download image {i}: {str(e)}")
                        zip_file.writestr(
                            f"image_{i}_failed.txt", 
                            f"Failed to download: {image_url}\nError: {str(e)}"
                        )
                
                # Add metadata file
                metadata = {
                    'prompt': image_data.get('prompt', ''),
                    'images_count': image_data.get('images_count', len(image_urls)),
                    'generation_method': image_data.get('generation_method', ''),
                    'image_style': image_data.get('image_style', ''),
                    'created_at': image_data.get('created_at', ''),
                    'username': image_data.get('username', ''),
                    'organization_name': image_data.get('organization_name', ''),
                    'image_urls': image_urls
                }
                
                zip_file.writestr('metadata.json', json.dumps(metadata, indent=2))
                
                # Add README file
                readme_content = f"""Image Generation Download
========================

Prompt: {metadata['prompt']}
Generated: {metadata['created_at']}
Author: {metadata['username']}
Organization: {metadata['organization_name']}
Method: {metadata['generation_method']}
Style: {metadata['image_style']}
Images: {metadata['images_count']}

This ZIP file contains {metadata['images_count']} generated images and metadata.
"""
                zip_file.writestr('README.txt', readme_content)
            
            zip_buffer.seek(0)
            return zip_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Error generating image ZIP: {str(e)}")
            raise

