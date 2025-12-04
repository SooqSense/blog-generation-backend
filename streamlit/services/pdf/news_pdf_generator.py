"""
News PDF Generator Module
Generates PDF files for AI news articles
"""

import logging
from typing import Dict, Any
from reportlab.platypus import Paragraph, Spacer
from services.pdf.base_pdf_generator import BasePDFGenerator

logger = logging.getLogger(__name__)


class NewsPDFGenerator(BasePDFGenerator):
    """PDF generator for AI news articles"""
    
    def generate(self, news_data: Dict[str, Any]) -> bytes:
        """Generate PDF for AI news"""
        try:
            story = []
            
            # Add title
            title = f"AI News - {news_data.get('news_date', 'Unknown Date')}"
            story.append(Paragraph(title, self.styles['BlogTitle']))
            story.append(Spacer(1, 12))
            
            # Add metadata
            metadata = f"Country: {news_data.get('country', 'Unknown')}<br/>"
            metadata += f"Keywords: {', '.join(news_data.get('keywords', []))}<br/>"
            metadata += f"Author: {news_data.get('username', 'Unknown')}<br/>"
            metadata += f"Created: {news_data.get('created_at', 'Unknown')}"
            self._add_metadata(story, metadata)
            
            # Add summary
            summary = news_data.get('summary', '')
            if summary:
                story.append(Paragraph("<b>Summary</b>", self.styles['BlogHeading']))
                story.append(Paragraph(summary, self.styles['BlogContent']))
                story.append(Spacer(1, 24))
            
            # Add content
            content = news_data.get('content', '')
            if content:
                story.append(Paragraph("<b>Content</b>", self.styles['BlogHeading']))
                self._add_content_elements_to_story(story, content)
            
            # Add sources
            sources = news_data.get('sources', [])
            if sources:
                self._add_sources_to_story(story, sources)
            
            # Build PDF
            return self._build_pdf(story)
            
        except Exception as e:
            logger.error(f"Error generating AI news PDF: {str(e)}")
            raise

