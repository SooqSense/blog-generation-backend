"""
Extraction module for blog generation.
Handles content extraction from various sources including websites.
"""

from .firecrawl_extractor import FirecrawlExtractor

__all__ = ["FirecrawlExtractor"]
