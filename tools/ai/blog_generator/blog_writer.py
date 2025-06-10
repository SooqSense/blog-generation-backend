from crewai import Agent, Task, Crew, Process
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from openai import OpenAI
import os
import requests
import boto3
import io
from datetime import datetime
from dotenv import load_dotenv
from typing import Optional

# Load environment variables
load_dotenv()



@CrewBase
class BlogWriter:
    """A crew for writing blog posts with a multi-agent approach"""        
    def __init__(self, use_custom_llm=False, topic=None, keywords=None, tone="professional", 
                 length_min=800, length_max=1500, introduction=True, table_of_content=False, 
                 faq=False, cta=False, conclusion=True, target_audience=None, sample_blog_url=None,
                 generate_image_prompts=True, max_image_prompts=5):
        self.use_custom_llm = use_custom_llm
        self.topic = topic
        self.keywords = keywords if keywords else []
        self.tone = tone
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
        self.max_image_prompts = max_image_prompts
        self.image_prompts = []
        self.search_tool = SerperDevTool()
        
        # Initialize LLM based on use_custom_llm flag - optimized for speed
        if use_custom_llm:
            gemini_api_key = os.getenv("GOOGLE_API_KEY")
            if not gemini_api_key: raise ValueError("GOOGLE_API_KEY not found")
            self.llm = ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=gemini_api_key, temperature=0.7)
        else:
            # Use GPT-4o-mini for faster response times while maintaining quality
            self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3, max_tokens=2000)
        

    
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
            
    @agent
    def planner(self):
        return Agent(
            role="Content Planner",
            goal=f"Create a comprehensive outline for a {self.length_min}-{self.length_max} word blog post about {self.topic}",
            backstory="You are an experienced content strategist who creates detailed outlines that result in engaging, well-structured blog posts.",
            verbose=True,
            llm=self.llm,
            tools=[]  # Removed search tool to reduce API calls
        )
    
    @agent
    def writer(self):
        return Agent(
            role="Content Writer",
            goal=f"Write a comprehensive {self.length_min}-{self.length_max} word blog post about {self.topic} based on the provided outline",
            backstory="You are a skilled content writer who creates engaging, informative blog posts that provide value to readers.",
            verbose=True,
            llm=self.llm
        )
    
    @agent
    def editor(self):
        return Agent(
            role="Content Editor",
            goal=f"Review and enhance the blog post to ensure it meets quality standards and word count requirements ({self.length_min}-{self.length_max} words)",
            backstory="You are an experienced editor who improves content quality, ensures proper structure, and verifies requirements are met.",
            verbose=True,
            llm=self.llm
        )
    
    @agent
    def image_prompt_generator(self):
        return Agent(
            role="Visual Content Strategist",
            goal=f"Generate {self.max_image_prompts} detailed image prompts that complement the blog content about {self.topic}",
            backstory="You are a creative strategist who creates compelling image prompts that enhance written content and engage readers.",
            verbose=True,
            llm=self.llm
        )
    

    
    @task
    def planning_task(self):
        # Simplified, focused prompt
        description = f"""Create a detailed outline for a blog post about: {self.topic}

REQUIREMENTS:
- Target length: {self.length_min}-{self.length_max} words
- Tone: {self.tone}
- Structure the outline to naturally support the target word count

OUTLINE STRUCTURE:
1. Title: Create an engaging title
2. Introduction ({250 if self.introduction else 0} words): Hook, context, preview
3. Main Content Sections (4-6 sections, ~{(self.length_min + self.length_max) // 2 // 5} words each):
   - Each section should have 2-3 subsections
   - Include specific talking points and examples
   - Add research data and case studies where relevant
4. {"FAQ Section (400-500 words): 5-7 questions with detailed answers" if self.faq else ""}
5. {"Call to Action (150-200 words): Actionable bullet points" if self.cta else ""}
6. Conclusion ({300 if self.conclusion else 0} words): Summary and final thoughts

CONTENT PLANNING:
- Include historical context and current trends
- Add real-world examples and case studies
- Incorporate industry statistics and expert insights
- Ensure practical applications and actionable advice"""
                
        # Add specifications based on parameters
        blog_specifications = []
        
        if self.target_audience:
            audience_str = ", ".join(self.target_audience)
            blog_specifications.append(f"Target audience: {audience_str}")
            
        if self.keywords:
            keywords_list, keywords_instruction = self._process_keywords_with_counts(self.keywords)
            if keywords_instruction:
                blog_specifications.append(keywords_instruction)
        
        # Add sample blog analysis if available
        sample_blog_instructions = self._analyze_sample_blog()
        if sample_blog_instructions:
            description += sample_blog_instructions
            
        if blog_specifications:
            description += "\n\nADDITIONAL REQUIREMENTS:\n" + "\n".join(blog_specifications)
                
        expected_output = f"A comprehensive outline that supports a {self.length_min}-{self.length_max} word blog post with detailed section breakdowns, specific word targets, talking points, examples, and supporting research."
            
        return Task(
            description=description,
            expected_output=expected_output,
            agent=self.planner()
        )
    
    @task
    def writing_task(self):
        # Streamlined writing prompt
        description = f"""Write a comprehensive blog post about: {self.topic}

CRITICAL REQUIREMENTS:
- Word count: {self.length_min}-{self.length_max} words (target: {(self.length_min + self.length_max) // 2})
- Tone: {self.tone}
- Use the provided outline as your guide

STRUCTURE REQUIREMENTS:
- Use # for the main title only
- Use ## for major section headers
- Use ### for subsections
- {"Include ## Introduction section" if self.introduction else ""}
- {"Include ## Table of Contents" if self.table_of_content else ""}
- {"Include ## FAQ section with 5-7 questions" if self.faq else ""}
- {"Include ## Call to Action with bullet points" if self.cta else ""}
- {"Include ## Conclusion section" if self.conclusion else ""}

CONTENT REQUIREMENTS:
- Write detailed paragraphs (150-200 words each)
- Include specific examples and case studies
- Add relevant statistics and data
- Provide practical applications
- Ensure each section adds significant value

QUALITY STANDARDS:
- Comprehensive coverage of the topic
- Engaging and informative content
- Proper markdown formatting
- Smooth transitions between sections"""
        
        # Add specifications
        blog_specifications = []
        
        if self.target_audience:
            audience_str = ", ".join(self.target_audience)
            blog_specifications.append(f"Target audience: {audience_str}")
            
        if self.keywords:
            keywords_list, keywords_instruction = self._process_keywords_with_counts(self.keywords)
            if keywords_instruction:
                blog_specifications.append(keywords_instruction)
        
        # Add sample blog analysis if available
        sample_blog_instructions = self._analyze_sample_blog()
        if sample_blog_instructions:
            description += sample_blog_instructions
            
        if blog_specifications:
            description += "\n\nADDITIONAL REQUIREMENTS:\n" + "\n".join(blog_specifications)
            
        expected_output = f"A complete blog post in markdown format that is {self.length_min}-{self.length_max} words, well-structured, engaging, and provides comprehensive value to readers."
            
        return Task(
            description=description,
            expected_output=expected_output,
            agent=self.writer()
        )
    
    @task
    def editing_task(self):
        # Focused editing prompt
        description = f"""Review and enhance the blog post about: {self.topic}

EDITING PRIORITIES:
1. WORD COUNT VERIFICATION: Ensure {self.length_min}-{self.length_max} words
2. CONTENT QUALITY: Improve clarity, flow, and engagement
3. STRUCTURE: Verify proper markdown formatting and organization
4. VALUE: Ensure each section provides substantial reader value

SPECIFIC CHECKS:
- Count total words and adjust if needed
- Enhance thin sections with examples and details
- Improve transitions between sections
- Verify all required sections are present
- Check for proper ## header formatting
- Ensure consistent tone throughout

ENHANCEMENT GUIDELINES:
- If below {self.length_min} words: Add detailed examples, case studies, or expand existing sections
- If above {self.length_max} words: Trim carefully while preserving value
- Improve paragraph structure and readability
- Add specific data and statistics where beneficial
- Strengthen conclusions and actionable insights"""
            
        # Add verification requirements
        blog_specifications = []
        
        blog_specifications.append(f"Verify {self.tone} tone is maintained throughout")
        blog_specifications.append(f"Ensure word count is exactly {self.length_min}-{self.length_max} words")
        
        if self.introduction:
            blog_specifications.append("Verify engaging ## Introduction section is present")
        if self.table_of_content:
            blog_specifications.append("Ensure ## Table of Contents is accurate")
        if self.faq:
            blog_specifications.append("Verify ## FAQ section with comprehensive answers")
        if self.cta:
            blog_specifications.append("Check ## Call to Action with actionable items")
        if self.conclusion:
            blog_specifications.append("Verify comprehensive ## Conclusion section")
            
        if self.target_audience:
            audience_str = ", ".join(self.target_audience)
            blog_specifications.append(f"Ensure content suits target audience: {audience_str}")
            
        if self.keywords:
            keywords_list, keywords_instruction = self._process_keywords_with_counts(self.keywords)
            if keywords_instruction:
                blog_specifications.append(f"Verify keyword usage: {keywords_instruction}")
        
        # Add sample blog analysis if available
        sample_blog_instructions = self._analyze_sample_blog()
        if sample_blog_instructions:
            description += sample_blog_instructions
            
        if blog_specifications:
            description += "\n\nVERIFICATION CHECKLIST:\n" + "\n".join(blog_specifications)
            
        expected_output = f"A polished, final blog post that is exactly {self.length_min}-{self.length_max} words, error-free, highly engaging, and provides exceptional value to readers."
            
        return Task(
            description=description,
            expected_output=expected_output,
            agent=self.editor()
        )
    
    @task
    def image_prompt_generation_task(self):
        description = f"""Generate {self.max_image_prompts} detailed image prompts for the blog post about: {self.topic}

REQUIREMENTS:
- Create exactly {self.max_image_prompts} unique image prompts
- Each prompt should be 50-100 words
- Focus on different sections of the blog content
- Make prompts specific and actionable for AI image generation

PROMPT ELEMENTS TO INCLUDE:
- Visual style (infographic, illustration, photo, etc.)
- Key elements and composition
- Color scheme suggestions
- Context related to blog section

PROMPT CATEGORIES:
1. Hero/header images for main topic
2. Section illustrations for key concepts
3. Infographics for data visualization
4. Conceptual images for abstract ideas
5. Process diagrams for step-by-step content

FORMAT:
Each prompt should be detailed enough for immediate use with AI image generation tools while being concise and focused."""

        expected_output = f"Exactly {self.max_image_prompts} detailed, actionable image prompts that enhance the blog content and are ready for AI image generation."

        return Task(
            description=description,
            expected_output=expected_output,
            agent=self.image_prompt_generator()
        )
    

    
    @crew
    def crew(self):
        agents_for_blog = [self.planner(), self.writer(), self.editor()]
        tasks_for_blog = [self.planning_task(), self.writing_task(), self.editing_task()]
        
        # Add image prompt generation if requested
        if self.generate_image_prompts:
            agents_for_blog.append(self.image_prompt_generator())
            tasks_for_blog.append(self.image_prompt_generation_task())

        blog_crew = Crew(
            agents=agents_for_blog, 
            tasks=tasks_for_blog, 
            verbose=True,  # Enable verbosity to show agent logs
            process=Process.sequential,
            memory=False,  # Disabled memory for speed
            max_iter=1,  # Single iteration for speed
            step_callback=None,  # Disable callbacks for speed
            task_callback=None   # Disable callbacks for speed
            )
        
        return blog_crew
    
    def _extract_image_prompts(self, crew_result):
        """
        Extract image prompts from the crew result
        
        Args:
            crew_result: The result from CrewAI execution
            
        Returns:
            list: List of extracted image prompts
        """
        if not self.generate_image_prompts:
            return []
        
        try:
            # Get the last task result which should be the image prompt generation
            if hasattr(crew_result, 'tasks_output') and crew_result.tasks_output:
                # Get the last task output (image prompt generation)
                last_task_output = crew_result.tasks_output[-1]
                if hasattr(last_task_output, 'raw'):
                    prompt_content = last_task_output.raw
                elif hasattr(last_task_output, 'result'):
                    prompt_content = last_task_output.result
                else:
                    prompt_content = str(last_task_output)
                
                # Parse the prompts from the content
                prompts = self._parse_prompts_from_content(prompt_content)
                return prompts[:self.max_image_prompts]  # Ensure we don't exceed the limit
            
            return []
        except Exception as e:
            print(f"Error extracting image prompts: {str(e)}")
            return []
    
    def _parse_prompts_from_content(self, content):
        """
        Parse individual prompts from the generated content
        
        Args:
            content (str): The raw content containing prompts
            
        Returns:
            list: List of individual prompts
        """
        prompts = []
        
        # Split content by common delimiters and clean up
        lines = content.strip().split('\n')
        current_prompt = ""
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and headers
            if not line or line.startswith('#') or line.startswith('🎨') or line.startswith('⚠️'):
                if current_prompt.strip():
                    prompts.append(current_prompt.strip())
                    current_prompt = ""
                continue
            
            # Check if this line starts a new prompt (numbered or bulleted)
            if (line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '10.')) or
                line.startswith(('•', '-', '*')) or
                line.lower().startswith(('prompt', 'image'))):
                
                if current_prompt.strip():
                    prompts.append(current_prompt.strip())
                
                # Clean the line and start new prompt
                current_prompt = line
                # Remove numbering and bullet points
                for prefix in ['1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '10.', '•', '-', '*']:
                    if current_prompt.startswith(prefix):
                        current_prompt = current_prompt[len(prefix):].strip()
                        break
            else:
                # Continue building current prompt
                if current_prompt:
                    current_prompt += " " + line
                else:
                    current_prompt = line
        
        # Add the last prompt if exists
        if current_prompt.strip():
            prompts.append(current_prompt.strip())
        
        # Filter and clean prompts
        cleaned_prompts = []
        for prompt in prompts:
            # Remove common prefixes and clean up
            prompt = prompt.strip()
            if len(prompt) > 30:  # Only keep substantial prompts
                # Remove common AI response artifacts
                prompt = prompt.replace('**', '').replace('*', '')
                cleaned_prompts.append(prompt)
        
        return cleaned_prompts
    
    def generate_blog(self, topic=None, keywords=None, tone=None, length_min=None, length_max=None, 
                      introduction=None, table_of_content=None, faq=None, cta=None, conclusion=None, 
                      target_audience=None, sample_blog_url=None, generate_image_prompts=None, 
                      max_image_prompts=None):
        # Update parameters if provided
        if topic: self.topic = topic
        if keywords is not None: self.keywords = keywords
        if tone is not None: self.tone = tone
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
        if max_image_prompts is not None: self.max_image_prompts = max_image_prompts
        
        # Generate blog using the crew
        result = self.crew().kickoff(inputs={"topic": self.topic})
        
        if not result:
            raise RuntimeError("CrewAI execution failed - no result returned from crew")
        
        # Extract image prompts if generation was requested
        if self.generate_image_prompts:
            self.image_prompts = self._extract_image_prompts(result)
        
        # Extract blog content from CrewAI result
        # For blog content, we want the editing task result (second to last if image prompts enabled, last if not)
        if self.generate_image_prompts and hasattr(result, 'tasks_output') and len(result.tasks_output) >= 2:
            # Get the editing task result (second to last)
            editing_result = result.tasks_output[-2]
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
            
        return self.blog_content