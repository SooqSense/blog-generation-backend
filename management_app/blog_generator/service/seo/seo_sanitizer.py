"""
SEO Content Sanitizer.
Handles HTML sanitization and security using bleach for XSS prevention.
"""

import bleach
import markdown
from typing import Dict, Any, Optional
from django.conf import settings


class SEOSanitizer:
    """Sanitizes HTML content to prevent XSS and ensure security."""

    # Allowed HTML tags for blog content
    ALLOWED_TAGS = [
        'p', 'br', 'strong', 'em', 'u', 'b', 'i', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'blockquote', 'code', 'pre', 'a', 'img', 'div', 'span',
        'table', 'thead', 'tbody', 'tr', 'th', 'td', 'hr', 'section', 'article'
    ]

    # Allowed HTML attributes
    ALLOWED_ATTRIBUTES = {
        'a': ['href', 'title', 'target', 'rel'],
        'img': ['src', 'alt', 'title', 'width', 'height', 'loading'],
        'div': ['class', 'id'],
        'span': ['class', 'id'],
        'section': ['class', 'id'],
        'article': ['class', 'id'],
        'table': ['class', 'id'],
        'code': ['class'],
        'pre': ['class'],
    }

    # Allowed URL schemes
    ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']

    @classmethod
    def markdown_to_html(cls, markdown_content: str) -> str:
        """
        Convert Markdown to HTML.

        Args:
            markdown_content: Markdown content

        Returns:
            HTML content
        """
        if not markdown_content:
            return ""
        
        # Convert markdown to HTML
        html = markdown.markdown(
            markdown_content,
            extensions=['extra', 'codehilite', 'tables', 'nl2br']
        )
        
        return html

    @classmethod
    def sanitize_html(cls, html_content: str) -> str:
        """
        Sanitize HTML content to prevent XSS attacks.

        Args:
            html_content: HTML content to sanitize

        Returns:
            Sanitized HTML content
        """
        if not html_content:
            return ""
        
        # Sanitize HTML using bleach
        sanitized = bleach.clean(
            html_content,
            tags=cls.ALLOWED_TAGS,
            attributes=cls.ALLOWED_ATTRIBUTES,
            protocols=cls.ALLOWED_PROTOCOLS,
            strip=True  # Remove disallowed tags instead of escaping
        )
        
        return sanitized

    @classmethod
    def markdown_to_sanitized_html(cls, markdown_content: str) -> str:
        """
        Convert Markdown to sanitized HTML in one step.

        Args:
            markdown_content: Markdown content

        Returns:
            Sanitized HTML content
        """
        html = cls.markdown_to_html(markdown_content)
        sanitized = cls.sanitize_html(html)
        return sanitized

    @classmethod
    def add_alt_text_to_images(cls, html_content: str, alt_texts: Optional[Dict[int, str]] = None) -> str:
        """
        Add or update alt text for images in HTML.

        Args:
            html_content: HTML content with images
            alt_texts: Dictionary mapping image index to alt text

        Returns:
            HTML with alt text added/updated
        """
        if not html_content or not alt_texts:
            return html_content
        
        import re
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html_content, 'html.parser')
        images = soup.find_all('img')
        
        for idx, img in enumerate(images):
            if idx in alt_texts:
                img['alt'] = alt_texts[idx]
            elif not img.get('alt'):
                # Default alt text if none provided
                img['alt'] = f"Image {idx + 1}"
        
        return str(soup)

    @classmethod
    def validate_html_structure(cls, html_content: str) -> Dict[str, Any]:
        """
        Validate HTML structure for SEO best practices.

        Args:
            html_content: HTML content to validate

        Returns:
            Validation result with recommendations
        """
        from bs4 import BeautifulSoup
        
        result = {
            "valid": True,
            "h1_count": 0,
            "h2_count": 0,
            "h3_count": 0,
            "images_without_alt": 0,
            "links_without_rel": 0,
            "recommendations": []
        }
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Count headings
            result["h1_count"] = len(soup.find_all('h1'))
            result["h2_count"] = len(soup.find_all('h2'))
            result["h3_count"] = len(soup.find_all('h3'))
            
            # Check for multiple H1 tags
            if result["h1_count"] > 1:
                result["valid"] = False
                result["recommendations"].append("Multiple H1 tags found. Use only one H1 per page.")
            elif result["h1_count"] == 0:
                result["valid"] = False
                result["recommendations"].append("No H1 tag found. Add a main heading.")
            
            # Check images for alt text
            images = soup.find_all('img')
            for img in images:
                if not img.get('alt'):
                    result["images_without_alt"] += 1
            
            if result["images_without_alt"] > 0:
                result["valid"] = False
                result["recommendations"].append(
                    f"{result['images_without_alt']} image(s) missing alt text. Add descriptive alt text for accessibility and SEO."
                )
            
            # Check external links for rel="noopener noreferrer"
            links = soup.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                if href.startswith('http') and 'noopener' not in link.get('rel', []):
                    result["links_without_rel"] += 1
            
            if result["links_without_rel"] > 0:
                result["recommendations"].append(
                    f"{result['links_without_rel']} external link(s) should have rel='noopener noreferrer' for security."
                )
        
        except Exception as e:
            result["valid"] = False
            result["recommendations"].append(f"HTML validation error: {str(e)}")
        
        return result

