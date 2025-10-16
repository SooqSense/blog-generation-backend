from crewai import Agent
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from django.conf import settings
import re
import random
import logging

logger = logging.getLogger(__name__)


class ContextualImagePromptAgent:
    """
    AI agent that generates diverse, contextually appropriate image prompts for blog sections.

    Key Features:
    - Analyzes topic and section content for visual direction
    - Generates varied, realistic styles (photo, illustration, infographic, etc.)
    - Ensures professional, ultra-clean, artifact-free prompts
    """

    def __init__(self, use_custom_llm=False):
        """
        Initialize the contextual image prompt agent

        Args:
            use_custom_llm (bool): Use Google Gemini (True) or OpenAI (False)
        """
        self.use_custom_llm = use_custom_llm

        # Initialize model from Django settings
        if use_custom_llm:
            gemini_api_key = getattr(settings, "GOOGLE_API_KEY", None)
            if not gemini_api_key:
                raise ValueError("GOOGLE_API_KEY missing in Django settings")
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-pro",
                google_api_key=gemini_api_key,
                temperature=0.8
            )
        else:
            openai_api_key = getattr(settings, "OPENAI_API_KEY", None)
            if not openai_api_key:
                raise ValueError("OPENAI_API_KEY missing in Django settings")
            self.llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.8,
                max_tokens=2000,
                openai_api_key=openai_api_key
            )

        # Preferred visual styles by domain
        self.style_preferences = {
            'technology': ['ultra-clean professional photography', 'crystal-clear futuristic illustration', 'pristine technical diagram', 'premium tech photography'],
            'business': ['ultra-realistic professional photography', 'crystal-clear infographic', 'pristine corporate illustration', 'premium data visualization'],
            'science': ['crystal-clear scientific illustration', 'ultra-clean infographic', 'pristine technical diagram', 'professional abstract visualization'],
            'healthcare': ['ultra-clean medical illustration', 'crystal-clear professional photography', 'pristine scientific visualization', 'premium medical infographic'],
            'education': ['crystal-clear educational illustration', 'ultra-clean infographic', 'pristine conceptual art', 'premium professional photography'],
            'finance': ['ultra-clean data visualization', 'crystal-clear professional photography', 'pristine minimalist illustration', 'premium financial infographic'],
            'environment': ['ultra-realistic nature photography', 'crystal-clear environmental illustration', 'pristine conceptual art', 'premium professional photography'],
            'politics': ['ultra-realistic professional photography', 'crystal-clear editorial illustration', 'pristine infographic', 'premium documentary style'],
            'culture': ['crystal-clear artistic illustration', 'ultra-realistic creative photography', 'pristine cultural art', 'premium conceptual design'],
            'sports': ['ultra-realistic action photography', 'crystal-clear dynamic illustration', 'pristine sports infographic', 'premium professional photography']
        }

        logger.info(f"✅ ContextualImagePromptAgent initialized (LLM: {'Gemini' if use_custom_llm else 'OpenAI'})")

    # -------------------------------------------------------------------------
    # ANALYSIS METHODS
    # -------------------------------------------------------------------------

    def analyze_topic_domain(self, topic):
        """Identify the main domain and visual preferences for the topic."""
        topic_lower = topic.lower()
        domain_keywords = {
            'technology': ['ai', 'artificial intelligence', 'machine learning', 'tech', 'software', 'digital', 'cyber', 'robot', 'automation', 'algorithm', 'data', 'computer', 'internet', 'blockchain', 'cryptocurrency'],
            'business': ['business', 'marketing', 'startup', 'company', 'corporate', 'entrepreneurship', 'management', 'leadership', 'strategy', 'sales', 'revenue', 'profit', 'market', 'industry'],
            'science': ['science', 'research', 'study', 'experiment', 'discovery', 'innovation', 'biology', 'chemistry', 'physics', 'medicine', 'pharmaceutical', 'clinical'],
            'healthcare': ['health', 'medical', 'medicine', 'hospital', 'doctor', 'patient', 'treatment', 'therapy', 'disease', 'healthcare', 'wellness', 'diagnosis'],
            'education': ['education', 'learning', 'school', 'university', 'student', 'teacher', 'academic', 'curriculum', 'training', 'knowledge', 'skill'],
            'finance': ['finance', 'financial', 'investment', 'banking', 'money', 'economy', 'economic', 'stock', 'cryptocurrency', 'trading', 'insurance', 'loan'],
            'environment': ['environment', 'climate', 'sustainability', 'green', 'renewable', 'energy', 'carbon', 'pollution', 'conservation', 'ecosystem', 'nature'],
            'politics': ['politics', 'political', 'government', 'policy', 'election', 'democracy', 'law', 'legal', 'regulation', 'legislation', 'public'],
            'culture': ['culture', 'cultural', 'art', 'music', 'entertainment', 'media', 'social', 'community', 'lifestyle', 'creative', 'design'],
            'sports': ['sports', 'athletic', 'fitness', 'exercise', 'competition', 'team', 'player', 'game', 'championship', 'training', 'performance']
        }

        # Score domain matches
        domain_scores = {d: sum(1 for kw in kws if kw in topic_lower) for d, kws in domain_keywords.items()}
        domain_scores = {d: s for d, s in domain_scores.items() if s > 0}
        primary_domain = max(domain_scores, key=domain_scores.get) if domain_scores else 'business'
        suggested_styles = self.style_preferences.get(primary_domain, ['professional photography', 'illustration'])

        return {
            'primary_domain': primary_domain,
            'domain_score': domain_scores.get(primary_domain, 0),
            'suggested_styles': suggested_styles,
            'topic_characteristics': self._extract_topic_characteristics(topic, primary_domain)
        }

    def _extract_topic_characteristics(self, topic, domain):
        """Identify qualitative features of the topic."""
        characteristics = {
            'complexity': 'medium',
            'data_heavy': any(x in topic.lower() for x in ['data', 'statistics', 'metrics', 'analysis']),
            'conceptual': any(x in topic.lower() for x in ['concept', 'idea', 'strategy']),
            'technical': any(x in topic.lower() for x in ['technical', 'engineering', 'system']),
            'human_focused': any(x in topic.lower() for x in ['people', 'user', 'team']),
            'process_oriented': any(x in topic.lower() for x in ['process', 'workflow', 'method', 'guide'])
        }
        return characteristics

    # -------------------------------------------------------------------------
    # AGENT CREATION
    # -------------------------------------------------------------------------

    def create_contextual_agent(self):
        """Create CrewAI Agent specialized in high-quality professional photography prompts."""
        return Agent(
            role="Professional Photography Prompt Specialist",
            goal="Generate ultra-clean, photorealistic prompts for professional photography.",
            backstory="""You are an elite photography prompt engineer, specializing in magazine-quality
            imagery with perfect clarity, realistic lighting, and zero AI artifacts.""",
            llm=self.llm,
            verbose=False,
            allow_delegation=False
        )

    # -------------------------------------------------------------------------
    # SECTION ANALYSIS + PROMPT GENERATION
    # -------------------------------------------------------------------------

    def analyze_section_context(self, section_content, section_name, topic, blog_type):
        """Analyze section and generate a contextually relevant image prompt."""
        topic_analysis = self.analyze_topic_domain(topic)
        content_analysis = self._analyze_content_characteristics(section_content, section_name)
        selected_style = self._select_visual_style(section_name, topic_analysis, content_analysis)

        try:
            enhanced_prompt = self._generate_enhanced_prompt(
                section_content, section_name, topic, blog_type,
                topic_analysis, content_analysis, selected_style
            )
            logger.debug(f"Generated prompt for {section_name} ({selected_style}): {enhanced_prompt[:100]}...")
            return enhanced_prompt
        except Exception as e:
            logger.error(f"Prompt generation failed for {section_name}: {e}")
            return self._generate_fallback_prompt(section_content, section_name, topic, blog_type, selected_style)

    def _analyze_content_characteristics(self, content, section_name):
        """Light content analysis for visual requirements."""
        if not content:
            return {'type': 'general', 'elements': [], 'data_present': False, 'concepts': []}

        content_lower = content.lower()
        analysis = {'type': 'general', 'elements': [], 'data_present': False, 'concepts': []}

        if any(k in content_lower for k in ['data', 'statistics', 'percent']):
            analysis['type'] = 'data_driven'
            analysis['data_present'] = True
        elif any(k in content_lower for k in ['process', 'workflow', 'method']):
            analysis['type'] = 'process'
        elif any(k in content_lower for k in ['concept', 'idea']):
            analysis['type'] = 'conceptual'
        elif any(k in content_lower for k in ['technical', 'system']):
            analysis['type'] = 'technical'
        elif any(k in content_lower for k in ['people', 'team', 'human']):
            analysis['type'] = 'human_centered'

        return analysis

    def _select_visual_style(self, section_name, topic_analysis, content_analysis):
        """Match visual style to domain and section type."""
        domain = topic_analysis['primary_domain']
        available_styles = self.style_preferences.get(domain, ['professional photography', 'illustration'])
        return random.choice(available_styles)

    # -------------------------------------------------------------------------
    # PROMPT GENERATION + CLEANUP
    # -------------------------------------------------------------------------

    def _generate_enhanced_prompt(self, section_content, section_name, topic, blog_type,
                                  topic_analysis, content_analysis, selected_style):
        """Generate enhanced AI prompt based on section and topic context."""
        context_prompt = f"""
Topic: {topic}
Section: {section_name}
Domain: {topic_analysis['primary_domain']}
Selected Style: {selected_style}
Blog Type: {blog_type}
Content (excerpt): {section_content[:400]}

Generate a single ultra-clean, crystal-clear image generation prompt with:
- {selected_style} style
- professional aesthetics, zero AI artifacts
- perfect lighting, clean composition, realistic appearance
- contextually relevant to {section_name} of a {blog_type} blog about {topic}
Output only the final prompt, no commentary.
"""
        response = self.llm.invoke(context_prompt)
        prompt = getattr(response, "content", str(response)).strip()
        return self._clean_generated_prompt(prompt)

    def _clean_generated_prompt(self, prompt):
        """Sanitize AI-generated prompt text."""
        if not prompt:
            return ""
        clean = re.sub(r"^(Prompt:|Image prompt:|Generated prompt:)\s*", "", prompt, flags=re.I)
        clean = clean.strip().strip('"').strip("'")
        if not any(t in clean.lower() for t in ['ultra-realistic', 'crystal clear']):
            clean = f"Ultra-realistic professional photograph, {clean}, crystal clear, perfect lighting, clean composition, magazine quality, zero AI artifacts"
        return clean

    def _generate_fallback_prompt(self, section_content, section_name, topic, blog_type, selected_style):
        """Fallback ultra-clean prompt."""
        concept = topic.split()[0] if topic else "subject"
        return (f"Ultra-realistic professional photograph of {concept} related to {topic}, "
                f"{selected_style}, crystal clear focus, perfect lighting, clean composition, "
                f"magazine quality, pristine image quality, zero AI artifacts.")

    # -------------------------------------------------------------------------
    # BULK PROMPT GENERATION
    # -------------------------------------------------------------------------

    def generate_section_prompts(self, content_sections, topic, blog_type):
        """Generate contextual prompts for all standard blog sections."""
        section_prompts = {}
        sections = {
            'banner': content_sections.get('introduction', ''),
            'main_content': content_sections.get('main_content', ''),
            'supporting_details': content_sections.get('supporting_details', ''),
            'evidence': content_sections.get('evidence', ''),
            'conclusion': content_sections.get('conclusion', '')
        }

        logger.info(f"🧠 Generating contextual prompts for topic '{topic}' ({blog_type})")

        for section_name, content in sections.items():
            try:
                if content.strip():
                    section_prompts[section_name] = self.analyze_section_context(
                        content, section_name, topic, blog_type
                    )
                else:
                    topic_analysis = self.analyze_topic_domain(topic)
                    style = random.choice(topic_analysis['suggested_styles'])
                    section_prompts[section_name] = self._generate_fallback_prompt(
                        "", section_name, topic, blog_type, style
                    )
            except Exception as e:
                logger.error(f"Error in {section_name}: {e}")
                section_prompts[section_name] = f"Ultra-realistic professional photograph related to {topic}, crystal clear, clean composition, magazine quality."

        logger.info(f"✅ Generated {len(section_prompts)} section prompts for '{topic}'")
        return section_prompts
