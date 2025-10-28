"""
Centralized Download Service for Streamlit
Handles PDF and image downloads for all features
"""

import io
import logging
import re
import zipfile
from datetime import datetime
from typing import Dict, Any, List, Optional
import requests
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, ListFlowable, ListItem
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

logger = logging.getLogger(__name__)


class StreamlitDownloadService:
    """Centralized download service for Streamlit applications"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom styles for PDF generation"""
        # Blog title style
        self.styles.add(ParagraphStyle(
            name='BlogTitle',
            parent=self.styles['Title'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        ))
        
        # Blog subtitle style
        self.styles.add(ParagraphStyle(
            name='BlogSubtitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=20,
            textColor=colors.darkblue
        ))
        
        # Blog heading style
        self.styles.add(ParagraphStyle(
            name='BlogHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceAfter=15,
            textColor=colors.darkblue
        ))
        
        # Blog content style
        self.styles.add(ParagraphStyle(
            name='BlogContent',
            parent=self.styles['Normal'],
            fontSize=12,
            spaceAfter=12,
            alignment=TA_JUSTIFY
        ))
        
        # Sources style
        self.styles.add(ParagraphStyle(
            name='Sources',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            leftIndent=20
        ))
        
        # Source URL style
        self.styles.add(ParagraphStyle(
            name='SourceURL',
            parent=self.styles['Normal'],
            fontSize=9,
            spaceAfter=6,
            leftIndent=40,
            textColor=colors.blue
        ))
    
    def _download_image(self, image_url: str) -> Optional[io.BytesIO]:
        """Download image from URL"""
        try:
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            return io.BytesIO(response.content)
        except Exception as e:
            logger.error(f"Failed to download image from {image_url}: {str(e)}")
            return None
    
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
    
    def _get_heading_style(self, level: int) -> str:
        """Get appropriate heading style based on level"""
        if level == 1:
            return 'BlogTitle'
        elif level == 2:
            return 'BlogSubtitle'
        else:
            return 'BlogHeading'
    
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
    
    def generate_blog_pdf(self, blog_data: Dict[str, Any]) -> bytes:
        """Generate PDF for blog post"""
        try:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
            story = []
            
            # Add title
            story.append(Paragraph(blog_data.get('topic', 'Blog Post'), self.styles['BlogTitle']))
            story.append(Spacer(1, 12))
            
            # Add metadata
            metadata = f"Author: {blog_data.get('username', 'Unknown')}<br/>"
            metadata += f"Email: {blog_data.get('email', 'Unknown')}<br/>"
            metadata += f"Created: {blog_data.get('created_at', 'Unknown')}<br/>"
            metadata += f"Organization: {blog_data.get('organization_name', 'Unknown')}"
            story.append(Paragraph(metadata, self.styles['BlogContent']))
            story.append(Spacer(1, 24))
            
            # Parse and add content
            content = blog_data.get('content', '')
            if content:
                # Parse markdown content into structured elements
                elements = self._parse_markdown_content(content)
                
                for element in elements:
                    if element['type'] == 'heading':
                        level = element['level']
                        heading_text = self._process_inline_formatting(element['content'])
                        style_name = self._get_heading_style(level)
                        story.append(Paragraph(heading_text, self.styles[style_name]))
                        story.append(Spacer(1, 12))
                    
                    elif element['type'] == 'paragraph':
                        paragraph_text = self._process_inline_formatting(element['content'])
                        story.append(Paragraph(paragraph_text, self.styles['BlogContent']))
                        story.append(Spacer(1, 12))
                    
                    elif element['type'] == 'image':
                        self._add_image_to_story(story, element['url'], element['alt_text'])
                    
                    elif element['type'] == 'ordered_list':
                        list_items = []
                        for item in element['items']:
                            # Remove the number prefix
                            item_text = re.sub(r'^\d+\.\s*', '', item)
                            item_text = self._process_inline_formatting(item_text)
                            list_items.append(ListItem(Paragraph(item_text, self.styles['BlogContent'])))
                        story.append(ListFlowable(list_items, bulletType='1', start='1', leftIndent=0.2*inch))
                        story.append(Spacer(1, 12))
                    
                    elif element['type'] == 'unordered_list':
                        list_items = []
                        for item in element['items']:
                            # Remove the bullet prefix
                            item_text = re.sub(r'^[-*]\s*', '', item)
                            item_text = self._process_inline_formatting(item_text)
                            list_items.append(ListItem(Paragraph(item_text, self.styles['BlogContent'])))
                        story.append(ListFlowable(list_items, bulletType='bullet', leftIndent=0.2*inch))
                        story.append(Spacer(1, 12))
            
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
            doc.build(story)
            buffer.seek(0)
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Error generating blog PDF: {str(e)}")
            raise
    
    def generate_ai_news_pdf(self, news_data: Dict[str, Any]) -> bytes:
        """Generate PDF for AI news"""
        try:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
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
            story.append(Paragraph(metadata, self.styles['BlogContent']))
            story.append(Spacer(1, 24))
            
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
                # Parse markdown content into structured elements
                elements = self._parse_markdown_content(content)
                
                for element in elements:
                    if element['type'] == 'heading':
                        level = element['level']
                        heading_text = self._process_inline_formatting(element['content'])
                        style_name = self._get_heading_style(level)
                        story.append(Paragraph(heading_text, self.styles[style_name]))
                        story.append(Spacer(1, 12))
                    
                    elif element['type'] == 'paragraph':
                        paragraph_text = self._process_inline_formatting(element['content'])
                        story.append(Paragraph(paragraph_text, self.styles['BlogContent']))
                        story.append(Spacer(1, 12))
                    
                    elif element['type'] == 'image':
                        self._add_image_to_story(story, element['url'], element['alt_text'])
                    
                    elif element['type'] == 'ordered_list':
                        list_items = []
                        for item in element['items']:
                            item_text = re.sub(r'^\d+\.\s*', '', item)
                            item_text = self._process_inline_formatting(item_text)
                            list_items.append(ListItem(Paragraph(item_text, self.styles['BlogContent'])))
                        story.append(ListFlowable(list_items, bulletType='1', start='1', leftIndent=0.2*inch))
                        story.append(Spacer(1, 12))
                    
                    elif element['type'] == 'unordered_list':
                        list_items = []
                        for item in element['items']:
                            item_text = re.sub(r'^[-*]\s*', '', item)
                            item_text = self._process_inline_formatting(item_text)
                            list_items.append(ListItem(Paragraph(item_text, self.styles['BlogContent'])))
                        story.append(ListFlowable(list_items, bulletType='bullet', leftIndent=0.2*inch))
                        story.append(Spacer(1, 12))
            
            # Add sources
            sources = news_data.get('sources', [])
            if sources:
                self._add_sources_to_story(story, sources)
            
            # Build PDF
            doc.build(story)
            buffer.seek(0)
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Error generating AI news PDF: {str(e)}")
            raise
    
    def generate_linkedin_post_pdf(self, post_data: Dict[str, Any]) -> bytes:
        """Generate PDF for LinkedIn post"""
        try:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
            story = []
            
            # Add title
            story.append(Paragraph("LinkedIn Post", self.styles['BlogTitle']))
            story.append(Spacer(1, 12))
            
            # Add metadata
            metadata = f"Topic: {post_data.get('topic', 'Unknown')}<br/>"
            metadata += f"Author: {post_data.get('username', 'Unknown')}<br/>"
            metadata += f"Created: {post_data.get('created_at', 'Unknown')}"
            story.append(Paragraph(metadata, self.styles['BlogContent']))
            story.append(Spacer(1, 24))
            
            # Add content
            content = post_data.get('content', '')
            if content:
                # Parse markdown content into structured elements
                elements = self._parse_markdown_content(content)
                
                for element in elements:
                    if element['type'] == 'heading':
                        level = element['level']
                        heading_text = self._process_inline_formatting(element['content'])
                        style_name = self._get_heading_style(level)
                        story.append(Paragraph(heading_text, self.styles[style_name]))
                        story.append(Spacer(1, 12))
                    
                    elif element['type'] == 'paragraph':
                        paragraph_text = self._process_inline_formatting(element['content'])
                        story.append(Paragraph(paragraph_text, self.styles['BlogContent']))
                        story.append(Spacer(1, 12))
                    
                    elif element['type'] == 'image':
                        self._add_image_to_story(story, element['url'], element['alt_text'])
                    
                    elif element['type'] == 'ordered_list':
                        list_items = []
                        for item in element['items']:
                            item_text = re.sub(r'^\d+\.\s*', '', item)
                            item_text = self._process_inline_formatting(item_text)
                            list_items.append(ListItem(Paragraph(item_text, self.styles['BlogContent'])))
                        story.append(ListFlowable(list_items, bulletType='1', start='1', leftIndent=0.2*inch))
                        story.append(Spacer(1, 12))
                    
                    elif element['type'] == 'unordered_list':
                        list_items = []
                        for item in element['items']:
                            item_text = re.sub(r'^[-*]\s*', '', item)
                            item_text = self._process_inline_formatting(item_text)
                            list_items.append(ListItem(Paragraph(item_text, self.styles['BlogContent'])))
                        story.append(ListFlowable(list_items, bulletType='bullet', leftIndent=0.2*inch))
                        story.append(Spacer(1, 12))
            
            # Build PDF
            doc.build(story)
            buffer.seek(0)
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Error generating LinkedIn post PDF: {str(e)}")
            raise
    
    # Removed PDF generation for Upwork proposals. Use generate_upwork_proposal_md() instead.
    
    def _parse_markdown_content(self, content: str) -> List[Dict[str, Any]]:
        """Parse markdown content into structured elements"""
        import re
        
        elements = []
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                i += 1
                continue
            
            # Handle headings
            if line.startswith('#'):
                level = len(line) - len(line.lstrip('#'))
                heading_text = line.lstrip('#').strip()
                elements.append({
                    'type': 'heading',
                    'level': level,
                    'content': heading_text
                })
            
            # Handle images
            elif line.startswith('![') and '](' in line:
                match = re.match(r'!\[([^\]]*)\]\(([^)]+)\)', line)
                if match:
                    alt_text = match.group(1)
                    image_url = match.group(2)
                    elements.append({
                        'type': 'image',
                        'alt_text': alt_text,
                        'url': image_url
                    })
            
            # Handle lists
            elif re.match(r'^\d+\.\s', line):
                # Ordered list
                list_items = [line]
                i += 1
                while i < len(lines) and (lines[i].strip().startswith(('  ', '\t')) or re.match(r'^\d+\.\s', lines[i].strip())):
                    if lines[i].strip():
                        list_items.append(lines[i].strip())
                    i += 1
                i -= 1  # Back up one since we went too far
                
                elements.append({
                    'type': 'ordered_list',
                    'items': list_items
                })
            
            elif line.startswith('- ') or line.startswith('* '):
                # Unordered list
                list_items = [line]
                i += 1
                while i < len(lines) and (lines[i].strip().startswith(('  ', '\t')) or lines[i].strip().startswith(('- ', '* '))):
                    if lines[i].strip():
                        list_items.append(lines[i].strip())
                    i += 1
                i -= 1  # Back up one since we went too far
                
                elements.append({
                    'type': 'unordered_list',
                    'items': list_items
                })
            
            # Handle paragraphs
            else:
                paragraph_lines = [line]
                i += 1
                while i < len(lines) and lines[i].strip() and not lines[i].startswith('#') and not lines[i].startswith('![') and not re.match(r'^\d+\.\s', lines[i].strip()) and not lines[i].strip().startswith(('- ', '* ')):
                    paragraph_lines.append(lines[i].strip())
                    i += 1
                i -= 1  # Back up one since we went too far
                
                elements.append({
                    'type': 'paragraph',
                    'content': ' '.join(paragraph_lines)
                })
            
            i += 1
        
        return elements
    
    def _process_inline_formatting(self, text: str) -> str:
        """Process inline markdown formatting and convert to HTML-like tags for ReportLab"""
        import re
        
        # Process links: [text](url) -> <link href="url">text</link>
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<link href="\2">\1</link>', text)
        
        # Process bold: **text** -> <b>text</b>
        text = re.sub(r'\*\*([^*]+?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'__([^_]+?)__', r'<b>\1</b>', text)
        
        # Process italic: *text* -> <i>text</i>
        text = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<i>\1</i>', text)
        text = re.sub(r'(?<!_)_([^_]+?)_(?!_)', r'<i>\1</i>', text)
        
        return text
    
    def download_images_as_zip(self, image_urls: List[str], zip_filename: str = None) -> bytes:
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
                        response = requests.get(image_url, timeout=30)
                        response.raise_for_status()
                        
                        # Determine file extension from URL or content type
                        file_extension = self._get_image_extension(image_url, response.headers.get('content-type', ''))
                        filename = f"image_{i}{file_extension}"
                        
                        # Add to ZIP
                        zip_file.writestr(filename, response.content)
                        logger.info(f"Added {filename} to ZIP file")
                        
                    except Exception as e:
                        logger.error(f"Failed to download image {i} from {image_url}: {str(e)}")
                        # Add placeholder file for failed downloads
                        zip_file.writestr(f"image_{i}_failed.txt", f"Failed to download: {image_url}\nError: {str(e)}")
            
            zip_buffer.seek(0)
            return zip_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Error creating ZIP file: {str(e)}")
            raise
    
    def _get_image_extension(self, url: str, content_type: str) -> str:
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
    
    def generate_image_generation_zip(self, image_data: Dict[str, Any]) -> bytes:
        """Generate ZIP file for image generation data"""
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
                        response = requests.get(image_url, timeout=30)
                        response.raise_for_status()
                        
                        file_extension = self._get_image_extension(image_url, response.headers.get('content-type', ''))
                        filename = f"image_{i}{file_extension}"
                        zip_file.writestr(filename, response.content)
                        
                    except Exception as e:
                        logger.error(f"Failed to download image {i}: {str(e)}")
                        zip_file.writestr(f"image_{i}_failed.txt", f"Failed to download: {image_url}\nError: {str(e)}")
                
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
                
                import json
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
    
    def generate_upwork_proposal_md(self, proposal_data: Dict[str, Any]) -> str:
        """Generate Markdown content for Upwork proposal - returns raw MD content from database"""
        try:
            # Get the raw proposal content from the database
            proposal_content = proposal_data.get('proposal_content', '')
            
            if not proposal_content:
                # If no proposal content, create a basic structure
                proposal_content = f"""# Upwork Proposal

**Project:** {proposal_data.get('title', 'Unknown Project')}
**Company:** {proposal_data.get('company_name', 'Unknown Company')}
**Client:** {proposal_data.get('client_name', 'Unknown Client')}
**Author:** {proposal_data.get('username', 'Unknown')}
**Created:** {proposal_data.get('created_at', 'Unknown')}

## Project Requirements
{proposal_data.get('requirements', 'No requirements provided')}

## Proposal Content
No proposal content available yet. Please wait for the AI to generate the proposal.

## Contact Information
{proposal_data.get('contact_information', 'No contact information provided')}
"""
            
            return proposal_content
            
        except Exception as e:
            logger.error(f"Error generating Upwork proposal MD: {str(e)}")
            raise


# Global instance
download_service = StreamlitDownloadService()
