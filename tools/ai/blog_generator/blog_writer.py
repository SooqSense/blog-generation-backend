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
    """A crew for writing blog posts with a multi-agent approach using SERPER API for research"""        
    def __init__(self, use_custom_llm=False, topic=None, keywords=None, blog_type="News", 
                 length_min=800, length_max=1500, introduction=True, table_of_content=False, 
                 faq=False, cta=False, conclusion=True, target_audience=None, sample_blog_url=None,
                 generate_image_prompts=True, max_image_prompts=5):
        self.use_custom_llm = use_custom_llm
        self.topic = topic
        self.keywords = keywords if keywords else []
        self.blog_type = blog_type  # Changed from tone to blog_type
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
        self.research_sources = []  # New: Store research sources
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
    
    def _get_blog_type_instructions(self):
        """
        Get specific instructions based on blog type
        
        Returns:
            str: Type-specific instructions
        """
        if self.blog_type == "News":
            return """
NEWS BLOG TYPE REQUIREMENTS:
- Start with a compelling headline that captures the latest information
- Use an inverted pyramid structure (most important information first)
- Include recent developments, updates, and current events
- Use present tense and active voice
- Include quotes from experts or stakeholders when available
- Structure with: Lead paragraph, Body paragraphs with supporting details, Background information
- Focus on WHO, WHAT, WHEN, WHERE, WHY, and HOW
- Include recent statistics and data
- Maintain objectivity and factual reporting style
- End with implications or what's next
"""
        elif self.blog_type == "Comparison":
            return """
COMPARISON BLOG TYPE REQUIREMENTS:
- Create a clear comparison framework between two or more subjects
- Use structured comparison format with pros and cons
- Include side-by-side analysis tables or bullet points
- Structure with: Introduction to items being compared, Feature-by-feature comparison, Advantages and disadvantages, Use cases for each option
- Use neutral, analytical tone
- Include criteria for evaluation (price, features, performance, etc.)
- Provide clear recommendations based on different user needs
- Use comparison keywords: "versus", "compared to", "while", "on the other hand", "alternatively"
- End with clear conclusions and recommendations
"""
        else:
            return "Follow standard blog writing practices with engaging and informative content."
            
    @agent
    def researcher(self):
        return Agent(
            role="Content Researcher",
            goal=f"Research and gather comprehensive information about {self.topic} using Google search to find top-ranked blogs and reliable sources",
            backstory="You are an expert researcher who uses SERPER API to find the most relevant and authoritative sources on any topic. You analyze search results to extract key insights and reliable information for content creation.",
            verbose=True,
            llm=self.llm,
            tools=[self.search_tool]
        )
            
    @agent
    def planner(self):
        return Agent(
            role="Content Planner",
            goal=f"Create a comprehensive outline for a {self.length_min}-{self.length_max} word {self.blog_type.lower()} blog post about {self.topic} based on researched information",
            backstory="You are an experienced content strategist who creates detailed outlines based on research findings. You specialize in creating structured plans that result in engaging, well-researched blog posts.",
            verbose=True,
            llm=self.llm,
            tools=[]
        )
    
    @agent
    def writer(self):
        return Agent(
            role="Content Writer",
            goal=f"Write a comprehensive {self.length_min}-{self.length_max} word {self.blog_type.lower()} blog post about {self.topic} based on research and outline",
            backstory="You are a skilled content writer who creates engaging, informative blog posts using researched information. You excel at different blog types and always include proper source citations.",
            verbose=True,
            llm=self.llm
        )
    
    @agent
    def editor(self):
        return Agent(
            role="Content Editor",
            goal=f"Review and enhance the {self.blog_type.lower()} blog post to ensure it meets quality standards, includes proper sources, and follows {self.blog_type.lower()} blog format requirements",
            backstory="You are an experienced editor who improves content quality, ensures proper structure, verifies source citations, and confirms the blog follows the specified type format.",
            verbose=True,
            llm=self.llm
        )
    
    @agent
    def image_prompt_generator(self):
        return Agent(
            role="Content-Aware Visual Strategist",
            goal=f"Analyze the written {self.blog_type.lower()} blog content and generate {self.max_image_prompts} highly specific, content-based AI image generation prompts",
            backstory="You are an expert visual content strategist who specializes in reading and analyzing written content to create precise AI image generation prompts. You excel at identifying key visual elements within blog posts and translating specific content details into actionable prompts for DALL-E, Midjourney, and Stable Diffusion. You understand how to match visual styles to content types and create images that directly support and enhance the written material. Your strength is in analyzing actual content rather than creating generic visuals.",
            verbose=True,
            llm=self.llm
        )

    @task
    def research_task(self):
        description = f"""Research comprehensive information about the topic: {self.topic}

RESEARCH REQUIREMENTS:
1. Use SERPER API to search for: "{self.topic}"
2. Search for additional queries like: "{self.topic} latest news", "{self.topic} analysis", "{self.topic} guide"
3. Identify and analyze the top 10-15 search results
4. Extract key information, insights, and data points
5. Note the source URLs and titles for citation purposes
6. Focus on recent, authoritative, and relevant content

INFORMATION TO GATHER:
- Current trends and developments related to {self.topic}
- Key statistics, facts, and figures
- Expert opinions and analysis
- Recent news and updates
- Different perspectives and viewpoints
- Technical details and explanations
- Real-world examples and case studies

OUTPUT FORMAT:
- Comprehensive research summary with key findings
- List of reliable sources with URLs and titles
- Important quotes and statistics with attribution
- Recent developments and trends
- Expert insights and analysis

BLOG TYPE FOCUS: {self.blog_type}
{self._get_blog_type_instructions()}

Ensure the research is thorough and provides sufficient information for writing a comprehensive {self.blog_type.lower()} blog post."""

        expected_output = f"Detailed research report with key findings, statistics, trends, expert insights, and a comprehensive list of sources with URLs for the topic '{self.topic}' suitable for {self.blog_type.lower()} blog creation."

        return Task(
            description=description,
            expected_output=expected_output,
            agent=self.researcher()
        )
    
    @task
    def planning_task(self):
        description = f"""Create a detailed outline for a {self.blog_type.lower()} blog post about: {self.topic}

REQUIREMENTS:
- Target length: {self.length_min}-{self.length_max} words
- Blog Type: {self.blog_type}
- Use the research findings to structure the outline
- Include source references in the outline

{self._get_blog_type_instructions()}

OUTLINE STRUCTURE FOR {self.blog_type.upper()} BLOG:
1. Title: Create an engaging title that reflects the {self.blog_type.lower()} nature
2. Introduction ({250 if self.introduction else 0} words): Hook, context, preview based on research
3. Main Content Sections (4-6 sections, ~{(self.length_min + self.length_max) // 2 // 5} words each):
   - Each section should be based on research findings
   - Include specific data points and statistics from sources
   - Reference expert opinions and analysis
   - Add real-world examples from research
4. {"FAQ Section (400-500 words): 5-7 questions based on research insights" if self.faq else ""}
5. {"Call to Action (150-200 words): Actionable recommendations based on findings" if self.cta else ""}
6. Conclusion ({300 if self.conclusion else 0} words): Summary of key research insights
7. Sources Section: List of all referenced sources with URLs

CONTENT PLANNING BASED ON RESEARCH:
- Incorporate all key findings from the research
- Use specific statistics and data points discovered
- Include expert quotes and analysis
- Reference recent developments and trends
- Ensure fact-based, well-sourced content"""
                
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
                
        expected_output = f"A comprehensive outline for a {self.blog_type.lower()} blog post that incorporates research findings, includes source references, and supports a {self.length_min}-{self.length_max} word article with detailed section breakdowns."
            
        return Task(
            description=description,
            expected_output=expected_output,
            agent=self.planner()
        )
    
    @task
    def writing_task(self):
        description = f"""Write a comprehensive {self.blog_type.lower()} blog post about: {self.topic}

CRITICAL REQUIREMENTS:
- Word count: {self.length_min}-{self.length_max} words (target: {(self.length_min + self.length_max) // 2})
- Blog Type: {self.blog_type}
- Use the research findings and outline as your guide
- Include proper source citations throughout the content

{self._get_blog_type_instructions()}

STRUCTURE REQUIREMENTS:
- Use # for the main title only
- Use ## for major section headers
- Use ### for subsections
- {"Include ## Introduction section based on research" if self.introduction else ""}
- {"Include ## Table of Contents" if self.table_of_content else ""}
- {"Include ## FAQ section with research-backed answers" if self.faq else ""}
- {"Include ## Call to Action with recommendations from findings" if self.cta else ""}
- {"Include ## Conclusion section summarizing key insights" if self.conclusion else ""}
- **REQUIRED: Include ## Sources section at the end with all referenced URLs**

CONTENT REQUIREMENTS BASED ON RESEARCH:
- Write detailed paragraphs incorporating research findings
- Include specific statistics and data from sources
- Add expert quotes and analysis discovered in research
- Reference recent developments and trends
- Use factual, well-sourced information throughout
- Cite sources within the content using [Source: URL] format
- Ensure information accuracy and reliability

SOURCING REQUIREMENTS:
- Include in-text citations: [Source: website-name.com]
- Add a comprehensive Sources section at the end
- List all URLs with brief descriptions
- Ensure all claims are backed by sources

QUALITY STANDARDS:
- {self.blog_type} blog format compliance
- Comprehensive coverage using research insights
- Engaging and informative content with proper attribution
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
            
        expected_output = f"A complete {self.blog_type.lower()} blog post in markdown format that is {self.length_min}-{self.length_max} words, well-researched, properly sourced, and provides comprehensive value to readers following {self.blog_type.lower()} blog format."
            
        return Task(
            description=description,
            expected_output=expected_output,
            agent=self.writer()
        )
    
    @task
    def editing_task(self):
        description = f"""Review and enhance the {self.blog_type.lower()} blog post about: {self.topic}

