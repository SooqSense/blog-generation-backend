from crewai import Crew, Process
from crewai_tools import SerperDevTool
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from django.conf import settings  # ✅ use Django settings for envs
from typing import Optional

from .agents.blog_writer_agents import BlogWriterAgents
from .tasks.blog_writer_tasks import BlogWriterTasks
from .prompts.prompts import BlogWriterPrompts
from .source_extractor.source_extractor import SourceExtractor
from .image_prompts.image_generation_prompts import ImageGenerationPrompts
from .images.blog_images import (
    generate_section_specific_images,
    generate_section_image_prompts_only,
    embed_images_in_blog_content,
    get_section_image_urls_list,
)

# LangSmith integration for cost tracking
try:
    from management_app.langsmith_integration.langsmith_integration import (
        log_cost,
        trace_blog_writer,
    )
    LANGSMITH_AVAILABLE = True
    print("✅ LangSmith integration successfully imported for blog generation")
except ImportError as e:
    print(f"❌ LangSmith integration import failed for blog generation: {str(e)}")

    # Fallback if LangSmith integration is not available
    def log_cost(operation, model, tokens_used=None, cost_estimate=None, additional_data=None):
        pass

    def trace_blog_writer(operation, metadata=None):
        def decorator(func):
            return func
        return decorator

    LANGSMITH_AVAILABLE = False
except Exception as e:
    print(f"❌ Unexpected error importing LangSmith for blog generation: {str(e)}")
    LANGSMITH_AVAILABLE = False


