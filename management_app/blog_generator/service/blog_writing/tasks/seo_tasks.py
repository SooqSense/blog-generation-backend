"""
SEO Tasks for the SEO Specialist Agent.
Defines tasks for comprehensive SEO optimization following all 30 SEO rules.
"""

from crewai import Task
from typing import Optional


class SEOTasks:
    """Tasks for SEO optimization workflow."""

    def __init__(
        self,
        topic: str,
        blog_type: str = "News",
        markdown_content: str = "",
        image_urls: Optional[list] = None,
        research_sources: Optional[list] = None,
    ):
        """
        Initialize SEO Tasks.

        Args:
            topic: Blog topic
            blog_type: Type of blog (News, Comparison, etc.)
            markdown_content: Complete markdown content of the blog
            image_urls: List of image URLs in the blog
            research_sources: List of research sources used
        """
        self.topic = topic
        self.blog_type = blog_type
        self.markdown_content = markdown_content
        self.image_urls = image_urls or []
        self.research_sources = research_sources or []

    def seo_optimization_task(self, agent) -> Task:
        """
        Create comprehensive SEO optimization task.

        This task covers all 30 SEO rules:
        - Metadata generation (title, description, keywords, slug, canonical)
        - Content structure validation (headings, internal linking)
        - Image optimization (alt text recommendations)
        - Content quality checks (readability, word count, duplicate detection)
        - Structured data recommendations
        - Social media metadata
        - Technical SEO factors
        """
        description = self._get_seo_optimization_prompt()
        expected_output = (
            "A comprehensive JSON object containing all SEO optimization data including: "
            "seo_title (50-60 chars), meta_description (150-160 chars), keywords (array), "
            "slug (URL-friendly), canonical_url, heading_structure_analysis, "
            "keyword_density_analysis, internal_linking_suggestions, alt_text_recommendations, "
            "content_quality_score, readability_metrics, and optimization_recommendations."
        )

        return Task(
            description=description,
            expected_output=expected_output,
            agent=agent,
        )

    def _get_seo_optimization_prompt(self) -> str:
        """Generate comprehensive SEO optimization prompt covering all 30 rules."""
        return f"""Analyze and optimize the following {self.blog_type.lower()} blog post about '{self.topic}' 
according to all 30 SEO best practices.

BLOG CONTENT (Markdown):
{self.markdown_content[:5000]}...

IMAGES IN BLOG: {len(self.image_urls)} images
RESEARCH SOURCES: {len(self.research_sources)} sources

SEO OPTIMIZATION REQUIREMENTS:

1. METADATA GENERATION:
   - Generate SEO-optimized title (50-60 characters, keyword-rich, compelling)
   - Create meta description (150-160 characters, includes primary keyword, call-to-action)
   - Extract and suggest 5-10 relevant keywords (primary + secondary)
   - Generate URL-friendly slug (lowercase, hyphens, no special chars)
   - Create canonical URL structure

2. CONTENT STRUCTURE ANALYSIS:
   - Validate heading hierarchy (H1 → H2 → H3, proper nesting)
   - Check heading distribution and balance
   - Identify missing or redundant headings
   - Ensure proper content flow and logical structure

3. KEYWORD OPTIMIZATION:
   - Analyze keyword density (target: 1-2% for primary keyword)
   - Identify keyword placement opportunities (title, headings, first paragraph, alt text)
   - Suggest LSI (Latent Semantic Indexing) keywords
   - Check for keyword stuffing (avoid over-optimization)

4. INTERNAL LINKING:
   - Identify opportunities for internal links based on topic relevance
   - Suggest anchor text for internal links
   - Recommend related content connections
   - Ensure natural link placement

5. IMAGE OPTIMIZATION:
   - Generate descriptive alt text for each image (if not provided)
   - Ensure alt text includes relevant keywords naturally
   - Verify image relevance to content
   - Check image-to-text ratio

6. CONTENT QUALITY:
   - Calculate reading time (average reading speed: 200-250 words/minute)
   - Count total words
   - Assess readability score
   - Check for duplicate content patterns
   - Validate content uniqueness

7. STRUCTURED DATA RECOMMENDATIONS:
   - Article schema requirements (author, date, image, publisher)
   - BreadcrumbList schema structure
   - Organization schema data
   - Website schema elements

8. SOCIAL MEDIA METADATA:
   - Open Graph title, description, image recommendations
   - Twitter Card type and content
   - Social sharing optimization

9. TECHNICAL SEO:
   - Content sanitization requirements
   - HTML structure recommendations
   - Mobile-friendliness considerations
   - Page speed optimization suggestions

10. CONTENT MODERATION:
    - Mark as AI-generated content (transparency)
    - Content review recommendations
    - Quality assurance checklist

OUTPUT FORMAT (STRICT JSON ONLY):
{{
    "seo_title": "Optimized title (50-60 chars)",
    "meta_description": "Compelling description (150-160 chars)",
    "keywords": ["primary", "secondary1", "secondary2", ...],
    "slug": "url-friendly-slug",
    "canonical_url": "https://domain.com/blog/url-friendly-slug",
    "heading_structure": {{
        "h1_count": 1,
        "h2_count": 5,
        "h3_count": 8,
        "hierarchy_valid": true,
        "recommendations": ["..."]
    }},
    "keyword_analysis": {{
        "primary_keyword": "...",
        "keyword_density": 1.5,
        "keyword_placement": {{
            "in_title": true,
            "in_first_paragraph": true,
            "in_headings": true,
            "in_meta_description": true
        }},
        "lsi_keywords": ["...", "..."]
    }},
    "internal_linking": {{
        "suggestions": [
            {{"anchor_text": "...", "target_topic": "...", "position": "section_name"}}
        ],
        "related_topics": ["...", "..."]
    }},
    "image_optimization": {{
        "alt_text_recommendations": [
            {{"image_index": 0, "alt_text": "...", "keyword_included": true}}
        ],
        "missing_alt_text_count": 0
    }},
    "content_metrics": {{
        "word_count": 1200,
        "reading_time_minutes": 5,
        "readability_score": "college",
        "content_hash": "sha256_hash_here"
    }},
    "structured_data_recommendations": {{
        "article_schema": {{
            "headline": "...",
            "author": {{"name": "...", "type": "Person"}},
            "publisher": {{"name": "...", "type": "Organization"}},
            "datePublished": "...",
            "image": ["..."]
        }},
        "breadcrumb_schema": {{
            "items": [
                {{"name": "Home", "position": 1}},
                {{"name": "Blog", "position": 2}},
                {{"name": "Article Title", "position": 3}}
            ]
        }}
    }},
    "social_metadata": {{
        "og_title": "...",
        "og_description": "...",
        "og_image": "...",
        "og_type": "article",
        "twitter_card": "summary_large_image",
        "twitter_title": "...",
        "twitter_description": "..."
    }},
    "optimization_recommendations": [
        "Recommendation 1",
        "Recommendation 2",
        ...
    ],
    "seo_score": 85,
    "is_ai_generated": true
}}

IMPORTANT:
- All text fields must be within specified character limits
- Keywords should be natural and relevant, not stuffed
- Recommendations should be actionable and specific
- JSON must be valid and complete
- Do not include any prose or explanations outside the JSON structure.
"""