EDITING PRIORITIES:
1. WORD COUNT VERIFICATION: Ensure {self.length_min}-{self.length_max} words
2. BLOG TYPE COMPLIANCE: Verify it follows {self.blog_type.lower()} blog format
3. SOURCE VERIFICATION: Check all sources are properly cited and linked
4. CONTENT QUALITY: Improve clarity, flow, and engagement
5. STRUCTURE: Verify proper markdown formatting and organization

SPECIFIC CHECKS:
- Count total words and adjust if needed
- Verify {self.blog_type.lower()} blog format requirements are met
- Ensure all research findings are properly incorporated
- Check that all sources are cited with [Source: URL] format
- Verify Sources section is complete and accurate
- Enhance thin sections with research-backed details
- Improve transitions between sections
- Check for proper ## header formatting
- Ensure consistent style throughout

ENHANCEMENT GUIDELINES:
- If below {self.length_min} words: Add research-backed examples, statistics, or expand existing sections
- If above {self.length_max} words: Trim carefully while preserving valuable research insights
- Improve paragraph structure and readability
- Strengthen source citations and attributions
- Enhance {self.blog_type.lower()}-specific elements

SOURCE VERIFICATION:
- Ensure all URLs in Sources section are properly listed
- Check in-text citations are properly formatted
- Verify all claims have source backing
- Add source descriptions in the Sources section"""
            
        # Add verification requirements
        blog_specifications = []
        
        blog_specifications.append(f"Verify {self.blog_type} blog format is maintained throughout")
        blog_specifications.append(f"Ensure word count is exactly {self.length_min}-{self.length_max} words")
        blog_specifications.append("Verify comprehensive Sources section with all referenced URLs")
        
        if self.introduction:
            blog_specifications.append("Verify engaging ## Introduction section with research context")
        if self.table_of_content:
            blog_specifications.append("Ensure ## Table of Contents is accurate")
        if self.faq:
            blog_specifications.append("Verify ## FAQ section with research-backed answers")
        if self.cta:
            blog_specifications.append("Check ## Call to Action with actionable research-based recommendations")
        if self.conclusion:
            blog_specifications.append("Verify comprehensive ## Conclusion section summarizing key research insights")
            
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
            
        expected_output = f"A polished, final {self.blog_type.lower()} blog post that is exactly {self.length_min}-{self.length_max} words, properly sourced, error-free, highly engaging, and provides exceptional research-backed value to readers."
            
        return Task(
            description=description,
            expected_output=expected_output,
            agent=self.editor()
        )
    
    @task
    def image_prompt_generation_task(self):
        description = f"""ANALYZE the completed {self.blog_type.lower()} blog post content and generate {self.max_image_prompts} detailed AI image generation prompts based on the ACTUAL blog content.

