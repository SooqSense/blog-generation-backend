"""
Blog PDF Generator Module
Generates PDF files for blog posts
"""

import logging
from typing import Dict, Any
from reportlab.platypus import Paragraph, Spacer
from services.pdf.base_pdf_generator import BasePDFGenerator

logger = logging.getLogger(__name__)


class BlogPDFGenerator(BasePDFGenerator):
    """PDF generator for blog posts"""
    
    def generate(self, blog_data: Dict[str, Any]) -> bytes:
        """Generate PDF for blog post"""
        try:
            story = []
            
            # Add title
            story.append(Paragraph(blog_data.get('topic', 'Blog Post'), self.styles['BlogTitle']))
            story.append(Spacer(1, 12))
            
            # Add metadata
            metadata = f"Author: {blog_data.get('username', 'Unknown')}<br/>"
            metadata += f"Email: {blog_data.get('email', 'Unknown')}<br/>"
            metadata += f"Created: {blog_data.get('created_at', 'Unknown')}<br/>"
            metadata += f"Organization: {blog_data.get('organization_name', 'Unknown')}"
            self._add_metadata(story, metadata)
            
            # Parse and add content
            content = blog_data.get('content', '')
            if content:
                self._add_content_elements_to_story(story, content)
            
            # Add images if available
            image_urls = blog_data.get('image_urls', [])
            if image_urls:
                story.append(Spacer(1, 24))
                story.append(Paragraph("<b>Images</b>", self.styles['BlogHeading']))
                for i, image_url in enumerate(image_urls, 1):
                    self._add_image_to_story(story, image_url, f"Image {i}")
            
            # Add sources if available
            sources = blog_data.get('sources', [])
            if sources:
                self._add_sources_to_story(story, sources)
            
            # Build PDF
            return self._build_pdf(story)
            
        except Exception as e:
            logger.error(f"Error generating blog PDF: {str(e)}")
            raise

