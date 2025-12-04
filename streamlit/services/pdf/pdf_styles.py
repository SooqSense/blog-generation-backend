"""
PDF Styles Configuration Module
Manages PDF styling for all document types
"""

from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY


class PDFStyles:
    """Manages PDF styles for document generation"""
    
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
    
    def get_heading_style(self, level: int) -> str:
        """Get appropriate heading style based on level"""
        if level == 1:
            return 'BlogTitle'
        elif level == 2:
            return 'BlogSubtitle'
        else:
            return 'BlogHeading'

