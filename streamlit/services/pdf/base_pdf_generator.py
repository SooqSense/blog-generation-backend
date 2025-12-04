"""
Base PDF Generator Module
Provides common PDF generation functionality
"""

import io
import logging
from typing import Dict, Any, List, Optional
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, ListFlowable, ListItem
from services.pdf.pdf_styles import PDFStyles
from services.image.image_downloader import ImageDownloader
from services.markdown.markdown_parser import MarkdownParser
from services.markdown.markdown_formatter import MarkdownFormatter

logger = logging.getLogger(__name__)


class BasePDFGenerator:
    """Base class for PDF generation with common functionality"""
    
    def __init__(self):
        self.styles_manager = PDFStyles()
        self.styles = self.styles_manager.styles
        self.image_downloader = ImageDownloader()
        self.markdown_parser = MarkdownParser()
        self.markdown_formatter = MarkdownFormatter()
    
    def _download_image(self, image_url: str) -> Optional[io.BytesIO]:
        """Download image from URL"""
        return self.image_downloader.download(image_url)
    
    def _add_image_to_story(self, story: List, image_url: str, alt_text: str = "Image", max_width: float = 6.0):
        """Add image to PDF story"""
        try:
            image_data = self._download_image(image_url)
            if image_data:
                # Create image from downloaded data
                img = Image(image_data, width=max_width*inch, height=4*inch)
                img.hAlign = 'CENTER'
                story.append(Spacer(1, 12))
                story.append(img)
                story.append(Spacer(1, 12))
            else:
                # Add placeholder text if image download fails
                story.append(Paragraph(f"[Image: {alt_text}]", self.styles['BlogContent']))
        except Exception as e:
            logger.error(f"Error adding image to PDF: {str(e)}")
            story.append(Paragraph(f"[Image: {alt_text}]", self.styles['BlogContent']))
    
    def _add_sources_to_story(self, story: List, sources: List[Dict[str, Any]]):
        """Add sources section to PDF"""
        if not sources:
            return
        
        story.append(Spacer(1, 24))
        story.append(Paragraph("<b>Sources</b>", self.styles['BlogHeading']))
        
        for i, source in enumerate(sources, 1):
            title = source.get("title", f"Source {i}")
            url = source.get("url")
            description = source.get("description", "")
            
            # Add source title
            story.append(Paragraph(f"{i}. {title}", self.styles['Sources']))
            
            # Add URL if available
            if url:
                story.append(Paragraph(f"<link href='{url}'>{url}</link>", self.styles['SourceURL']))
            
            # Add description if available
            if description:
                story.append(Paragraph(description, self.styles['SourceURL']))
            
            story.append(Spacer(1, 6))
    
    def _add_content_elements_to_story(self, story: List, content: str):
        """Add parsed markdown content elements to PDF story"""
        if not content:
            return
        
        # Parse markdown content into structured elements
        elements = self.markdown_parser.parse(content)
        
        for element in elements:
            if element['type'] == 'heading':
                level = element['level']
                heading_text = self.markdown_formatter.process_inline_formatting(element['content'])
                style_name = self.styles_manager.get_heading_style(level)
                story.append(Paragraph(heading_text, self.styles[style_name]))
                story.append(Spacer(1, 12))
            
            elif element['type'] == 'paragraph':
                paragraph_text = self.markdown_formatter.process_inline_formatting(element['content'])
                story.append(Paragraph(paragraph_text, self.styles['BlogContent']))
                story.append(Spacer(1, 12))
            
            elif element['type'] == 'image':
                self._add_image_to_story(story, element['url'], element['alt_text'])
            
            elif element['type'] == 'ordered_list':
                list_items = []
                for item in element['items']:
                    item_text = self.markdown_formatter.clean_list_item(item, 'ordered')
                    item_text = self.markdown_formatter.process_inline_formatting(item_text)
                    list_items.append(ListItem(Paragraph(item_text, self.styles['BlogContent'])))
                story.append(ListFlowable(list_items, bulletType='1', start='1', leftIndent=0.2*inch))
                story.append(Spacer(1, 12))
            
            elif element['type'] == 'unordered_list':
                list_items = []
                for item in element['items']:
                    item_text = self.markdown_formatter.clean_list_item(item, 'unordered')
                    item_text = self.markdown_formatter.process_inline_formatting(item_text)
                    list_items.append(ListItem(Paragraph(item_text, self.styles['BlogContent'])))
                story.append(ListFlowable(list_items, bulletType='bullet', leftIndent=0.2*inch))
                story.append(Spacer(1, 12))
    
    def _build_pdf(self, story: List) -> bytes:
        """Build PDF from story and return bytes"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4, 
            rightMargin=72, 
            leftMargin=72, 
            topMargin=72, 
            bottomMargin=18
        )
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    
    def _add_metadata(self, story: List, metadata_html: str):
        """Add metadata section to PDF story"""
        story.append(Paragraph(metadata_html, self.styles['BlogContent']))
        story.append(Spacer(1, 24))

