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

from .prompts.prompts import BlogWriterPrompts
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
    # PARALLEL STREAMING VERSION FOR WEBSOCKET CONSUMER
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
        on_batch_status=None,
        on_section_progress=None,
        on_section_error=None,
        *,
        cancel_event: Optional[asyncio.Event] = None,
        research_timeout: float = 60.0,
        writing_timeout: float = 90.0,
        toc_timeout: float = 30.0,
        image_timeout: float = 60.0,
        max_parallel_sections: int = 3,
        max_retries: int = 2,
        **kwargs,
    ):
        """
        Parallel streaming version of generate_blog() for WebSocket use.
        Processes multiple sections concurrently with rate limiting and retry logic.
        
        Args:
            max_parallel_sections: Maximum number of sections to process concurrently (default: 3)
            max_retries: Maximum retry attempts for failed sections (default: 2)
        """
        import time
        start_time = time.time()
        
        try:
            if on_status:
                await on_status("starting", f"🚀 Starting parallel blog generation for '{self.topic}'")

            # === STEP 1: TOC Generation (Sequential) ===
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
            
            # Send TOC with section IDs
            section_metadata = [
                {"id": f"section-{idx}", "title": title, "index": idx}
                for idx, title in enumerate(sections)
            ]
            if on_toc:
                await on_toc(section_metadata)

            logger.info(f"📋 TOC created with {len(sections)} sections - Starting parallel processing")

            # === STEP 2: Parallel Section Processing ===
            self.research_sources = []
            sources_lock = asyncio.Lock()
            
            # Semaphore for rate limiting
            section_semaphore = asyncio.Semaphore(max_parallel_sections)
            
            # Track section results
            section_results = {}
            completed_count = 0
            failed_sections = []
            
            async def process_single_section(section_id: str, section_title: str, section_index: int):
                """Process a single section with research → write → image pipeline"""
                nonlocal completed_count
                
                async with section_semaphore:
                    retry_count = 0
                    last_error = None
                    
                    while retry_count <= max_retries:
                        try:
                            if cancel_event and cancel_event.is_set():
                                return None
                            
                            # Notify section start
                            if on_section_start:
                                await on_section_start(section_title, section_index, section_id)
                            
                            # === RESEARCH PHASE ===
                            if on_section_progress:
                                await on_section_progress(
                                    section_id, section_title, "research", 
                                    f"🔍 Researching '{section_title}'..."
                                )
                            
                            research_task = self.tasks.section_research_task(self.agents, section_title)
                            research_crew = Crew(
                                agents=[self.agents.section_researcher()],
                                tasks=[research_task],
                                process=Process.sequential,
                            )
                            research_result = await self._to_thread(
                                research_crew.kickoff, 
                                inputs={"topic": self.topic}, 
                                timeout=research_timeout
                            )
                            raw_research = getattr(research_result, "raw", None) or str(research_result)
                            
                            # Parse research
                            research_summary = ""
                            try:
                                research_json = json.loads(raw_research)
                                research_summary = "\n".join(research_json.get("key_findings", []))
                                
                                # Thread-safe source collection
                                async with sources_lock:
                                    for s in research_json.get("sources", []):
                                        u = (s.get("url") or "").strip()
                                        if u and len(self.research_sources) < _MAX_SOURCES:
                                            title = s.get("title") or urlparse(u).netloc.replace("www.", "")
                                            if not any(src["url"] == u for src in self.research_sources):
                                                self.research_sources.append(
                                                    {"url": u, "title": title, "type": s.get("type", "reference")}
                                                )
                            except Exception:
                                research_summary = raw_research
                            
                            if cancel_event and cancel_event.is_set():
                                return None
                            
                            
                            # === WRITING PHASE ===
                            if on_section_progress:
                                await on_section_progress(
                                    section_id, section_title, "writing",
                                    f"✍️ Writing '{section_title}'..."
                                )
                            
                            
                            # Construct prompts manually for direct streaming
                            from langchain_core.messages import HumanMessage, SystemMessage
                            
                            writing_prompt = BlogWriterPrompts.get_section_writing_prompt(
                                self.topic,
                                self.blog_type,
                                section_title,
                                section_index + 1,
                                len(sections),
                                research_summary,
                            )
                            
                            # Use agent backstory as system prompt
                            writer_system_prompt = (
                                "You are an experienced content writer who specializes in creating in-depth, SEO-optimized "
                                "sections for blogs. You transform research insights into clear, engaging writing that "
                                "educates and retains readers."
                            )

                            messages = [
                                SystemMessage(content=writer_system_prompt),
                                HumanMessage(content=writing_prompt)
                            ]
                            
                            section_content = ""
                            
                            # Stream directly from LLM
                            if on_section_token:
                                async for chunk in self.llm.astream(messages):
                                    if cancel_event and cancel_event.is_set():
                                        break
                                        
                                    token = chunk.content
                                    if token:
                                        section_content += token
                                        await on_section_token(token, section_id)
                            else:
                                # Fallback if no token handler (unlikely in this flow)
                                result = await self.llm.ainvoke(messages)
                                section_content = result.content
                            
                            if cancel_event and cancel_event.is_set():
                                return None
                            
                            # === IMAGE GENERATION PHASE ===
                            image_url = None
                            if self.generate_images:
                                if on_section_progress:
                                    await on_section_progress(
                                        section_id, section_title, "image_generation",
                                        f"🖼️ Generating image for '{section_title}'..."
                                    )
                                
                                try:
                                    image_prompt_data = await self._to_thread(
                                        self.image_prompt_agent.generate_prompt,
                                        self.topic, section_title, section_content, self.blog_type,
                                        timeout=15.0,
                                    )
                                    image_prompt = image_prompt_data["prompt"]
                                    
                                    section_images = await self._to_thread(
                                        generate_section_specific_images,
                                        self.topic, self.blog_type, image_prompt,
                                        "blog_images", "flux", False,
                                        timeout=image_timeout,
                                    )
                                    
                                    if section_images and "banner" in section_images:
                                        banner = section_images["banner"]
                                        image_url = banner.get("image_url")
                                        if image_url:
                                            self.section_images[section_title] = banner
                                            self.image_urls.append(image_url)
                                            section_content = embed_images_in_blog_content(
                                                section_content, {"banner": banner}
                                            )
                                            if on_image:
                                                await on_image(section_title, banner, section_id)
                                except Exception as e:
                                    logger.warning(f"Image generation failed for '{section_title}': {e}")
                                    # Continue without image - not critical
                            
                            # === SUCCESS ===
                            if on_section_complete:
                                await on_section_complete(section_title, section_content, section_id, image_url)
                            
                            completed_count += 1
                            
                            # Update batch status
                            if on_batch_status:
                                await on_batch_status(completed_count, len(sections), len(failed_sections))
                            
                            return {
                                "section_id": section_id,
                                "section_title": section_title,
                                "section_index": section_index,
                                "content": section_content,
                                "image_url": image_url,
                                "success": True
                            }
                        
                        except Exception as e:
                            last_error = str(e)
                            retry_count += 1
                            
                            logger.warning(
                                f"Section '{section_title}' failed (attempt {retry_count}/{max_retries + 1}): {e}"
                            )
                            
                            if retry_count <= max_retries:
                                # Notify retry
                                if on_section_error:
                                    await on_section_error(
                                        section_id, section_title, last_error,
                                        retry_count, max_retries, will_retry=True
                                    )
                                # Exponential backoff
                                await asyncio.sleep(2 ** retry_count)
                            else:
                                # Max retries exceeded
                                if on_section_error:
                                    await on_section_error(
                                        section_id, section_title, last_error,
                                        retry_count, max_retries, will_retry=False
                                    )
                                failed_sections.append({
                                    "section_id": section_id,
                                    "section_title": section_title,
                                    "error": last_error
                                })
                                return None
                    
                    return None
            
            # Create tasks for all sections
            section_tasks = [
                process_single_section(f"section-{idx}", title, idx)
                for idx, title in enumerate(sections)
            ]
            
            # Process all sections in parallel
            if on_status:
                await on_status(
                    "parallel_processing", 
                    f"⚡ Processing {len(sections)} sections in parallel (max {max_parallel_sections} concurrent)..."
                )
            
            results = await asyncio.gather(*section_tasks, return_exceptions=True)
            
            # Collect successful results and sort by index
            successful_results = []
            for result in results:
                if isinstance(result, dict) and result.get("success"):
                    successful_results.append(result)
                elif isinstance(result, Exception):
                    logger.error(f"Section processing exception: {result}")
            
            # Sort by original index to maintain order
            successful_results.sort(key=lambda x: x["section_index"])
            
            if cancel_event and cancel_event.is_set():
                if on_status:
                    await on_status("cancelled", "🛑 Generation cancelled")
                return
            
            # === STEP 3: Finalize Blog ===
            if on_status:
                await on_status("finalizing", "🧩 Finalizing blog content...")
            
            blog_sections = [r["content"] for r in successful_results]
            self.blog_content = f"# {self.topic}\n\n{toc_content}\n\n" + "\n\n".join(blog_sections)
            
            total_time = time.time() - start_time
            
            if on_complete:
                await on_complete({
                    "content": self.blog_content,
                    "sections": sections,
                    "image_urls": self.image_urls,
                    "sources": self.research_sources[:_MAX_SOURCES],
                    "successful_sections": len(successful_results),
                    "failed_sections": len(failed_sections),
                    "total_sections": len(sections),
                    "total_time_seconds": round(total_time, 2),
                    "failed_section_details": failed_sections
                })
            
            logger.info(
                f"✅ Blog generation complete: {len(successful_results)}/{len(sections)} sections "
                f"in {total_time:.1f}s ({len(failed_sections)} failed)"
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
