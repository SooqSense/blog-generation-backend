from crewai import Agent
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv
import re
import random

load_dotenv()

class ContextualImagePromptAgent:
    """
    An AI agent that generates diverse, contextually appropriate image prompts for blog sections.
    This agent analyzes the TOPIC and CONTENT to determine the best visual style and approach
    for each image, creating varied styles from professional photography to digital art, 
    infographics, illustrations, and artistic representations.
    
    Key Features:
    - Analyzes topic domain to understand appropriate visual styles
    - Analyzes section content to extract key visual concepts
    - Generates varied image styles: professional photography, digital art, infographics, 
      illustrations, abstract art, technical diagrams, artistic representations
    - Matches image style to content context and topic domain
    - Creates unique prompts for each section to avoid repetitive imagery
    
    Enhanced Flow:
    1. Topic Analysis: Understand the subject domain and appropriate visual approaches
    2. Content Analysis: Extract key concepts, data, and visual elements from section text
    3. Style Selection: Choose appropriate visual style based on content type and section purpose  
    4. Prompt Generation: Create detailed, contextually appropriate image prompts
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
                temperature=0.8,  # Higher creativity for varied styles
            )
        else:
            self.llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.8,  # Higher creativity for varied styles
                max_tokens=2000
            )
        
        # Ultra-clean style mapping for different content types and topics
        self.style_preferences = {
            'technology': ['ultra-clean professional photography', 'crystal-clear futuristic illustration', 'pristine technical diagram', 'premium tech photography'],
            'business': ['ultra-realistic professional photography', 'crystal-clear infographic', 'pristine corporate illustration', 'premium data visualization'],
            'science': ['crystal-clear scientific illustration', 'ultra-clean infographic', 'pristine technical diagram', 'professional abstract visualization'],
            'healthcare': ['ultra-clean medical illustration', 'crystal-clear professional photography', 'pristine scientific visualization', 'premium medical infographic'],
            'education': ['crystal-clear educational illustration', 'ultra-clean infographic', 'pristine conceptual art', 'premium professional photography'],
            'finance': ['ultra-clean data visualization', 'crystal-clear professional photography', 'pristine minimalist illustration', 'premium financial infographic'],
            'environment': ['ultra-realistic nature photography', 'crystal-clear environmental illustration', 'pristine conceptual art', 'premium professional photography'],
            'politics': ['ultra-realistic professional photography', 'crystal-clear editorial illustration', 'pristine infographic', 'premium documentary style'],
            'culture': ['crystal-clear artistic illustration', 'ultra-realistic creative photography', 'pristine cultural art', 'premium conceptual design'],
            'sports': ['ultra-realistic action photography', 'crystal-clear dynamic illustration', 'pristine sports infographic', 'premium professional photography']
        }
    
    def analyze_topic_domain(self, topic):
        """
        Analyze the topic to understand its domain and appropriate visual approaches
        
        Args:
            topic (str): The blog topic
            
        Returns:
            dict: Domain analysis with suggested styles
        """
        topic_lower = topic.lower()
        
        # Determine domain based on keywords
        domain_keywords = {
            'technology': ['ai', 'artificial intelligence', 'machine learning', 'tech', 'software', 'digital', 'cyber', 'robot', 'automation', 'algorithm', 'data', 'computer', 'internet', 'blockchain', 'cryptocurrency'],
            'business': ['business', 'marketing', 'startup', 'company', 'corporate', 'entrepreneurship', 'management', 'leadership', 'strategy', 'sales', 'revenue', 'profit', 'market', 'industry'],
            'science': ['science', 'research', 'study', 'experiment', 'discovery', 'innovation', 'biology', 'chemistry', 'physics', 'medicine', 'pharmaceutical', 'clinical'],
            'healthcare': ['health', 'medical', 'medicine', 'hospital', 'doctor', 'patient', 'treatment', 'therapy', 'disease', 'healthcare', 'wellness', 'diagnosis'],
            'education': ['education', 'learning', 'school', 'university', 'student', 'teacher', 'academic', 'curriculum', 'training', 'knowledge', 'skill'],
            'finance': ['finance', 'financial', 'investment', 'banking', 'money', 'economy', 'economic', 'stock', 'cryptocurrency', 'trading', 'insurance', 'loan'],
            'environment': ['environment', 'climate', 'sustainability', 'green', 'renewable', 'energy', 'carbon', 'pollution', 'conservation', 'ecosystem', 'nature'],
            'politics': ['politics', 'political', 'government', 'policy', 'election', 'democracy', 'law', 'legal', 'regulation', 'legislation', 'public'],
            'culture': ['culture', 'cultural', 'art', 'music', 'entertainment', 'media', 'social', 'community', 'lifestyle', 'creative', 'design'],
            'sports': ['sports', 'athletic', 'fitness', 'exercise', 'competition', 'team', 'player', 'game', 'championship', 'training', 'performance']
        }
        
        # Find the best matching domain
        domain_scores = {}
        for domain, keywords in domain_keywords.items():
            score = sum(1 for keyword in keywords if keyword in topic_lower)
            if score > 0:
                domain_scores[domain] = score
        
        # Get the primary domain
        primary_domain = max(domain_scores.keys(), key=lambda k: domain_scores[k]) if domain_scores else 'business'
        
        # Get suggested styles for this domain
        suggested_styles = self.style_preferences.get(primary_domain, ['professional photography', 'infographic', 'illustration'])
        
        return {
            'primary_domain': primary_domain,
            'domain_score': domain_scores.get(primary_domain, 0),
            'suggested_styles': suggested_styles,
            'topic_characteristics': self._extract_topic_characteristics(topic, primary_domain)
        }
    
    def _extract_topic_characteristics(self, topic, domain):
        """Extract key characteristics from the topic for visual representation"""
        characteristics = {
            'complexity': 'medium',  # simple, medium, complex
            'data_heavy': False,
            'conceptual': False,
            'technical': False,
            'human_focused': False,
            'process_oriented': False
        }
        
        topic_lower = topic.lower()
        
        # Determine complexity
        complex_indicators = ['analysis', 'comprehensive', 'advanced', 'detailed', 'in-depth', 'complex', 'sophisticated']
        simple_indicators = ['introduction', 'basic', 'simple', 'guide', 'beginner', 'overview']
        
        if any(indicator in topic_lower for indicator in complex_indicators):
            characteristics['complexity'] = 'complex'
        elif any(indicator in topic_lower for indicator in simple_indicators):
            characteristics['complexity'] = 'simple'
        
        # Check for other characteristics
        characteristics['data_heavy'] = any(word in topic_lower for word in ['data', 'statistics', 'metrics', 'numbers', 'analysis', 'research', 'study'])
        characteristics['conceptual'] = any(word in topic_lower for word in ['concept', 'theory', 'idea', 'philosophy', 'strategy', 'framework'])
        characteristics['technical'] = any(word in topic_lower for word in ['technical', 'technology', 'engineering', 'system', 'architecture', 'implementation'])
        characteristics['human_focused'] = any(word in topic_lower for word in ['people', 'human', 'user', 'customer', 'employee', 'team', 'leadership', 'management'])
        characteristics['process_oriented'] = any(word in topic_lower for word in ['process', 'workflow', 'step', 'guide', 'how-to', 'method', 'procedure'])
        
        return characteristics
    
    def create_contextual_agent(self):
        """Create the contextual image prompt generation agent"""
        return Agent(
            role="Professional Photography Prompt Specialist",
            goal="""Generate ultra-clean, photorealistic image prompts that produce crystal-clear, 
            professional photographs with perfect clarity, readable text, and zero AI artifacts.""",
            backstory="""You are an elite professional photography prompt specialist who creates 
            prompts for ultra-realistic, magazine-quality business photography. You have 30+ years 
            of experience in high-end commercial photography and specialize in creating images so 
            realistic they are indistinguishable from professional studio photography.
            
            Your CORE SPECIALIZATIONS:
            - Ultra-clean, crystal-clear professional business photography
            - Perfect lighting with zero shadows or artifacts
            - Razor-sharp focus with professional depth of field
            - Readable, clear text elements when included
            - Immaculate compositions with perfect color balance
            - Natural, authentic human subjects in premium settings
            - Magazine-quality commercial photography aesthetics
            - Professional studio and natural lighting mastery
            - High-end camera equipment simulation (Canon 5D, Nikon D850)
            
            CRITICAL QUALITY STANDARDS:
            - NEVER generate messy, cluttered, or chaotic imagery
            - ALWAYS ensure text is readable, clear, and professional
            - ELIMINATE all AI artifacts and artificial-looking elements
            - CREATE images that look like expensive professional photography
            - FOCUS on clean, minimalist, premium aesthetics
            - ENSURE perfect lighting without harsh shadows
            - GUARANTEE realistic human expressions and poses
            
            You EXCLUSIVELY create prompts for photorealistic photography that achieves:
            1. Crystal-clear image quality with zero blur or distortion
            2. Professional lighting that enhances rather than obscures
            3. Clean, organized compositions without visual clutter
            4. Readable text elements with perfect typography
            5. Natural, authentic appearance with zero AI detection
            
            Your prompts always specify: "ultra-realistic professional photograph", "crystal clear", 
            "perfect lighting", "clean composition", "shot with high-end professional camera", 
            "magazine quality", and "zero AI artifacts".""",
            verbose=True,
            llm=self.llm,
            allow_delegation=False
        )
    
    def analyze_section_context(self, section_content, section_name, topic, blog_type):
        """
        Analyze section content to determine appropriate visual style and generate contextual prompt
        
        Args:
            section_content (str): The actual text content of the section
            section_name (str): Name of the section (banner, main_content, etc.)
            topic (str): Overall blog topic
            blog_type (str): Type of blog (News, Opinion, etc.)
            
        Returns:
            str: A contextually appropriate and stylistically varied image prompt
        """
        # Step 1: Analyze topic domain
        topic_analysis = self.analyze_topic_domain(topic)
        
        # Step 2: Analyze section content
        content_analysis = self._analyze_content_characteristics(section_content, section_name)
        
        # Step 3: Select appropriate visual style
        selected_style = self._select_visual_style(section_name, topic_analysis, content_analysis)
        
        # Step 4: Generate contextual prompt using AI
        try:
            enhanced_prompt = self._generate_enhanced_prompt(
                section_content, section_name, topic, blog_type,
                topic_analysis, content_analysis, selected_style
            )
            
            print(f"DEBUG: Generated {selected_style} style prompt for {section_name}: {enhanced_prompt[:100]}...")
            return enhanced_prompt
            
        except Exception as e:
            print(f"ERROR: Failed to generate contextual prompt for {section_name}: {str(e)}")
            return self._generate_fallback_prompt(section_content, section_name, topic, blog_type, selected_style)
    
    def _analyze_content_characteristics(self, content, section_name):
        """Analyze the content to understand its visual requirements"""
        if not content:
            return {'type': 'general', 'elements': [], 'data_present': False, 'concepts': []}
        
        content_lower = content.lower()
        
        analysis = {
            'type': 'general',
            'elements': [],
            'data_present': False,
            'concepts': [],
            'tone': 'neutral',
            'complexity': 'medium'
        }
        
        # Determine content type
        if any(word in content_lower for word in ['statistics', 'data', 'numbers', 'percent', '%', 'research', 'study']):
            analysis['type'] = 'data_driven'
            analysis['data_present'] = True
        elif any(word in content_lower for word in ['process', 'steps', 'workflow', 'method', 'procedure']):
            analysis['type'] = 'process'
        elif any(word in content_lower for word in ['concept', 'theory', 'idea', 'philosophy', 'framework']):
            analysis['type'] = 'conceptual'
        elif any(word in content_lower for word in ['technical', 'system', 'architecture', 'implementation', 'algorithm']):
            analysis['type'] = 'technical'
        elif any(word in content_lower for word in ['people', 'team', 'human', 'user', 'customer', 'community']):
            analysis['type'] = 'human_centered'
        
        # Extract key visual elements
        visual_keywords = re.findall(r'\b(?:graph|chart|diagram|visualization|interface|dashboard|system|network|platform|device|tool|equipment|building|office|laboratory|facility|meeting|conference|presentation|screen|display|technology|innovation|growth|success|collaboration|teamwork|leadership|strategy|solution|future|progress|development|transformation|improvement)\b', content_lower)
        analysis['elements'] = list(set(visual_keywords))
        
        # Extract key concepts
        sentences = content.split('.')[:3]  # First 3 sentences
        for sentence in sentences:
            words = sentence.split()
            meaningful_words = [word.strip('.,!?()[]{}').lower() for word in words 
                             if len(word) > 4 and word.lower() not in ['this', 'that', 'with', 'from', 'they', 'have', 'been', 'will']]
            analysis['concepts'].extend(meaningful_words[:3])
        
        analysis['concepts'] = list(set(analysis['concepts']))[:5]
        
        return analysis
    
    def _select_visual_style(self, section_name, topic_analysis, content_analysis):
        """Select the most appropriate visual style based on analysis"""
        domain = topic_analysis['primary_domain']
        content_type = content_analysis['type']
        
        # Ultra-clean style selection matrix based on section and content type
        style_matrix = {
            'banner': {
                'technology': ['crystal-clear futuristic digital art', 'ultra-realistic modern professional photography', 'pristine tech illustration'],
                'business': ['ultra-realistic corporate photography', 'crystal-clear business illustration', 'premium professional composition'],
                'science': ['crystal-clear scientific visualization', 'ultra-clean abstract art', 'pristine laboratory photography'],
                'healthcare': ['ultra-realistic medical photography', 'crystal-clear health illustration', 'premium professional imagery'],
                'default': ['ultra-realistic professional photography', 'crystal-clear creative illustration', 'pristine conceptual art']
            },
            'main_content': {
                'data_driven': ['ultra-clean infographic design', 'crystal-clear data visualization', 'pristine chart illustration'],
                'technical': ['crystal-clear technical diagram', 'ultra-clean system illustration', 'pristine engineering visualization'],
                'process': ['ultra-clean process diagram', 'crystal-clear workflow illustration', 'pristine step-by-step visual'],
                'conceptual': ['crystal-clear conceptual art', 'ultra-clean abstract illustration', 'pristine metaphorical imagery'],
                'default': ['ultra-clean modern illustration', 'crystal-clear professional photography', 'pristine digital art']
            },
            'supporting_details': {
                'technology': ['crystal-clear technical illustration', 'ultra-clean digital composition', 'pristine interface mockup'],
                'business': ['ultra-clean business infographic', 'crystal-clear corporate visualization', 'pristine professional diagram'],
                'science': ['crystal-clear scientific diagram', 'ultra-clean research visualization', 'pristine analytical illustration'],
                'default': ['crystal-clear detailed illustration', 'ultra-clean explanatory diagram', 'pristine professional visualization']
            },
            'evidence': {
                'data_driven': ['ultra-clean statistical visualization', 'crystal-clear research infographic', 'pristine data presentation'],
                'academic': ['crystal-clear scholarly illustration', 'ultra-realistic research photography', 'pristine academic visualization'],
                'default': ['ultra-clean professional documentation', 'crystal-clear evidence visualization', 'pristine authoritative imagery']
            },
            'conclusion': {
                'technology': ['crystal-clear future technology art', 'ultra-clean innovation illustration', 'pristine forward-looking imagery'],
                'business': ['ultra-clean success visualization', 'crystal-clear growth illustration', 'pristine achievement imagery'],
                'environment': ['ultra-realistic nature photography', 'crystal-clear sustainability art', 'pristine environmental concept'],
                'default': ['crystal-clear inspirational art', 'ultra-clean conclusion imagery', 'pristine forward-thinking visualization']
            }
        }
        
        # Get styles for this section
        section_styles = style_matrix.get(section_name, {})
        
        # First try content type match
        if content_type in section_styles:
            available_styles = section_styles[content_type]
        # Then try domain match
        elif domain in section_styles:
            available_styles = section_styles[domain]
        # Fall back to default
        else:
            available_styles = section_styles.get('default', ['professional photography', 'illustration', 'digital art'])
        
        # Select a random style to ensure variety
        selected_style = random.choice(available_styles)
        
        return selected_style
    
    def _generate_enhanced_prompt(self, section_content, section_name, topic, blog_type, 
                                 topic_analysis, content_analysis, selected_style):
        """Generate an enhanced, contextually appropriate prompt using AI analysis"""
        
        # Create comprehensive context for the AI
        context_prompt = f"""
