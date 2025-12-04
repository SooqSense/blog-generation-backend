"""
SEO Processor - Main orchestrator for all SEO services.
Coordinates metadata generation, content optimization, structured data, and publishing.
"""

import logging
from typing import Dict, Any, Optional, List
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from django.conf import settings

from .seo_metadata_generator import SEOMetadataGenerator
from .seo_content_optimizer import SEOContentOptimizer
from .seo_structured_data import SEOStructuredData
from .seo_publishing import SEOPublishing
from .seo_utils import SEOUtils

logger = logging.getLogger(__name__)


class SEOProcessor:
    """Main processor that orchestrates all SEO optimization services."""

    def __init__(self, use_custom_llm: bool = False):
        """
        Initialize SEO Processor.

        Args:
            use_custom_llm: Whether to use Google Gemini instead of OpenAI
        """
        self.use_custom_llm = use_custom_llm
        self.llm = self._init_llm(use_custom_llm)
        
        # Initialize services
        self.metadata_generator = SEOMetadataGenerator(self.llm, use_custom_llm)
        self.content_optimizer = SEOContentOptimizer()
        self.structured_data_generator = SEOStructuredData()
        self.publishing_service = SEOPublishing()

    def _init_llm(self, use_custom_llm: bool):
        """Initialize language model."""
        if use_custom_llm:
            gemini_key = getattr(settings, "GOOGLE_API_KEY", None)
            if not gemini_key:
                raise ValueError("GOOGLE_API_KEY not found in Django settings")
            return ChatGoogleGenerativeAI(
                model="gemini-pro",
                google_api_key=gemini_key,
                temperature=0.4,
            )
        
        openai_key = getattr(settings, "OPENAI_API_KEY", None)
        if not openai_key:
            raise ValueError("OPENAI_API_KEY not found in Django settings")
        
        return ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.4,
            max_tokens=2000,
            api_key=openai_key,
        )

    def process_blog_for_seo(
        self,
        blog_instance,
        ping_search_engines: bool = False,
    ) -> Dict[str, Any]:
        """
        Process blog for comprehensive SEO optimization.

        Args:
            blog_instance: BlogGeneral model instance
            ping_search_engines: Whether to ping search engines after processing

        Returns:
            Complete SEO optimization results
        """
        try:
            logger.info(f"Processing blog ID {blog_instance.id} for SEO optimization")

            # Prepare blog data
            blog_data = {
                "id": blog_instance.id,
                "topic": blog_instance.topic,
                "content": blog_instance.content,
                "image_urls": blog_instance.image_urls or [],
                "username": blog_instance.username,
                "email": blog_instance.email,
                "organization_name": blog_instance.organization_name,
                "organization_id": blog_instance.organization_id,
                "created_at": blog_instance.created_at,
            }

            # Step 1: Generate SEO metadata
            logger.info("Step 1: Generating SEO metadata...")
            seo_metadata = self.metadata_generator.generate_metadata(
                topic=blog_instance.topic,
                blog_type="News",  # Could be made dynamic
                markdown_content=blog_instance.content,
                image_urls=blog_instance.image_urls or [],
                research_sources=[],  # Could be added to model if needed
            )

            # Step 2: Optimize content (Markdown → HTML)
            logger.info("Step 2: Optimizing content...")
            content_optimization = self.content_optimizer.optimize_content(
                markdown_content=blog_instance.content,
                seo_metadata=seo_metadata,
                image_urls=blog_instance.image_urls or [],
            )

            # Step 3: Generate structured data
            logger.info("Step 3: Generating structured data...")
            structured_data = self.structured_data_generator.generate_structured_data(
                seo_metadata=seo_metadata,
                blog_data=blog_data,
            )

            # Step 4: Generate publishing data (sitemap, RSS)
            logger.info("Step 4: Generating publishing data...")
            sitemap_entry = self.publishing_service.generate_sitemap_entry(
                blog_id=blog_instance.id,
                seo_metadata=seo_metadata,
                blog_data=blog_data,
            )
            
            rss_entry = self.publishing_service.generate_rss_entry(
                blog_id=blog_instance.id,
                seo_metadata=seo_metadata,
                blog_data=blog_data,
            )

            # Step 5: Ping search engines (optional)
            search_engine_ping = None
            if ping_search_engines:
                logger.info("Step 5: Pinging search engines...")
                sitemap_url = f"{self.publishing_service.base_url}/sitemap.xml"
                search_engine_ping = self.publishing_service.ping_search_engines(sitemap_url)

            # Compile results
            results = {
                "status": "success",
                "blog_id": blog_instance.id,
                "seo_metadata": seo_metadata,
                "html_content": content_optimization.get("html_content", ""),
                "full_html": content_optimization.get("full_html", ""),
                "html_validation": content_optimization.get("html_validation", {}),
                "structured_data": structured_data,
                "sitemap_entry": sitemap_entry,
                "rss_entry": rss_entry,
                "optimization_applied": content_optimization.get("optimization_applied", {}),
                "search_engine_ping": search_engine_ping,
            }

            logger.info(f"✅ SEO processing completed for blog ID {blog_instance.id}")
            return results

        except Exception as e:
            logger.error(f"Error processing blog for SEO: {e}", exc_info=True)
            raise

    def update_blog_with_seo_data(
        self,
        blog_instance,
        seo_results: Dict[str, Any],
    ) -> None:
        """
        Update blog instance with SEO data.

        Args:
            blog_instance: BlogGeneral model instance
            seo_results: SEO processing results
        """
        try:
            seo_metadata = seo_results.get("seo_metadata", {})
            structured_data = seo_results.get("structured_data", {})

            # Update SEO metadata fields
            blog_instance.seo_title = seo_metadata.get("seo_title", "")
            blog_instance.seo_meta_description = seo_metadata.get("meta_description", "")
            blog_instance.seo_keywords = seo_metadata.get("keywords", [])
            blog_instance.seo_slug = seo_metadata.get("slug", "")
            blog_instance.canonical_url = seo_metadata.get("canonical_url", "")

            # Update content metrics
            blog_instance.reading_time_minutes = seo_metadata.get("reading_time_minutes", 0)
            blog_instance.word_count = seo_metadata.get("word_count", 0)
            blog_instance.content_hash = seo_metadata.get("content_hash", "")

            # Update HTML content
            blog_instance.html_content = seo_results.get("html_content", "")

            # Update social metadata
            social_metadata = seo_metadata.get("social_metadata", {})
            blog_instance.og_title = social_metadata.get("og_title", "")
            blog_instance.og_description = social_metadata.get("og_description", "")
            blog_instance.og_image_url = social_metadata.get("og_image", "")
            blog_instance.twitter_card_type = social_metadata.get("twitter_card", "summary_large_image")

            # Update structured data
            blog_instance.structured_data = structured_data

            # Mark as SEO optimized
            blog_instance.seo_optimized = True
            blog_instance.is_ai_generated = seo_metadata.get("is_ai_generated", True)

            # Save instance
            blog_instance.save()

            logger.info(f"✅ Blog ID {blog_instance.id} updated with SEO data")

        except Exception as e:
            logger.error(f"Error updating blog with SEO data: {e}", exc_info=True)
            raise

