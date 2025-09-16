from crewai import Agent
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv
import re

load_dotenv()

class ContextualImagePromptAgent:
    """
    An AI agent that generates realistic, professional photography prompts for blog sections.
    This agent is the PRIMARY source for ALL blog image generation prompts, ensuring consistent
    realistic, clean, professional imagery across all blog content.
    
    Key Features:
    - Generates ONLY photorealistic, professional photography prompts
    - Analyzes blog content for contextually relevant visual concepts  
    - Enforces realistic business/corporate photography aesthetics
    - Removes any digital art, illustration, or stylized imagery terminology
    - Adds essential photography terms (professional camera, natural lighting, etc.)
    - Provides realistic fallback prompts for error cases
    
    Important: This agent focuses exclusively on realistic photography that looks like
    professional business magazine photos or high-end corporate website imagery.
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
            role="Professional Photography Prompt Specialist",
            goal="""Generate photorealistic image prompts that produce professional, clean, 
            realistic photographs for blog content using FLUX AI.""",
            backstory="""You are a professional photography prompt specialist who creates prompts 
            for realistic, high-quality business photography. You have extensive experience in 
            commercial photography and understand how to describe professional shots that look 
            like real photographs taken with professional cameras.
            
            Your specializations include:
            - Professional business and corporate photography
            - Clean, minimal compositions with proper lighting
            - Realistic human subjects in professional settings
            - High-end commercial photography aesthetics
            - Natural and studio lighting techniques
            - Professional camera equipment and techniques
            
            You NEVER create prompts for digital art, illustrations, or stylized imagery. 
            You focus exclusively on realistic photography that looks professional, clean, 
            and authentic - like photographs from high-end business magazines or corporate websites.
            
            Your prompts always specify "photorealistic", "professional photograph", 
            "shot with professional camera", and include proper photography terminology.""",
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
        
        # Generate a realistic, professional image prompt
        analysis_prompt = f"""
Create a photorealistic image prompt for {section_name} section about {topic}.

Content: {section_content[:500]}...

Generate a realistic photography prompt that creates:
- Professional photorealistic photography (NOT digital art, NOT illustrations)
- Clean, minimal composition with professional lighting
- Real-world business/professional setting
- High-quality camera shot with proper depth of field
- Realistic people in professional attire if humans are needed
- Clean backgrounds without clutter
- Natural lighting or professional studio lighting
- Corporate/business aesthetic matching {blog_type} content
- Specific visual elements from the actual content

Requirements:
- Start with "Professional photograph of" or "Photorealistic shot of"
- Include "shot with professional camera, clean composition, natural lighting"
- Avoid: digital art, illustrations, cartoons, overly stylized imagery
- Focus: realistic, professional, clean, minimal

Output only the realistic photography prompt, no explanations.
"""

        try:
            # Use the LLM to analyze and generate the prompt
            response = self.llm.invoke(analysis_prompt)
            generated_prompt = response.content.strip()
            
            # Clean the prompt - remove any prefixes or explanations
            cleaned_prompt = self._clean_generated_prompt(generated_prompt)
            
            # Enhance with photography terminology for realism
            enhanced_prompt = self._enhance_for_realism(cleaned_prompt, topic, blog_type)
            
            print(f"DEBUG: Generated realistic prompt for {section_name}: {enhanced_prompt[:100]}...")
            
            return enhanced_prompt
            
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
    
    def _enhance_for_realism(self, prompt, topic, blog_type):
        """
        Enhance the prompt to ensure it generates realistic, professional photography
        
        Args:
            prompt (str): The cleaned prompt
            topic (str): Blog topic
            blog_type (str): Blog type
            
        Returns:
            str: Enhanced realistic photography prompt
        """
        if not prompt or len(prompt.strip()) < 10:
            return self._generate_fallback_prompt("", "general", topic, blog_type)
        
        prompt = prompt.strip()
        
        # Remove any digital art/illustration terminology
        unrealistic_terms = {
            'digital art': 'professional photograph',
            'illustration': 'professional photograph', 
            'cartoon': 'professional photograph',
            'anime': 'professional photograph',
            'drawing': 'professional photograph',
            'painting': 'professional photograph',
            'artistic rendering': 'professional photograph',
            'stylized': 'photorealistic',
            'abstract': 'professional',
            'neon': 'professional lighting',
            'glowing': 'well-lit',
            'futuristic': 'modern professional'
        }
        
        prompt_lower = prompt.lower()
        for unrealistic, realistic in unrealistic_terms.items():
            if unrealistic in prompt_lower:
                prompt = prompt.lower().replace(unrealistic, realistic)
        
        # Ensure it starts with photography terminology
        photography_starters = ['professional photograph', 'photorealistic shot', 'professional photo', 'high-quality photograph']
        if not any(starter in prompt.lower() for starter in photography_starters):
            prompt = f"Professional photograph of {prompt}"
        
        # Ensure it includes essential photography terms
        essential_terms = ['photorealistic', 'professional camera', 'natural lighting', 'clean composition']
        missing_terms = [term for term in essential_terms if term not in prompt.lower()]
        
        if missing_terms:
            prompt += f", {', '.join(missing_terms)}"
        
        # Add quality and style specifications
        if 'depth of field' not in prompt.lower():
            prompt += ", depth of field"
        
        if 'high quality' not in prompt.lower() and 'high-quality' not in prompt.lower():
            prompt += ", high quality business photography"
        
        # Ensure realistic human descriptions if people are mentioned
        if any(word in prompt.lower() for word in ['people', 'person', 'man', 'woman', 'team', 'group', 'professional']):
            if 'professional attire' not in prompt.lower() and 'business attire' not in prompt.lower():
                prompt += ", people in professional business attire"
        
        return prompt.strip()
    
    def _generate_fallback_prompt(self, section_content, section_name, topic, blog_type):
        """Generate a realistic photography fallback prompt if the LLM analysis fails"""
        # Simple categorization for realistic photography styles
        content_lower = section_content.lower() if section_content else ""
        
        # Determine realistic photography style based on content type
        if any(word in content_lower for word in ['government', 'policy', 'political', 'election']):
            setting = "professional government office with clean modern architecture"
        elif any(word in content_lower for word in ['technology', 'ai', 'digital', 'tech']):
            setting = "modern technology office with clean minimal design and professional equipment"
        elif any(word in content_lower for word in ['business', 'market', 'financial']):
            setting = "sophisticated corporate boardroom with professional business atmosphere"
        elif any(word in content_lower for word in ['health', 'medical', 'healthcare']):
            setting = "clean modern medical facility with professional healthcare environment"
        else:
            setting = "professional modern office space with minimal clean design"
        
        return f"Professional photograph of {setting} related to {topic}, shot with professional camera, natural lighting, clean composition, photorealistic, high quality business photography, depth of field"
    
    def generate_section_prompts(self, content_sections, topic, blog_type):
        """
        Generate contextual prompts for all blog sections
        
        This is the PRIMARY method for generating all blog image prompts.
        All blog image generation should use prompts generated by this agent.
        
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
