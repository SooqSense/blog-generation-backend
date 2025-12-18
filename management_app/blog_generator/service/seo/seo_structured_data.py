"""
SEO Structured Data Generator.
Generates JSON-LD structured data schemas for rich search results.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from django.conf import settings

logger = logging.getLogger(__name__)


class SEOStructuredData:
    """Generates structured data (JSON-LD) for SEO."""

    def __init__(self):
        """Initialize SEO Structured Data Generator."""
        pass

    def generate_structured_data(
        self,
        seo_metadata: Dict[str, Any],
        blog_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate all structured data schemas.

        Args:
            seo_metadata: SEO metadata
            blog_data: Blog data (topic, content, images, etc.)

        Returns:
            Dictionary containing all structured data schemas
        """
        try:
            logger.info("Generating structured data schemas")

            # Generate Article schema
            article_schema = self._generate_article_schema(seo_metadata, blog_data)

            # Generate BreadcrumbList schema
            breadcrumb_schema = self._generate_breadcrumb_schema(seo_metadata)

            # Generate Organization schema
            organization_schema = self._generate_organization_schema()

            # Generate Website schema
            website_schema = self._generate_website_schema()

            structured_data = {
                "article_schema": article_schema,
                "breadcrumb_schema": breadcrumb_schema,
                "organization_schema": organization_schema,
                "website_schema": website_schema,
            }

            logger.info("✅ Structured data generated successfully")
            return structured_data

        except Exception as e:
            logger.error(f"Error generating structured data: {e}", exc_info=True)
            return {
                "article_schema": {},
                "breadcrumb_schema": {},
                "organization_schema": {},
                "website_schema": {},
            }

    def _generate_article_schema(
        self,
        seo_metadata: Dict[str, Any],
        blog_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate Article schema (JSON-LD).

        Args:
            seo_metadata: SEO metadata
            blog_data: Blog data

        Returns:
            Article schema dictionary
        """
        base_url = getattr(settings, "BACKEND_API_BASE_URL", "http://localhost:8000")
        canonical_url = seo_metadata.get("canonical_url", "")
        seo_title = seo_metadata.get("seo_title", blog_data.get("topic", ""))
        meta_description = seo_metadata.get("meta_description", "")
        
        # Get images
        image_urls = blog_data.get("image_urls", [])
        images = [{"@type": "ImageObject", "url": url} for url in image_urls[:5]]  # Limit to 5 images
        
        # If no images, use default
        if not images:
            images = [{"@type": "ImageObject", "url": f"{base_url}/static/default-blog-image.jpg"}]

        # Get dates
        created_at = blog_data.get("created_at")
        if isinstance(created_at, str):
            date_published = created_at
        elif hasattr(created_at, "isoformat"):
            date_published = created_at.isoformat()
        else:
            date_published = datetime.utcnow().isoformat()

        # Get author info (from user data)
        username = blog_data.get("username", "Author")
        author_name = blog_data.get("email", username)

        # Get organization info
        organization_name = blog_data.get("organization_name", "Blog Platform")
        organization_id = blog_data.get("organization_id", "")

        article_schema = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": seo_title,
            "description": meta_description,
            "image": images,
            "datePublished": date_published,
            "dateModified": date_published,
            "author": {
                "@type": "Person",
                "name": author_name,
            },
            "publisher": {
                "@type": "Organization",
                "name": organization_name,
                "logo": {
                    "@type": "ImageObject",
                    "url": f"{base_url}/static/logo.png",
                },
            },
            "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": canonical_url,
            },
        }

        # Add keywords if available
        keywords = seo_metadata.get("keywords", [])
        if keywords:
            article_schema["keywords"] = ", ".join(keywords[:10])

        return article_schema

    def _generate_breadcrumb_schema(self, seo_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate BreadcrumbList schema (JSON-LD).

        Args:
            seo_metadata: SEO metadata

        Returns:
            BreadcrumbList schema dictionary
        """
        base_url = getattr(settings, "BACKEND_API_BASE_URL", "http://localhost:8000")
        seo_title = seo_metadata.get("seo_title", "Blog Post")

        breadcrumb_schema = {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": 1,
                    "name": "Home",
                    "item": base_url,
                },
                {
                    "@type": "ListItem",
                    "position": 2,
                    "name": "Blog",
                    "item": f"{base_url}/blog",
                },
                {
                    "@type": "ListItem",
                    "position": 3,
                    "name": seo_title,
                    "item": seo_metadata.get("canonical_url", ""),
                },
            ],
        }

        return breadcrumb_schema

    def _generate_organization_schema(self) -> Dict[str, Any]:
        """
        Generate Organization schema (JSON-LD).

        Returns:
            Organization schema dictionary
        """
        base_url = getattr(settings, "BACKEND_API_BASE_URL", "http://localhost:8000")
        organization_name = getattr(settings, "ORGANIZATION_NAME", "Blog Platform")

        organization_schema = {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": organization_name,
            "url": base_url,
            "logo": {
                "@type": "ImageObject",
                "url": f"{base_url}/static/logo.png",
            },
        }

        return organization_schema

    def _generate_website_schema(self) -> Dict[str, Any]:
        """
        Generate Website schema (JSON-LD).

        Returns:
            Website schema dictionary
        """
        base_url = getattr(settings, "BACKEND_API_BASE_URL", "http://localhost:8000")
        site_name = getattr(settings, "SITE_NAME", "Blog Platform")

        website_schema = {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": site_name,
            "url": base_url,
            "potentialAction": {
                "@type": "SearchAction",
                "target": {
                    "@type": "EntryPoint",
                    "urlTemplate": f"{base_url}/search?q={{search_term_string}}",
                },
                "query-input": "required name=search_term_string",
            },
        }

        return website_schema

    def format_json_ld(self, schema: Dict[str, Any]) -> str:
        """
        Format schema as JSON-LD script tag.

        Args:
            schema: Schema dictionary

        Returns:
            JSON-LD script tag HTML
        """
        import json
        json_str = json.dumps(schema, indent=2, ensure_ascii=False)
        return f'<script type="application/ld+json">\n{json_str}\n</script>'