class BlogWriter:
    """A crew for writing blog posts with a multi-agent approach using SERPER API for research"""

    def __init__(
        self,
        use_custom_llm=False,
        topic=None,
        keywords=None,
        blog_type="News",
        length_min=800,
        length_max=1500,
        introduction=True,
        table_of_content=False,
        faq=False,
        cta=False,
        conclusion=True,
        target_audience=None,
        sample_blog_url=None,
        generate_image_prompts=True,
        generate_images=True,
    ):
        self.use_custom_llm = use_custom_llm
        self.topic = topic
        self.keywords = keywords if keywords else []
        self.blog_type = blog_type
        self.length_min = length_min
        self.length_max = length_max
        self.introduction = introduction
        self.table_of_content = table_of_content
        self.faq = faq
        self.cta = cta
        self.conclusion = conclusion
        self.target_audience = target_audience if target_audience else []
        self.sample_blog_url = sample_blog_url
        self.sample_blog_analysis = None
        self.blog_content = None
        self.generate_image_prompts = generate_image_prompts
        self.generate_images = generate_images
        self.image_prompts = []
        self.section_images = {}  # Store section-specific images data
        self.image_urls = []  # Store S3 URLs for database
        self.research_sources = []
        self.search_tool = SerperDevTool()

        # ✅ Initialize LLM based on Django settings (no dotenv)
        if use_custom_llm:
            gemini_api_key = getattr(settings, "GOOGLE_API_KEY", None)
            if not gemini_api_key:
                raise ValueError("GOOGLE_API_KEY not found in Django settings")

            self.llm = ChatGoogleGenerativeAI(
                model="gemini-pro",
                google_api_key=gemini_api_key,
                temperature=0.7,
            )
        else:
            openai_api_key = getattr(settings, "OPENAI_API_KEY", None)
            if not openai_api_key:
                raise ValueError("OPENAI_API_KEY not found in Django settings")

            self.llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.3,
                max_tokens=6000,
                api_key=openai_api_key,
            )

        # Initialize modular components
        self.agents = BlogWriterAgents(
            llm=self.llm,
            search_tool=self.search_tool,
            topic=self.topic,
            blog_type=self.blog_type,
            length_min=self.length_min,
            length_max=self.length_max,
            max_image_prompts=5,
        )

        self.tasks = BlogWriterTasks(
            topic=self.topic,
            blog_type=self.blog_type,
            length_min=self.length_min,
            length_max=self.length_max,
            introduction=self.introduction,
            table_of_content=self.table_of_content,
            faq=self.faq,
            cta=self.cta,
            conclusion=self.conclusion,
            target_audience=self.target_audience,
            keywords=self.keywords,
            process_keywords_func=self._process_keywords_with_counts,
            analyze_sample_blog_func=self._analyze_sample_blog,
        )

        self.image_prompt_handler = ImageGenerationPrompts(
            topic=self.topic,
            blog_type=self.blog_type,
            max_image_prompts=5,
        )

        self.source_extractor = SourceExtractor(
            generate_image_prompts=self.generate_image_prompts,
            max_image_prompts=5,
        )

    # -------------------------------------------------------------------
    # Helper functions (unchanged)
    # -------------------------------------------------------------------
    def _process_keywords_with_counts(self, keywords):
        if not keywords:
            return [], ""

        keywords_list = []
        instruction_parts = []

        for kw_data in keywords:
            if isinstance(kw_data, dict):
                keyword = kw_data.get("keyword", "")
                count = kw_data.get("count", 1)
                keywords_list.append(keyword)

                if count > 1:
                    instruction_parts.append(f"'{keyword}' (use exactly {count} times)")
                else:
                    instruction_parts.append(f"'{keyword}'")
            else:
                keywords_list.append(str(kw_data))
                instruction_parts.append(f"'{kw_data}'")

        instruction_string = "Keywords: " + ", ".join(instruction_parts)
        return keywords_list, instruction_string

    def _analyze_sample_blog(self):
        if not self.sample_blog_url:
            return ""

        try:
            from .blog_analyzer import analyze_sample_blog

            analysis_result, style_instructions = analyze_sample_blog(self.sample_blog_url)

            if analysis_result and style_instructions:
                self.sample_blog_analysis = style_instructions
                return (
                    f"\n\nStyle Reference: {self.sample_blog_url}\n"
                    f"Style Guide: {style_instructions}\n"
                    f"Requirement: Match the identified style and structure."
                )
            else:
                return ""
        except Exception:
            return ""

    # -------------------------------------------------------------------
    # Crew setup (unchanged)
    # -------------------------------------------------------------------
    def get_crew(self):
        agents_for_blog = [
            self.agents.researcher(),
            self.agents.planner(),
            self.agents.writer(),
            self.agents.editor(),
        ]
        tasks_for_blog = [
            self.tasks.research_task(self.agents),
            self.tasks.planning_task(self.agents),
            self.tasks.writing_task(self.agents),
            self.tasks.editing_task(self.agents),
        ]

        return Crew(
            agents=agents_for_blog,
            tasks=tasks_for_blog,
            verbose=True,
            process=Process.sequential,
            memory=False,
            max_iter=1,
            step_callback=None,
            task_callback=None,
        )

    # -------------------------------------------------------------------
    # Blog generation (unchanged except env handling)
    # -------------------------------------------------------------------
    @trace_blog_writer("generate_blog", metadata={"type": "long_form_content", "platform": "blog"})
    def generate_blog(
        self,
        topic=None,
        keywords=None,
        blog_type=None,
        length_min=None,
        length_max=None,
        introduction=None,
        table_of_content=None,
        faq=None,
        cta=None,
        conclusion=None,
        target_audience=None,
        sample_blog_url=None,
        generate_image_prompts=None,
        generate_images=None,
        image_model=None,
    ):
        # ⚙️ Update runtime params
        if topic: self.topic = topic
        if keywords is not None: self.keywords = keywords
        if blog_type is not None: self.blog_type = blog_type
        if length_min is not None: self.length_min = length_min
        if length_max is not None: self.length_max = length_max
        if introduction is not None: self.introduction = introduction
        if table_of_content is not None: self.table_of_content = table_of_content
        if faq is not None: self.faq = faq
        if cta is not None: self.cta = cta
        if conclusion is not None: self.conclusion = conclusion
        if target_audience is not None: self.target_audience = target_audience
        if sample_blog_url is not None: self.sample_blog_url = sample_blog_url
        if generate_image_prompts is not None: self.generate_image_prompts = generate_image_prompts
        if generate_images is not None: self.generate_images = generate_images

        expected_word_count = (self.length_min + self.length_max) // 2
        print(f"📝 Starting blog generation for '{self.topic}' ({self.blog_type})")

        # LangSmith tracking (unchanged)
        if LANGSMITH_AVAILABLE:
            model_name = "gpt-4o-mini" if not self.use_custom_llm else "gemini-pro"
            est_tokens = int(expected_word_count * 1.5)
            est_cost = est_tokens * (0.00001 if "gpt-4o-mini" in model_name else 0.000005)

            log_cost(
                operation="blog_generation_start",
                model=model_name,
                tokens_used=est_tokens,
                cost_estimate=est_cost,
                additional_data={
                    "topic": self.topic,
                    "blog_type": self.blog_type,
                    "target_length": f"{self.length_min}-{self.length_max}",
                    "generate_images": self.generate_images,
                    "image_model": image_model,
                    "estimated_tokens": est_tokens,
                },
            )

        result = self.get_crew().kickoff(inputs={"topic": self.topic})
        if not result:
            raise RuntimeError("CrewAI execution failed - no result returned from crew")

        # Extract blog content
        if hasattr(result, "tasks_output") and len(result.tasks_output) >= 4:
            editing_result = result.tasks_output[3]
            self.blog_content = getattr(editing_result, "raw", None) or getattr(editing_result, "result", str(editing_result))
        else:
            self.blog_content = getattr(result, "raw", None) or getattr(result, "result", str(result))

        self.blog_content = self.blog_content.strip()
        if self.blog_content and not self.blog_content.startswith("# "):
            self.blog_content = f"# {self.topic}\n\n{self.blog_content}"

        # Image generation (unchanged)
        if self.generate_image_prompts:
            try:
                if self.generate_images:
                    gen_method = "flux"
                    if image_model == "flux_schnell":
                        gen_method = "flux_schnell"

                    self.section_images = generate_section_specific_images(
                        topic=self.topic,
                        blog_type=self.blog_type,
                        blog_content=self.blog_content,
                        generation_method=gen_method,
                        output_dir="blog_images",
                        use_custom_llm=self.use_custom_llm,
                    )
                    self.image_urls = get_section_image_urls_list(self.section_images)
                    self.blog_content = embed_images_in_blog_content(self.blog_content, self.section_images)
                else:
                    self.section_images = generate_section_image_prompts_only(
                        topic=self.topic,
                        blog_type=self.blog_type,
                        blog_content=self.blog_content,
                        use_custom_llm=self.use_custom_llm,
                    )
                    self.image_urls = []

                self.image_prompts = [
                    data["prompt"]
                    for data in self.section_images.values()
                    if data.get("prompt")
                ]
            except Exception as e:
                print(f"ERROR: Failed to generate image prompts/images: {str(e)}")
                self.section_images, self.image_urls, self.image_prompts = {}, [], []
        else:
            self.section_images, self.image_urls, self.image_prompts = {}, [], []

        # Final cost logging (unchanged)
        if LANGSMITH_AVAILABLE and self.blog_content:
            actual_words = len(self.blog_content.split())
            model_name = "gpt-4o-mini" if not self.use_custom_llm else "gemini-pro"
            est_tokens = int(actual_words * 1.3)
            text_cost = est_tokens * (0.00001 if "gpt-4o-mini" in model_name else 0.000005)
            img_cost = len(self.image_urls) * 0.04 if self.generate_images else 0
            total_cost = text_cost + img_cost

            log_cost(
                operation="blog_generation_complete",
                model=model_name,
                tokens_used=est_tokens,
                cost_estimate=total_cost,
                additional_data={
                    "topic": self.topic,
                    "blog_type": self.blog_type,
                    "actual_word_count": actual_words,
                    "images_generated": len(self.image_urls),
                    "image_generation_cost": img_cost,
                    "text_generation_cost": text_cost,
                    "total_sources": len(self.research_sources),
                    "success": True,
                },
            )

        print(f"🎉 Blog generation completed for topic: '{self.topic}'")
        return self.blog_content
