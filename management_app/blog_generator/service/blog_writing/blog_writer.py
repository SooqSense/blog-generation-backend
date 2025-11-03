import json
import asyncio
import logging
from urllib.parse import urlparse
from typing import Dict, Any, List, Optional

from crewai import Crew, Process
from crewai_tools import SerperDevTool
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from django.conf import settings

from .agents.blog_writer_agents import BlogWriterAgents
from .tasks.blog_writer_tasks import BlogWriterTasks
from .agents.contextual_image_agent import ContextualImagePromptAgent
from .images.blog_images import (
    generate_section_specific_images,
    embed_images_in_blog_content,
)

# Optional LangSmith tracing/cost logging
try:
    from management_app.langsmith_integration.langsmith_integration import (
        log_cost,
        trace_blog_writer,
    )
    LANGSMITH_AVAILABLE = True
except Exception:
    LANGSMITH_AVAILABLE = False

    def log_cost(*_, **__):
        pass

    def trace_blog_writer(*_, **__):
        def decorator(func):
            return func
        return decorator


logger = logging.getLogger(__name__)

# Stream tuning
_CHUNK_BYTES = 1500  # ~1–2KB per push keeps UI smooth
_IMAGE_CONCURRENCY = 2  # parallel image jobs (tune to infra)
_MAX_SOURCES = 30       # cap references to avoid bloat


