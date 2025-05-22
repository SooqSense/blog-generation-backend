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
import yaml

# Load environment variables
load_dotenv()

def optimize_image_prompt(prompt, topic=None):
    """
    Optimize the image generation prompt using an AI agent
    
    Args:
        prompt (str): The original prompt for image generation
        topic (str, optional): The blog topic for context
        
    Returns:
        str: Enhanced prompt optimized for DALL-E 3
    """
    try:
        # Check for API key
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return prompt  # Return original prompt if no API key
            
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Context to provide to the optimization agent
        topic_context = f" about {topic}" if topic else ""
        
        # Create a system message for the prompt optimization agent
        system_message = """You are an expert image prompt engineer for DALL-E 3. 
Your job is to enhance and optimize image prompts to create stunning, detailed, and professional blog banner images.
Focus on adding details that improve composition, lighting, color schemes, and visual elements.
Make the prompt specific and descriptive while maintaining the original intent.
For blog banners, ensure the enhanced prompt will generate images that:
1. Look professional and polished
2. Have good composition for text overlay
3. Are visually appealing and relevant to the topic
4. Have appropriate negative prompts to avoid text generation
"""
        
        # Call the OpenAI API to optimize the prompt
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": f"Optimize this image prompt for a blog banner{topic_context}: {prompt}"}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        # Extract the optimized prompt
        optimized_prompt = response.choices[0].message.content.strip()
        
        # If the optimized prompt is empty or too short, fallback to original
        if not optimized_prompt or len(optimized_prompt) < 20:
            return prompt
            
        return optimized_prompt
        
    except Exception as e:
        print(f"Error optimizing image prompt: {str(e)}")
        return prompt  # Return original prompt on error

