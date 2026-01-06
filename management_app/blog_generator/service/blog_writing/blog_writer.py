import json
import asyncio
import logging
import time
from urllib.parse import urlparse
from typing import Dict, Any, List, Optional
from channels.layers import get_channel_layer
from crewai_tools import SerperDevTool
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from django.conf import settings

from .agents.blog_writer_agents import BlogWriterAgents
from .tasks.blog_writer_tasks import BlogWriterTasks
from .agents.contextual_image_agent import ContextualImagePromptAgent
from .images.blog_images import (
    generate_section_specific_images,
    embed_images_in_blog_content,
)
from ..extraction.firecrawl_extractor import FirecrawlExtractor

logger = logging.getLogger(__name__)

MAX_SOURCES = 30

# Initialize the Redis client using settings.REDIS_URL
# Redis client removed in favor of Channels Group Layer


class BlogWriter:
    """Multi-agent blog generator with parallel section processing and word-by-word streaming."""

    def __init__(
        self,
        topic: str,
        task_id: str,
        blog_type: str = "News",
        length_min: int = 800,
        length_max: int = 1500,
        keywords: Optional[List[str]] = None,
        target_audience: Optional[List[str]] = None,
        use_custom_llm: bool = False,
        generate_images: bool = True,
        max_image_prompts: int = 5,
        website_urls: Optional[List[str]] = None,
    ):
        self.topic = topic
        self.task_id = task_id
        self.blog_type = blog_type
        self.length_min = length_min
        self.length_max = length_max
        self.keywords = keywords or []
        self.target_audience = target_audience or []
        self.generate_images = generate_images
        self.max_image_prompts = max_image_prompts
        self.website_urls = website_urls or []

        # Initialize LLM and tools
        self.llm = self._init_llm(use_custom_llm)
        self.search_tool = SerperDevTool()
        self.channel_layer = get_channel_layer()

        # Initialize agents and tasks
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

        self.image_prompt_agent = ContextualImagePromptAgent(use_custom_llm=use_custom_llm)

        # Runtime state
        self.blog_content: str = ""
        self.image_urls: List[str] = []
        self.research_sources: List[Dict[str, str]] = []
        self.website_content: str = ""  # Store extracted website content

    def _init_llm(self, use_custom_llm: bool):
        """Initialize language model based on configuration."""
        if use_custom_llm:
            gemini_key = getattr(settings, "GOOGLE_API_KEY", None)
            if not gemini_key:
                raise ValueError("GOOGLE_API_KEY not found in settings")
            return ChatGoogleGenerativeAI(
                model="gemini-pro", 
                google_api_key=gemini_key, 
                temperature=0.6,
                streaming=True
            )

        openai_key = getattr(settings, "OPENAI_API_KEY", None)
        if not openai_key:
            raise ValueError("OPENAI_API_KEY not found in settings")

        return ChatOpenAI(
            model="gpt-4o-mini", 
            temperature=0.4, 
            max_tokens=2000, 
            api_key=openai_key,
            streaming=True
        )

    async def _publish(self, event_type: str, payload: Dict[str, Any]):
        """Helper to publish events to Django Channels Group."""
        try:
            await self.channel_layer.group_send(
                f"blog_{self.task_id}",
                {
                    "type": "stream_message", 
                    "data": {
                        "type": event_type,
                        **payload
                    }
                }
            )
        except Exception as e:
            logger.error(f"Group send failed: {e}")

    async def _to_thread(self, func, *args, timeout: Optional[float] = None, **kwargs):
        """Helper to run sync work in a thread with optional timeout."""
        coro = asyncio.to_thread(func, *args, **kwargs)
        return await (asyncio.wait_for(coro, timeout=timeout) if timeout else coro)

    def _clean_sources(self, raw_sources):
        """Clean and deduplicate research sources."""
        unique = {}
        for s in raw_sources or []:
            url = (s.get("url") or "").strip()
            if not url or url in unique:
                continue
            title = s.get("title") or urlparse(url).netloc.replace("www.", "")
            unique[url] = {"url": url, "title": title, "type": s.get("type", "reference")}
            if len(unique) >= MAX_SOURCES:
                break
        return list(unique.values())

    def _parse_toc_sections(self, toc_content: str) -> List[str]:
        """Parse Table of Contents to extract section titles."""
        sections: List[str] = []
        for line in toc_content.split("\n"):
            title = self._extract_section_title(line)
            if title:
                sections.append(title)
        return sections or ["Introduction", "Analysis", "Conclusion"]

    def _extract_section_title(self, line: str) -> Optional[str]:
        """Extract title from a single TOC line (e.g. '1. Introduction - ...')."""
        line = line.strip()
        if line and line[0].isdigit() and "." in line:
            # Matches '1. Title' or '1. Title - context'
            parts = line.split(".", 1)[1].split("-")[0].strip()
            if parts and "table of contents" not in parts.lower():
                return parts
        return None

    async def _process_section(
        self, 
        section_id: str, 
        title: str, 
        index: int, 
        total_sections: int,
        semaphore: asyncio.Semaphore,
        sources_lock: asyncio.Lock,
        cancel_event: Optional[asyncio.Event] = None
    ):
        """Worker method for parallel section generation."""
        async with semaphore:
            if cancel_event and cancel_event.is_set():
                return None

            try:
                await self._publish("section_start", {"section_id": section_id, "title": title, "index": index})

                # Phase 1: Rapid Research
                await self._publish("section_progress", {"section_id": section_id, "phase": "research", "message": f"Researching {title}..."})

                # Direct tool-call for SPEED (bypass the heavy Crew setup for individual sections)
                query = f"{title} {self.topic} detailed information and facts"
                search_results = await self._to_thread(self.search_tool.run, search_query=query)
                research_summary = str(search_results)
                
                # Add website content to research context if available
                if self.website_content:
                    research_summary += f"\n\nAdditional Context from Provided Websites:\n{self.website_content[:2000]}"  # Limit to avoid token overflow

                # Optional sources cleanup if the tool returned list-like data
                try:
                    # If results is a list of dicts (depends on tool version/config)
                    if isinstance(search_results, list):
                        async with sources_lock:
                            for src in self._clean_sources(search_results):
                                if not any(s["url"] == src["url"] for s in self.research_sources):
                                    self.research_sources.append(src)
                except Exception:
                    pass

                if cancel_event and cancel_event.is_set(): return None

                # Phase 2: Writing (Word-by-Word Streaming)
                await self._publish("section_progress", {"section_id": section_id, "phase": "writing", "message": f"Writing {title}..."})

                # Use the abstracted Task and Agent to get prompts/context
                writer_task = self.tasks.section_writing_task(self.agents, title, index + 1, total_sections, research_summary)
                writer_agent = writer_task.agent

                messages = [
                    SystemMessage(content=f"Role: {writer_agent.role}\nBackstory: {writer_agent.backstory}"),
                    HumanMessage(content=f"Goal: {writer_agent.goal}\n\nTask: {writer_task.description}\n\nExpectation: {writer_task.expected_output}")
                ]

                content = ""
                async for chunk in self.llm.astream(messages):
                    if cancel_event and cancel_event.is_set(): break
                    token = chunk.content
                    if token:
                        content += token
                        # Real-time token publishing to Redis for absolute word-by-word streaming
                        await self._publish("section_token", {"section_id": section_id, "content": token})

                if cancel_event and cancel_event.is_set(): return None

                # Phase 3: Image Generation
                image_url = None
                if self.generate_images:
                    try:
                        await self._publish("section_progress", {"section_id": section_id, "phase": "image", "message": f"Generating image for {title}..."})
                        prompt_data = await self._to_thread(
                            self.image_prompt_agent.generate_prompt, 
                            self.topic, title, content, self.blog_type
                        )
                        images = await self._to_thread(
                            generate_section_specific_images,
                            self.topic, self.blog_type, prompt_data["prompt"], "blog_images", "flux", False
                        )
                        if images and "banner" in images:
                            banner = images["banner"]
                            image_url = banner.get("image_url")
                            if image_url:
                                self.image_urls.append(image_url)
                                content = embed_images_in_blog_content(content, {"banner": banner})
                                await self._publish("image", {"section_id": section_id, "data": banner, "image_url": image_url})
                    except Exception as e:
                        logger.warning(f"Image failed for {title}: {e}")

                await self._publish("section_complete", {"section_id": section_id, "content": content, "image_url": image_url})
                return {"index": index, "content": content, "success": True}

            except Exception as e:
                logger.error(f"Section {title} failed: {e}")
                await self._publish("section_error", {"section_id": section_id, "error": str(e)})
                return None

    async def generate_streaming_blog(self, cancel_event=None, max_parallel=None):
        """Orchestrate parallel blog generation with direct event streaming."""
        start_time = time.time()
        try:
            await self._publish("status", {"status": "starting", "message": f"Starting blog: {self.topic}"})

            # Step 0: Extract website content if URLs provided
            if self.website_urls:
                await self._publish("status", {"status": "extracting", "message": f"Extracting content from {len(self.website_urls)} website(s)..."})
                try:
                    extractor = FirecrawlExtractor()
                    extraction_result = await self._to_thread(
                        extractor.extract_content_from_urls,
                        self.website_urls
                    )
                    self.website_content = extraction_result["combined_content"]
                    
                    # Add extracted sources to research sources
                    for source in extraction_result["sources"]:
                        self.research_sources.append({
                            "url": source["url"],
                            "title": source["title"],
                            "type": "website_extraction"
                        })
                    
                    await self._publish("extraction_complete", {
                        "sources_count": len(extraction_result["sources"]),
                        "failed_count": len(extraction_result["failed_urls"]),
                        "content_length": len(self.website_content)
                    })
                    
                    logger.info(f"Extracted {len(self.website_content)} characters from {len(extraction_result['sources'])} websites")
                except Exception as e:
                    logger.error(f"Website extraction failed: {str(e)}")
                    await self._publish("extraction_error", {"error": str(e)})
                    # Continue with blog generation even if extraction fails

            # Step 1: Streamed TOC for INSTANT response
            await self._publish("status", {"status": "toc", "message": "Planning content..."})

            # Use the abstracted TOC Task and Agent
            toc_task = self.tasks.toc_generation_task(self.agents)
            toc_agent = toc_task.agent

            toc_messages = [
                SystemMessage(content=f"Role: {toc_agent.role}\nBackstory: {toc_agent.backstory}"),
                HumanMessage(content=f"Goal: {toc_agent.goal}\n\nTask: {toc_task.description}\n\nExpectation: {toc_task.expected_output}")
            ]

            toc_content = ""
            line_buffer = ""
            section_tasks = []

            # Setup parallel control
            # Fallback to a liberal parallel limit since we don't know total count yet
            effective_parallel = max_parallel if max_parallel else 15 
            sem = asyncio.Semaphore(effective_parallel)
            lock = asyncio.Lock()

            async for chunk in self.llm.astream(toc_messages):
                token = chunk.content
                if not token: continue

                toc_content += token
                line_buffer += token
                await self._publish("toc_token", {"content": token})

                # Instant Pipeline: Start sections as they appear in the TOC stream
                if "\n" in line_buffer:
                    lines = line_buffer.split("\n")
                    for line in lines[:-1]:
                        title = self._extract_section_title(line)
                        if title:
                            s_idx = len(section_tasks)
                            section_id = f"s-{s_idx}"
                            task = asyncio.create_task(
                                self._process_section(section_id, title, s_idx, 8, sem, lock, cancel_event)
                            )
                            section_tasks.append(task)
                    line_buffer = lines[-1]

            # CRITICAL FIX: Process the remaining buffer (often the last section title)
            if line_buffer.strip():
                last_title = self._extract_section_title(line_buffer)
                if last_title:
                    # Check if we already started this (highly unlikely with the \n split logic but safe)
                    s_idx = len(section_tasks)
                    section_id = f"s-{s_idx}"
                    task = asyncio.create_task(
                        self._process_section(section_id, last_title, s_idx, 8, sem, lock, cancel_event)
                    )
                    section_tasks.append(task)

            # Broadcast final structural plan (Frontend sync)
            sections = self._parse_toc_sections(toc_content)
            payload = {
                "sections": [{"id": f"s-{i}", "title": t, "index": i} for i, t in enumerate(sections)],
                "total_sections": len(sections)
            }
            await self._publish("toc_complete", payload)

            # Step 2: Parallel Sections Wait
            # Wait for all identified sections to finish writing
            print(f"Section tasks: {section_tasks}")
            if section_tasks:
                print(f"Section tasks: {section_tasks}")
                results = await asyncio.gather(*section_tasks)
                print(f"Results: {results}")
            else:
                results = []
            successful = sorted([r for r in results if r], key=lambda x: x["index"])
            print(f"Successful: {successful}")
            if cancel_event and cancel_event.is_set():
                await self._publish("status", {"status": "cancelled", "message": "Generation stopped."})
                return

            # Step 3: Finalize
            await self._publish("status", {"status": "finalizing", "message": "Assembling blog..."})
            clean_sections = [r["content"] for r in successful]
            self.blog_content = f"# {self.topic}\n\n{toc_content}\n\n" + "\n\n".join(clean_sections)

            await self._publish("complete", {
                "content": self.blog_content,
                "sources": self.research_sources[:MAX_SOURCES],
                "image_urls": self.image_urls,
                "time": round(time.time() - start_time, 2)
            })

        except Exception as e:
            logger.exception("Generation crash")
            await self._publish("error", {"message": str(e)})

