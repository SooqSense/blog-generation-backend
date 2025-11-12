"""
LinkedIn PDF Generator Module
Generates PDF files for LinkedIn posts
"""

import logging
from typing import Dict, Any
from reportlab.platypus import Paragraph, Spacer
from services.pdf.base_pdf_generator import BasePDFGenerator

logger = logging.getLogger(__name__)


class LinkedInPDFGenerator(BasePDFGenerator):
    """PDF generator for LinkedIn posts"""
    
    def generate(self, post_data: Dict[str, Any]) -> bytes:
        """Generate PDF for LinkedIn post"""
        try:
            story = []
            
            # Add title
            story.append(Paragraph("LinkedIn Post", self.styles['BlogTitle']))
            story.append(Spacer(1, 12))
            
            # Add metadata
            metadata = f"Topic: {post_data.get('topic', 'Unknown')}<br/>"
            metadata += f"Author: {post_data.get('username', 'Unknown')}<br/>"
            metadata += f"Created: {post_data.get('created_at', 'Unknown')}"
            self._add_metadata(story, metadata)
            
            # Add content
            content = post_data.get('content', '')
            if content:
                self._add_content_elements_to_story(story, content)
            
            # Build PDF
            return self._build_pdf(story)
            
        except Exception as e:
            logger.error(f"Error generating LinkedIn post PDF: {str(e)}")
            raise

