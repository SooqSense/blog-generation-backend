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
                 faq=False, cta=False, conclusion=True, target_audience=None, sample_blog_url=None):
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
        self.search_tool = SerperDevTool()
        
        # Initialize LLM based on use_custom_llm flag
        if use_custom_llm:
            gemini_api_key = os.getenv("GOOGLE_API_KEY")
            if not gemini_api_key: raise ValueError("GOOGLE_API_KEY not found")
            self.llm = ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=gemini_api_key, temperature=0.8)
        else:
            # Use GPT-4 for better long-form content generation and higher temperature for creativity
            self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.8, max_tokens=4000)
        

    
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
        
        instruction_string = "Focus on these keywords with specific usage requirements: " + ", ".join(instruction_parts)
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
                return f"""

🎯 CRITICAL SAMPLE BLOG STYLE REPLICATION REQUIREMENT 🎯
YOU MUST REPLICATE THE STYLE AND STRUCTURE OF THE SAMPLE BLOG AT: {self.sample_blog_url}

📋 SAMPLE BLOG ANALYSIS RESULTS:
{style_instructions}

🚨 MANDATORY STYLE REPLICATION INSTRUCTIONS 🚨
1. FOLLOW THE EXACT WRITING STYLE identified in the analysis above
2. REPLICATE THE STRUCTURE AND FORMATTING patterns found in the sample
3. MATCH THE TONE AND VOICE characteristics described
4. USE SIMILAR SECTION ORGANIZATION and heading styles
5. INCORPORATE THE SAME CONTENT APPROACH and presentation methods
6. MAINTAIN THE IDENTIFIED ENGAGEMENT TECHNIQUES and writing patterns

⚠️ CRITICAL REQUIREMENTS ⚠️
- Create completely ORIGINAL content while following the identified style patterns
- Do NOT copy any text from the sample blog
- ADAPT the style to your topic while maintaining the core characteristics
- ENSURE your content feels like it could be from the same author/publication
- PRIORITIZE style consistency throughout the entire blog post

This style replication is MANDATORY and should be your PRIMARY focus alongside word count requirements."""
            else:
                return f"\n\n⚠️ SAMPLE BLOG ANALYSIS FAILED ⚠️\nCould not analyze sample blog at {self.sample_blog_url}. Proceeding with standard blog generation."
                
        except Exception as e:
            print(f"Error analyzing sample blog: {str(e)}")
            return f"\n\nNote: Error analyzing sample blog at {self.sample_blog_url}. Proceeding with standard blog generation."
            
    @agent
    def planner(self):
        return Agent(
            role="Expert Research Planner & Content Strategist",
            goal=f"Create exceptionally detailed, comprehensive outlines for authoritative blog posts about {self.topic} that will become definitive resources in the field.",
            backstory="You are a world-class content strategist with deep expertise in research methodology and content planning. You have a proven track record of creating content outlines that result in industry-leading blog posts. You understand how to structure complex information into engaging, comprehensive content that provides exceptional value to readers.",
            verbose=True,
            llm=self.llm,
            tools=[self.search_tool]
        )
    
    @agent
    def writer(self):
        return Agent(
            role="Expert Content Writer & Subject Matter Specialist",
            goal=f"Write exceptionally detailed, authoritative, and engaging blog posts about {self.topic} that establish thought leadership and provide comprehensive value to readers.",
            backstory="You are an award-winning content writer with deep subject matter expertise across multiple industries. You have a talent for transforming complex topics into engaging, comprehensive content that readers find invaluable. Your writing combines thorough research, practical insights, and compelling storytelling to create content that becomes the go-to resource in any field.",
            verbose=True,
            llm=self.llm
        )
    
    @agent
    def editor(self):
        return Agent(
            role="Senior Content Editor & Quality Assurance Specialist",
            goal=f"Transform good content into exceptional, comprehensive content about {self.topic} that exceeds industry standards and provides unmatched value to readers.",
            backstory="You are a senior content editor with over 15 years of experience in publishing and content optimization. You have an exceptional eye for detail and a deep understanding of what makes content truly valuable. You specialize in enhancing content depth, improving readability, and ensuring every piece becomes a comprehensive resource that readers will reference repeatedly.",
            verbose=True,
            llm=self.llm
        )
    

    
    @task
    def planning_task(self):
        # ALWAYS use aggressive prompts - ignore YAML config for word count enforcement
        description = f"""🚨🚨🚨 ULTRA-CRITICAL MISSION: CREATE COMPREHENSIVE OUTLINE FOR {self.length_min}-{self.length_max} WORDS 🚨🚨🚨

You are creating an outline for a blog post on: {self.topic}

⚠️ ABSOLUTE NON-NEGOTIABLE REQUIREMENTS ⚠️
- This outline MUST guarantee a {self.length_min}-{self.length_max} word blog post
- TARGET: {(self.length_min + self.length_max) // 2} WORDS EXACTLY
- NO SHORTCUTS, NO EXCEPTIONS, NO COMPROMISES

🎯 MANDATORY ULTRA-DETAILED OUTLINE STRUCTURE 🎯

1. TITLE: Create a compelling, attention-grabbing title

2. INTRODUCTION (250-300 words planned):
   - Hook paragraph (75-100 words)
   - Background context (75-100 words)  
   - Preview of what readers will learn (75-100 words)
   - Transition to main content (25-50 words)

3. TABLE OF CONTENTS (if requested): List all major sections

4. MAIN CONTENT SECTIONS (Plan for MINIMUM 6-8 major sections for {self.length_min}-{self.length_max} words):

   SECTION 1: [Title] (400-500 words planned)
   - Introduction paragraph with context (100-125 words)
   - Subsection A: [Specific detailed topic] (125-150 words)
   - Subsection B: [Specific detailed topic] (125-150 words)
   - Real-world example/case study with analysis (75-100 words)

   SECTION 2: [Title] (400-500 words planned)
   - Introduction paragraph with background (100-125 words)
   - Subsection A: [Specific detailed topic] (125-150 words)
   - Subsection B: [Specific detailed topic] (125-150 words)
   - Statistical data and detailed analysis (75-100 words)

   SECTION 3: [Title] (400-500 words planned)
   - Introduction paragraph with overview (100-125 words)
   - Subsection A: [Specific detailed topic] (125-150 words)
   - Subsection B: [Specific detailed topic] (125-150 words)
   - Expert insights and quotes with context (75-100 words)

   SECTION 4: [Title] (400-500 words planned)
   - Introduction paragraph (100-125 words)
   - Subsection A: [Implementation details] (125-150 words)
   - Subsection B: [Best practices] (125-150 words)
   - Practical examples and applications (75-100 words)

   SECTION 5: [Title] (400-500 words planned)
   - Introduction paragraph (100-125 words)
   - Subsection A: [Challenges and solutions] (125-150 words)
   - Subsection B: [Future implications] (125-150 words)
   - Industry trends and predictions (75-100 words)

   SECTION 6: [Title] (400-500 words planned)
   - Introduction paragraph (100-125 words)
   - Subsection A: [Comparative analysis] (125-150 words)
   - Subsection B: [Technical deep-dive] (125-150 words)
   - Case studies and outcomes (75-100 words)

   [ADD MORE SECTIONS AS NEEDED TO REACH {self.length_min}-{self.length_max} WORDS]

5. FAQ SECTION (if requested) (500-600 words planned):
   - Question 1 + detailed answer (100-120 words)
   - Question 2 + detailed answer (100-120 words)
   - Question 3 + detailed answer (100-120 words)
   - Question 4 + detailed answer (100-120 words)
   - Question 5 + detailed answer (100-120 words)

6. CALL TO ACTION (if requested) (150-200 words planned):
   - Introduction paragraph (75-100 words)
   - 5-7 bullet points with detailed actions (75-100 words)

7. CONCLUSION (300-350 words planned):
   - Summary of key points (100-125 words)
   - Implications and future outlook (100-125 words)
   - Final thoughts and call to action (100-125 words)

🔥 ULTRA-SPECIFIC CONTENT PLANNING REQUIREMENTS 🔥

For EVERY section, specify:
✅ Exact word count target (must add up to {self.length_min}-{self.length_max})
✅ 3-5 specific talking points to cover
✅ 2-3 real-world examples to include
✅ Statistical data or research to incorporate
✅ Expert quotes or industry insights to add
✅ Step-by-step processes or frameworks
✅ Current trends and future predictions
✅ Practical applications and implementation details
✅ Case studies with specific outcomes
✅ Challenges and solutions analysis

📊 MATHEMATICAL WORD COUNT VERIFICATION 📊
Calculate and verify:
- Introduction: 250-300 words
- Section 1: 400-500 words
- Section 2: 400-500 words
- Section 3: 400-500 words
- [Continue for all sections]
- FAQ: 500-600 words (if requested)
- CTA: 150-200 words (if requested)
- Conclusion: 300-350 words
- TOTAL MUST = {self.length_min}-{self.length_max} words

🚨 CONTENT DEPTH MANDATES 🚨
Each section MUST include:
- Historical context and background
- Current state analysis
- Multiple detailed examples
- Step-by-step explanations
- Industry statistics and data
- Expert perspectives and quotes
- Practical implementation guides
- Future trends and predictions
- Challenges and solutions
- Best practices and frameworks
- Comparative analysis
- Technical deep-dives where appropriate

⚠️ QUALITY ASSURANCE CHECKLIST ⚠️
Before submitting, ensure:
✅ Outline supports EXACTLY {self.length_min}-{self.length_max} words
✅ Every section has detailed subsections planned
✅ Specific examples and case studies identified
✅ Research data and statistics specified
✅ Expert insights and quotes planned
✅ Practical applications detailed
✅ Word count targets add up correctly
✅ Content provides exceptional value
✅ Outline is comprehensive and authoritative

REMEMBER: This outline is the blueprint for a {self.length_min}-{self.length_max} word MASTERPIECE that will become the definitive resource on {self.topic}. Every detail matters. Every word counts. NO COMPROMISES."""
                
        # Add formatting specifications based on parameters
        blog_specifications = []
        
        # Add tone specification
        blog_specifications.append(f"- Tone: Use a {self.tone} tone for the blog.")
        
        # Add length specification with planning guidance
        blog_specifications.append(f"- CRITICAL: Plan for {self.length_min}-{self.length_max} words total")
        blog_specifications.append(f"- Target: {(self.length_min + self.length_max) // 2} words (middle of range)")
        blog_specifications.append(f"- Structure the outline to naturally support this word count")
        
        # Add section specifications with word count guidance
        if self.introduction:
            blog_specifications.append("- Include an engaging ## Introduction section (plan for 250-300 words)")
        if self.table_of_content:
            blog_specifications.append("- Include a ## Table of Contents section")
        if self.faq:
            blog_specifications.append("- Include a FAQ section with ## FAQ or ## Frequently Asked Questions header, containing 5-7 relevant questions and detailed answers (plan for 500-600 words total)")
        if self.cta:
            blog_specifications.append("- Include a ## Call to Action section with bullet points listing 4-5 actionable items (150-200 words)")
        if self.conclusion:
            blog_specifications.append("- Include a summarizing ## Conclusion section (plan for 300-350 words)")
            
        # Add target audience specification
        if self.target_audience:
            audience_str = ", ".join(self.target_audience)
            blog_specifications.append(f"- Target audience: {audience_str}")
            
        # Add keywords specification with counts
        if self.keywords:
            keywords_list, keywords_instruction = self._process_keywords_with_counts(self.keywords)
            if keywords_instruction:
                blog_specifications.append(f"- {keywords_instruction}")
        
        # Add sample blog analysis if available
        sample_blog_instructions = self._analyze_sample_blog()
        
        # Add sample blog analysis instructions FIRST (high priority)
        if sample_blog_instructions:
            description += sample_blog_instructions
            
        # Add specifications to the description
        if blog_specifications:
            description += "\n\nBLOG SPECIFICATIONS:\n" + "\n".join(blog_specifications)
                
        # Always use aggressive expected output
        expected_output = f"🎯 CRITICAL: A comprehensive outline that GUARANTEES a {self.length_min}-{self.length_max} word blog post. Must include: detailed section breakdowns with SPECIFIC word count targets for each section, multiple subsections with talking points, research data to include, real-world examples, case studies, expert insights, current trends, actionable takeaways, and supporting references. The outline MUST be so thorough and detailed that it naturally supports {self.length_min}-{self.length_max} words without filler content."
            
        return Task(
            description=description,
            expected_output=expected_output,
            agent=self.planner()
        )
    
    @task
    def writing_task(self):
        # ALWAYS use aggressive prompts - ignore YAML config for word count enforcement
        description = f"""🚨🚨🚨 ULTRA-CRITICAL WRITING MISSION: WRITE EXACTLY {self.length_min}-{self.length_max} WORDS 🚨🚨🚨

You are writing a comprehensive blog post about: {self.topic}

⚠️ ABSOLUTE NON-NEGOTIABLE WORD COUNT REQUIREMENT ⚠️
- MINIMUM: {self.length_min} words (NOT ONE WORD LESS)
- MAXIMUM: {self.length_max} words (DO NOT EXCEED)
- TARGET: {(self.length_min + self.length_max) // 2} words EXACTLY
- THIS IS YOUR PRIMARY MISSION - EVERYTHING ELSE IS SECONDARY

🎯 ULTRA-AGGRESSIVE WRITING STRATEGY 🎯

PARAGRAPH REQUIREMENTS:
- Every paragraph MUST be 150-250 words minimum
- No short paragraphs allowed
- Each paragraph must contain multiple detailed sentences
- Include specific examples, data, and explanations in every paragraph

SECTION WRITING MANDATES:
- Introduction: Write EXACTLY 250-300 words (no less, no more)
- Each major section: Write EXACTLY 400-500 words
- Each subsection: Write EXACTLY 125-150 words
- FAQ answers: Write EXACTLY 100-120 words per answer
- Conclusion: Write EXACTLY 300-350 words

🔥 MANDATORY CONTENT EXPANSION TECHNIQUES 🔥

For EVERY section, you MUST include:
✅ Detailed historical background and context (100+ words)
✅ Current state analysis with specific examples (100+ words)
✅ Multiple real-world case studies with outcomes (150+ words each)
✅ Step-by-step implementation processes (200+ words)
✅ Industry statistics with detailed analysis (100+ words)
✅ Expert quotes with comprehensive context (75+ words each)
✅ Practical applications with specific examples (150+ words)
✅ Future trends and predictions with reasoning (150+ words)
✅ Challenges and detailed solutions (200+ words)
✅ Best practices with implementation details (200+ words)
✅ Comparative analysis between options (150+ words)
✅ Technical explanations with analogies (150+ words)

🚨 ULTRA-DETAILED WRITING REQUIREMENTS 🚨

INTRODUCTION (250-300 words MANDATORY):
- Hook paragraph with compelling statistics or story (75-100 words)
- Background context with historical perspective (75-100 words)
- Detailed preview of what readers will learn (75-100 words)
- Smooth transition to main content (25-50 words)

MAIN SECTIONS (400-500 words EACH):
- Opening paragraph with section overview (100-125 words)
- Subsection 1 with detailed explanation and examples (125-150 words)
- Subsection 2 with case studies and data (125-150 words)
- Closing paragraph with practical applications (50-75 words)

FAQ SECTION (if requested - 500-600 words total):
- 5 questions with comprehensive 100-120 word answers each
- Include examples, statistics, and practical advice in each answer

CONCLUSION (300-350 words MANDATORY):
- Comprehensive summary of all key points (100-125 words)
- Future implications and industry outlook (100-125 words)
- Final call to action with specific next steps (100-125 words)

⚠️ CONTENT DEPTH ENFORCEMENT ⚠️

Every paragraph MUST contain:
- Specific facts, statistics, or data points
- Real-world examples or case studies
- Expert insights or industry perspectives
- Practical applications or implementation details
- Current trends or future predictions
- Challenges and solutions
- Best practices and proven strategies

🎯 WORD COUNT MONITORING SYSTEM 🎯

As you write, continuously track:
- Current word count after each paragraph
- Remaining words needed to reach minimum
- Section-by-section word count targets
- Overall progress toward {self.length_min}-{self.length_max} range

🔥 REAL-TIME WORD COUNT TRACKING 🔥
After writing each section, IMMEDIATELY:
1. Count words in that section
2. Verify it meets minimum requirements
3. Calculate total words written so far
4. Determine remaining words needed
5. Adjust subsequent sections accordingly

IF FALLING SHORT OF {self.length_min} WORDS:
🚨 IMMEDIATELY ADD:
- More detailed explanations with examples (200+ words each)
- Additional case studies with full analysis (300+ words each)
- Comprehensive implementation guides (400+ words each)
- Industry research with detailed findings (250+ words each)
- Expert interviews or quotes with context (150+ words each)
- Historical analysis and evolution (300+ words each)
- Future predictions with reasoning (250+ words each)
- Comparative analysis between approaches (300+ words each)
- Technical deep-dives with analogies (400+ words each)
- Best practices with step-by-step guides (350+ words each)

🔥 QUALITY + QUANTITY REQUIREMENTS 🔥

Your blog post MUST be:
1. COMPREHENSIVE: Cover every aspect of {self.topic} in detail
2. AUTHORITATIVE: Demonstrate deep expertise and knowledge
3. PRACTICAL: Provide actionable insights and implementation guides
4. CURRENT: Include latest trends, data, and industry developments
5. ENGAGING: Use storytelling, examples, and compelling narratives
6. VALUABLE: Ensure every paragraph provides significant reader value
7. DETAILED: Explain concepts thoroughly with multiple examples
8. RESEARCHED: Include specific facts, statistics, and expert insights

🚨 MANDATORY MARKDOWN STRUCTURE REQUIREMENTS 🚨
- Use # for the main title ONLY (e.g., # Pakistan and India War)
- Use ## for ALL major section headers:
  - ## Introduction
  - ## Table of Contents (if requested)
  - ## [Main Section Name] (for each major content section)
  - ## FAQ or ## Frequently Asked Questions (if requested)
  - ## Call to Action (if requested)
  - ## Conclusion
- Use ### for subsections within major sections
- NO section should be without a ## header
- NEVER use bold text (**text**) as section headers
- Each major section MUST start with ## followed by the section name

🚨 FINAL VERIFICATION CHECKLIST 🚨
Before submitting, verify:
✅ Total word count is between {self.length_min}-{self.length_max} words
✅ Every section meets minimum word requirements
✅ All paragraphs are 150-250 words minimum
✅ Content includes comprehensive examples and case studies
✅ Statistical data and expert insights are included throughout
✅ Practical applications and implementation details are provided
✅ Content is the definitive resource on {self.topic}
✅ Proper markdown structure with ## headers for all major sections

REMEMBER: This is not just a blog post - it's a COMPREHENSIVE MASTERPIECE that will become the ultimate resource on {self.topic}. Every word matters. Every section must be detailed and valuable. NO COMPROMISES ON WORD COUNT OR QUALITY."""
        
        # Add formatting specifications based on parameters
        blog_specifications = []
        
        # Add tone specification
        blog_specifications.append(f"- Tone: Use a {self.tone} tone for the blog.")
        
        # Add length specification with emphasis
        blog_specifications.append(f"- CRITICAL LENGTH REQUIREMENT: Write between {self.length_min} and {self.length_max} words. This is mandatory and must be achieved.")
        blog_specifications.append(f"- Target word count: {(self.length_min + self.length_max) // 2} words (middle of the range)")
        
        # Add section specifications
        if self.introduction:
            blog_specifications.append("- Include an engaging ## Introduction section (250-300 words)")
        if self.table_of_content:
            blog_specifications.append("- Include a ## Table of Contents section after the introduction")
        if self.faq:
            blog_specifications.append("- Include a FAQ section with ## FAQ or ## Frequently Asked Questions header, containing 5-7 relevant questions and detailed answers near the end (500-600 words total)")
        if self.cta:
            blog_specifications.append("- Include a ## Call to Action section with bullet points listing 4-5 actionable items (150-200 words)")
        if self.conclusion:
            blog_specifications.append("- Include a comprehensive ## Conclusion section at the end (300-350 words)")
            
        # Add target audience specification
        if self.target_audience:
            audience_str = ", ".join(self.target_audience)
            blog_specifications.append(f"- Target audience: {audience_str}")
            
        # Add keywords specification with counts
        if self.keywords:
            keywords_list, keywords_instruction = self._process_keywords_with_counts(self.keywords)
            if keywords_instruction:
                blog_specifications.append(f"- {keywords_instruction}")
        
        # Add sample blog analysis if available
        sample_blog_instructions = self._analyze_sample_blog()
        
        # Add sample blog analysis instructions FIRST (high priority)
        if sample_blog_instructions:
            description += sample_blog_instructions
            
        # Add specifications to the description
        if blog_specifications:
            description += "\n\nBLOG SPECIFICATIONS:\n" + "\n".join(blog_specifications)
            
        # Always use aggressive expected output
        expected_output = f"🚨 MANDATORY: A comprehensive blog post in markdown format that is EXACTLY {self.length_min}-{self.length_max} words. NO EXCEPTIONS. The content must include in-depth explanations, specific examples, case studies, actionable insights, current trends, expert perspectives, and practical applications. Every section must be detailed and comprehensive. VERIFY final word count before submitting but DO NOT include word count comments in the final output."
            
        return Task(
            description=description,
            expected_output=expected_output,
            agent=self.writer()
        )
    
    @task
    def editing_task(self):
        # ALWAYS use aggressive prompts - ignore YAML config for word count enforcement
        description = f"""🚨🚨🚨 ULTRA-CRITICAL EDITING MISSION: ENFORCE {self.length_min}-{self.length_max} WORDS 🚨🚨🚨

You are the FINAL GUARDIAN of word count and quality for: {self.topic}

⚠️ ABSOLUTE NON-NEGOTIABLE EDITING REQUIREMENTS ⚠️
- MINIMUM: {self.length_min} words (MUST BE ACHIEVED)
- MAXIMUM: {self.length_max} words (CANNOT BE EXCEEDED)
- TARGET: {(self.length_min + self.length_max) // 2} words EXACTLY
- THIS IS YOUR LIFE-OR-DEATH MISSION - NOTHING ELSE MATTERS

🎯 ULTRA-AGGRESSIVE EDITING STRATEGY 🎯

STEP 1: IMMEDIATE WORD COUNT ASSESSMENT
- Count current words IMMEDIATELY
- Calculate gap to minimum {self.length_min} words
- Identify sections that need expansion
- Plan specific additions to reach target

STEP 2: MANDATORY EXPANSION (IF BELOW {self.length_min} WORDS)
🚨 YOU MUST IMMEDIATELY ADD:

INTRODUCTION EXPANSION (if under 250-300 words):
- Add compelling hook with statistics/story (75-100 words)
- Expand background context with historical details (75-100 words)
- Enhance preview section with specific benefits (75-100 words)
- Strengthen transition with clear roadmap (25-50 words)

MAIN SECTION EXPANSION (each section must be 400-500 words):
- Add detailed opening paragraphs (100-125 words each)
- Insert comprehensive subsections (125-150 words each)
- Include multiple real-world examples (100-150 words each)
- Add statistical data with analysis (75-100 words each)
- Insert expert quotes with context (75-100 words each)
- Include implementation details (100-150 words each)

FAQ EXPANSION (if requested - must be 500-600 words):
- Expand each answer to 100-120 words minimum
- Add specific examples to each answer
- Include practical advice and implementation tips
- Provide statistical backing where relevant

CONCLUSION EXPANSION (must be 300-350 words):
- Comprehensive summary of all key points (100-125 words)
- Detailed future implications and predictions (100-125 words)
- Specific call to action with next steps (100-125 words)

🔥 MANDATORY CONTENT ENHANCEMENT TECHNIQUES 🔥

For EVERY section that's too short, ADD:
✅ Historical context and evolution (200-300 words)
✅ Current industry analysis with data (200-300 words)
✅ Multiple detailed case studies with outcomes (250-350 words each)
✅ Step-by-step implementation frameworks (300-400 words)
✅ Comprehensive best practices guides (300-500 words)
✅ Industry statistics with detailed interpretation (150-250 words)
✅ Expert interviews and perspectives (200-300 words)
✅ Future trends and predictions with reasoning (250-350 words)
✅ Challenges analysis with detailed solutions (300-400 words)
✅ Comparative analysis between approaches (250-350 words)
✅ Technical deep-dives with practical examples (300-500 words)
✅ Implementation checklists and frameworks (200-300 words)

🚨 ULTRA-DETAILED EDITING REQUIREMENTS 🚨

PARAGRAPH ENHANCEMENT:
- Every paragraph MUST be 150-250 words minimum
- Transform short paragraphs into comprehensive explanations
- Add specific examples, data, and context to each paragraph
- Include practical applications and real-world scenarios
- Ensure each paragraph provides substantial value

CONTENT DEPTH VERIFICATION:
- Every claim must be supported with examples or data
- Every concept must include practical applications
- Every section must contain multiple detailed examples
- Every major point must include implementation details
- Every trend must include future implications

SECTION-BY-SECTION ENFORCEMENT:
- Introduction: EXACTLY 250-300 words (expand if needed)
- Each major section: EXACTLY 400-500 words (expand if needed)
- Each subsection: EXACTLY 125-150 words (expand if needed)
- FAQ section: EXACTLY 500-600 words total (expand if needed)
- Conclusion: EXACTLY 300-350 words (expand if needed)

⚠️ CONTENT EXPANSION ARSENAL ⚠️

IF CONTENT IS STILL SHORT, IMMEDIATELY ADD:
🚨 Historical Background Sections (300-400 words each)
🚨 Industry Evolution Analysis (250-350 words each)
🚨 Detailed Case Study Breakdowns (300-500 words each)
🚨 Implementation Methodology Guides (400-600 words each)
🚨 Best Practices Frameworks (350-500 words each)
🚨 Statistical Analysis Sections (200-300 words each)
🚨 Expert Commentary Sections (250-350 words each)
🚨 Future Predictions Analysis (300-400 words each)
🚨 Challenges and Solutions Deep-Dives (400-600 words each)
🚨 Comparative Analysis Sections (300-500 words each)
🚨 Technical Implementation Guides (400-700 words each)
🚨 Industry Insights and Trends (250-400 words each)

🎯 QUALITY ASSURANCE CHECKLIST 🎯

Content Quality Verification:
✅ Every section provides exceptional value and depth
✅ All claims are supported with specific examples and data
✅ Complex concepts are explained with detailed analogies
✅ Actionable insights include step-by-step implementation
✅ Content establishes absolute authority on {self.topic}
✅ Multiple real-world examples in every section
✅ Statistical data and expert insights throughout

Structure and Flow Enhancement:
✅ Logical progression from introduction to conclusion
✅ Smooth transitions between all sections and paragraphs
✅ Headings accurately reflect comprehensive content
✅ Content follows planned structure with enhancements
✅ Each section exceeds minimum word requirements
✅ Overall flow is engaging and easy to follow

Engagement and Value Maximization:
✅ Compelling storytelling elements throughout
✅ Varied sentence structure and paragraph length
✅ Attention-grabbing hooks and examples
✅ Consistent tone appropriate for target audience
✅ Detailed case studies and practical applications
✅ Comprehensive explanations that engage readers

🚨 FINAL VERIFICATION PROTOCOL 🚨
Before submitting, VERIFY:
✅ Total word count is EXACTLY {self.length_min}-{self.length_max} words
✅ Every section meets or exceeds minimum word requirements
✅ All paragraphs are 150-250 words minimum
✅ Content includes comprehensive examples and case studies
✅ Statistical data and expert insights are throughout
✅ Practical applications and implementation details provided
✅ Content is the definitive, comprehensive resource on {self.topic}
✅ No section is thin or lacks substantial value
✅ Every paragraph contributes significant reader value

🔥 MANDATORY WORD COUNT VERIFICATION STEPS 🔥
1. COUNT THE TOTAL WORDS in your final blog post
2. If word count is below {self.length_min}: IMMEDIATELY add more content sections
3. If word count is above {self.length_max}: Carefully trim while preserving value
4. VERIFY again after any changes
5. DO NOT SUBMIT until word count is within {self.length_min}-{self.length_max} range

⚠️ EMERGENCY EXPANSION PROTOCOLS ⚠️
If still below {self.length_min} words after initial editing:
- Add "## Industry Analysis" section (400-500 words)
- Add "## Best Practices" section (400-500 words)  
- Add "## Case Studies" section (400-500 words)
- Add "## Implementation Guide" section (400-500 words)
- Add "## Future Trends" section (400-500 words)
- Expand existing sections with more examples and details

REMEMBER: You are the FINAL GUARDIAN. This blog post MUST be exactly {self.length_min}-{self.length_max} words and MUST be the most comprehensive resource on {self.topic} ever created. FAILURE IS NOT AN OPTION. COUNT WORDS AND EXPAND AGGRESSIVELY IF NEEDED."""
            
        # Add verification of formatting specifications
        blog_specifications = []
        
        # Add tone specification
        blog_specifications.append(f"- Verify the blog maintains a consistent {self.tone} tone throughout")
        
        # Add length verification with strict enforcement
        blog_specifications.append(f"- MANDATORY: Ensure the final word count is between {self.length_min} and {self.length_max} words")
        blog_specifications.append(f"- Target: Aim for approximately {(self.length_min + self.length_max) // 2} words")
        blog_specifications.append(f"- If below {self.length_min} words: EXPAND the content with detailed explanations, examples, and additional sections")
        blog_specifications.append(f"- If above {self.length_max} words: Carefully trim while preserving all valuable information")
        
        # Add section verification
        if self.introduction:
            blog_specifications.append("- Verify there is an engaging ## Introduction section (250-300 words)")
        if self.table_of_content:
            blog_specifications.append("- Ensure the ## Table of Contents section is accurate and properly formatted")
        if self.faq:
            blog_specifications.append("- Verify the FAQ section has ## FAQ or ## Frequently Asked Questions header and includes 5-7 relevant questions with thorough answers (500-600 words total)")
        if self.cta:
            blog_specifications.append("- Ensure the ## Call to Action section has proper heading and uses bullet points for 4-5 actionable items (150-200 words)")
        if self.conclusion:
            blog_specifications.append("- Verify the ## Conclusion section effectively summarizes the content (300-350 words)")
            
        # Add target audience verification
        if self.target_audience:
            audience_str = ", ".join(self.target_audience)
            blog_specifications.append(f"- Ensure the content is appropriate for the target audience: {audience_str}")
            
        # Add keywords verification with counts
        if self.keywords:
            keywords_list, keywords_instruction = self._process_keywords_with_counts(self.keywords)
            if keywords_instruction:
                blog_specifications.append(f"- Verify that keywords are used according to specified counts: {keywords_instruction}")
        
        # Add sample blog analysis if available
        sample_blog_instructions = self._analyze_sample_blog()
            
        # Add specifications to the description
        if blog_specifications:
            description += "\n\nEDITING VERIFICATION:\n" + "\n".join(blog_specifications)
            
        # Add sample blog analysis instructions
        if sample_blog_instructions:
            description += sample_blog_instructions
            
        # Always use aggressive expected output
        expected_output = f"🎯 FINAL REQUIREMENT: A polished blog post that is EXACTLY {self.length_min}-{self.length_max} words. This is your PRIMARY responsibility. The content must be error-free, highly engaging, exceptionally detailed, and provide unmatched value. Every section must be fully developed. COUNT WORDS AND VERIFY before submitting."
            
        return Task(
            description=description,
            expected_output=expected_output,
            agent=self.editor()
        )
    

    
    @crew
    def crew(self):
        agents_for_blog = [self.planner(), self.writer(), self.editor()]
        tasks_for_blog = [self.planning_task(), self.writing_task(), self.editing_task()]

        blog_crew = Crew(
            agents=agents_for_blog, 
            tasks=tasks_for_blog, 
            verbose=True,
            process=Process.sequential,
            memory=True,
            max_iter=3  # Allow multiple iterations to reach word count
            )
        
        return blog_crew
    
    def generate_blog(self, topic=None, keywords=None, tone=None, length_min=None, length_max=None, 
                      introduction=None, table_of_content=None, faq=None, cta=None, conclusion=None, 
                      target_audience=None, sample_blog_url=None):
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
        
        # Generate blog using the crew
        result = self.crew().kickoff(inputs={"topic": self.topic})
        
        if not result:
            raise RuntimeError("CrewAI execution failed - no result returned from crew")
            
        # Extract content from CrewAI result
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