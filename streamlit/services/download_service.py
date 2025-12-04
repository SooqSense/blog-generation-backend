"""
Centralized Download Service for Streamlit
Main facade that orchestrates all download services
Maintains backward compatibility with existing code
"""

import logging
from typing import Dict, Any, List

from services.pdf.blog_pdf_generator import BlogPDFGenerator
from services.pdf.news_pdf_generator import NewsPDFGenerator
from services.pdf.linkedin_pdf_generator import LinkedInPDFGenerator
from services.image.image_zip_service import ImageZipService
from services.markdown.upwork_markdown_generator import UpworkMarkdownGenerator

logger = logging.getLogger(__name__)


class StreamlitDownloadService:
    """
    Centralized download service for Streamlit applications.
    Facade that delegates to specialized generators.
    """
    
    def __init__(self):
        # Initialize PDF generators
        self.blog_pdf_generator = BlogPDFGenerator()
        self.news_pdf_generator = NewsPDFGenerator()
        self.linkedin_pdf_generator = LinkedInPDFGenerator()
        
        # Initialize image services
        self.image_zip_service = ImageZipService()
        
        # Initialize markdown generators
        self.upwork_md_generator = UpworkMarkdownGenerator()
    
    # ===================================================================
    # PDF Generation Methods (Backward Compatible)
    # ===================================================================
    
    def generate_blog_pdf(self, blog_data: Dict[str, Any]) -> bytes:
        """Generate PDF for blog post"""
        return self.blog_pdf_generator.generate(blog_data)
    
    def generate_ai_news_pdf(self, news_data: Dict[str, Any]) -> bytes:
        """Generate PDF for AI news"""
        return self.news_pdf_generator.generate(news_data)
    
    def generate_linkedin_post_pdf(self, post_data: Dict[str, Any]) -> bytes:
        """Generate PDF for LinkedIn post"""
        return self.linkedin_pdf_generator.generate(post_data)
    
    # ===================================================================
    # Image Download Methods (Backward Compatible)
    # ===================================================================
    
    def download_images_as_zip(self, image_urls: List[str], zip_filename: str = None) -> bytes:
        """Download multiple images and create a ZIP file"""
        return self.image_zip_service.create_images_zip(image_urls)
    
    def generate_image_generation_zip(self, image_data: Dict[str, Any]) -> bytes:
        """Generate ZIP file for image generation data"""
        return self.image_zip_service.create_image_generation_zip(image_data)
    
    # ===================================================================
    # Markdown Generation Methods (Backward Compatible)
    # ===================================================================
    
    def generate_upwork_proposal_md(self, proposal_data: Dict[str, Any]) -> str:
        """Generate Markdown content for Upwork proposal"""
        return self.upwork_md_generator.generate(proposal_data)


# Global instance for backward compatibility
download_service = StreamlitDownloadService()
