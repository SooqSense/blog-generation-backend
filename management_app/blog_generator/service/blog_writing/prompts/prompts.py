class BlogWriterPrompts:
    """Centralized prompts and instructions for JSON-driven, TOC-first blog workflow."""

    # === 1. TOC GENERATION PROMPT ===
    @staticmethod
    def get_toc_generation_prompt(topic, blog_type):
        return f"""Search Google for existing blogs about '{topic}' and build a realistic Table of Contents for a {blog_type.lower()} blog post.

TASK:
Analyze 5–10 top-ranking blogs to identify section structures and patterns.

OUTPUT FORMAT:
## Table of Contents
1. [Section Title] - [Brief Description]
2. [Section Title] - [Brief Description]
...
"""

    # === 2. SECTION RESEARCH PROMPT ===
    @staticmethod
    def get_section_research_prompt(topic, section_title):
        return f"""Research authoritative, factual, and recent information for the section '{section_title}' in a blog about '{topic}'.

GOAL:
Use Google search to gather insights, data, and examples from credible sources (<2 years old).

RESEARCH STEPS:
1. Search for: "{section_title}" + "{topic}" + (blog OR article OR study OR report).
2. Focus on diverse and recent perspectives.
3. Prefer sources from .gov, .edu, .org, major publishers, or data platforms.

OUTPUT (STRICT JSON ONLY):
{{
  "key_findings": [
    "Main insight or data point 1",
    "Main insight or data point 2",
    "Main insight or data point 3"
  ],
  "sources": [
    {{"url": "https://example.com", "title": "Example Report", "type": "report"}},
    {{"url": "https://example.org", "title": "Industry Analysis", "type": "article"}}
  ]
}}
Do not include any prose, explanations, or commentary outside the JSON.
"""

    # === 3. SECTION WRITING PROMPT ===
    @staticmethod
    def get_section_writing_prompt(topic, blog_type, section_title, idx, total_sections, research_summary=""):
        return f"""Write a detailed and engaging section for a {blog_type.lower()} blog post about '{topic}'.

SECTION CONTEXT:
Section {idx} of {total_sections}: {section_title}

RESEARCH INPUT:
{research_summary or "(No research summary available. Use domain knowledge.)"}

WRITING RULES:
1. Begin with '## {section_title}' as the heading.
2. Write 200–400 words of original, well-structured content.
3. Use examples, data, and factual explanations.
4. Attribute facts in (Source: domain.com) format.
5. Include subheadings (###) where logical.
6. Avoid repetition and filler text.
7. Write for clarity and authority.

OUTPUT FORMAT:
## {section_title}
[Markdown section content here]
"""

    # === 4. OPTIONAL EDITING PROMPT ===
    @staticmethod
    def get_editing_prompt(topic, blog_type):
        return f"""You are an experienced editor reviewing a complete {blog_type.lower()} blog post about '{topic}'.

GOAL:
1. Ensure flow between sections.
2. Unify tone and readability.
3. Fix grammar and small factual inconsistencies.
4. Keep citations, data, and structure intact.

DO NOT:
- Add or remove sections.
- Change factual meaning.

Return the edited blog post in full markdown format.
"""

    # === 5. IMAGE PROMPT GENERATION PROMPT ===
    @staticmethod
    def get_image_prompt_generation_prompt(topic, blog_type, max_image_prompts):
        return f"""Analyze the final {blog_type.lower()} blog post about '{topic}' and create {max_image_prompts} detailed AI image generation prompts.

Each prompt should describe a realistic visual concept inspired by the blog's content.

FORMAT:
1. [Prompt for image 1]
2. [Prompt for image 2]
...
Use professional, descriptive, editorial tone (60–100 words each).
"""
