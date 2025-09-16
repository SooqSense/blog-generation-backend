from crewai import Crew, Process
from crewai_tools import SerperDevTool
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv
from typing import Optional

from .agents.blog_writer_agents import BlogWriterAgents
from .tasks.blog_writer_tasks import BlogWriterTasks
from .prompts.prompts import BlogWriterPrompts
from .source_extractor.source_extractor import SourceExtractor
from .image_prompts.image_generation_prompts import ImageGenerationPrompts
from .images.blog_images import generate_section_specific_images, generate_section_image_prompts_only, embed_images_in_blog_content, get_section_image_urls_list

# Load environment variables
load_dotenv()



class BlogWriter:
    """A crew for writing blog posts with a multi-agent approach using SERPER API for research"""        
    def __init__(self, use_custom_llm=False, topic=None, keywords=None, blog_type="News", 
                 length_min=800, length_max=1500, introduction=True, table_of_content=False, 
                 faq=False, cta=False, conclusion=True, target_audience=None, sample_blog_url=None,
                 generate_image_prompts=True, generate_images=True):
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
        
        # Initialize LLM based on use_custom_llm flag - optimized for speed
        if use_custom_llm:
            gemini_api_key = os.getenv("GOOGLE_API_KEY")
            if not gemini_api_key: raise ValueError("GOOGLE_API_KEY not found")
            self.llm = ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=gemini_api_key, temperature=0.7)
        else:
            # Use GPT-4o-mini for faster response times while maintaining quality
            self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3, max_tokens=6000)
        
        # Initialize modular components
        self.agents = BlogWriterAgents(
            llm=self.llm,
            search_tool=self.search_tool,
            topic=self.topic,
            blog_type=self.blog_type,
            length_min=self.length_min,
            length_max=self.length_max,
            max_image_prompts=5  # Fixed at 5 sections
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
            analyze_sample_blog_func=self._analyze_sample_blog
        )
        
        self.image_prompt_handler = ImageGenerationPrompts(
            topic=self.topic,
            blog_type=self.blog_type,
            max_image_prompts=5  # Fixed at 5 sections
        )
        
        self.source_extractor = SourceExtractor(
            generate_image_prompts=self.generate_image_prompts,
            max_image_prompts=5  # Fixed at 5 sections
        )
        

    
    def _process_keywords_with_counts(self, keywords):
        """
        Process keywords with counts and create a formatted string for AI instructions
        
        Args:
            keywords (list): List of keyword dictionaries with 'keyword' and 'count' keys
            
        Returns:
            tuple: (keywords_list, keywords_instruction_string)
        """
        if not keywords:
            return [], ""
        
        keywords_list = []
        instruction_parts = []
        
        for kw_data in keywords:
            if isinstance(kw_data, dict):
                keyword = kw_data.get('keyword', '')
                count = kw_data.get('count', 1)
                keywords_list.append(keyword)
                
                if count > 1:
                    instruction_parts.append(f"'{keyword}' (use exactly {count} times)")
                else:
                    instruction_parts.append(f"'{keyword}'")
            else:
                # Fallback for simple string keywords
                keywords_list.append(str(kw_data))
                instruction_parts.append(f"'{kw_data}'")
        
        instruction_string = "Keywords: " + ", ".join(instruction_parts)
        return keywords_list, instruction_string
    
    def _analyze_sample_blog(self):
        """
        Analyze the sample blog URL if provided
        
        Returns:
            str: Analysis instructions for style replication
        """
        if not self.sample_blog_url:
            return ""
        
        try:
            # Import the blog analyzer
            from .blog_analyzer import analyze_sample_blog
            
            analysis_result, style_instructions = analyze_sample_blog(self.sample_blog_url)
            
            if analysis_result and style_instructions:
                self.sample_blog_analysis = style_instructions
                return f"\n\nStyle Reference: {self.sample_blog_url}\nStyle Guide: {style_instructions}\nRequirement: Match the identified style and structure."
            else:
                return ""
                
        except Exception as e:
            return ""



    def get_crew(self):
        """Create and return the crew for blog generation"""
        # Simplified workflow: Research -> Plan -> Write -> Edit (Images handled post-generation)
        agents_for_blog = [
            self.agents.researcher(), 
            self.agents.planner(), 
            self.agents.writer(), 
            self.agents.editor()
        ]
        tasks_for_blog = [
            self.tasks.research_task(self.agents), 
            self.tasks.planning_task(self.agents), 
            self.tasks.writing_task(self.agents), 
            self.tasks.editing_task(self.agents)
        ]

        blog_crew = Crew(
            agents=agents_for_blog, 
            tasks=tasks_for_blog, 
            verbose=True,
            process=Process.sequential,
            memory=False,
            max_iter=1,
            step_callback=None,
            task_callback=None
        )
        
        return blog_crew
    

    
    def generate_blog(self, topic=None, keywords=None, blog_type=None, length_min=None, length_max=None, 
                      introduction=None, table_of_content=None, faq=None, cta=None, conclusion=None, 
                      target_audience=None, sample_blog_url=None, generate_image_prompts=None, generate_images=None, 
                      image_model=None):
        # Update parameters if provided
        if topic: self.topic = topic
        if keywords is not None: self.keywords = keywords
        if blog_type is not None: self.blog_type = blog_type  # Changed from tone to blog_type
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
        
        # Generate blog using the crew with research workflow
        result = self.get_crew().kickoff(inputs={"topic": self.topic})
        
        if not result:
            raise RuntimeError("CrewAI execution failed - no result returned from crew")
        
        # Extract sources from research using source extractor
        self.research_sources = self.source_extractor.extract_sources_from_result(result)
        
        # Extract blog content from CrewAI result (editing task result)
        if hasattr(result, 'tasks_output') and len(result.tasks_output) >= 4:
            # Get the editing task result (4th task: research -> plan -> write -> edit)
            editing_result = result.tasks_output[3]  # 0-indexed, so 3 is the 4th task (editing)
            if hasattr(editing_result, 'raw'):
                self.blog_content = editing_result.raw
            elif hasattr(editing_result, 'result'):
                self.blog_content = editing_result.result
            else:
                self.blog_content = str(editing_result)
        else:
            # Fallback to the main result
            if hasattr(result, 'raw'):
                self.blog_content = result.raw
            elif hasattr(result, 'result'):
                self.blog_content = result.result
            else:
                self.blog_content = str(result)
        
        self.blog_content = self.blog_content.strip()
        
        # Ensure content starts with a proper title if it doesn't already
        if self.blog_content and not self.blog_content.startswith("# "):
            self.blog_content = f"# {self.topic}\n\n{self.blog_content}"
        
        # Handle image prompts and image generation based on flags
        if self.generate_image_prompts:
            print(f"DEBUG: Image prompts enabled for topic: {self.topic}")
            
            try:
                if self.generate_images:
                    # Generate both prompts and actual images
                    print(f"DEBUG: Generating both prompts and images using {image_model or 'flux_dev'}")
                    
                    # Map frontend model names to backend method names
                    generation_method = "flux"  # Default
                    if image_model == "flux_schnell":
                        generation_method = "flux_schnell"
                    elif image_model == "flux_dev":
                        generation_method = "flux"
                    
                    self.section_images = generate_section_specific_images(
                        topic=self.topic,
                        blog_type=self.blog_type,
                        blog_content=self.blog_content,
                        generation_method=generation_method,
                        output_dir="blog_images",
                        use_custom_llm=self.use_custom_llm
                    )
                    
                    # Extract image URLs for database storage
                    self.image_urls = get_section_image_urls_list(self.section_images)
                    
                    # Embed images into blog content since we have actual images
                    self.blog_content = embed_images_in_blog_content(self.blog_content, self.section_images)
                    print(f"DEBUG: Embedded {len(self.image_urls)} images into blog content")
                    
                else:
                    # Generate only contextual prompts without actual images
                    print(f"DEBUG: Generating contextual prompts only (no actual images)")
                    self.section_images = generate_section_image_prompts_only(
                        topic=self.topic,
                        blog_type=self.blog_type,
                        blog_content=self.blog_content,
                        use_custom_llm=self.use_custom_llm
                    )
                    
                    # No image URLs since no images were generated
                    self.image_urls = []
                    print(f"DEBUG: Generated {len(self.section_images)} section prompts without images")
                
                # Create image prompts list from section images (for backward compatibility)
                self.image_prompts = []
                for section, image_data in self.section_images.items():
                    if image_data.get('prompt'):
                        self.image_prompts.append(image_data['prompt'])
                
                print(f"DEBUG: Created {len(self.image_prompts)} image prompts")
                
            except Exception as e:
                print(f"ERROR: Failed to generate image prompts/images: {str(e)}")
                # Continue without images rather than failing the entire blog generation
                self.section_images = {}
                self.image_urls = []
                self.image_prompts = []
        else:
            # Initialize empty image data when image prompts are disabled
            print(f"DEBUG: Image prompts disabled (generate_image_prompts=False)")
            self.section_images = {}
            self.image_urls = []
            self.image_prompts = []
            
        return self.blog_content