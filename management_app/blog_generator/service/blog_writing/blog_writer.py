import json
import asyncio
from urllib.parse import urlparse
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

try:
    from management_app.langsmith_integration.langsmith_integration import (
        log_cost, trace_blog_writer
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


class BlogWriter:
    """Multi-agent blog generator with per-section contextual image workflow."""

    def __init__(
        self,
        topic,
        blog_type="News",
        length_min=800,
        length_max=1500,
        keywords=None,
        target_audience=None,
        use_custom_llm=False,
        generate_images=True,
        max_image_prompts=5,
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
        self.blog_content = ""
        self.section_images = {}
        self.image_urls = []
        self.research_sources = []

    # -------------------------------------------------------------------
    # LLM SETUP
    # -------------------------------------------------------------------
    def _init_llm(self, use_custom_llm):
        if use_custom_llm:
            gemini_key = getattr(settings, "GOOGLE_API_KEY", None)
            if not gemini_key:
                raise ValueError("GOOGLE_API_KEY not found in Django settings")
            return ChatGoogleGenerativeAI(
                model="gemini-pro",
                google_api_key=gemini_key,
                temperature=0.6,
            )
        else:
            openai_key = getattr(settings, "OPENAI_API_KEY", None)
            if not openai_key:
                raise ValueError("OPENAI_API_KEY not found in Django settings")
            return ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.4,
                max_tokens=6000,
                api_key=openai_key,
            )

    # -------------------------------------------------------------------
    # HELPER: CLEAN SOURCES
    # -------------------------------------------------------------------
    def _clean_and_deduplicate_sources(self, raw_sources):
        unique = {}
        for s in raw_sources:
            url = s.get("url", "").strip()
            if not url or url in unique:
                continue
            title = s.get("title", urlparse(url).netloc.replace("www.", ""))
            unique[url] = {"url": url, "title": title, "type": s.get("type", "reference")}
        return list(unique.values())

    # -------------------------------------------------------------------
    # MAIN PIPELINE (SYNC)
    # -------------------------------------------------------------------
    @trace_blog_writer("generate_blog_v6", metadata={"workflow": "section_image_sync"})
    def generate_blog(self):
        print(f"🚀 Generating blog for topic: {self.topic}")

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
        print(f"📋 TOC created with {len(sections)} sections")

        blog_sections = []

        # === STEP 2: Section loop ===
        for idx, section_title in enumerate(sections, 1):
            print(f"\n🔍 Researching section {idx}/{len(sections)}: {section_title}")

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
            section_content = getattr(section_result, "raw", None) or str(section_result)
            section_content = section_content.strip()

            if self.generate_images:
                print(f"🖼️ Generating contextual image for section: {section_title}")
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
                        section_image = section_images["banner"]
                        image_url = section_image.get("image_url")
                        if image_url:
                            self.section_images[section_title] = section_image
                            self.image_urls.append(image_url)
                            section_content = embed_images_in_blog_content(
                                section_content, {"banner": section_image}
                            )
                            print(f"✅ Image embedded for '{section_title}'")
                except Exception as e:
                    print(f"⚠️ Image generation failed for '{section_title}': {e}")

            blog_sections.append(section_content)

        self.blog_content = f"# {self.topic}\n\n{toc_content}\n\n" + "\n\n".join(blog_sections)
        print(f"✅ Blog complete. Sections: {len(sections)} | Images: {len(self.image_urls)}")

        return {
            "content": self.blog_content,
            "sections": sections,
            "images": self.image_urls,
            "sources": self.research_sources,
        }

    # -------------------------------------------------------------------
    # STREAMING VERSION FOR WEBSOCKET CONSUMER
    # -------------------------------------------------------------------
    async def generate_streaming_blog(self, websocket=None, on_status=None, on_toc=None, on_section_start=None, on_section_token=None, on_image=None, on_section_complete=None, on_complete=None, on_error=None, **kwargs):
        """
        Streaming version of generate_blog() for WebSocket use.
        Uses callback functions to send incremental updates to the WebSocket consumer.
        """
        try:
            # Call status callback
            if on_status:
                await on_status("starting", f"🚀 Starting blog generation for '{self.topic}'")

            # === STEP 1: TOC ===
            if on_status:
                await on_status("toc_generation", f"📋 Generating table of contents...")
            
            toc_crew = Crew(
                agents=[self.agents.toc_builder()],
                tasks=[self.tasks.toc_generation_task(self.agents)],
                process=Process.sequential,
                verbose=False,
            )
            toc_result = toc_crew.kickoff(inputs={"topic": self.topic})
            toc_content = getattr(toc_result, "raw", None) or str(toc_result)
            sections = self._parse_toc_sections(toc_content)
            
            # Call TOC callback
            if on_toc:
                await on_toc(sections)

            blog_sections = []

            # === STEP 2: Section loop ===
            for idx, section_title in enumerate(sections, 1):
                # Call section start callback
                if on_section_start:
                    await on_section_start(section_title, idx)

                # Research phase
                if on_status:
                    await on_status("research", f"🔍 Researching content for section '{section_title}'...")
                
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

                # Writing phase
                if on_status:
                    await on_status("writing", f"✍️ Writing content for section '{section_title}'...")
                
                writing_task = self.tasks.section_writing_task(
                    self.agents, section_title, idx, len(sections), research_summary=research_summary
                )
                writing_crew = Crew(
                    agents=[self.agents.section_writer()],
                    tasks=[writing_task],
                    process=Process.sequential,
                )
                section_result = writing_crew.kickoff(inputs={"topic": self.topic})
                section_content = getattr(section_result, "raw", None) or str(section_result)

                # Send the complete section content immediately
                if on_section_token:
                    try:
                        # Send the entire section content at once for better reliability
                        await on_section_token(section_content)
                        print(f"📝 [BLOG STREAM] Sent section content: {len(section_content)} characters")
                        
                        # Send a heartbeat to keep connection alive
                        if on_status:
                            await on_status("heartbeat", f"Section {idx} content sent successfully")
                            
                    except Exception as e:
                        print(f"⚠️ Section content streaming error: {e}")
                        # Try to send in smaller chunks if full content fails
                        try:
                            words = section_content.split()
                            for i, word in enumerate(words):
                                await on_section_token(word + " ")
                                if i % 10 == 0:
                                    await asyncio.sleep(0.1)
                        except Exception as e2:
                            print(f"⚠️ Chunked streaming also failed: {e2}")
                            continue

                # === Image Generation ===
                if self.generate_images:
                    if on_status:
                        await on_status("image_generation", f"🖼️ Generating contextual image for section '{section_title}'...")
                    
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
                            section_image = section_images["banner"]
                            image_url = section_image.get("image_url")
                            if image_url:
                                self.section_images[section_title] = section_image
                                self.image_urls.append(image_url)
                                section_content = embed_images_in_blog_content(
                                    section_content, {"banner": section_image}
                                )
                                # Call image callback
                                if on_image:
                                    await on_image(section_title, section_image)
                    except Exception as e:
                        print(f"⚠️ Image generation failed for '{section_title}': {e}")
                        if on_error:
                            await on_error(f"⚠️ Image generation failed for '{section_title}': {e}")

                # Call section complete callback
                if on_section_complete:
                    await on_section_complete(section_title, section_content)
                blog_sections.append(section_content)

            # Final assembly
            if on_status:
                await on_status("finalizing", f"📝 Finalizing blog content...")
            
            self.blog_content = f"# {self.topic}\n\n{toc_content}\n\n" + "\n\n".join(blog_sections)

            # Call complete callback
            if on_complete:
                result_data = {
                    "content": self.blog_content,
                    "sections": sections,
                    "image_urls": self.image_urls,
                    "sources": self.research_sources
                }
                await on_complete(result_data)

        except Exception as e:
            print(f"❌ Blog generation error: {e}")
            if on_error:
                await on_error(str(e))

    # -------------------------------------------------------------------
    # TOC PARSER
    # -------------------------------------------------------------------
    def _parse_toc_sections(self, toc_content):
        sections = []
        for line in toc_content.split("\n"):
            line = line.strip()
            if line and line[0].isdigit() and "." in line:
                title = line.split(".", 1)[1].split("-")[0].strip()
                if title and "table of contents" not in title.lower():
                    sections.append(title)
        return sections or ["Introduction", "Main Body", "Conclusion"]
