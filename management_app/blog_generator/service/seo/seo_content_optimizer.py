"""
SEO Content Optimizer.
Handles content optimization including Markdown to HTML conversion, internal linking, and alt text.
"""

import logging
from typing import Dict, Any, Optional, List
from django.conf import settings

from .seo_sanitizer import SEOSanitizer
from .seo_utils import SEOUtils

logger = logging.getLogger(__name__)


class SEOContentOptimizer:
    """Optimizes blog content for SEO including HTML conversion and enhancements."""

    def __init__(self):
        """Initialize SEO Content Optimizer."""
        pass

    def optimize_content(
        self,
        markdown_content: str,
        seo_metadata: Dict[str, Any],
        image_urls: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Optimize content for SEO.

        Args:
            markdown_content: Original markdown content
            seo_metadata: SEO metadata from metadata generator
            image_urls: List of image URLs

        Returns:
            Dictionary containing optimized HTML and optimization details
        """
        try:
            logger.info("Optimizing content for SEO")

            # Convert markdown to HTML
            html_content = SEOSanitizer.markdown_to_sanitized_html(markdown_content)

            # Add alt text to images
            alt_texts = self._extract_alt_texts(seo_metadata, image_urls or [])
            html_content = SEOSanitizer.add_alt_text_to_images(html_content, alt_texts)

            # Implement internal linking
            html_content = self._add_internal_links(html_content, seo_metadata)

            # Validate HTML structure
            html_validation = SEOSanitizer.validate_html_structure(html_content)

            # Generate full HTML document with head section
            full_html = self._generate_full_html(html_content, seo_metadata)

            logger.info("✅ Content optimization completed")

            return {
                "html_content": html_content,
                "full_html": full_html,
                "html_validation": html_validation,
                "optimization_applied": {
                    "markdown_to_html": True,
                    "sanitization": True,
                    "alt_text_added": len(alt_texts) > 0,
                    "internal_links_added": len(seo_metadata.get("internal_linking", {}).get("suggestions", [])) > 0,
                }
            }

        except Exception as e:
            logger.error(f"Error optimizing content: {e}", exc_info=True)
            # Return basic HTML conversion as fallback
            html_content = SEOSanitizer.markdown_to_sanitized_html(markdown_content)
            return {
                "html_content": html_content,
                "full_html": self._generate_full_html(html_content, seo_metadata),
                "html_validation": {},
                "optimization_applied": {
                    "markdown_to_html": True,
                    "sanitization": True,
                    "alt_text_added": False,
                    "internal_links_added": False,
                }
            }

    def _extract_alt_texts(
        self,
        seo_metadata: Dict[str, Any],
        image_urls: List[str],
    ) -> Dict[int, str]:
        """
        Extract alt text recommendations from SEO metadata.

        Args:
            seo_metadata: SEO metadata containing image optimization data
            image_urls: List of image URLs

        Returns:
            Dictionary mapping image index to alt text
        """
        alt_texts = {}
        image_optimization = seo_metadata.get("image_optimization", {})
        recommendations = image_optimization.get("alt_text_recommendations", [])

        for rec in recommendations:
            if isinstance(rec, dict):
                idx = rec.get("image_index", -1)
                alt_text = rec.get("alt_text", "")
                if idx >= 0 and alt_text:
                    alt_texts[idx] = alt_text

        # If no recommendations, generate basic alt text
        if not alt_texts and image_urls:
            for idx in range(len(image_urls)):
                if idx not in alt_texts:
                    alt_texts[idx] = f"Image {idx + 1} for {seo_metadata.get('seo_title', 'blog post')}"

        return alt_texts

    def _add_internal_links(
        self,
        html_content: str,
        seo_metadata: Dict[str, Any],
    ) -> str:
        """
        Add internal links to HTML content based on SEO recommendations.

        Args:
            html_content: HTML content
            seo_metadata: SEO metadata with internal linking suggestions

        Returns:
            HTML content with internal links added
        """
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html_content, 'html.parser')
            internal_linking = seo_metadata.get("internal_linking", {})
            suggestions = internal_linking.get("suggestions", [])

            # For now, we'll add links based on anchor text matching
            # In a full implementation, you'd have a database of related posts
            for suggestion in suggestions:
                anchor_text = suggestion.get("anchor_text", "")
                target_topic = suggestion.get("target_topic", "")
                
                if anchor_text and target_topic:
                    # Find text matching anchor_text and convert to link
                    # This is a simplified implementation
                    # In production, you'd match against actual blog posts
                    for text_node in soup.find_all(string=lambda text: anchor_text.lower() in text.lower() if text else False):
                        if text_node.parent.name not in ['a', 'script', 'style']:
                            # Create link (using placeholder URL - would be real URLs in production)
                            slug = SEOUtils.generate_slug(target_topic)
                            base_url = getattr(settings, "BACKEND_API_BASE_URL", "http://localhost:8000")
                            link_url = f"{base_url}/blog/{slug}"
                            
                            new_link = soup.new_tag('a', href=link_url, rel="internal")
                            new_link.string = anchor_text
                            text_node.replace_with(new_link)
                            break  # Only replace first occurrence

            return str(soup)

        except Exception as e:
            logger.warning(f"Error adding internal links: {e}")
            return html_content

    def _generate_full_html(
        self,
        body_content: str,
        seo_metadata: Dict[str, Any],
    ) -> str:
        """
        Generate complete HTML document with head section containing all SEO metadata.

        Args:
            body_content: HTML body content
            seo_metadata: SEO metadata

        Returns:
            Complete HTML document
        """
        seo_title = seo_metadata.get("seo_title", "")
        meta_description = seo_metadata.get("meta_description", "")
        keywords = seo_metadata.get("keywords", [])
        canonical_url = seo_metadata.get("canonical_url", "")
        social_metadata = seo_metadata.get("social_metadata", {})

        # Build meta tags
        meta_tags = []
        
        # Basic meta tags
        if meta_description:
            meta_tags.append(f'    <meta name="description" content="{self._escape_html(meta_description)}">')
        
        if keywords:
            keywords_str = ", ".join(keywords[:10])  # Limit to 10 keywords
            meta_tags.append(f'    <meta name="keywords" content="{self._escape_html(keywords_str)}">')
        
        # Canonical URL
        if canonical_url:
            meta_tags.append(f'    <link rel="canonical" href="{self._escape_html(canonical_url)}">')
        
        # Robots meta (for drafts)
        robots_index = seo_metadata.get("robots_index", True)
        if not robots_index:
            meta_tags.append('    <meta name="robots" content="noindex, nofollow">')
        else:
            meta_tags.append('    <meta name="robots" content="index, follow">')
        
        # Open Graph tags
        og_title = social_metadata.get("og_title", seo_title)
        og_description = social_metadata.get("og_description", meta_description)
        og_image = social_metadata.get("og_image", "")
        og_type = social_metadata.get("og_type", "article")
        og_url = social_metadata.get("og_url", canonical_url)
        
        if og_title:
            meta_tags.append(f'    <meta property="og:title" content="{self._escape_html(og_title)}">')
        if og_description:
            meta_tags.append(f'    <meta property="og:description" content="{self._escape_html(og_description)}">')
        if og_image:
            meta_tags.append(f'    <meta property="og:image" content="{self._escape_html(og_image)}">')
        if og_type:
            meta_tags.append(f'    <meta property="og:type" content="{og_type}">')
        if og_url:
            meta_tags.append(f'    <meta property="og:url" content="{self._escape_html(og_url)}">')
        
        # Twitter Card tags
        twitter_card = social_metadata.get("twitter_card", "summary_large_image")
        twitter_title = social_metadata.get("twitter_title", seo_title)
        twitter_description = social_metadata.get("twitter_description", meta_description)
        twitter_image = social_metadata.get("twitter_image", og_image)
        
        if twitter_card:
            meta_tags.append(f'    <meta name="twitter:card" content="{twitter_card}">')
        if twitter_title:
            meta_tags.append(f'    <meta name="twitter:title" content="{self._escape_html(twitter_title)}">')
        if twitter_description:
            meta_tags.append(f'    <meta name="twitter:description" content="{self._escape_html(twitter_description)}">')
        if twitter_image:
            meta_tags.append(f'    <meta name="twitter:image" content="{self._escape_html(twitter_image)}">')
        
        # AI-generated content transparency
        is_ai_generated = seo_metadata.get("is_ai_generated", True)
        if is_ai_generated:
            meta_tags.append('    <meta name="generator" content="AI Blog Generator">')
        
        # Build complete HTML
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self._escape_html(seo_title)}</title>
{chr(10).join(meta_tags)}
</head>
<body>
{body_content}
</body>
</html>"""

        return html

    def _escape_html(self, text: str) -> str:
        """
        Escape HTML special characters.

        Args:
            text: Text to escape

        Returns:
            Escaped text
        """
        if not text:
            return ""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )

