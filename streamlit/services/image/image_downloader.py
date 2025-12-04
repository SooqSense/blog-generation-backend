"""
Image Downloader Module
Handles downloading images from URLs
"""

import io
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


class ImageDownloader:
    """Downloads images from URLs"""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
    
    def download(self, image_url: str) -> Optional[io.BytesIO]:
        """Download image from URL"""
        try:
            response = requests.get(image_url, timeout=self.timeout)
            response.raise_for_status()
            return io.BytesIO(response.content)
        except Exception as e:
            logger.error(f"Failed to download image from {image_url}: {str(e)}")
            return None
    
    def download_multiple(self, image_urls: list) -> dict:
        """Download multiple images and return dict of url -> BytesIO"""
        results = {}
        for url in image_urls:
            image_data = self.download(url)
            if image_data:
                results[url] = image_data
        return results

