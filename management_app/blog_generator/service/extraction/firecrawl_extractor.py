"""
Firecrawl content extraction service.
Extracts and processes content from websites using Firecrawl API.
"""

import logging
from typing import List, Dict, Any, Optional
from django.conf import settings
import requests

logger = logging.getLogger(__name__)


class FirecrawlExtractor:
    """
    Service for extracting content from websites using Firecrawl API.
    Provides clean, structured content extraction for blog generation.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Firecrawl extractor.

        Args:
            api_key: Firecrawl API key. If not provided, uses settings.FIRECRAWL_API_KEY
        """
        self.api_key = api_key or getattr(settings, "FIRECRAWL_API_KEY", None)
        if not self.api_key:
            raise ValueError(
                "Firecrawl API key is required. Set FIRECRAWL_API_KEY in settings or pass it to the constructor."
            )
        
        self.base_url = "https://api.firecrawl.dev/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def scrape_url(self, url: str, formats: List[str] = None) -> Dict[str, Any]:
        """
        Scrape a single URL using Firecrawl API.

        Args:
            url: The URL to scrape
            formats: List of formats to return (e.g., ["markdown", "html"]). Defaults to ["markdown"]

        Returns:
            Dict containing scraped content and metadata

        Raises:
            requests.RequestException: If the API request fails
        """
        if formats is None:
            formats = ["markdown"]

        endpoint = f"{self.base_url}/scrape"
        payload = {
            "url": url,
            "formats": formats,
        }

        try:
            logger.info(f"Scraping URL with Firecrawl: {url}")
            response = requests.post(
                endpoint,
                json=payload,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Successfully scraped URL: {url}")
            return data
            
        except requests.RequestException as e:
            logger.error(f"Failed to scrape URL {url}: {str(e)}")
            raise

    def extract_content_from_urls(
        self, 
        urls: List[str], 
        formats: List[str] = None
    ) -> Dict[str, Any]:
        """
        Extract content from multiple URLs.

        Args:
            urls: List of URLs to extract content from
            formats: List of formats to return. Defaults to ["markdown"]

        Returns:
            Dict containing:
                - combined_content: All extracted content combined
                - sources: List of successfully scraped sources with metadata
                - failed_urls: List of URLs that failed to scrape
        """
        if not urls:
            logger.warning("No URLs provided for extraction")
            return {
                "combined_content": "",
                "sources": [],
                "failed_urls": []
            }

        if formats is None:
            formats = ["markdown"]

        combined_content = []
        sources = []
        failed_urls = []

        for url in urls:
            try:
                result = self.scrape_url(url, formats=formats)
                
                # Extract content based on format
                content = ""
                if "data" in result:
                    data = result["data"]
                    if "markdown" in data:
                        content = data["markdown"]
                    elif "html" in data:
                        content = data["html"]
                    
                    # Add source metadata
                    source_info = {
                        "url": url,
                        "title": data.get("metadata", {}).get("title", url),
                        "description": data.get("metadata", {}).get("description", ""),
                        "content_length": len(content),
                    }
                    sources.append(source_info)
                    
                    # Add to combined content with source attribution
                    if content:
                        combined_content.append(f"\n\n--- Source: {url} ---\n\n{content}")
                
            except Exception as e:
                logger.error(f"Failed to extract content from {url}: {str(e)}")
                failed_urls.append(url)

        # Combine all content
        final_content = "\n".join(combined_content)
        
        logger.info(
            f"Extracted content from {len(sources)}/{len(urls)} URLs. "
            f"Total content length: {len(final_content)} characters"
        )

        return {
            "combined_content": final_content,
            "sources": sources,
            "failed_urls": failed_urls,
        }

    def extract_and_summarize(
        self, 
        urls: List[str], 
        max_length: int = 10000
    ) -> str:
        """
        Extract content from URLs and return a summarized version suitable for blog context.

        Args:
            urls: List of URLs to extract content from
            max_length: Maximum length of combined content (truncates if exceeded)

        Returns:
            Summarized content string
        """
        result = self.extract_content_from_urls(urls)
        content = result["combined_content"]
        
        # Truncate if too long
        if len(content) > max_length:
            logger.warning(
                f"Extracted content ({len(content)} chars) exceeds max_length ({max_length}). Truncating."
            )
            content = content[:max_length] + "\n\n[Content truncated...]"
        
        return content
