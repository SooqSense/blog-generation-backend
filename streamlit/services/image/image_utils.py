"""
Image Utilities Module
Provides image-related utility functions
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ImageUtils:
    """Utility functions for image processing"""
    
    @staticmethod
    def get_image_extension(url: str, content_type: str = '') -> str:
        """Determine file extension from URL or content type"""
        # Try to get extension from URL
        if '.' in url:
            url_ext = url.split('.')[-1].lower()
            if url_ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                return f'.{url_ext}'
        
        # Try to get extension from content type
        if 'jpeg' in content_type or 'jpg' in content_type:
            return '.jpg'
        elif 'png' in content_type:
            return '.png'
        elif 'gif' in content_type:
            return '.gif'
        elif 'webp' in content_type:
            return '.webp'
        
        # Default to jpg
        return '.jpg'