TOPIC ANALYSIS:
- Primary Domain: {topic_analysis['primary_domain']}
- Topic Characteristics: {topic_analysis['topic_characteristics']}
- Suggested Visual Approaches: {', '.join(topic_analysis['suggested_styles'])}

SECTION ANALYSIS:
- Section: {section_name}
- Content Type: {content_analysis['type']}
- Key Visual Elements: {', '.join(content_analysis['elements']) if content_analysis['elements'] else 'None identified'}
- Key Concepts: {', '.join(content_analysis['concepts']) if content_analysis['concepts'] else 'None identified'}
- Data Present: {content_analysis['data_present']}

SELECTED VISUAL STYLE: {selected_style}

SECTION CONTENT (First 400 chars): {section_content[:400]}...

Generate an ULTRA-CLEAN, CRYSTAL-CLEAR professional image prompt that:
1. Uses the selected visual style: {selected_style}
2. Incorporates specific concepts and elements from the content
3. Matches the {topic_analysis['primary_domain']} domain
4. Creates appropriate imagery for the {section_name} section
5. Ensures variety and uniqueness from other blog images

CRITICAL QUALITY REQUIREMENTS - MANDATORY:
- ULTRA-REALISTIC: Must look like expensive professional photography, NOT AI-generated
- CRYSTAL CLEAR: Perfect focus, zero blur, magazine-quality sharpness
- CLEAN COMPOSITION: Minimal, organized, zero visual clutter or mess
- PERFECT LIGHTING: Soft, professional lighting with no harsh shadows or overexposure
- READABLE TEXT: If text elements are included, they must be crystal clear and perfectly legible
- PREMIUM AESTHETICS: High-end, sophisticated visual appeal
- NATURAL APPEARANCE: Authentic, realistic subjects and environments
- ZERO AI ARTIFACTS: No artificial-looking elements, distortions, or obvious AI generation

