"""
PDF and document content extraction service.
Supports PDF, DOCX, MD, and TXT files.
"""

import os
import io
import logging
import re
from typing import Dict, Any, Optional, Tuple, List
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

# Compiled URL regex + exclusions (fast and reasonably strict)
_URL_RE = re.compile(
    r"https?://(?:[\w-]+\.)+[\w-]+(?:/[^\s<>\"'\[\]{}|\\^`\n]*)?",
    re.IGNORECASE,
)

_EXCLUDED_URL_PATTERNS = [
    r".*\.s3[\w.-]*\.amazonaws\.com",
    r".*storage\.googleapis\.com",
    r".*blob\.core\.windows\.net",
    r".*dropbox\.com.*",
    r".*drive\.google\.com.*",
    r".*onedrive\.com.*",
    r".*example\.(?:com|org|net).*",
    r".*localhost.*",
    r".*127\.0\.0\.1.*",
    r".*0\.0\.0\.0.*",
]
_EXCLUDED_URL_RE_LIST = [re.compile(p, re.IGNORECASE) for p in _EXCLUDED_URL_PATTERNS]

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
    
    def extract_links(self, text: str, max_links: int = 20) -> List[str]:
        """
        Extracts and cleans URLs from text.
        - Dedupes
        - Filters common storage/placeholder domains
        - Trims trailing punctuation
        """
        if not text:
            return []
        
        raw = _URL_RE.findall(text)
        seen = set()
        out: List[str] = []

        for url in raw:
            clean = re.sub(r"[.,:;!?)\]}\s]+$", "", url).strip()
            if not clean or clean in seen:
                continue

            # filter exclusions
            excluded = False
            for rx in _EXCLUDED_URL_RE_LIST:
                if rx.match(clean):
                    excluded = True
                    break
            if excluded:
                continue

            out.append(clean)
            seen.add(clean)
            if len(out) >= max_links:
                break

        return out
    
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
                
                # Extract links from the content (inline URLs)
                extracted_links = self.extract_links(result['content'])
                
                # Add hyperlinks from PDF annotations if available
                # Hyperlinks are now objects with {description, url}
                if 'hyperlinks' in result and result['hyperlinks']:
                    for link_obj in result['hyperlinks']:
                        # Extract URL from link object
                        link_url = link_obj.get('url') if isinstance(link_obj, dict) else link_obj
                        # Avoid duplicates and ensure it's a valid link
                        if link_url and link_url not in extracted_links:
                            extracted_links.append(link_url)
                    logger.info(f"📎 Added {len(result['hyperlinks'])} hyperlinks from PDF annotations")
                
                result['links'] = extracted_links
                
                # Extract Loom link objects from hyperlinks
                loom_link_objects = self._extract_loom_link_objects(result.get('hyperlinks', []))
                result['loom_links'] = loom_link_objects
                logger.info(f"📹 Extracted {len(loom_link_objects)} Loom link objects from {filename}")
                
                logger.info(f"✅ Successfully extracted {word_count} words and {len(extracted_links)} links from {filename}")
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
    
    def _extract_loom_link_objects(self, hyperlinks: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Extract Loom link objects from hyperlinks.
        
        Args:
            hyperlinks: List of link objects with {description, url}
            
        Returns:
            List of Loom link objects
        """
        loom_links = []
        
        if not hyperlinks:
            return loom_links
        
        for link_obj in hyperlinks:
            if isinstance(link_obj, dict):
                url = link_obj.get('url', '')
                if 'loom.com' in url.lower():
                    loom_links.append(link_obj)
        
        return loom_links
    
    def _extract_pdf_hyperlinks(self, pdf_reader, return_by_page: bool = False) -> List[Dict[str, str]] | Dict[int, List[Dict[str, str]]]:
        """Extract hyperlinks from PDF annotations with their descriptions.
        
        Args:
            pdf_reader: PyPDF2.PdfReader instance
            return_by_page: If True, returns dict mapping page_num -> [link_objects], else returns flat list
            
        Returns:
            List of link objects {description, url} or Dict mapping page numbers to lists of link objects
        """
        if return_by_page:
            links_by_page = {}
        else:
            links = []
        
        try:
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                page_links = []
                seen_urls = set()
                
                if "/Annots" in page:
                    annots = page["/Annots"]
                    for annot in annots:
                        try:
                            obj = annot.get_object()
                            if "/A" in obj and "/URI" in obj["/A"]:
                                uri = obj["/A"]["/URI"]
                                # Handle both string and bytes
                                if isinstance(uri, bytes):
                                    uri = uri.decode('utf-8', errors='ignore')
                                
                                if uri:
                                    # Extract description from /Contents or /Rect text
                                    description = ""
                                    if "/Contents" in obj:
                                        desc = obj["/Contents"]
                                        if isinstance(desc, bytes):
                                            description = desc.decode('utf-8', errors='ignore')
                                        else:
                                            description = str(desc)
                                    
                                    # If no description, try to get it from the annotation's appearance
                                    if not description and "/Subj" in obj:
                                        subj = obj["/Subj"]
                                        if isinstance(subj, bytes):
                                            description = subj.decode('utf-8', errors='ignore')
                                        else:
                                            description = str(subj)
                                    
                                    # Fallback: use a portion of the URL as description
                                    if not description:
                                        description = uri.split('/')[-1][:50] if '/' in uri else uri[:50]
                                    
                                    link_obj = {
                                        "description": description.strip(),
                                        "url": uri
                                    }
                                    
                                    if return_by_page:
                                        if uri not in seen_urls:
                                            page_links.append(link_obj)
                                            seen_urls.add(uri)
                                    else:
                                        if uri not in [l["url"] for l in links]:
                                            links.append(link_obj)
                        except Exception:
                            # Skip malformed annotations
                            continue
                
                if return_by_page and page_links:
                    links_by_page[page_num] = page_links
                    
        except Exception as e:
            logger.warning(f"⚠️ Could not extract hyperlinks from PDF annotations: {str(e)}")
        
        return links_by_page if return_by_page else links
    
    def _extract_pdf_content(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Extract content from PDF files with context-aware link injection."""
        if not PDF_AVAILABLE:
            return {
                'success': False,
                'error': 'PDF extraction libraries not available',
                'content': '',
                'hyperlinks': []
            }
        
        try:
            content_parts = []
            all_hyperlinks = []
            
            # Try with pdfplumber first (better for complex PDFs)
            try:
                pdf_file = io.BytesIO(file_content)
                with pdfplumber.open(pdf_file) as pdf:
                    # Extract text and hyperlinks page by page
                    for page_num, page in enumerate(pdf.pages):
                        text = page.extract_text()
                        page_links = []
                        
                        # Extract hyperlinks using pdfplumber's spatial awareness
                        if hasattr(page, 'hyperlinks') and page.hyperlinks:
                            for link in page.hyperlinks:
                                uri = link.get('uri')
                                if not uri:
                                    continue
                                    
                                # Extract text associated with the link using its bounding box
                                description = ""
                                try:
                                    # link object has 'top', 'bottom', 'x0', 'x1'
                                    # We crop the page to this area to get the text
                                    link_bbox = (link['x0'], link['top'], link['x1'], link['bottom'])
                                    cropped = page.crop(link_bbox)
                                    description = cropped.extract_text()
                                except Exception:
                                    pass
                                
                                # Clean up description
                                if description:
                                    description = description.strip().replace('\n', ' ')
                                
                                # Fallback if no text found
                                if not description:
                                    description = uri.split('/')[-1][:50] if '/' in uri else uri[:50]
                                
                                link_obj = {
                                    "description": description,
                                    "url": uri
                                }
                                
                                # Avoid duplicates on the page
                                if link_obj not in page_links:
                                    page_links.append(link_obj)
                                
                                # Add to global list (avoid duplicates)
                                if link_obj not in all_hyperlinks:
                                    all_hyperlinks.append(link_obj)
                        
                        if text:
                            page_text = text.strip()
                            
                            # Inject links found on this page
                            if page_links:
                                links_section = "\n\n--- Related Links ---\n" + "\n".join(
                                    f"• {link['description']}: {link['url']}" for link in page_links
                                )
                                page_text += links_section
                                logger.debug(f"📎 Injected {len(page_links)} links into page {page_num + 1}")
                            
                            content_parts.append(page_text)
                
                if content_parts:
                    content = '\n\n'.join(content_parts)
                    return {
                        'success': True,
                        'content': content,
                        'method': 'pdfplumber',
                        'hyperlinks': all_hyperlinks
                    }
            except Exception as e:
                logger.warning(f"⚠️ pdfplumber failed for {filename}: {str(e)}, trying PyPDF2")
            
            # Fallback to PyPDF2
            try:
                pdf_file = io.BytesIO(file_content)
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                
                # Extract hyperlinks by page
                links_by_page = self._extract_pdf_hyperlinks(pdf_reader, return_by_page=True)
                all_hyperlinks = self._extract_pdf_hyperlinks(pdf_reader, return_by_page=False)
                
                # Extract text page by page and inject links
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()
                    if text:
                        page_text = text.strip()
                        
                        # Inject links found on this page
                        if page_num in links_by_page and links_by_page[page_num]:
                            page_links = links_by_page[page_num]
                            links_section = "\n\n--- Related Links ---\n" + "\n".join(
                                f"• {link['description']}: {link['url']}" for link in page_links
                            )
                            page_text += links_section
                            logger.debug(f"📎 Injected {len(page_links)} links into page {page_num + 1}")
                        
                        content_parts.append(page_text)
                
                if content_parts:
                    content = '\n\n'.join(content_parts)
                    return {
                        'success': True,
                        'content': content,
                        'method': 'PyPDF2',
                        'hyperlinks': all_hyperlinks
                    }
                else:
                    return {
                        'success': False,
                        'error': 'No text content found in PDF',
                        'content': '',
                        'hyperlinks': all_hyperlinks
                    }
                    
            except Exception as e:
                return {
                    'success': False,
                    'error': f'PyPDF2 extraction failed: {str(e)}',
                    'content': '',
                    'hyperlinks': []
                }
            
        except Exception as e:
            logger.error(f"❌ Unexpected error extracting content from {filename}: {str(e)}")
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}',
                'content': '',
                'word_count': 0,
                'file_type': 'unknown'
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
