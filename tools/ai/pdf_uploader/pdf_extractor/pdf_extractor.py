"""
PDF and document content extraction service.
Supports PDF, DOCX, MD, and TXT files.
"""

import os
import io
import logging
from typing import Dict, Any, Optional, Tuple
import mimetypes

# Import libraries for different file types
try:
    import PyPDF2
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("⚠️ PDF extraction libraries not available. Install: pip install PyPDF2 pdfplumber")

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    print("⚠️ DOCX extraction library not available. Install: pip install python-docx")

try:
    import markdown
    from bs4 import BeautifulSoup
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False
    print("⚠️ Markdown processing libraries not available. Install: pip install markdown beautifulsoup4")

logger = logging.getLogger(__name__)

class DocumentExtractor:
    """Service for extracting content from various document types."""
    
    def __init__(self):
        self.supported_types = {
            'pdf': self._extract_pdf_content,
            'docx': self._extract_docx_content,
            'md': self._extract_markdown_content,
            'txt': self._extract_text_content
        }
    
    def get_supported_types(self) -> list:
        """Return list of supported file types."""
        return list(self.supported_types.keys())
    
    def detect_file_type(self, filename: str, file_content: bytes) -> str:
        """Detect file type from filename and content."""
        # Get extension from filename
        file_extension = os.path.splitext(filename.lower())[1][1:]  # Remove the dot
        
        # Map common extensions
        extension_map = {
            'pdf': 'pdf',
            'docx': 'docx',
            'doc': 'docx',  # Treat .doc as .docx for now
            'md': 'md',
            'markdown': 'md',
            'txt': 'txt',
            'text': 'txt'
        }
        
        detected_type = extension_map.get(file_extension, 'txt')
        
        # Validate with MIME type if possible
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type:
            if mime_type == 'application/pdf':
                detected_type = 'pdf'
            elif mime_type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                detected_type = 'docx'
            elif mime_type == 'text/markdown':
                detected_type = 'md'
            elif mime_type.startswith('text/'):
                detected_type = 'txt'
        
        return detected_type
    
    def extract_content(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Extract content from file based on its type."""
        try:
            # Detect file type
            file_type = self.detect_file_type(filename, file_content)
            
            logger.info(f"📄 Extracting content from {filename} (detected as {file_type})")
            
            if file_type not in self.supported_types:
                return {
                    'success': False,
                    'error': f'Unsupported file type: {file_type}',
                    'content': '',
                    'word_count': 0,
                    'file_type': file_type
                }
            
            # Extract content using appropriate method
            extractor_func = self.supported_types[file_type]
            result = extractor_func(file_content, filename)
            
            if result['success']:
                # Calculate word count
                word_count = len(result['content'].split()) if result['content'] else 0
                result['word_count'] = word_count
                result['file_type'] = file_type
                
                logger.info(f"✅ Successfully extracted {word_count} words from {filename}")
            else:
                logger.error(f"❌ Failed to extract content from {filename}: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Unexpected error extracting content from {filename}: {str(e)}")
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}',
                'content': '',
                'word_count': 0,
                'file_type': 'unknown'
            }
    
    def _extract_pdf_content(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Extract content from PDF files."""
        if not PDF_AVAILABLE:
            return {
                'success': False,
                'error': 'PDF extraction libraries not available',
                'content': ''
            }
        
        try:
            content_parts = []
            
            # Try with pdfplumber first (better for complex PDFs)
            try:
                pdf_file = io.BytesIO(file_content)
                with pdfplumber.open(pdf_file) as pdf:
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            content_parts.append(text.strip())
                
                if content_parts:
                    content = '\n\n'.join(content_parts)
                    return {
                        'success': True,
                        'content': content,
                        'method': 'pdfplumber'
                    }
            except Exception as e:
                logger.warning(f"⚠️ pdfplumber failed for {filename}: {str(e)}, trying PyPDF2")
            
            # Fallback to PyPDF2
            try:
                pdf_file = io.BytesIO(file_content)
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()
                    if text:
                        content_parts.append(text.strip())
                
                if content_parts:
                    content = '\n\n'.join(content_parts)
                    return {
                        'success': True,
                        'content': content,
                        'method': 'PyPDF2'
                    }
                else:
                    return {
                        'success': False,
                        'error': 'No text content found in PDF',
                        'content': ''
                    }
                    
            except Exception as e:
                return {
                    'success': False,
                    'error': f'PyPDF2 extraction failed: {str(e)}',
                    'content': ''
                }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'PDF extraction error: {str(e)}',
                'content': ''
            }
    
    def _extract_docx_content(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Extract content from DOCX files."""
        if not DOCX_AVAILABLE:
            return {
                'success': False,
                'error': 'DOCX extraction library not available',
                'content': ''
            }
        
        try:
            docx_file = io.BytesIO(file_content)
            doc = Document(docx_file)
            
            content_parts = []
            
            # Extract paragraphs
            for paragraph in doc.paragraphs:
                text = paragraph.text.strip()
                if text:
                    content_parts.append(text)
            
            # Extract tables
            for table in doc.tables:
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        cell_text = cell.text.strip()
                        if cell_text:
                            row_text.append(cell_text)
                    if row_text:
                        content_parts.append(' | '.join(row_text))
            
            if content_parts:
                content = '\n\n'.join(content_parts)
                return {
                    'success': True,
                    'content': content,
                    'method': 'python-docx'
                }
            else:
                return {
                    'success': False,
                    'error': 'No text content found in DOCX',
                    'content': ''
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'DOCX extraction error: {str(e)}',
                'content': ''
            }
    
    def _extract_markdown_content(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Extract content from Markdown files."""
        try:
            # Decode text content
            content = file_content.decode('utf-8', errors='ignore')
            
            if MARKDOWN_AVAILABLE:
                # Convert markdown to HTML and then extract plain text
                html = markdown.markdown(content)
                soup = BeautifulSoup(html, 'html.parser')
                plain_text = soup.get_text()
                
                # Also keep original markdown for reference
                final_content = f"Original Markdown:\n{content}\n\nPlain Text:\n{plain_text}"
                
                return {
                    'success': True,
                    'content': final_content,
                    'method': 'markdown + beautifulsoup'
                }
            else:
                # Just return raw markdown content
                return {
                    'success': True,
                    'content': content,
                    'method': 'raw_markdown'
                }
                
        except UnicodeDecodeError as e:
            try:
                # Try with different encoding
                content = file_content.decode('latin-1')
                return {
                    'success': True,
                    'content': content,
                    'method': 'latin-1_encoding'
                }
            except Exception:
                return {
                    'success': False,
                    'error': f'Encoding error: {str(e)}',
                    'content': ''
                }
        except Exception as e:
            return {
                'success': False,
                'error': f'Markdown extraction error: {str(e)}',
                'content': ''
            }
    
    def _extract_text_content(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Extract content from plain text files."""
        try:
            # Try UTF-8 first
            content = file_content.decode('utf-8', errors='ignore')
            
            if content.strip():
                return {
                    'success': True,
                    'content': content,
                    'method': 'utf-8_text'
                }
            else:
                # Try different encoding
                content = file_content.decode('latin-1', errors='ignore')
                return {
                    'success': True,
                    'content': content,
                    'method': 'latin-1_text'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Text extraction error: {str(e)}',
                'content': ''
            }
    
    def validate_file(self, file_content: bytes, filename: str, max_size_mb: int = 50) -> Dict[str, Any]:
        """Validate file before processing."""
        # Check file size
        file_size = len(file_content)
        if file_size > max_size_mb * 1024 * 1024:
            return {
                'valid': False,
                'error': f'File size ({file_size / (1024*1024):.2f} MB) exceeds maximum ({max_size_mb} MB)'
            }
        
        # Check file type
        file_type = self.detect_file_type(filename, file_content)
        if file_type not in self.supported_types:
            return {
                'valid': False,
                'error': f'Unsupported file type: {file_type}'
            }
        
        # Check if file is empty
        if file_size == 0:
            return {
                'valid': False,
                'error': 'File is empty'
            }
        
        return {
            'valid': True,
            'file_type': file_type,
            'file_size': file_size
        }


# Create global extractor instance
document_extractor = DocumentExtractor()
