from crewai import Task
from ..prompts.prompts import BlogWriterPrompts


class BlogWriterTasks:
    """Tasks for the blog writing crew (TOC → Section Research → Section Writing → Editing)"""

    def __init__(
        self,
        topic,
        blog_type,
        length_min,
        length_max,
        target_audience=None,
        keywords=None,
        process_keywords_func=None,
        analyze_sample_blog_func=None,
    ):
        self.topic = topic
        self.blog_type = blog_type
        self.length_min = length_min
        self.length_max = length_max
        self.target_audience = target_audience or []
        self.keywords = keywords or []
        self.process_keywords_with_counts = process_keywords_func
        self.analyze_sample_blog = analyze_sample_blog_func

    # === 1. TOC Generation Task ===
    def toc_generation_task(self, agents):
        description = BlogWriterPrompts.get_toc_generation_prompt(self.topic, self.blog_type)
        expected_output = (
            f"A complete, data-driven Table of Contents for a {self.blog_type.lower()} blog post "
            f"about '{self.topic}', including 6–10 main sections with brief descriptions."
        )

        return Task(
            description=description,
            expected_output=expected_output,
            agent=agents.toc_builder(),
        )

    # === 2. Section Research Task ===
    def section_research_task(self, agents, section_title):
        description = BlogWriterPrompts.get_section_research_prompt(self.topic, section_title)
        expected_output = (
            f"A structured research summary for the section '{section_title}' "
            "including key insights, statistics, case studies, and 5–10 source URLs."
        )

        return Task(
            description=description,
            expected_output=expected_output,
            agent=agents.section_researcher(),
        )

    # === 3. Section Writing Task ===
    def section_writing_task(self, agents, section_title, idx, total_sections, research_summary=""):
        description = BlogWriterPrompts.get_section_writing_prompt(
            self.topic,
            self.blog_type,
            section_title,
            idx,
            total_sections,
            research_summary,
        )
        expected_output = (
            f"A polished markdown-formatted section titled '{section_title}' "
            f"with 200–400 words of detailed, engaging content supported by research."
        )

        return Task(
            description=description,
            expected_output=expected_output,
            agent=agents.section_writer(),
        )

    # === 4. Optional Editing Task ===
    def editing_task(self, agents):
        description = BlogWriterPrompts.get_editing_prompt(self.topic, self.blog_type)
        expected_output = (
            f"A fully edited, cohesive {self.blog_type.lower()} blog post about '{self.topic}', "
            "polished for tone, structure, and flow consistency, ready for publication."
        )

        return Task(
            description=description,
            expected_output=expected_output,
            agent=agents.editor(),
        )

