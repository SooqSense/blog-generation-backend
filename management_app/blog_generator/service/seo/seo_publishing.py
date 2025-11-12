"""
SEO Publishing Service.
Handles sitemap generation, robots.txt, RSS feed, and search engine pinging.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from django.conf import settings

logger = logging.getLogger(__name__)


class SEOPublishing:
    """Handles SEO publishing tasks like sitemap, robots.txt, and RSS."""

    def __init__(self):
        """Initialize SEO Publishing Service."""
        self.base_url = getattr(settings, "BACKEND_API_BASE_URL", "http://localhost:8000")

    def generate_sitemap_entry(
        self,
        blog_id: int,
        seo_metadata: Dict[str, Any],
        blog_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate sitemap entry for a blog post.

        Args:
            blog_id: Blog ID
            seo_metadata: SEO metadata
            blog_data: Blog data

        Returns:
            Sitemap entry dictionary
        """
        canonical_url = seo_metadata.get("canonical_url", "")
        created_at = blog_data.get("created_at")
        
        if isinstance(created_at, str):
            lastmod = created_at
        elif hasattr(created_at, "isoformat"):
            lastmod = created_at.isoformat()
        else:
            lastmod = datetime.utcnow().isoformat()

        # Determine priority and changefreq based on content
        word_count = seo_metadata.get("word_count", 0)
        if word_count > 2000:
            priority = "0.9"
            changefreq = "weekly"
        elif word_count > 1000:
            priority = "0.8"
            changefreq = "monthly"
        else:
            priority = "0.7"
            changefreq = "monthly"

        sitemap_entry = {
            "loc": canonical_url,
            "lastmod": lastmod,
            "changefreq": changefreq,
            "priority": priority,
        }

        return sitemap_entry

    def generate_robots_txt_content(self, allow_all: bool = True) -> str:
        """
        Generate robots.txt content.

        Args:
            allow_all: Whether to allow all crawlers

        Returns:
            robots.txt content
        """
        sitemap_url = f"{self.base_url}/sitemap.xml"

        if allow_all:
            content = f"""User-agent: *
Allow: /

Sitemap: {sitemap_url}
"""
        else:
            content = f"""User-agent: *
Disallow: /

Sitemap: {sitemap_url}
"""

        return content

    def generate_rss_entry(
        self,
        blog_id: int,
        seo_metadata: Dict[str, Any],
        blog_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate RSS feed entry for a blog post.

        Args:
            blog_id: Blog ID
            seo_metadata: SEO metadata
            blog_data: Blog data

        Returns:
            RSS entry dictionary
        """
        canonical_url = seo_metadata.get("canonical_url", "")
        seo_title = seo_metadata.get("seo_title", blog_data.get("topic", ""))
        meta_description = seo_metadata.get("meta_description", "")
        
        # Get images
        image_urls = blog_data.get("image_urls", [])
        image_url = image_urls[0] if image_urls else ""

        # Get dates
        created_at = blog_data.get("created_at")
        if isinstance(created_at, str):
            pub_date = created_at
        elif hasattr(created_at, "isoformat"):
            pub_date = created_at.isoformat()
        else:
            pub_date = datetime.utcnow().isoformat()

        # Get author
        author = blog_data.get("username", "Author")
        author_email = blog_data.get("email", "")

        rss_entry = {
            "title": seo_title,
            "link": canonical_url,
            "description": meta_description,
            "author": f"{author_email} ({author})" if author_email else author,
            "pubDate": pub_date,
            "guid": canonical_url,
            "image": image_url,
        }

        return rss_entry

    def ping_search_engines(
        self,
        sitemap_url: str,
        ping_google: bool = True,
        ping_bing: bool = True,
    ) -> Dict[str, Any]:
        """
        Ping search engines to notify about sitemap updates.

        Args:
            sitemap_url: URL of the sitemap
            ping_google: Whether to ping Google
            ping_bing: Whether to ping Bing

        Returns:
            Dictionary with ping results
        """
        results = {
            "google": {"pinged": False, "success": False, "error": None},
            "bing": {"pinged": False, "success": False, "error": None},
        }

        if ping_google:
            try:
                import requests
                google_url = f"https://www.google.com/ping?sitemap={sitemap_url}"
                response = requests.get(google_url, timeout=10)
                results["google"]["pinged"] = True
                results["google"]["success"] = response.status_code == 200
                if response.status_code != 200:
                    results["google"]["error"] = f"HTTP {response.status_code}"
            except Exception as e:
                results["google"]["pinged"] = True
                results["google"]["error"] = str(e)
                logger.warning(f"Failed to ping Google: {e}")

        if ping_bing:
            try:
                import requests
                bing_url = f"https://www.bing.com/ping?sitemap={sitemap_url}"
                response = requests.get(bing_url, timeout=10)
                results["bing"]["pinged"] = True
                results["bing"]["success"] = response.status_code == 200
                if response.status_code != 200:
                    results["bing"]["error"] = f"HTTP {response.status_code}"
            except Exception as e:
                results["bing"]["pinged"] = True
                results["bing"]["error"] = str(e)
                logger.warning(f"Failed to ping Bing: {e}")

        return results