def generate_image(prompt, size="1024x1024", output_dir="blog_images", topic=None):
    """
    Generate an image using OpenAI's DALL-E 3 API and upload to S3
    
    Args:
        prompt (str): The prompt for image generation
        size (str): The size of the image (default: "1024x1024")
        output_dir (str): Directory to save the image (now only used as a prefix in S3)
        topic (str, optional): The blog topic for prompt optimization context
        
    Returns:
        tuple: (image_url, optimized_prompt) where image_url is the S3 URL to the generated image (or None if failed)
              and optimized_prompt is the enhanced prompt used for generation
    """
    # Validate prompt and provide fallback if needed
    if not prompt or not prompt.strip():
        fallback_topic = getattr(BlogWriter, '_current_topic', "Professional blog post")
        prompt = f"Create a professional banner image for a blog about {fallback_topic}."
        topic = fallback_topic

    # Optimize the prompt using the AI agent
    optimized_prompt = optimize_image_prompt(prompt, topic)
    print(f"Original prompt: {prompt}")
    print(f"Optimized prompt: {optimized_prompt}")

    # Check for API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None, optimized_prompt
        
    try:
        # Initialize OpenAI client and generate image
        client = OpenAI(api_key=api_key)
        response = client.images.generate(
            model="dall-e-3",
            prompt=optimized_prompt,
            size=size,
            quality="standard",
            n=1,
        )
        
        # Download the image
        image_url = response.data[0].url
        image_response = requests.get(image_url)
        
        # Prepare S3 upload
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}.png"
        s3_key = f"{output_dir}/{filename}"
        
        # Get S3 credentials from environment
        aws_access_key = os.environ.get("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        bucket_name = os.environ.get("S3_BUCKET_NAME")
        region = os.environ.get("AWS_REGION")
        
        if not aws_access_key or not aws_secret_key:
            # Fallback to local storage if no S3 credentials
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            filepath = os.path.join(output_dir, filename)
            with open(filepath, "wb") as f:
                f.write(image_response.content)
            return filepath, optimized_prompt
        
        # Initialize S3 client
        s3_client = boto3.client(
            's3',
            region_name=region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key
        )
        
        # Upload to S3
        s3_client.upload_fileobj(
            io.BytesIO(image_response.content),
            bucket_name,
            s3_key,
            ExtraArgs={'ContentType': 'image/png'}
        )
        
        # Generate S3 URL
        s3_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{s3_key}"
        return s3_url, optimized_prompt
    
    except Exception as e:
        print(f"Error generating or uploading image: {str(e)}")
        return None, optimized_prompt

@CrewBase
class BlogWriter:
    """A crew for writing blog posts with a multi-agent approach"""        
    def __init__(self, use_custom_llm=False, topic=None, keywords=None, tone="professional", 
                 length_min=800, length_max=1500, introduction=True, table_of_content=False, 
                 faq=False, cta=False, conclusion=True, target_audience=None):
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
        self.blog_content = None
        self.search_tool = SerperDevTool()
        
        # Initialize LLM based on use_custom_llm flag
        if use_custom_llm:
            gemini_api_key = os.getenv("GOOGLE_API_KEY")
            if not gemini_api_key: raise ValueError("GOOGLE_API_KEY not found")
            self.llm = ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=gemini_api_key, temperature=0.7)
        else:
            self.llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7)
        
        # Load YAML configurations from the configuration folder
        self.agents_config = {}
        self.tasks_config = {}
        
        # Get the absolute path to the configuration files
        current_dir = os.path.dirname(os.path.abspath(__file__))
        agents_file = os.path.join(current_dir, 'configuration', 'agents.yaml')
        tasks_file = os.path.join(current_dir, 'configuration', 'tasks.yaml')
        
        # Load agents config
        try:
            with open(agents_file, 'r') as f:
                self.agents_config = yaml.safe_load(f)
        except Exception as e:
            pass
            
        # Load tasks config
        try:
            with open(tasks_file, 'r') as f:
                self.tasks_config = yaml.safe_load(f)
        except Exception as e:
            pass
            
    @agent
    def planner(self):
        agent_config = self.agents_config.get("planner", {}).copy()
        
        # Format any placeholders in the configuration
        if 'goal' in agent_config and '{topic}' in agent_config['goal']:
            agent_config['goal'] = agent_config['goal'].format(topic=self.topic)
        if 'backstory' in agent_config and '{topic}' in agent_config['backstory']:
            agent_config['backstory'] = agent_config['backstory'].format(topic=self.topic)
            
        # Set default values if not in config
        role = agent_config.get('role', "Research Planner")
        goal = agent_config.get('goal', f"Create comprehensive outlines for high-quality blog posts about {self.topic}.")
        backstory = agent_config.get('backstory', "You are an expert content strategist who excels at researching topics and creating detailed content plans.")
            
        return Agent(
            role=role,
            goal=goal,
            backstory=backstory,
            verbose=True,
            llm=self.llm,
            tools=[self.search_tool]
        )
    
    @agent
    def writer(self):
        agent_config = self.agents_config.get("writer", {}).copy()
        
        # Format any placeholders in the configuration
        if 'goal' in agent_config and '{topic}' in agent_config['goal']:
            agent_config['goal'] = agent_config['goal'].format(topic=self.topic)
        if 'backstory' in agent_config and '{topic}' in agent_config['backstory']:
            agent_config['backstory'] = agent_config['backstory'].format(topic=self.topic)
        
        # Set default values if not in config
        role = agent_config.get('role', "Content Writer")
        goal = agent_config.get('goal', f"Write engaging, informative blog posts about {self.topic}.")
        backstory = agent_config.get('backstory', "You are a professional writer with expertise in creating clear, engaging content.")
            
        return Agent(
            role=role,
            goal=goal,
            backstory=backstory,
            verbose=True,
            llm=self.llm
        )
    
    @agent
    def editor(self):
        agent_config = self.agents_config.get("editor", {}).copy()
        
        # Format any placeholders in the configuration
        if 'goal' in agent_config and '{topic}' in agent_config['goal']:
            agent_config['goal'] = agent_config['goal'].format(topic=self.topic)
        if 'backstory' in agent_config and '{topic}' in agent_config['backstory']:
            agent_config['backstory'] = agent_config['backstory'].format(topic=self.topic)
        
        # Set default values if not in config
        role = agent_config.get('role', "Content Editor")
        goal = agent_config.get('goal', "Polish and improve written content to make it more engaging, readable, and valuable.")
        backstory = agent_config.get('backstory', "You are a meticulous editor with years of experience improving content.")
            
        return Agent(
            role=role,
            goal=goal,
            backstory=backstory,
            verbose=True,
            llm=self.llm
        )
    
    @agent
    def designer(self):
        agent_config = self.agents_config.get("designer", {}).copy()
        
        # Format any placeholders in the configuration
        if 'goal' in agent_config and '{topic}' in agent_config['goal']:
            agent_config['goal'] = agent_config['goal'].format(topic=self.topic)
        if 'backstory' in agent_config and '{topic}' in agent_config['backstory']:
            agent_config['backstory'] = agent_config['backstory'].format(topic=self.topic)
        
        # Set default values if not in config
        role = agent_config.get('role', "Image Designer")
        goal = agent_config.get('goal', f"Create visually appealing image prompts for blog post banner images about {self.topic}.")
        backstory = agent_config.get('backstory', "You are an expert at creating descriptive prompts for AI image generation.")
            
        return Agent(
            role=role,
            goal=goal,
            backstory=backstory,
            verbose=True,
            llm=self.llm
        )
    
    @task
    def planning_task(self):
        # Get the base task configuration
        task_config = self.tasks_config.get("planning_task", {}).copy()
        
        # Format the description with topic and other variables
        description = ""
        if 'description' in task_config and task_config['description']:
            description = task_config['description'].format(topic=self.topic)
        else:
            # Use a default description if none exists in config
            description = f"""Create a comprehensive outline and research plan for a blog post on the topic: {self.topic}.
Provide a detailed structure including main sections, sub-points, and key information to cover.
The final output should be a structured plan that the writer can easily follow."""
                
        # Add formatting specifications based on parameters
        blog_specifications = []
        
        # Add tone specification
        blog_specifications.append(f"- Tone: Use a {self.tone} tone for the blog.")
        
        # Add length specification
        blog_specifications.append(f"- Length: Target between {self.length_min} and {self.length_max} words.")
        
        # Add section specifications
        if self.introduction:
            blog_specifications.append("- Include an engaging introduction section")
        if self.table_of_content:
            blog_specifications.append("- Include a table of contents")
        if self.faq:
            blog_specifications.append("- Include a FAQ section with 3-5 relevant questions and answers")
        if self.cta:
            blog_specifications.append("- Include a compelling call-to-action section")
        if self.conclusion:
            blog_specifications.append("- Include a summarizing conclusion section")
            
        # Add target audience specification
        if self.target_audience:
            audience_str = ", ".join(self.target_audience)
            blog_specifications.append(f"- Target audience: {audience_str}")
            
        # Add keywords specification
        if self.keywords:
            keywords_str = ", ".join(self.keywords)
            blog_specifications.append(f"- Incorporate these keywords naturally: {keywords_str}")
            
        # Add specifications to the description
        if blog_specifications:
            description += "\n\nBLOG SPECIFICATIONS:\n" + "\n".join(blog_specifications)
                
        # Get expected output from config or use default
        expected_output = task_config.get('expected_output', "A detailed blog post outline and research plan, with clear specifications for formatting and style.")
            
        return Task(
            description=description,
            expected_output=expected_output,
            agent=self.planner()
        )
    
    @task
    def writing_task(self):
        # Get the base task configuration
        task_config = self.tasks_config.get("writing_task", {}).copy()
        
        # Format the description with topic and other variables
        description = ""
        if 'description' in task_config and task_config['description']:
            description = task_config['description'].format(topic=self.topic)
        else:
            description = f"Write a comprehensive blog post based on the outline provided by the planner about {self.topic}."
        
        # Add formatting specifications based on parameters
        blog_specifications = []
        
        # Add tone specification
        blog_specifications.append(f"- Tone: Use a {self.tone} tone for the blog.")
        
        # Add length specification
        blog_specifications.append(f"- Length: Write between {self.length_min} and {self.length_max} words. Aim for a word count within this range.")
        
        # Add section specifications
        if self.introduction:
            blog_specifications.append("- Include an engaging introduction section")
        if self.table_of_content:
            blog_specifications.append("- Include a table of contents section after the introduction")
        if self.faq:
            blog_specifications.append("- Include a FAQ section with 3-5 relevant questions and answers near the end")
        if self.cta:
            blog_specifications.append("- Include a compelling call-to-action section before the conclusion")
        if self.conclusion:
            blog_specifications.append("- Include a summarizing conclusion section at the end")
            
        # Add target audience specification
        if self.target_audience:
            audience_str = ", ".join(self.target_audience)
            blog_specifications.append(f"- Target audience: {audience_str}")
            
        # Add keywords specification
        if self.keywords:
            keywords_str = ", ".join(self.keywords)
            blog_specifications.append(f"- Incorporate these keywords naturally: {keywords_str}")
            
        # Add specifications to the description
        if blog_specifications:
            description += "\n\nBLOG SPECIFICATIONS:\n" + "\n".join(blog_specifications)
            
        # Get expected output from config or use default
        expected_output = task_config.get('expected_output', "A well-written, engaging blog post in markdown format.")
            
        return Task(
            description=description,
            expected_output=expected_output,
            agent=self.writer()
        )
    
    @task
    def editing_task(self):
        # Get the base task configuration
        task_config = self.tasks_config.get("editing_task", {}).copy()
        
        # Format the description with topic and other variables if needed
        description = ""
        if 'description' in task_config and task_config['description']:
            description = task_config['description'].format(topic=self.topic)
        else:
            description = "Review and improve the blog post written by the writer. Fix any grammatical issues, improve readability, and ensure the content is engaging and valuable."
            
        # Add verification of formatting specifications
        blog_specifications = []
        
        # Add tone specification
        blog_specifications.append(f"- Verify the blog maintains a consistent {self.tone} tone throughout")
        
        # Add length verification
        blog_specifications.append(f"- Check that the word count is between {self.length_min} and {self.length_max} words")
        
        # Add section verification
        if self.introduction:
            blog_specifications.append("- Verify there is an engaging introduction section")
        if self.table_of_content:
            blog_specifications.append("- Ensure the table of contents is accurate and properly formatted")
        if self.faq:
            blog_specifications.append("- Verify the FAQ section includes relevant questions and thorough answers")
        if self.cta:
            blog_specifications.append("- Ensure the call-to-action is compelling and relevant")
        if self.conclusion:
            blog_specifications.append("- Verify the conclusion effectively summarizes the content")
            
        # Add target audience verification
        if self.target_audience:
            audience_str = ", ".join(self.target_audience)
            blog_specifications.append(f"- Ensure the content is appropriate for the target audience: {audience_str}")
            
        # Add keywords verification
        if self.keywords:
            keywords_str = ", ".join(self.keywords)
            blog_specifications.append(f"- Check that these keywords are used naturally and effectively: {keywords_str}")
            
        # Add specifications to the description
        if blog_specifications:
            description += "\n\nEDITING VERIFICATION:\n" + "\n".join(blog_specifications)
            
        # Get expected output from config or use default
        expected_output = task_config.get('expected_output', "A polished, professional blog post ready for publication.")
            
        return Task(
            description=description,
            expected_output=expected_output,
            agent=self.editor()
        )
    
    @task
    def designing_task(self):
        # Get the base task configuration
        task_config = self.tasks_config.get("designing_task", {}).copy()
        
        # Format the description with topic and other variables
        description = ""
        if 'description' in task_config and task_config['description']:
            description = task_config['description'].format(topic=self.topic)
        else:
            description = f"Create a detailed image prompt for a banner image about the topic: {self.topic}."
            
        # Get expected output from config or use default
        expected_output = task_config.get('expected_output', "A detailed image generation prompt for DALL-E 3.")
            
        return Task(
            description=description,
            expected_output=expected_output,
            agent=self.designer()
        )
    
    @crew
    def crew(self):
        agents_for_blog = [self.planner(), self.writer(), self.editor()]
        tasks_for_blog = [self.planning_task(), self.writing_task(), self.editing_task()]

        blog_crew = Crew(
            agents=agents_for_blog, 
            tasks=tasks_for_blog, 
            verbose=True 
            )
        
        return blog_crew
    
    def generate_blog(self, topic=None, keywords=None, tone=None, length_min=None, length_max=None, 
                      introduction=None, table_of_content=None, faq=None, cta=None, conclusion=None, 
                      target_audience=None):
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
        
        try:
            # Generate blog using the crew
            result = self.crew().kickoff(inputs={"topic": self.topic})
        except Exception as e:
            raise
            
        blog_content_raw = str(result)
        self.blog_content = blog_content_raw.strip()
        
        # Extract content directly from agents as fallback
        actual_blog_content = None
        try:
            for task_instance in self.crew().tasks:
                if hasattr(task_instance, 'agent') and hasattr(task_instance.agent, 'role') and task_instance.agent.role.lower() == "editor":
                    if hasattr(task_instance, 'output') and task_instance.output: 
                        editor_content = str(task_instance.output)
                        if "# " in editor_content and len(editor_content) > 100: 
                            actual_blog_content = editor_content
                            break 
            if not actual_blog_content:
                for task_instance in self.crew().tasks:
                    if hasattr(task_instance, 'agent') and hasattr(task_instance.agent, 'role') and task_instance.agent.role.lower() == "writer":
                        if hasattr(task_instance, 'output') and task_instance.output:
                            writer_content = str(task_instance.output)
                            if "# " in writer_content and len(writer_content) > 100: 
                                actual_blog_content = writer_content
                                break
        except Exception as e:
            pass
        
        if actual_blog_content:
            self.blog_content = actual_blog_content.strip()

        # Fallback and formatting logic
        if len(self.blog_content) < 100 or ('# ' not in self.blog_content and '## ' not in self.blog_content):
            self.blog_content = self._generate_fallback_blog_content(self.topic if self.topic else "Fallback Topic")
            
        if self.blog_content and not self.blog_content.startswith("# ") and not self.blog_content.startswith("## "):
            self.blog_content = f"# {self.topic if self.topic else 'Fallback Title'}\n\n{self.blog_content}"
            
        # Generate table of contents if requested but not included
        if self.table_of_content and "## Table of Contents" not in self.blog_content:
            self.blog_content = self._add_table_of_contents(self.blog_content)
            
        # Add FAQ section if requested but not included
        if self.faq and "## FAQ" not in self.blog_content and "## Frequently Asked Questions" not in self.blog_content:
            self.blog_content = self._add_faq_section(self.blog_content)
            
        # Add CTA if requested but not included
        if self.cta and "## Call to Action" not in self.blog_content and "## CTA" not in self.blog_content:
            self.blog_content = self._add_cta_section(self.blog_content)
        
        return self.blog_content
        
    def _generate_fallback_blog_content(self, topic):
        """
        Generate a fallback blog post structure if the main generation failed
        
        Args:
            topic (str): The topic for the fallback blog
            
        Returns:
            str: Formatted blog content in markdown
        """
        title = f"# {topic}"
        
        sections = []
        
        # Add introduction if requested
        if self.introduction:
            sections.append(f"""
## Introduction

Welcome to this guide on {topic}. In this article, we'll explore the key aspects, 
latest developments, and practical applications of this fascinating subject.""")
        
        # Add table of contents if requested
        if self.table_of_content:
            toc = """
## Table of Contents

1. Introduction
2. Key Points
3. Main Concepts
4. Applications"""
            
            if self.faq:
                toc += "\n5. Frequently Asked Questions"
            if self.cta:
                toc += "\n6. Call to Action"
            if self.conclusion:
                toc += "\n7. Conclusion"
                
            sections.append(toc)
            
        # Add main content
        sections.append(f"""
## Key Points

{topic} encompasses a wide range of concepts and technologies that are continuously evolving. 
Let's examine some of the most important aspects that make it relevant today.

### Core Concepts

Understanding the fundamental principles is essential for mastering {topic}. 
These building blocks form the foundation of all advanced applications and developments in the field.

### Recent Developments

The landscape of {topic} is constantly changing with new research and technological advancements. 
Staying updated with these changes is crucial for anyone involved in this domain.""")

        # Add FAQ section if requested
        if self.faq:
            sections.append(f"""
## Frequently Asked Questions

### What is the main benefit of {topic}?
The main benefit is increased efficiency and improved outcomes through structured approaches.

### How can I get started with {topic}?
Begin by learning the fundamental concepts, then practice with small projects before scaling up.

### What are the latest trends in {topic}?
The field is seeing increased automation, integration with AI, and greater accessibility.""")
            
        # Add CTA if requested
        if self.cta:
            sections.append(f"""
## Call to Action

Ready to dive deeper into {topic}? Subscribe to our newsletter for weekly insights, or contact our team of experts for personalized guidance. Visit our website at example.com/contact to get started today.""")
            
        # Add conclusion if requested
        if self.conclusion:
            sections.append(f"""
## Conclusion

{topic} represents a significant area of opportunity and growth. By understanding its core principles 
and keeping pace with the latest developments, you can leverage its potential for innovation and 
problem-solving in various domains. As we continue to witness advancements in this field, its impact 
on our daily lives and professional endeavors will only grow stronger.""")
        
        return title + "".join(sections)
    
    def _add_table_of_contents(self, content):
        """Add a table of contents to the blog post"""
        lines = content.split("\n")
        headers = []
        
        # Extract all headers
        for line in lines:
            if line.startswith("## "):
                header_text = line.replace("## ", "").strip()
                headers.append(header_text)
                
        if not headers:
            # If no ## headers found, return original content
            return content
            
        # Create TOC
        toc_content = "## Table of Contents\n\n"
        for i, header in enumerate(headers):
            toc_content += f"{i+1}. [{header}](#{header.lower().replace(' ', '-')})\n"
            
        # Find position to insert TOC (after title and intro, before first ## header)
        position = 0
        for i, line in enumerate(lines):
            if line.startswith("## "):
                position = i
                break
                
        # Insert TOC at position
        result = "\n".join(lines[:position]) + "\n\n" + toc_content + "\n\n" + "\n".join(lines[position:])
        return result
        
    def _add_faq_section(self, content):
        """Add a FAQ section to the blog post"""
        faq_section = f"""
## Frequently Asked Questions

### What are the key benefits of {self.topic}?
The main benefits include improved efficiency, better outcomes, and streamlined processes that help organizations achieve their goals more effectively.

### How can I get started with {self.topic}?
Getting started involves understanding the basic concepts, following industry best practices, and potentially investing in relevant tools or training.

### What are common challenges with {self.topic}?
Common challenges include implementation difficulties, resistance to change, and finding the right resources or expertise to fully utilize its potential.
"""
        # Add FAQ before conclusion if it exists, otherwise add to the end
        if "## Conclusion" in content:
            parts = content.split("## Conclusion")
            return parts[0] + faq_section + "\n## Conclusion" + parts[1]
        else:
            return content + "\n" + faq_section
            
    def _add_cta_section(self, content):
        """Add a Call to Action section to the blog post"""
        cta_section = f"""
## Call to Action

Ready to take your knowledge of {self.topic} to the next level? Subscribe to our newsletter for weekly insights and updates. For personalized guidance, contact our team of experts who can help you implement these strategies effectively. Visit our website or reach out directly to start your journey today!
"""
        # Add CTA before conclusion if it exists, else before FAQ if it exists, otherwise add to the end
        if "## Conclusion" in content:
            parts = content.split("## Conclusion")
            return parts[0] + cta_section + "\n## Conclusion" + parts[1]
        elif "## Frequently Asked Questions" in content:
            parts = content.split("## Frequently Asked Questions")
            return parts[0] + cta_section + "\n## Frequently Asked Questions" + parts[1]
        else:
            return content + "\n" + cta_section
    
    def generate_banner_image_with_prompt(self, prompt, size="1792x1024", image_output_dir="blog_images"):
        """
        Generate a banner image using a provided prompt
        
        Args:
            prompt (str): The prompt for image generation
            size (str): Image size (default: "1792x1024")
            image_output_dir (str): Directory to save the image
            
        Returns:
            tuple: (image_path, optimized_prompt) where image_path is the path to the generated image (or None)
                  and optimized_prompt is the enhanced prompt used for generation
        """
        # Ensure prompt is not empty
        if not prompt or not prompt.strip():
            prompt = f"Create a professional banner image for a blog about '{self.topic}'."
            
        return generate_image(prompt, size=size, output_dir=image_output_dir, topic=self.topic)
    
    def generate_banner_image_for_blog(self, topic=None, image_output_dir="blog_images"):
        """
        Generate a banner image for a blog post
        
        Args:
            topic (str): Topic for the banner image, defaults to instance topic
            image_output_dir (str): Directory to save the image
            
        Returns:
            tuple: (image_path, optimized_prompt) where image_path is the path to the generated image (or None)
                  and optimized_prompt is the enhanced prompt used for generation
        """
        effective_topic = topic if topic else self.topic
        if not effective_topic:
            raise ValueError("Topic must be provided for banner image generation")
            
        # Create a generic image prompt
        prompt = f"Create a professional, visually appealing banner image for a blog post about {effective_topic}. Use vibrant colors and modern design elements. Include Artilence branding with the main color #04C996, along with black and white accents."
        
        return generate_image(prompt, size="1792x1024", output_dir=image_output_dir, topic=effective_topic)
    
    def save_blog_to_file(self, topic=None, output_file_name=None, base_output_dir=None):
        """Generate a blog post and save it to a file. Returns the file path."""
        # Use provided topic or instance topic
        effective_topic = topic if topic else self.topic
        if not effective_topic: 
            raise ValueError("Topic must be provided for save_blog_to_file.")
            
        # Store topic for potential future use
        BlogWriter._current_topic = effective_topic
        
        # Create a slug for the topic
        topic_slug = effective_topic.lower().replace(' ', '_')
        topic_slug = "".join(c for c in topic_slug if c.isalnum() or c in ('_', '-')).rstrip()
        if not topic_slug: 
            topic_slug = "untitled_blog"
            
        # Create directory for blog output
        current_blog_instance_dir = os.path.join(base_output_dir if base_output_dir else os.getcwd(), topic_slug)
        os.makedirs(current_blog_instance_dir, exist_ok=True)
        
        # Generate blog content
        blog_text_content = self.generate_blog(effective_topic) 

        # Determine output filename
        if output_file_name is None: 
            output_file_name = f"{topic_slug}_blog.md"
        
        # Save blog to file
        final_output_file_path = os.path.join(current_blog_instance_dir, output_file_name)
        with open(final_output_file_path, 'w', encoding='utf-8') as f:
            f.write(blog_text_content)
        
        return final_output_file_path 