"""
SEO Specialist Agent for blog content optimization.
Handles all 30 SEO rules through comprehensive content analysis and optimization.
"""

from crewai import Agent
from typing import Optional


class SEOSpecialistAgent:
    """SEO Specialist Agent that optimizes blog content according to all 30 SEO rules."""

    def __init__(self, llm, topic: str, blog_type: str = "News"):
        """
        Initialize SEO Specialist Agent.

        Args:
            llm: Language model instance (ChatOpenAI or ChatGoogleGenerativeAI)
            topic: Blog topic
            blog_type: Type of blog (News, Comparison, etc.)
        """
        self.llm = llm
        self.topic = topic
        self.blog_type = blog_type

    def seo_specialist(self) -> Agent:
        """
        Create SEO Specialist Agent with comprehensive SEO expertise.

        This agent is responsible for:
        - Analyzing content structure and SEO factors
        - Generating SEO-optimized metadata
        - Ensuring proper heading hierarchy
        - Identifying keyword opportunities
        - Recommending internal linking strategies
        - Validating content quality and SEO best practices
        """
        return Agent(
            role="Senior SEO Specialist",
            goal=(
                f"Analyze and optimize the blog post about '{self.topic}' "
                f"according to all 30 SEO best practices. Generate comprehensive SEO metadata, "
                "ensure proper content structure, validate heading hierarchy, identify keyword "
                "opportunities, and provide recommendations for internal linking, alt text, "
                "and content optimization to maximize search engine visibility and user engagement."
            ),
            backstory=(
                "You are a world-class SEO specialist with over 15 years of experience optimizing "
                "content for major search engines. You have deep expertise in on-page SEO, "
                "technical SEO, content optimization, structured data, and search engine algorithms. "
                "You understand the importance of user experience, content quality, and technical "
                "implementation in achieving top search rankings. Your approach combines data-driven "
                "analysis with creative optimization strategies to ensure content performs excellently "
                "in search results while providing genuine value to readers."
            ),
            verbose=True,
            llm=self.llm,
            allow_delegation=False,
        )