CRITICAL REQUIREMENTS:
- READ and ANALYZE the written blog post content from the previous writing task
- Create exactly {self.max_image_prompts} unique, detailed image prompts
- Each prompt should be 60-120 words describing a specific image
- Base prompts on SPECIFIC sections, concepts, and details from the written blog
- Make prompts actionable for AI image generation tools like DALL-E, Midjourney, or Stable Diffusion

CONTENT ANALYSIS STEPS:
1. Review the blog post structure and main sections
2. Identify key concepts, data points, and examples mentioned
3. Note specific technologies, processes, or comparisons discussed
4. Extract visual elements that would enhance understanding
5. Create prompts that illustrate the actual content written

PROMPT STRUCTURE FOR EACH IMAGE:
- Visual style that matches the {self.blog_type.lower()} content
- Main subject based on specific blog sections
- Lighting, colors, and mood appropriate for the content
- Background and setting relevant to blog examples
- Specific details mentioned in the blog content
- Technical specifications based on blog topics

EXAMPLES BASED ON BLOG CONTENT:
- If blog mentions "AI in healthcare": "Professional medical setting with AI diagnostic screens showing brain scans and neural network overlays, clean hospital environment, doctor reviewing AI analysis, modern medical equipment, photorealistic style"
- If blog discusses "performance comparisons": "Split-screen infographic showing side-by-side performance metrics, clean charts and graphs with the specific data mentioned in the blog, professional color scheme matching the comparison theme"

