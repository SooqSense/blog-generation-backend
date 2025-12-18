import re
import logging
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from django.conf import settings

logger = logging.getLogger(__name__)


class ContextualImagePromptAgent:
    """
    Agent that generates contextually accurate, professional-grade AI image prompts
    for each section of a blog post.

    Integrated into BlogWriter: called after each section is written.
    """

    def __init__(self, use_custom_llm=False):
        """
        Initialize the contextual image prompt agent.

        Args:
            use_custom_llm (bool): Use Google Gemini (True) or OpenAI (False)
        """
        self.use_custom_llm = use_custom_llm
        self.llm = self._init_llm()

        # Preferred visual styles by domain
        self.style_preferences = {
            'technology': 'ultra-clean professional photography, futuristic lighting, modern digital setting',
            'business': 'professional corporate photography, clean infographic aesthetic, realistic office setting',
            'science': 'crystal-clear scientific illustration, technical visualization, minimal lab environment',
            'healthcare': 'ultra-clean medical photography, bright hospital environment, professional lighting',
            'education': 'clear conceptual illustration, classroom or digital learning setting, bright tone',
            'finance': 'professional photography, clean charts and infographics, data visualization style',
            'environment': 'realistic environmental photography, natural lighting, scenic outdoor composition',
            'politics': 'editorial professional photography, conference or public setting, journalistic tone',
            'culture': 'creative cultural photography, artistic lighting, storytelling composition',
            'sports': 'dynamic action photography, realistic motion capture, professional sports setting'
        }

    # ---------------------------------------------------------------------
    # INIT LLM
    # ---------------------------------------------------------------------
    def _init_llm(self):
        """Initialize LLM model."""
        if self.use_custom_llm:
            gemini_api_key = getattr(settings, "GOOGLE_API_KEY", None)
            if not gemini_api_key:
                raise ValueError("GOOGLE_API_KEY missing in Django settings")
            return ChatGoogleGenerativeAI(
                model="gemini-pro",
                google_api_key=gemini_api_key,
                temperature=0.8
            )
        else:
            openai_api_key = getattr(settings, "OPENAI_API_KEY", None)
            if not openai_api_key:
                raise ValueError("OPENAI_API_KEY missing in Django settings")
            return ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.8,
                max_tokens=1500,
                api_key=openai_api_key
            )

    # ---------------------------------------------------------------------
    # DOMAIN + CONTENT ANALYSIS
    # ---------------------------------------------------------------------
    def _detect_domain(self, topic):
        """Detect domain from topic keywords."""
        domains = {
            "technology": ["ai", "tech", "software", "digital", "automation"],
            "business": ["business", "startup", "corporate", "management", "marketing"],
            "science": ["research", "experiment", "science", "innovation"],
            "healthcare": ["medical", "health", "doctor", "patient", "wellness"],
            "education": ["education", "learning", "school", "academic"],
            "finance": ["finance", "investment", "bank", "money", "economy"],
            "environment": ["environment", "climate", "sustainability", "nature"],
            "politics": ["politics", "policy", "government", "election"],
            "culture": ["culture", "art", "creative", "media"],
            "sports": ["sports", "athlete", "competition", "fitness"]
        }
        topic_lower = topic.lower()
        for domain, kws in domains.items():
            if any(k in topic_lower for k in kws):
                return domain
        return "business"

    # ---------------------------------------------------------------------
    # MAIN PROMPT GENERATION
    # ---------------------------------------------------------------------
    def generate_prompt(self, topic, section_title, section_content, blog_type="Article"):
        """
        Generate a clean, contextual image prompt for a blog section.

        Args:
            topic (str): Overall blog topic
            section_title (str): Title of the section
            section_content (str): Section text content
            blog_type (str): Type of blog (e.g. "Guide", "News", "Analysis")

        Returns:
            dict: {
                "prompt": str,
                "domain": str,
                "style": str
            }
        """
        domain = self._detect_domain(topic)
        style = self.style_preferences.get(domain, "professional photography, clean composition")

        base_context = f"""
You are an expert visual prompt engineer for professional editorial images.
Generate one highly detailed, realistic image prompt for an article section.

Topic: {topic}
Section Title: {section_title}
Section Content (excerpt): {section_content[:400]}
Blog Type: {blog_type}
Visual Style: {style}

Guidelines:
- Use ultra-clean professional tone
- Avoid generic or abstract phrases
- Mention the setting, subject, lighting, and mood
- No text, watermarks, or people with visible faces
- Keep it under 80 words
- Output only the final image prompt (no commentary)
"""

        try:
            response = self.llm.invoke(base_context)
            prompt_text = getattr(response, "content", str(response)).strip()
            prompt_text = self._clean_prompt(prompt_text)
        except Exception as e:
            logger.warning(f"⚠️ LLM image prompt failed for '{section_title}': {e}")
            prompt_text = self._fallback_prompt(topic, section_title, style)

        return {
            "prompt": prompt_text,
            "domain": domain,
            "style": style
        }

    # ---------------------------------------------------------------------
    # CLEANUP + FALLBACK
    # ---------------------------------------------------------------------
    def _clean_prompt(self, text):
        """Strip unnecessary formatting from model output."""
        text = re.sub(r"^(Prompt:|Image prompt:)\s*", "", text, flags=re.I)
        text = text.replace('"', '').replace("**", "").strip()
        return text

    def _fallback_prompt(self, topic, section_title, style):
        """Fallback safe prompt if LLM fails."""
        return (
            f"Professional editorial photograph showing the concept of '{section_title}' related to '{topic}', "
            f"in {style} style, clean composition, perfect lighting, no text or watermark."
        )
