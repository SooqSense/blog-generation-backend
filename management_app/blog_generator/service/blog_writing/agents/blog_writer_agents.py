from crewai import Agent
from crewai_tools import SerperDevTool


class BlogWriterAgents:
    """Agents for the blog writing crew"""

    def __init__(self, llm, search_tool, topic, blog_type, length_min, length_max, max_image_prompts):
        self.llm = llm
        self.search_tool = search_tool
        self.topic = topic
        self.blog_type = blog_type
        self.length_min = length_min
        self.length_max = length_max
        self.max_image_prompts = max_image_prompts

    # === 1. TOC Agent ===
    def toc_builder(self):
        return Agent(
            role="Table of Contents Builder",
            goal=(
                f"Search Google for existing blogs related to '{self.topic}' "
                "and build a dynamic, data-driven table of contents (TOC) "
                f"for a {self.blog_type.lower()} blog post. "
                "The TOC should reflect real-world blog structures from top-ranking results "
                "and organize the sections logically from introduction to conclusion."
            ),
            backstory=(
                "You are an expert content strategist who analyzes top-ranking blog posts "
                "to build realistic, SEO-optimized outlines. You identify how the best blogs "
                "structure their content and use that to create a data-backed table of contents."
            ),
            verbose=True,
            llm=self.llm,
            tools=[self.search_tool]
        )

    # === 2. Section Research Agent ===
    def section_researcher(self):
        return Agent(
            role="Section Researcher",
            goal=(
                f"For each section in the blog’s table of contents about '{self.topic}', "
                "perform a Google search to gather relevant, credible, and diverse information "
                "from top-ranking pages, articles, and sources. "
                "Summarize the key facts, statistics, examples, and perspectives "
                "to support writing detailed and accurate section content."
            ),
            backstory=(
                "You are a research specialist who excels at analyzing multiple sources to gather "
                "insightful, accurate, and verifiable information for each blog section. "
                "Your summaries help writers create content that is informative and authoritative."
            ),
            verbose=True,
            llm=self.llm,
            tools=[self.search_tool]
        )

    # === 3. Section Writer Agent ===
    def section_writer(self):
        return Agent(
            role="Section Content Writer",
            goal=(
                f"Using the research provided by the Section Researcher, "
                f"write a detailed, engaging, and well-structured section for the blog about '{self.topic}'. "
                "Each section should align with the TOC and provide value, clarity, and reader engagement. "
                "Maintain consistency in tone and flow across sections."
            ),
            backstory=(
                "You are an experienced content writer who specializes in creating in-depth, SEO-optimized "
                "sections for blogs. You transform research insights into clear, engaging writing that "
                "educates and retains readers."
            ),
            verbose=True,
            llm=self.llm
        )

    # === 4. Editor Agent ===
    def editor(self):
        return Agent(
            role="Content Editor",
            goal=(
                f"Review and refine the complete {self.blog_type.lower()} blog post about '{self.topic}'. "
                "Ensure it is coherent, well-structured, free of repetition, and factually accurate. "
                "Make sure each section flows naturally and matches the tone and format of the {self.blog_type.lower()} blog."
            ),
            backstory=(
                "You are a professional editor with a sharp eye for structure, accuracy, and tone consistency. "
                "You ensure that each blog post reads naturally, maintains narrative flow, and delivers on its intent."
            ),
            verbose=True,
            llm=self.llm
        )

    # === 5. Image Prompt Generator Agent ===
    def image_prompt_generator(self):
        return Agent(
            role="Content-Aware Visual Strategist",
            goal=(
                f"Analyze the final written blog about '{self.topic}' "
                f"and generate up to {self.max_image_prompts} specific, content-based AI image prompts. "
                "Each image should visually represent a concept, section, or example discussed in the content."
            ),
            backstory=(
                "You are a visual strategist who reads content closely and designs creative image prompts "
                "that enhance understanding and engagement. Your image ideas are detailed, relevant, and stylistically consistent."
            ),
            verbose=True,
            llm=self.llm
        )
