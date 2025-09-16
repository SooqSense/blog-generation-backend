from crewai import Agent
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv
import re

load_dotenv()

class ContextualImagePromptAgent:
    """
    An AI agent that deeply analyzes blog section content and generates 
    contextually appropriate image prompts based on semantic understanding
    """
    
    def __init__(self, use_custom_llm=False):
        """
        Initialize the contextual image prompt agent
        
        Args:
            use_custom_llm (bool): Whether to use Google Gemini instead of OpenAI
        """
        self.use_custom_llm = use_custom_llm
        
        # Initialize LLM
        if use_custom_llm:
            gemini_api_key = os.getenv("GOOGLE_API_KEY")
            if not gemini_api_key:
                raise ValueError("GOOGLE_API_KEY not found for custom LLM")
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-pro",
                google_api_key=gemini_api_key,
                temperature=0.7,
            )
        else:
            self.llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.7,
                max_tokens=2000
            )
    
    def create_contextual_agent(self):
        """Create the contextual image prompt generation agent"""
        return Agent(
            role="Contextual Visual Content Strategist",
            goal="""Analyze blog section content deeply to understand its semantic context, themes, 
            and subject matter, then generate highly specific, contextually appropriate image prompts 
            that perfectly match the content's meaning and tone.""",
            backstory="""You are an expert visual content strategist with deep understanding of semantic 
            analysis and contextual image generation. Your specialty is reading and comprehending written 
            content to identify its core themes, emotional tone, subject matter, and contextual elements, 
            then translating this understanding into precise image prompts.
            
            You excel at:
            - Semantic content analysis and theme extraction
            - Identifying the primary subject matter (political, technical, artistic, historical, etc.)
            - Understanding emotional tone and appropriate visual style
            - Generating contextually accurate image descriptions
            - Adapting visual style to match content type (photojournalistic for news, artistic for creative content, etc.)
            
            You avoid generic corporate imagery and instead focus on content-specific visuals that 
            directly support and enhance the written material's meaning.""",
            verbose=True,
            llm=self.llm,
            allow_delegation=False
        )
    
    def analyze_section_context(self, section_content, section_name, topic, blog_type):
        """
        Deeply analyze section content to understand context and generate appropriate image prompt
        
        Args:
            section_content (str): The actual text content of the section
            section_name (str): Name of the section (banner, main_content, etc.)
            topic (str): Overall blog topic
            blog_type (str): Type of blog (News, Opinion, etc.)
            
        Returns:
            str: A contextually appropriate image prompt
        """
        # Create the contextual agent
        agent = self.create_contextual_agent()
        
        # Analyze the content and generate a contextual prompt
        analysis_prompt = f"""
Analyze this blog section content and generate a highly specific, contextually appropriate image prompt:

**Blog Topic:** {topic}
**Blog Type:** {blog_type}
**Section:** {section_name}
**Section Content:**
{section_content}

**Task:** 
1. First, deeply analyze the content to understand:
   - Primary subject matter and themes
   - Emotional tone and atmosphere
   - Key concepts and entities mentioned
   - Appropriate visual style for this content type
   - Specific elements that should be visualized

2. Then generate a detailed, contextually accurate image prompt that:
   - Directly relates to the specific content discussed
   - Matches the appropriate visual style (photojournalistic for politics, technical for tech, artistic for creative topics, etc.)
   - Includes specific elements mentioned in the content
   - Captures the emotional tone and atmosphere
   - Is suitable for FLUX AI image generation
   - Uses 1920x1080 aspect ratio considerations

**Important Guidelines:**
- Be highly specific to the actual content, not generic
- Match the subject matter (political content = political imagery, tech content = tech imagery, etc.)
- Include relevant entities, locations, or concepts mentioned
- Consider the emotional weight and tone of the content
- Avoid generic corporate/business imagery unless specifically appropriate
- Make the prompt actionable for AI image generation

**Output:** Provide only the final image prompt (no explanations or analysis text).
"""

        try:
            # Use the LLM to analyze and generate the prompt
            response = self.llm.invoke(analysis_prompt)
            generated_prompt = response.content.strip()
            
            # Clean the prompt - remove any prefixes or explanations
            cleaned_prompt = self._clean_generated_prompt(generated_prompt)
            
            print(f"DEBUG: Generated contextual prompt for {section_name}: {cleaned_prompt[:100]}...")
            
            return cleaned_prompt
            
        except Exception as e:
            print(f"ERROR: Failed to generate contextual prompt for {section_name}: {str(e)}")
            # Fallback to a basic contextual prompt
            return self._generate_fallback_prompt(section_content, section_name, topic, blog_type)
    
    def _clean_generated_prompt(self, prompt):
        """Clean the generated prompt to ensure it's suitable for image generation"""
        # Remove common prefixes
        prefixes_to_remove = [
            "Image prompt:", "Prompt:", "Generated prompt:", "Final prompt:",
            "Here is the image prompt:", "The image prompt is:", "Image description:",
            "Visual prompt:", "Photo prompt:", "**Image Prompt:**", "**Prompt:**"
        ]
        
        cleaned_prompt = prompt.strip()
        
        for prefix in prefixes_to_remove:
            if cleaned_prompt.lower().startswith(prefix.lower()):
                cleaned_prompt = cleaned_prompt[len(prefix):].strip()
        
        # Remove quotes if the entire prompt is wrapped in them
        if (cleaned_prompt.startswith('"') and cleaned_prompt.endswith('"')) or \
           (cleaned_prompt.startswith("'") and cleaned_prompt.endswith("'")):
            cleaned_prompt = cleaned_prompt[1:-1].strip()
        
        # Ensure prompt is not too long (FLUX works best with concise prompts)
        if len(cleaned_prompt) > 300:
            # Keep the first 300 characters and try to end at a complete sentence
            truncated = cleaned_prompt[:300]
            last_period = truncated.rfind('.')
            if last_period > 200:  # Only truncate at period if it's not too early
                cleaned_prompt = truncated[:last_period + 1]
            else:
                cleaned_prompt = truncated
        
        return cleaned_prompt
    
    def _generate_fallback_prompt(self, section_content, section_name, topic, blog_type):
        """Generate a basic fallback prompt if the LLM analysis fails"""
        # Extract key themes from content for fallback
        content_lower = section_content.lower() if section_content else ""
        
        # Identify subject matter
        political_keywords = ['government', 'election', 'policy', 'political', 'congress', 'senate', 'president', 'minister', 'vote', 'democracy', 'israel', 'america', 'alliance', 'diplomat']
        tech_keywords = ['technology', 'ai', 'software', 'digital', 'algorithm', 'data', 'computer', 'internet', 'cyber', 'tech']
        business_keywords = ['business', 'company', 'market', 'economy', 'financial', 'corporate', 'industry', 'commerce']
        health_keywords = ['health', 'medical', 'doctor', 'hospital', 'treatment', 'disease', 'medicine', 'healthcare']
        
        if any(keyword in content_lower for keyword in political_keywords):
            subject_style = "photojournalistic documentary style showing political themes"
        elif any(keyword in content_lower for keyword in tech_keywords):
            subject_style = "modern technology and innovation focused"
        elif any(keyword in content_lower for keyword in business_keywords):
            subject_style = "professional business and industry focused"
        elif any(keyword in content_lower for keyword in health_keywords):
            subject_style = "medical and healthcare professional setting"
        else:
            subject_style = "contextually appropriate professional"
        
        return f"Professional {subject_style} image representing {topic} with {section_name} context, photorealistic quality, 1920x1080 aspect ratio"
    
    def generate_section_prompts(self, content_sections, topic, blog_type):
        """
        Generate contextual prompts for all blog sections
        
        Args:
            content_sections (dict): Dictionary with section names as keys and content as values
            topic (str): Blog topic
            blog_type (str): Blog type
            
        Returns:
            dict: Dictionary with section names as keys and contextual prompts as values
        """
        section_prompts = {}
        
        # Standard sections with their content
        sections_to_process = {
            'banner': content_sections.get('introduction', ''),
            'main_content': content_sections.get('main_content', ''),
            'supporting_details': content_sections.get('supporting_details', ''),
            'evidence': content_sections.get('evidence', ''),
            'conclusion': content_sections.get('conclusion', '')
        }
        
        for section_name, content in sections_to_process.items():
            if content and len(content.strip()) > 20:  # Only process if there's meaningful content
                contextual_prompt = self.analyze_section_context(
                    section_content=content,
                    section_name=section_name,
                    topic=topic,
                    blog_type=blog_type
                )
                section_prompts[section_name] = contextual_prompt
            else:
                # Generate a basic contextual prompt if no content available
                section_prompts[section_name] = self._generate_fallback_prompt(
                    "", section_name, topic, blog_type
                )
                
        print(f"DEBUG: Generated {len(section_prompts)} contextual prompts for {topic}")
        return section_prompts
