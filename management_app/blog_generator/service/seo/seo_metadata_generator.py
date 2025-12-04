"""
SEO Metadata Generator.
Generates SEO-optimized metadata including title, description, keywords, slug, and canonical URL.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from crewai import Crew, Process
from django.conf import settings

from ..blog_writing.agents.seo_specialist_agent import SEOSpecialistAgent
from ..blog_writing.tasks.seo_tasks import SEOTasks
from .seo_utils import SEOUtils

logger = logging.getLogger(__name__)


class SEOMetadataGenerator:
    """Generates comprehensive SEO metadata for blog posts."""

    def __init__(self, llm, use_custom_llm: bool = False):
        """
        Initialize SEO Metadata Generator.

        Args:
            llm: Language model instance
            use_custom_llm: Whether to use custom LLM (Gemini) instead of OpenAI
        """
        self.llm = llm
        self.use_custom_llm = use_custom_llm

    def generate_metadata(
        self,
        topic: str,
        blog_type: str,
        markdown_content: str,
        image_urls: Optional[List[str]] = None,
        research_sources: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Generate comprehensive SEO metadata using SEO Specialist Agent.

        Args:
            topic: Blog topic
            blog_type: Type of blog (News, Comparison, etc.)
            markdown_content: Complete markdown content
            image_urls: List of image URLs
            research_sources: List of research sources

        Returns:
            Dictionary containing all SEO metadata
        """
        try:
            logger.info(f"Generating SEO metadata for topic: {topic}")

            # Initialize SEO agent and tasks
            seo_agent = SEOSpecialistAgent(llm=self.llm, topic=topic, blog_type=blog_type)
            seo_tasks = SEOTasks(
                topic=topic,
                blog_type=blog_type,
                markdown_content=markdown_content,
                image_urls=image_urls or [],
                research_sources=research_sources or [],
            )

            # Create crew and run SEO optimization task
            seo_crew = Crew(
                agents=[seo_agent.seo_specialist()],
                tasks=[seo_tasks.seo_optimization_task(seo_agent.seo_specialist())],
                process=Process.sequential,
                verbose=False,
            )

            # Execute SEO optimization
            result = seo_crew.kickoff(inputs={"topic": topic})
            raw_result = getattr(result, "raw", None) or str(result)

            # Parse JSON response
            seo_data = self._parse_seo_result(raw_result)

            # Validate and enhance metadata
            metadata = self._enhance_metadata(seo_data, topic, markdown_content)

            logger.info("✅ SEO metadata generated successfully")
            return metadata

        except Exception as e:
            logger.error(f"Error generating SEO metadata: {e}", exc_info=True)
            # Return fallback metadata
            return self._generate_fallback_metadata(topic, markdown_content)

    def _parse_seo_result(self, raw_result: str) -> Dict[str, Any]:
        """
        Parse SEO agent result (JSON).

        Args:
            raw_result: Raw result from SEO agent

        Returns:
            Parsed SEO data dictionary
        """
        try:
            # Try to extract JSON from the result
            # The result might be wrapped in markdown code blocks or have extra text
            cleaned = raw_result.strip()
            
            # Remove markdown code blocks if present
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            
            cleaned = cleaned.strip()
            
            # Try to find JSON object in the text
            start_idx = cleaned.find("{")
            end_idx = cleaned.rfind("}") + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = cleaned[start_idx:end_idx]
                return json.loads(json_str)
            else:
                # Try parsing the whole string
                return json.loads(cleaned)
        
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse SEO result as JSON: {e}")
            logger.debug(f"Raw result: {raw_result[:500]}")
            return {}

    def _enhance_metadata(
        self,
        seo_data: Dict[str, Any],
        topic: str,
        markdown_content: str,
    ) -> Dict[str, Any]:
        """
        Enhance and validate SEO metadata.

        Args:
            seo_data: SEO data from agent
            topic: Blog topic
            markdown_content: Blog content

        Returns:
            Enhanced metadata dictionary
        """
        # Extract basic metadata
        seo_title = seo_data.get("seo_title", topic)
        meta_description = seo_data.get("meta_description", "")
        keywords = seo_data.get("keywords", [])
        slug = seo_data.get("slug", "")

        # Validate and fix title
        if not seo_title or len(seo_title) < 30:
            seo_title = topic[:60] if len(topic) <= 60 else topic[:57] + "..."
        elif len(seo_title) > 60:
            seo_title = seo_title[:57] + "..."

        # Validate and fix meta description
        if not meta_description or len(meta_description) < 120:
            # Generate fallback description
            word_count = SEOUtils.count_words(markdown_content)
            meta_description = f"Comprehensive {word_count}-word article about {topic}. Read more to discover insights and analysis."
            if len(meta_description) > 160:
                meta_description = meta_description[:157] + "..."
        elif len(meta_description) > 160:
            meta_description = meta_description[:157] + "..."

        # Generate slug if not provided
        if not slug:
            slug = SEOUtils.generate_slug(seo_title or topic)

        # Generate canonical URL
        base_url = getattr(settings, "BACKEND_API_BASE_URL", "http://localhost:8000")
        canonical_url = SEOUtils.generate_canonical_url(base_url, slug)

        # Calculate content metrics
        word_count = SEOUtils.count_words(markdown_content)
        reading_time = SEOUtils.calculate_reading_time(word_count)
        content_hash = SEOUtils.generate_content_hash(markdown_content)

        # Build enhanced metadata
        metadata = {
            "seo_title": seo_title,
            "meta_description": meta_description,
            "keywords": keywords if keywords else SEOUtils.extract_keywords_from_text(markdown_content),
            "slug": slug,
            "canonical_url": canonical_url,
            "reading_time_minutes": reading_time,
            "word_count": word_count,
            "content_hash": content_hash,
            "heading_structure": seo_data.get("heading_structure", {}),
            "keyword_analysis": seo_data.get("keyword_analysis", {}),
            "internal_linking": seo_data.get("internal_linking", {}),
            "image_optimization": seo_data.get("image_optimization", {}),
            "content_metrics": {
                "word_count": word_count,
                "reading_time_minutes": reading_time,
                "readability_score": seo_data.get("content_metrics", {}).get("readability_score", "unknown"),
                "content_hash": content_hash,
            },
            "structured_data_recommendations": seo_data.get("structured_data_recommendations", {}),
            "social_metadata": seo_data.get("social_metadata", {}),
            "optimization_recommendations": seo_data.get("optimization_recommendations", []),
            "seo_score": seo_data.get("seo_score", 0),
            "is_ai_generated": seo_data.get("is_ai_generated", True),
        }

        return metadata

    def _generate_fallback_metadata(self, topic: str, markdown_content: str) -> Dict[str, Any]:
        """
        Generate fallback metadata if SEO agent fails.

        Args:
            topic: Blog topic
            markdown_content: Blog content

        Returns:
            Basic metadata dictionary
        """
        word_count = SEOUtils.count_words(markdown_content)
        reading_time = SEOUtils.calculate_reading_time(word_count)
        slug = SEOUtils.generate_slug(topic)
        base_url = getattr(settings, "BACKEND_API_BASE_URL", "http://localhost:8000")
        canonical_url = SEOUtils.generate_canonical_url(base_url, slug)

        return {
            "seo_title": topic[:60] if len(topic) <= 60 else topic[:57] + "...",
            "meta_description": f"Comprehensive article about {topic}. Read more to discover insights and analysis."[:160],
            "keywords": SEOUtils.extract_keywords_from_text(markdown_content),
            "slug": slug,
            "canonical_url": canonical_url,
            "reading_time_minutes": reading_time,
            "word_count": word_count,
            "content_hash": SEOUtils.generate_content_hash(markdown_content),
            "heading_structure": {},
            "keyword_analysis": {},
            "internal_linking": {},
            "image_optimization": {},
            "content_metrics": {
                "word_count": word_count,
                "reading_time_minutes": reading_time,
                "readability_score": "unknown",
                "content_hash": SEOUtils.generate_content_hash(markdown_content),
            },
            "structured_data_recommendations": {},
            "social_metadata": {},
            "optimization_recommendations": [],
            "seo_score": 0,
            "is_ai_generated": True,
        }