OUTPUT FORMAT:
List each prompt clearly numbered (1., 2., 3., etc.) with no additional text or explanations.

CONTENT-SPECIFIC REQUIREMENTS:
- Reference specific sections from the blog (Introduction, main topics, conclusions)
- Include visual representations of data/statistics mentioned in the blog
- Create images that would appear logical alongside the written content
- Ensure each prompt relates to actual blog content, not generic topic ideas

Generate exactly {self.max_image_prompts} prompts that directly complement the written blog content."""

        expected_output = f"A numbered list of exactly {self.max_image_prompts} detailed, actionable AI image generation prompts (60-120 words each) that are based on SPECIFIC content from the written {self.blog_type.lower()} blog post about {self.topic}. Each prompt should reference actual blog sections and be immediately usable with AI image generation tools."

        return Task(
            description=description,
            expected_output=expected_output,
            agent=self.image_prompt_generator(),
            context=[self.writing_task(), self.editing_task()]  # Depend on the written content
        )

    @crew
    def crew(self):
        # Updated workflow: Research -> Plan -> Write -> Edit -> (Optional) Image Prompts
        agents_for_blog = [self.researcher(), self.planner(), self.writer(), self.editor()]
        tasks_for_blog = [self.research_task(), self.planning_task(), self.writing_task(), self.editing_task()]
        
        # Add image prompt generation if requested
        if self.generate_image_prompts:
            agents_for_blog.append(self.image_prompt_generator())
            tasks_for_blog.append(self.image_prompt_generation_task())

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
    
    def _extract_sources_from_result(self, crew_result):
        """
        Extract sources from the crew result
        
        Args:
            crew_result: The result from CrewAI execution
            
        Returns:
            list: List of extracted sources
        """
        sources = []
        try:
            # Get the research task result (first task)
            if hasattr(crew_result, 'tasks_output') and crew_result.tasks_output:
                research_result = crew_result.tasks_output[0]
                if hasattr(research_result, 'raw'):
                    research_content = research_result.raw
                elif hasattr(research_result, 'result'):
                    research_content = research_result.result
                else:
                    research_content = str(research_result)
                
                # Parse sources from research content
                sources = self._parse_sources_from_content(research_content)
                
        except Exception as e:
            print(f"Error extracting sources: {str(e)}")
            
        return sources
    
    def _parse_sources_from_content(self, content):
        """
        Parse sources from research content
        
        Args:
            content (str): The research content containing sources
            
        Returns:
            list: List of source dictionaries
        """
        sources = []
        import re
        
        # Look for URLs in the content
        url_pattern = r'https?://[^\s\)>\]]+[^\s\.\)>\]]*'
        urls = re.findall(url_pattern, content)
        
        # Clean and deduplicate URLs
        seen_urls = set()
        for url in urls:
            # Clean URL
            url = url.strip('.,;:')
            if url not in seen_urls and len(url) > 10:
                sources.append({
                    'url': url,
                    'title': self._extract_domain_name(url),
                    'type': 'research_source'
                })
                seen_urls.add(url)
        
        return sources[:10]  # Limit to top 10 sources
    
    def _extract_domain_name(self, url):
        """Extract a clean domain name from URL for title"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            return domain.title()
        except:
            return "External Source"
    
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
                
                # Debug logging
                print(f"DEBUG: Raw image prompt content length: {len(prompt_content)}")
                print(f"DEBUG: First 200 chars of prompt content: {prompt_content[:200]}...")
                
                # Parse the prompts from the content
                prompts = self._parse_prompts_from_content(prompt_content)
                
                print(f"DEBUG: Parsed {len(prompts)} image prompts")
                for i, prompt in enumerate(prompts[:3]):  # Show first 3 for debugging
                    print(f"DEBUG: Prompt {i+1} length: {len(prompt)}, content: {prompt[:100]}...")
                
                return prompts[:self.max_image_prompts]  # Ensure we don't exceed the limit
            
            return []
        except Exception as e:
            print(f"Error extracting image prompts: {str(e)}")
            import traceback
            traceback.print_exc()
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
        
        # Clean the content first
        content = content.strip()
        
        # Try different parsing strategies
        
        # Strategy 1: Look for numbered prompts (1., 2., 3., etc.)
        import re
        numbered_pattern = r'(\d+\.)\s*(.+?)(?=\d+\.|$)'
        numbered_matches = re.findall(numbered_pattern, content, re.DOTALL)
        
        print(f"DEBUG: Found {len(numbered_matches)} numbered matches")
        
        if numbered_matches:
            for i, (number, prompt_text) in enumerate(numbered_matches):
                print(f"DEBUG: Processing numbered match {i+1}: {prompt_text[:100]}...")
                cleaned_prompt = self._clean_prompt_text(prompt_text.strip())
                print(f"DEBUG: Cleaned prompt length: {len(cleaned_prompt)}")
                if len(cleaned_prompt) > 30:  # Reduced minimum threshold
                    prompts.append(cleaned_prompt)
                    print(f"DEBUG: Added prompt {len(prompts)}")
                else:
                    print(f"DEBUG: Rejected prompt due to length: {len(cleaned_prompt)}")
        
        # Strategy 2: If numbered parsing failed, try line-by-line parsing
        if not prompts:
            lines = content.split('\n')
            current_prompt = ""
            
            for line in lines:
                line = line.strip()
                
                # Skip headers, empty lines, and metadata
                if (not line or 
                    line.startswith('#') or 
                    line.startswith('**') or
                    line.startswith('•') or
                    line.lower().startswith(('note:', 'example:', 'output:', 'format:')) or
                    len(line) < 10):
                    
                    # If we have accumulated a prompt, save it
                    if current_prompt.strip() and len(current_prompt.strip()) > 50:
                        cleaned_prompt = self._clean_prompt_text(current_prompt.strip())
                        if cleaned_prompt:
                            prompts.append(cleaned_prompt)
                        current_prompt = ""
                    continue
                
                # Check if this line starts a new numbered prompt
                if re.match(r'^\d+\.', line):
                    # Save previous prompt if exists
                    if current_prompt.strip() and len(current_prompt.strip()) > 50:
                        cleaned_prompt = self._clean_prompt_text(current_prompt.strip())
                        if cleaned_prompt:
                            prompts.append(cleaned_prompt)
                    
                    # Start new prompt (remove the number)
                    current_prompt = re.sub(r'^\d+\.\s*', '', line)
                else:
                    # Continue building current prompt
                    if current_prompt:
                        current_prompt += " " + line
                    else:
                        current_prompt = line
            
            # Add the last prompt if exists
            if current_prompt.strip() and len(current_prompt.strip()) > 50:
                cleaned_prompt = self._clean_prompt_text(current_prompt.strip())
                if cleaned_prompt:
                    prompts.append(cleaned_prompt)
        
        # Strategy 3: If still no prompts, try to extract meaningful content blocks
        if not prompts:
            print("DEBUG: Strategy 3 - Trying content blocks")
            # Split by double newlines and filter for substantial content
            blocks = content.split('\n\n')
            for i, block in enumerate(blocks):
                block = block.strip()
                print(f"DEBUG: Block {i}: {len(block)} chars, starts with: {block[:50]}...")
                if (len(block) > 50 and 
                    not block.startswith('#') and 
                    not block.lower().startswith(('requirements:', 'output:', 'format:', 'note:'))):
                    
                    cleaned_prompt = self._clean_prompt_text(block)
                    if cleaned_prompt:
                        prompts.append(cleaned_prompt)
                        print(f"DEBUG: Added block as prompt")
        
        # Strategy 4: If we still have no prompts but have substantial content, use the whole content
        if not prompts and len(content.strip()) > 100:
            print("DEBUG: Strategy 4 - Using entire content as single prompt")
            cleaned_prompt = self._clean_prompt_text(content.strip())
            if cleaned_prompt:
                prompts.append(cleaned_prompt)
                print("DEBUG: Added entire content as single prompt")
        
        # Limit to max_image_prompts and ensure quality
        final_prompts = []
        for prompt in prompts[:self.max_image_prompts]:
            if len(prompt) >= 30 and len(prompt) <= 800:  # Adjusted length for image prompts
                final_prompts.append(prompt)
                print(f"DEBUG: Final prompt added: {prompt[:100]}...")
        
        print(f"DEBUG: Returning {len(final_prompts)} final prompts")
        return final_prompts
    
    def _clean_prompt_text(self, text):
        """
        Clean and format prompt text
        
        Args:
            text (str): Raw prompt text
            
        Returns:
            str: Cleaned prompt text or empty string if not a valid prompt
        """
        import re  # Import re module at the start of the method
        
        if not text:
            print("DEBUG: Empty text provided to _clean_prompt_text")
            return ""
        
        original_text = text
        print(f"DEBUG: Cleaning prompt text of length {len(text)}: {text[:100]}...")
        
        # Remove markdown formatting
        text = text.replace('**', '').replace('*', '').replace('_', '')
        
        # Remove quotes if they wrap the entire text
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]
        
        # Remove leading numbers and dots (1., 2., etc.)
        text = re.sub(r'^\d+\.\s*', '', text)
        
        # Remove common prefixes
        prefixes_to_remove = [
            'prompt:', 'image prompt:', 'generate:', 'create:', 
            'image:', 'description:', 'visual:', 'picture:'
        ]
        
        text_lower = text.lower()
        for prefix in prefixes_to_remove:
            if text_lower.startswith(prefix):
                text = text[len(prefix):].strip()
                break
        
        # Clean up whitespace
        text = ' '.join(text.split())
        
        # Check if this is likely a blog title or header rather than an image prompt
        title_indicators = [
            text.startswith('#'),  # Markdown header
            len(text.split()) < 8,  # Very short (likely a title)
            text.isupper(),  # All caps (likely a header)
            any(phrase in text.lower() for phrase in [
                'breaking news', 'analysis:', 'comparison:', 'vs', 'versus',
                'report:', 'study:', 'complete guide', 'ultimate guide'
            ]) and len(text.split()) < 12
        ]
        
        if any(title_indicators):
            print(f"DEBUG: Rejected as title/header: {text[:50]}...")
            return ""
        
        # Ensure it looks like an image prompt (contains visual descriptors)
        visual_keywords = [
            'image', 'photo', 'illustration', 'design', 'visual', 'graphic',
            'create', 'show', 'display', 'featuring', 'with', 'background',
            'style', 'color', 'lighting', 'composition', 'professional',
            'scene', 'setting', 'workspace', 'environment', 'shot'
        ]
        
        has_visual_keywords = any(keyword in text.lower() for keyword in visual_keywords)
        
        # Additional visual context words
        descriptive_words = [
            'bright', 'dark', 'clean', 'modern', 'sleek', 'futuristic',
            'detailed', 'high-resolution', 'dramatic', 'soft', 'natural',
            'corporate', 'business', 'technical', 'artistic'
        ]
        
        has_descriptive_words = any(word in text.lower() for word in descriptive_words)
        
        if not has_visual_keywords and not has_descriptive_words:
            # If it doesn't look like an image prompt and is substantial content, enhance it
            if len(text) > 20 and len(text) < 200:
                text = f"Create a professional, high-quality image showing {text}, with clean composition, modern style, and appropriate lighting"
            else:
                print(f"DEBUG: Rejected as non-visual content: {text[:50]}...")
                return ""
        
        # Final validation - should be substantial but not too long
        # Increased max length to accommodate detailed image prompts
        if len(text) < 30 or len(text) > 800:
            print(f"DEBUG: Rejected due to length ({len(text)}): {text[:50]}...")
            return ""
        
        return text.strip()
    
    def generate_blog(self, topic=None, keywords=None, blog_type=None, length_min=None, length_max=None, 
                      introduction=None, table_of_content=None, faq=None, cta=None, conclusion=None, 
                      target_audience=None, sample_blog_url=None, generate_image_prompts=None, 
                      max_image_prompts=None):
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
        if max_image_prompts is not None: self.max_image_prompts = max_image_prompts
        
        # Generate blog using the crew with research workflow
        result = self.crew().kickoff(inputs={"topic": self.topic})
        
        if not result:
            raise RuntimeError("CrewAI execution failed - no result returned from crew")
        
        # Extract sources from research
        self.research_sources = self._extract_sources_from_result(result)
        
        # Extract image prompts if generation was requested
        if self.generate_image_prompts:
            print(f"DEBUG: Starting image prompt extraction, generate_image_prompts={self.generate_image_prompts}")
            print(f"DEBUG: Total tasks output: {len(result.tasks_output) if hasattr(result, 'tasks_output') else 'No tasks_output'}")
            
            # Check if we have enough tasks (should be 5: research, plan, write, edit, image_prompts)
            if hasattr(result, 'tasks_output'):
                for i, task_output in enumerate(result.tasks_output):
                    task_name = getattr(task_output, 'name', 'unknown')
                    print(f"DEBUG: Task {i}: {task_name}")
            
            self.image_prompts = self._extract_image_prompts(result)
            print(f"DEBUG: Final image_prompts count: {len(self.image_prompts)}")
        
        # Extract blog content from CrewAI result
        # For blog content, we want the editing task result
        if self.generate_image_prompts and hasattr(result, 'tasks_output') and len(result.tasks_output) >= 4:
            # Get the editing task result (4th task: research -> plan -> write -> edit -> image_prompts)
            editing_result = result.tasks_output[3]  # 0-indexed, so 3 is the 4th task (editing)
            if hasattr(editing_result, 'raw'):
                self.blog_content = editing_result.raw
            elif hasattr(editing_result, 'result'):
                self.blog_content = editing_result.result
            else:
                self.blog_content = str(editing_result)
        else:
            # Get the last task result (editing task)
            if hasattr(result, 'tasks_output') and len(result.tasks_output) >= 4:
                editing_result = result.tasks_output[3]  # Editing is the 4th task
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