FORBIDDEN ELEMENTS - NEVER INCLUDE:
- Messy, cluttered, or chaotic compositions
- Blurry, distorted, or unclear text
- Artificial lighting or unrealistic color saturation
- Obviously AI-generated faces or objects
- Busy backgrounds that distract from the main subject
- Low-quality or amateur photography aesthetics

MANDATORY PROMPT ELEMENTS:
- Begin with: "Ultra-realistic professional photograph"
- Include: "crystal clear", "perfect lighting", "clean composition"
- Specify: "shot with high-end professional camera (Canon 5D Mark IV)"
- Add: "magazine quality", "zero AI artifacts"
- End with: "pristine image quality, authentic professional photography"

Requirements:
- Be specific about ultra-clean visual style, perfect composition, and premium aesthetics
- Include relevant elements mentioned in the content with crystal-clear execution
- Make it appropriate for {blog_type} blog content with professional standards
- Use descriptive language for {selected_style} with quality enhancements
- Create imagery that enhances understanding with perfect visual clarity
- Ensure photorealistic, non-AI appearance

Output only the enhanced ultra-clean image generation prompt, no explanations.
"""

        try:
            response = self.llm.invoke(context_prompt)
            generated_prompt = response.content.strip()
            
            # Clean and validate the prompt
            cleaned_prompt = self._clean_generated_prompt(generated_prompt)
            
            if len(cleaned_prompt) < 30:
                return self._generate_fallback_prompt(section_content, section_name, topic, blog_type, selected_style)
            
            return cleaned_prompt
            
        except Exception as e:
            print(f"ERROR: AI prompt generation failed: {str(e)}")
            return self._generate_fallback_prompt(section_content, section_name, topic, blog_type, selected_style)
    
    def _clean_generated_prompt(self, prompt):
        """Clean the generated prompt and ensure ultra-clean quality standards"""
        if not prompt:
            return ""
        
        # Remove common prefixes and unwanted text
        prefixes_to_remove = [
            "Image prompt:", "Prompt:", "Generated prompt:", "Final prompt:",
            "Here is the image prompt:", "The image prompt is:", "Image description:",
            "Visual prompt:", "Photo prompt:", "**Image Prompt:**", "**Prompt:**",
            "Create an image:", "Generate an image:", "Image of:", "Picture of:"
        ]
        
        cleaned_prompt = prompt.strip()
        
        for prefix in prefixes_to_remove:
            if cleaned_prompt.lower().startswith(prefix.lower()):
                cleaned_prompt = cleaned_prompt[len(prefix):].strip()
        
        # Remove quotes if they wrap the entire text
        if (cleaned_prompt.startswith('"') and cleaned_prompt.endswith('"')) or \
           (cleaned_prompt.startswith("'") and cleaned_prompt.endswith("'")):
            cleaned_prompt = cleaned_prompt[1:-1].strip()
        
        # Ensure it starts with ultra-realistic specification if not already present
        if not any(ultra_term in cleaned_prompt.lower() for ultra_term in ['ultra-realistic', 'crystal clear', 'professional photograph']):
            cleaned_prompt = f"Ultra-realistic professional photograph, {cleaned_prompt}"
        
        # Ensure quality specifications are present
        quality_terms = ['crystal clear', 'perfect lighting', 'clean composition', 'magazine quality', 'zero AI artifacts', 'pristine image quality']
        missing_terms = []
        
        for term in quality_terms:
            if term not in cleaned_prompt.lower():
                missing_terms.append(term)
        
        # Add missing quality terms
        if missing_terms:
            cleaned_prompt += f", {', '.join(missing_terms[:3])}"  # Add top 3 missing terms
        
        # Ensure reasonable length but maintain quality specifications
        if len(cleaned_prompt) > 500:
            sentences = cleaned_prompt.split('.')
            # Keep first 3 sentences but always preserve quality specifications
            base_content = '. '.join(sentences[:3])
            if not any(term in base_content.lower() for term in ['crystal clear', 'magazine quality', 'pristine']):
                base_content += ', crystal clear, magazine quality, pristine image quality'
            cleaned_prompt = base_content + '.' if not base_content.endswith('.') else base_content
        
        return cleaned_prompt
    
    
    def _generate_fallback_prompt(self, section_content, section_name, topic, blog_type, selected_style):
        """Generate an ultra-clean fallback prompt when AI generation fails"""
        
        # Ultra-clean fallback prompts based on style and section
        fallback_templates = {
            'professional photography': "Ultra-realistic professional photograph of {concept} related to {topic}, shot with high-end professional camera (Canon 5D Mark IV), crystal clear focus, perfect lighting, clean minimal composition, pristine corporate setting, magazine quality, zero AI artifacts, authentic professional photography",
            'digital art': "Ultra-clean digital art illustration of {concept} representing {topic}, crystal clear modern design, perfectly balanced colors, immaculate composition, professional digital rendering, magazine quality, zero visual clutter, pristine image quality",
            'infographic design': "Crystal-clear infographic design showing {concept} about {topic}, ultra-clean typography, perfect data visualization elements, premium color scheme, minimal design, readable text, professional layout, zero clutter, magazine quality",
            'technical diagram': "Ultra-clean technical diagram illustrating {concept} for {topic}, crystal clear lines, professional schematic style, perfect educational visualization, minimal background, readable labels, pristine composition, magazine quality",
            'scientific visualization': "Crystal-clear scientific visualization of {concept} related to {topic}, ultra-accurate representation, professional research-quality illustration, clean educational design, perfect clarity, readable elements, pristine composition",
            'conceptual art': "Ultra-clean conceptual art representing {concept} about {topic}, crystal clear creative interpretation, pristine artistic composition, meaningful visual metaphor, professional aesthetics, magazine quality, zero AI artifacts",
            'business illustration': "Ultra-professional business illustration showing {concept} for {topic}, crystal clear corporate style, pristine design, clean modern aesthetic, perfect composition, readable elements, magazine quality, premium business photography"
        }
        
        # Extract a concept from content or use topic
        concept = topic
        if section_content:
            words = section_content.split()[:10]
            meaningful_words = [w for w in words if len(w) > 4]
            if meaningful_words:
                concept = meaningful_words[0]
        
        # Find matching template
        template = None
        for style_key in fallback_templates:
            if style_key in selected_style.lower():
                template = fallback_templates[style_key]
                break
        
        if not template:
            template = fallback_templates['professional photography']  # Default ultra-clean fallback
        
        # Enhance with additional quality specifications
        enhanced_template = template + ", pristine image quality, ultra-realistic appearance, professional studio lighting, zero blur or distortion, crystal clear details, authentic professional photography"
        
        return enhanced_template.format(concept=concept, topic=topic)
    
    def generate_section_prompts(self, content_sections, topic, blog_type):
        """
        Generate contextual prompts for all blog sections with varied styles
        
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
        
        print(f"DEBUG: Starting contextual prompt generation for {len(sections_to_process)} sections")
        print(f"DEBUG: Topic domain analysis: {self.analyze_topic_domain(topic)['primary_domain']}")
        
        for section_name, content in sections_to_process.items():
            try:
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
                    topic_analysis = self.analyze_topic_domain(topic)
                    selected_style = random.choice(topic_analysis['suggested_styles'])
                    section_prompts[section_name] = self._generate_fallback_prompt(
                        "", section_name, topic, blog_type, selected_style
                    )
                    
            except Exception as e:
                print(f"ERROR: Failed to generate prompt for {section_name}: {str(e)}")
                # Emergency fallback - now ultra-clean
                section_prompts[section_name] = f"Ultra-realistic professional photograph related to {topic} for {section_name} section, crystal clear, perfect lighting, clean composition, magazine quality, zero AI artifacts, pristine image quality"
                
        print(f"DEBUG: Generated {len(section_prompts)} varied contextual prompts for {topic}")
        return section_prompts