class BlogWriter:
    """Multi-agent blog generator with per-section contextual image workflow."""

    def __init__(
        self,
        topic: str,
        blog_type: str = "News",
        length_min: int = 800,
        length_max: int = 1500,
        keywords: Optional[List[str]] = None,
        target_audience: Optional[List[str]] = None,
        use_custom_llm: bool = False,
        generate_images: bool = True,
        max_image_prompts: int = 5,
    ):
        self.topic = topic
        self.blog_type = blog_type
        self.length_min = length_min
        self.length_max = length_max
        self.keywords = keywords or []
        self.target_audience = target_audience or []
        self.generate_images = generate_images
        self.max_image_prompts = max_image_prompts

        # Core tools
        self.search_tool = SerperDevTool()
        self.llm = self._init_llm(use_custom_llm)

        # Core agents and tasks
        self.agents = BlogWriterAgents(
            llm=self.llm,
            search_tool=self.search_tool,
            topic=self.topic,
            blog_type=self.blog_type,
            length_min=self.length_min,
            length_max=self.length_max,
            max_image_prompts=self.max_image_prompts,
        )
        self.tasks = BlogWriterTasks(
            topic=self.topic,
            blog_type=self.blog_type,
            length_min=self.length_min,
            length_max=self.length_max,
            target_audience=self.target_audience,
            keywords=self.keywords,
        )

        # Image prompt agent
        self.image_prompt_agent = ContextualImagePromptAgent(use_custom_llm=use_custom_llm)

        # Runtime data
        self.blog_content: str = ""
        self.section_images: Dict[str, Dict[str, Any]] = {}
        self.image_urls: List[str] = []
        self.research_sources: List[Dict[str, str]] = []

    # -------------------------------------------------------------------
    # LLM SETUP
    # -------------------------------------------------------------------
    def _init_llm(self, use_custom_llm: bool):
        if use_custom_llm:
            gemini_key = getattr(settings, "GOOGLE_API_KEY", None)
            if not gemini_key:
                raise ValueError("GOOGLE_API_KEY not found in Django settings")
            return ChatGoogleGenerativeAI(
                model="gemini-pro",
                google_api_key=gemini_key,
                temperature=0.6,
            )

        openai_key = getattr(settings, "OPENAI_API_KEY", None)
        if not openai_key:
            raise ValueError("OPENAI_API_KEY not found in Django settings")
        # Keep output token cap reasonable for latency/cost
        return ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.4,
            max_tokens=900,
            api_key=openai_key,
        )

    # -------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------
    async def _to_thread(self, func, *args, timeout: Optional[float] = None, **kwargs):
        """Run sync work off the event loop with optional timeout."""
        coro = asyncio.to_thread(func, *args, **kwargs)
        return await (asyncio.wait_for(coro, timeout=timeout) if timeout else coro)

    def _iter_chunks(self, text: str, size: int = _CHUNK_BYTES):
        b = text.encode("utf-8")
        for i in range(0, len(b), size):
            yield b[i : i + size].decode("utf-8", errors="ignore")

    def _clean_and_deduplicate_sources(self, raw_sources):
        unique = {}
        for s in raw_sources or []:
            url = (s.get("url") or "").strip()
            if not url or url in unique:
                continue
            title = s.get("title") or urlparse(url).netloc.replace("www.", "")
            unique[url] = {"url": url, "title": title, "type": s.get("type", "reference")}
            if len(unique) >= _MAX_SOURCES:
                break
        return list(unique.values())

    # -------------------------------------------------------------------
    # MAIN PIPELINE (SYNC)
    # -------------------------------------------------------------------
    @trace_blog_writer("generate_blog_v6", metadata={"workflow": "section_image_sync"})
    def generate_blog(self):
        logger.info("Generating blog for topic=%s", self.topic)

        # === STEP 1: TOC ===
        toc_crew = Crew(
            agents=[self.agents.toc_builder()],
            tasks=[self.tasks.toc_generation_task(self.agents)],
            process=Process.sequential,
            verbose=False,
        )
        toc_result = toc_crew.kickoff(inputs={"topic": self.topic})
        toc_content = getattr(toc_result, "raw", None) or str(toc_result)
        sections = self._parse_toc_sections(toc_content)
        logger.info("TOC created with %d sections", len(sections))

        blog_sections: List[str] = []
        self.research_sources = []

        # === STEP 2: Section loop ===
        for idx, section_title in enumerate(sections, 1):
            logger.info("Researching section %d/%d: %s", idx, len(sections), section_title)

            research_task = self.tasks.section_research_task(self.agents, section_title)
            research_crew = Crew(
                agents=[self.agents.section_researcher()],
                tasks=[research_task],
                process=Process.sequential,
            )
            research_result = research_crew.kickoff(inputs={"topic": self.topic})
            raw_research = getattr(research_result, "raw", None) or str(research_result)

            try:
                research_json = json.loads(raw_research)
                research_summary = "\n".join(research_json.get("key_findings", []))
                section_sources = self._clean_and_deduplicate_sources(research_json.get("sources", []))
                self.research_sources.extend(section_sources)
            except Exception:
                research_summary = raw_research

            writing_task = self.tasks.section_writing_task(
                self.agents, section_title, idx, len(sections), research_summary=research_summary
            )
            writing_crew = Crew(
                agents=[self.agents.section_writer()],
                tasks=[writing_task],
                process=Process.sequential,
            )
            section_result = writing_crew.kickoff(inputs={"topic": self.topic})
            section_content = (getattr(section_result, "raw", None) or str(section_result)).strip()

            # === Images ===
            if self.generate_images:
                try:
                    image_prompt_data = self.image_prompt_agent.generate_prompt(
                        topic=self.topic,
                        section_title=section_title,
                        section_content=section_content,
                        blog_type=self.blog_type,
                    )
                    image_prompt = image_prompt_data["prompt"]

                    section_images = generate_section_specific_images(
                        topic=self.topic,
                        blog_type=self.blog_type,
                        blog_content=image_prompt,
                        output_dir="blog_images",
                        generation_method="flux",
                        use_custom_llm=False,
                    )

                    if section_images and "banner" in section_images:
                        banner = section_images["banner"]
                        url = banner.get("image_url")
                        if url:
                            self.section_images[section_title] = banner
                            self.image_urls.append(url)
                            section_content = embed_images_in_blog_content(
                                section_content, {"banner": banner}
                            )
                except Exception as e:
                    logger.warning("Image generation failed for '%s': %s", section_title, e)

            blog_sections.append(section_content)

        self.blog_content = f"# {self.topic}\n\n{toc_content}\n\n" + "\n\n".join(blog_sections)
        logger.info("Blog complete. sections=%d images=%d", len(sections), len(self.image_urls))

        return {
            "content": self.blog_content,
            "sections": sections,
            "images": self.image_urls,
            "sources": self.research_sources[:_MAX_SOURCES],
        }

    # -------------------------------------------------------------------
    # STREAMING VERSION FOR WEBSOCKET CONSUMER
    # -------------------------------------------------------------------
    async def generate_streaming_blog(
        self,
        websocket=None,
        on_status=None,
        on_toc=None,
        on_section_start=None,
        on_section_token=None,
        on_image=None,
        on_section_complete=None,
        on_complete=None,
        on_error=None,
        *,
        cancel_event: Optional[asyncio.Event] = None,
        research_timeout: float = 60.0,
        writing_timeout: float = 90.0,
        toc_timeout: float = 30.0,
        image_timeout: float = 60.0,
        **kwargs,
    ):
        """
        Streaming version of generate_blog() for WebSocket use.
        Uses callback functions to send incremental updates.
        Adds timeouts, chunked streaming, cancellation, and image concurrency caps.
        """
        try:
            if on_status:
                await on_status("starting", f"🚀 Starting blog generation for '{self.topic}'")

            # === TOC ===
            if on_status:
                await on_status("toc_generation", "📋 Generating table of contents...")
            toc_crew = Crew(
                agents=[self.agents.toc_builder()],
                tasks=[self.tasks.toc_generation_task(self.agents)],
                process=Process.sequential,
                verbose=False,
            )
            toc_result = await self._to_thread(
                toc_crew.kickoff, inputs={"topic": self.topic}, timeout=toc_timeout
            )
            toc_content = getattr(toc_result, "raw", None) or str(toc_result)
            sections = self._parse_toc_sections(toc_content)
            if on_toc:
                await on_toc(sections)

            blog_sections: List[str] = []
            self.research_sources = []
            sources_seen = set()

            sem_images = asyncio.Semaphore(_IMAGE_CONCURRENCY)
            sent_images = 0
            max_images = int(self.max_image_prompts or 0)

            for idx, section_title in enumerate(sections, 1):
                if cancel_event and cancel_event.is_set():
                    if on_status:
                        await on_status("cancelled", "🛑 Generation cancelled")
                    return

                if on_section_start:
                    await on_section_start(section_title, idx)

                # === Research ===
                if on_status:
                    await on_status("research", f"🔍 Researching '{section_title}'...")
                research_task = self.tasks.section_research_task(self.agents, section_title)
                research_crew = Crew(
                    agents=[self.agents.section_researcher()],
                    tasks=[research_task],
                    process=Process.sequential,
                )
                research_result = await self._to_thread(
                    research_crew.kickoff, inputs={"topic": self.topic}, timeout=research_timeout
                )
                raw_research = getattr(research_result, "raw", None) or str(research_result)

                try:
                    research_json = json.loads(raw_research)
                    research_summary = "\n".join(research_json.get("key_findings", []))
                    for s in research_json.get("sources", []):
                        u = (s.get("url") or "").strip()
                        if u and u not in sources_seen:
                            title = s.get("title") or urlparse(u).netloc.replace("www.", "")
                            self.research_sources.append(
                                {"url": u, "title": title, "type": s.get("type", "reference")}
                            )
                            sources_seen.add(u)
                    if len(self.research_sources) > _MAX_SOURCES:
                        self.research_sources = self.research_sources[:_MAX_SOURCES]
                except Exception:
                    research_summary = raw_research

                if cancel_event and cancel_event.is_set():
                    if on_status:
                        await on_status("cancelled", "🛑 Generation cancelled")
                    return

                # === Writing ===
                if on_status:
                    await on_status("writing", f"✍️ Writing '{section_title}'...")
                writing_task = self.tasks.section_writing_task(
                    self.agents, section_title, idx, len(sections), research_summary=research_summary
                )
                writing_crew = Crew(
                    agents=[self.agents.section_writer()],
                    tasks=[writing_task],
                    process=Process.sequential,
                )
                section_result = await self._to_thread(
                    writing_crew.kickoff, inputs={"topic": self.topic}, timeout=writing_timeout
                )
                section_content = (getattr(section_result, "raw", None) or str(section_result)).strip()

                # Stream in fixed-size chunks
                if on_section_token and section_content:
                    for chunk in self._iter_chunks(section_content):
                        if cancel_event and cancel_event.is_set():
                            break
                        await on_section_token(chunk)

                # === Images (capped & concurrency-controlled) ===
                if self.generate_images and (max_images <= 0 or sent_images < max_images):
                    if on_status:
                        await on_status("image_generation", f"🖼️ Generating image for '{section_title}'...")
                    try:
                        image_prompt_data = await self._to_thread(
                            self.image_prompt_agent.generate_prompt,
                            self.topic,
                            section_title,
                            section_content,
                            self.blog_type,
                            timeout=15.0,
                        )
                        image_prompt = image_prompt_data["prompt"]

                        async with sem_images:
                            section_images = await self._to_thread(
                                generate_section_specific_images,
                                self.topic,
                                self.blog_type,
                                image_prompt,
                                "blog_images",
                                "flux",
                                False,
                                timeout=image_timeout,
                            )

                        if section_images and "banner" in section_images:
                            banner = section_images["banner"]
                            url = banner.get("image_url")
                            if url:
                                self.section_images[section_title] = banner
                                self.image_urls.append(url)
                                section_content = embed_images_in_blog_content(
                                    section_content, {"banner": banner}
                                )
                                sent_images += 1
                                if on_image:
                                    await on_image(section_title, banner)
                    except Exception as e:
                        logger.warning("Image generation failed for '%s': %s", section_title, e)
                        if on_error:
                            await on_error(f"Image generation failed for '{section_title}': {e}")

                if on_section_complete:
                    await on_section_complete(section_title, section_content)
                blog_sections.append(section_content)

            if cancel_event and cancel_event.is_set():
                if on_status:
                    await on_status("cancelled", "🛑 Generation cancelled")
                return

            if on_status:
                await on_status("finalizing", "🧩 Finalizing blog content...")
            self.blog_content = f"# {self.topic}\n\n{toc_content}\n\n" + "\n\n".join(blog_sections)

            if on_complete:
                await on_complete(
                    {
                        "content": self.blog_content,
                        "sections": sections,
                        "image_urls": self.image_urls,
                        "sources": self.research_sources[:_MAX_SOURCES],
                    }
                )

        except Exception as e:
            logger.exception("Blog generation error")
            if on_error:
                await on_error(str(e))

    # -------------------------------------------------------------------
    # TOC PARSER
    # -------------------------------------------------------------------
    def _parse_toc_sections(self, toc_content: str) -> List[str]:
        sections: List[str] = []
        for line in toc_content.split("\n"):
            line = line.strip()
            if line and line[0].isdigit() and "." in line:
                title = line.split(".", 1)[1].split("-")[0].strip()
                if title and "table of contents" not in title.lower():
                    sections.append(title)
        return sections or ["Introduction", "Main Body", "Conclusion"]
