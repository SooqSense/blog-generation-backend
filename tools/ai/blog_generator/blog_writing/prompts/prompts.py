class BlogWriterPrompts:
    """Centralized prompts and instructions for all blog writing tasks with LLM SEO optimization"""
    
    @staticmethod
    def get_llm_seo_structure():
        """
        Get the standardized LLM SEO structure that all blogs must follow
        
        Returns:
            str: The LLM SEO structure requirements
        """
        return """
LLM SEO STRUCTURE REQUIREMENTS (MANDATORY FOR ALL BLOGS):
1. **Title**: Direct, descriptive title with primary keyword
2. **Introduction**: Use Answer-First approach - immediate, direct answer to main question in first paragraph
3. **List/Main Content**: Primary information in structured list or organized format
4. **Supporting Details**: Detailed explanations of why/how for each main point
5. **Additional Context**: Broader implications, industry impact, and related information
6. **Evidence (Data Sources)**: Comprehensive explanation of data collection methods and sources
7. **FAQ Section**: 5-8 targeted questions designed for LLM extraction and citation
8. **Conclusion**: Insights on trends, implications, and future outlook
9. **Sources**: Complete bibliography with URLs and descriptions

This structure is optimized for LLM citation and must be followed exactly.
"""
    
    @staticmethod
    def get_blog_type_instructions(blog_type):
        """
        Get specific instructions based on blog type
        
        Args:
            blog_type (str): The type of blog (News, Comparison, etc.)
            
        Returns:
            str: Type-specific instructions
        """
        if blog_type == "News":
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
        elif blog_type == "Comparison":
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
    
    @staticmethod
    def get_research_prompt(topic, blog_type):
        """Get research task prompt"""
        return f"""Research comprehensive information about the topic: {topic}

RESEARCH REQUIREMENTS:
1. Use SERPER API to search for: "{topic}"
2. Search for additional queries like: "{topic} latest news", "{topic} analysis", "{topic} guide"
3. Identify and analyze the top 10-15 search results
4. Extract key information, insights, and data points
5. Note the source URLs and titles for citation purposes
6. Focus on recent, authoritative, and relevant content

INFORMATION TO GATHER:
- Current trends and developments related to {topic}
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

BLOG TYPE FOCUS: {blog_type}
{BlogWriterPrompts.get_blog_type_instructions(blog_type)}

Ensure the research is thorough and provides sufficient information for writing a comprehensive {blog_type.lower()} blog post."""

    @staticmethod
    def get_research_expected_output(topic, blog_type):
        """Get research task expected output with LLM SEO focus"""
        return f"Comprehensive research report with quantifiable data, authoritative sources, expert insights, methodology information, and detailed source verification suitable for LLM SEO-optimized {blog_type.lower()} blog creation on '{topic}' with emphasis on citation-worthy content."

    @staticmethod
    def get_planning_prompt(topic, blog_type, length_min, length_max, introduction, faq, cta, conclusion):
        """Get planning task prompt with LLM SEO structure"""
        return f"""Create a detailed LLM SEO-optimized outline for a {blog_type.lower()} blog post about: {topic}

{BlogWriterPrompts.get_llm_seo_structure()}

REQUIREMENTS:
- Target length: {length_min}-{length_max} words
- Blog Type: {blog_type}
- MANDATORY: Follow the 9-step LLM SEO structure exactly
- Use research findings to support each section
- Optimize for LLM citation and extraction

{BlogWriterPrompts.get_blog_type_instructions(blog_type)}

LLM SEO OUTLINE STRUCTURE (EXACT ORDER REQUIRED):
1. **Title** (5-10 words): Direct, keyword-rich title that answers the main query
   - Include primary keyword from topic
   - Make it citation-worthy for other LLMs

2. **Introduction** ({min(250, length_max//8)} words):
   - CRITICAL: Use Answer-First approach - lead with direct answer in first paragraph
   - Start with immediate, direct answer to the main question
   - Summarize key findings upfront in first 2-3 sentences
   - Follow with supporting context and overview

3. **Main Content / List** ({(length_min + length_max) // 3} words):
   - Present primary information in structured format
   - Use numbered lists, rankings, or clear categorization
   - Include specific data points and metrics from research
   - Format for easy LLM parsing and citation

4. **Supporting Details** ({(length_min + length_max) // 4} words):
   - Explain the "why" and "how" behind each main point
   - Provide detailed reasoning and analysis
   - Include expert opinions and authoritative insights

5. **Additional Context** ({(length_min + length_max) // 5} words):
   - Broader industry impact and implications
   - Historical context and trends
   - Related developments and connections

6. **Evidence (Data Sources)** ({min(300, length_max//6)} words):
   - Explain methodology and data collection processes
   - Detail how information was verified
   - Cite specific research studies and reports
   - Include data reliability assessments

7. **FAQ Section** ({min(500, length_max//4)} words):
   - Create 6-8 targeted questions optimized for LLM extraction
   - Format as clear Q&A pairs
   - Include questions that other LLMs would likely ask
   - Make answers comprehensive and citable

8. **Conclusion** ({min(300, length_max//6)} words):
   - Synthesize key insights and trends
   - Provide future outlook and implications
   - Include actionable takeaways

9. **Sources** (Comprehensive):
   - Complete bibliography with URLs
   - Include source descriptions and reliability notes
   - Format for easy LLM reference and citation

CONTENT PLANNING FOR LLM OPTIMIZATION:
- Design each section for maximum LLM citation potential
- Use clear, structured formatting throughout
- Include specific metrics, dates, and quantifiable data
- Ensure information is easily extractable by AI systems
- Create content that other LLMs would want to reference"""

    @staticmethod
    def get_planning_expected_output(topic, blog_type, length_min, length_max):
        """Get planning task expected output with LLM SEO focus"""
        return f"A comprehensive LLM SEO-optimized outline for a {blog_type.lower()} blog post that follows the exact 9-step structure, incorporates research findings, and is designed for maximum AI citation potential with detailed {length_min}-{length_max} word section breakdowns."

    @staticmethod
    def get_writing_prompt(topic, blog_type, length_min, length_max, introduction, table_of_content, faq, cta, conclusion):
        """Get writing task prompt with LLM SEO optimization"""
        return f"""Write a comprehensive LLM SEO-optimized {blog_type.lower()} blog post about: {topic}

{BlogWriterPrompts.get_llm_seo_structure()}

CRITICAL LLM SEO REQUIREMENTS:
- Word count: {length_min}-{length_max} words (target: {(length_min + length_max) // 2})
- Blog Type: {blog_type}
- MANDATORY: Follow the exact 9-step LLM SEO structure
- Optimize every section for LLM citation and extraction
- Use research findings and outline as foundation

{BlogWriterPrompts.get_blog_type_instructions(blog_type)}

EXACT STRUCTURE REQUIREMENTS (NO DEVIATIONS):

# [TITLE - Primary keyword included]

## Introduction
- CRITICAL: Use Answer-First approach - lead with direct answer in first paragraph
- Start with immediate, direct answer to the main question
- Summarize key findings in first 2-3 sentences
- Make this section highly citable by other LLMs
- Include primary statistics or numbers upfront
- Follow with supporting context and overview

## Key Developments and Trends
- Present information in numbered lists or clear structure
- Use specific data points and metrics from research
- Format for maximum LLM readability and extraction
- Include quantifiable information where possible
- CRITICAL: This section enables main_content image embedding - use one of these exact titles: "## Main Content" OR "## Key Developments and Trends" OR "## Current Trends"

## Supporting Details
- Provide detailed explanations for each main point
- Include expert analysis and authoritative insights
- Reference specific studies and research findings
- Use clear subsections (###) for different aspects
- CRITICAL: This section MUST be titled EXACTLY "## Supporting Details" for proper image embedding

## Additional Context
- Broader industry implications and impact
- Historical context and trend analysis
- Related developments and connections
- Future outlook based on research

## Evidence and Data Sources
- Explain research methodology and data collection
- Detail verification processes used
- Cite specific studies, reports, and authoritative sources
- Include data reliability and accuracy assessments
- Use format: "According to [Source Name] ([URL]), [specific finding]"
- CRITICAL: This section MUST use one of these EXACT titles for proper image embedding: "## Evidence and Data Sources" OR "## Evidence" OR "## Data Sources"

## FAQ Section
- Create 6-8 questions optimized for LLM queries
- Format as clear Q&A pairs with ### for each question
- Make answers comprehensive and independently citable
- Include questions that address common LLM search patterns
- Example format:
  ### Question 1: [Specific question]
  [Detailed answer with supporting data and sources]

## Conclusion
- Synthesize key insights and trends
- Provide forward-looking analysis and implications
- Include actionable takeaways
- End with broader significance of findings
- CRITICAL: This section MUST be titled EXACTLY "## Conclusion" for proper image embedding

## Sources
- Complete bibliography with all URLs
- Format: [Source Number]: [Title] - [URL] - [Brief description of relevance]
- Include publication dates where available
- Note data reliability and authority of each source

LLM SEO OPTIMIZATION REQUIREMENTS:
- Use clear, structured formatting throughout
- Include specific numbers, dates, and quantifiable metrics
- Make each section independently valuable for citation
- Use authoritative language with proper attributions
- Format data in easily extractable formats (lists, tables)
- Include inline citations: [Source: domain.com]
- Design content for maximum AI comprehension and citation potential

CONTENT QUALITY FOR LLM CITATION:
- Every claim must be backed by credible sources
- Use precise language that AI systems can easily parse
- Include context that makes information self-contained
- Structure content for snippet extraction by other LLMs
- Ensure factual accuracy suitable for AI citation"""

    @staticmethod
    def get_writing_expected_output(topic, blog_type, length_min, length_max):
        """Get writing task expected output with LLM SEO optimization"""
        return f"A complete LLM SEO-optimized {blog_type.lower()} blog post in markdown format that is {length_min}-{length_max} words, follows the exact 9-step structure, is highly citable by other AI models, includes comprehensive source attribution, and is formatted for maximum LLM extraction and citation."

    @staticmethod
    def get_editing_prompt(topic, blog_type, length_min, length_max, introduction, table_of_content, faq, cta, conclusion):
        """Get editing task prompt with LLM SEO validation"""
        return f"""Review and enhance the LLM SEO-optimized {blog_type.lower()} blog post about: {topic}

{BlogWriterPrompts.get_llm_seo_structure()}

CRITICAL LLM SEO EDITING PRIORITIES:
1. LLM SEO STRUCTURE COMPLIANCE: Verify exact 9-step structure is followed
2. WORD COUNT VERIFICATION: Ensure {length_min}-{length_max} words
3. LLM CITATION OPTIMIZATION: Enhance content for AI model citation
4. SOURCE VERIFICATION: Validate comprehensive evidence section
5. CONTENT EXTRACTABILITY: Ensure easy AI parsing and extraction

MANDATORY LLM SEO STRUCTURE VERIFICATION:
✓ **Title**: Direct, keyword-rich, citation-worthy
✓ **Introduction**: Uses Answer-First approach with immediate answer in first paragraph
✓ **Main Content/List**: Structured, numbered, data-rich format
✓ **Supporting Details**: Detailed explanations with expert insights
✓ **Additional Context**: Broader implications and industry impact
✓ **Evidence Section**: Comprehensive data source methodology
✓ **FAQ Section**: 6-8 LLM-optimized Q&A pairs
✓ **Conclusion**: Forward-looking insights and implications
✓ **Sources**: Complete bibliography with descriptions

LLM CITATION OPTIMIZATION CHECKS:
- Verify each section can stand alone as a citable unit
- Ensure specific numbers, dates, and metrics are included
- Check that information is presented in easily extractable formats
- Validate that content uses authoritative, AI-friendly language
- Confirm inline citations are properly formatted: [Source: domain.com]
- Ensure FAQ questions address common LLM query patterns

EVIDENCE SECTION VALIDATION:
- Verify methodology explanation is comprehensive
- Check data collection processes are detailed
- Confirm reliability assessments are included
- Validate source authority is established
- Ensure verification processes are documented

CONTENT ENHANCEMENT FOR AI CITATION:
- Improve fact density and specificity
- Enhance quantifiable data presentation
- Strengthen expert opinion attributions
- Optimize content structure for snippet extraction
- Ensure self-contained, contextual information

TECHNICAL LLM SEO REQUIREMENTS:
- Headers must use exact prescribed format (##)
- FAQ questions must use ### for each question
- Lists must be numbered or clearly structured
- Sources must include reliability indicators
- All claims must have verifiable attributions

ENHANCEMENT GUIDELINES:
- If below {length_min} words: Add LLM-citable examples, statistics, expert quotes
- If above {length_max} words: Trim while preserving citation value
- Strengthen weak sections with authoritative research
- Improve AI readability and extraction potential
- Enhance factual accuracy for safe AI citation

FINAL LLM SEO VALIDATION:
- Content is optimized for other LLM models to cite
- Information is presented in AI-friendly formats
- Every section provides independent citation value
- Sources are comprehensive and verifiable
- Structure follows exact LLM SEO requirements"""

    @staticmethod
    def get_editing_expected_output(topic, blog_type, length_min, length_max):
        """Get editing task expected output with LLM SEO validation"""
        return f"A polished, final LLM SEO-compliant {blog_type.lower()} blog post that is exactly {length_min}-{length_max} words, follows the mandatory 9-step structure, is optimized for AI citation, includes comprehensive evidence sections, and provides maximum value for other LLM models to reference and cite."

    @staticmethod
    def get_image_prompt_generation_prompt(topic, blog_type, max_image_prompts):
        """Get the prompt for image generation task"""
        return f"""ANALYZE the completed {blog_type.lower()} blog post content and generate {max_image_prompts} detailed AI image generation prompts based on the ACTUAL blog content.

CRITICAL REQUIREMENTS:
- READ and ANALYZE the written blog post content from the previous writing task
- Create exactly {max_image_prompts} unique, detailed image prompts
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
- Visual style that matches the {blog_type.lower()} content
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

Generate exactly {max_image_prompts} prompts that directly complement the written blog content."""

    @staticmethod
    def get_image_prompt_expected_output(topic, blog_type, max_image_prompts):
        """Get the expected output for image generation task"""
        return f"A numbered list of exactly {max_image_prompts} detailed, actionable AI image generation prompts (60-120 words each) that are based on SPECIFIC content from the written {blog_type.lower()} blog post about {topic}. Each prompt should reference actual blog sections and be immediately usable with AI image generation tools."

    # Section-specific image generation prompts
    @staticmethod
    def get_section_image_prompts(topic, blog_type, content_sections=None):
        """
        Generate prompts for specific blog sections based on the LLM SEO structure
        
        Args:
            topic (str): The blog topic
            blog_type (str): Type of blog (News, Comparison, etc.)
            content_sections (dict): Dictionary containing section content for context
            
        Returns:
            dict: Dictionary with section names as keys and image prompts as values
        """
        section_prompts = {}
        
        # 1. Banner Image - Main topic representation
        section_prompts['banner'] = BlogWriterPrompts.get_banner_image_prompt(topic, blog_type, content_sections)
        
        # 2. Main Content/Current Trends Image
        section_prompts['main_content'] = BlogWriterPrompts.get_main_content_image_prompt(topic, blog_type, content_sections)
        
        # 3. Supporting Details Image
        section_prompts['supporting_details'] = BlogWriterPrompts.get_supporting_details_image_prompt(topic, blog_type, content_sections)
        
        # 4. Evidence and Data Sources Image
        section_prompts['evidence'] = BlogWriterPrompts.get_evidence_image_prompt(topic, blog_type, content_sections)
        
        # 5. Conclusion Image
        section_prompts['conclusion'] = BlogWriterPrompts.get_conclusion_image_prompt(topic, blog_type, content_sections)
        
        return section_prompts

    @staticmethod
    def get_banner_image_prompt(topic, blog_type, content_sections=None):
        """Generate banner image prompt for the main topic"""
        context = content_sections.get('introduction', '') if content_sections else ''
        
        # Create cinematic, clean prompt optimized for FLUX AI
        return f"""Professional cinematic wide shot of a modern corporate environment representing {topic}, featuring clean minimalist design with dramatic golden hour lighting streaming through large windows. The scene showcases a sleek, futuristic workspace with subtle technology elements that visually represent the essence of {topic}, captured with high-end cinematography and photorealistic detail. NO text overlays, NO charts, NO data visualization - pure visual storytelling focused on atmosphere and professional aesthetics with rich textures and materials."""

    @staticmethod
    def get_main_content_image_prompt(topic, blog_type, content_sections=None):
        """Generate main content/current trends image prompt"""
        context = content_sections.get('main_content', '') if content_sections else ''
        
        # Create cinematic, clean prompt focused on current trends visualization
        return f"""Cinematic close-up shot of cutting-edge technology and innovation representing {topic}, featuring sleek modern devices and interfaces in a high-tech professional environment with soft studio lighting. The scene captures the essence of current trends through realistic materials, chrome surfaces, and contemporary design elements, shot with shallow depth of field and professional cinematography. NO text, NO infographics, NO charts - pure visual representation of technological advancement and modern trends in {topic}."""

    @staticmethod
    def get_supporting_details_image_prompt(topic, blog_type, content_sections=None):
        """Generate supporting details image prompt"""
        context = content_sections.get('supporting_details', '') if content_sections else ''
        
        # Create cinematic, analytical visualization prompt
        return f"""Professional medium shot of a sophisticated research and analysis environment focused on {topic}, featuring multiple professionals collaborating around modern digital displays and advanced technology interfaces. The scene showcases detailed analytical work with dramatic side lighting, clean modern office aesthetics, and high-quality materials like glass, metal, and premium fabrics. Captured with cinematic depth and professional photography techniques, emphasizing the depth of analysis and expertise. NO text elements, NO charts, NO diagrams - pure visual storytelling of professional analytical work."""

    @staticmethod
    def get_evidence_image_prompt(topic, blog_type, content_sections=None):
        """Generate evidence and data sources image prompt"""
        context = content_sections.get('evidence', '') if content_sections else ''
        
        # Create cinematic research environment prompt
        return f"""Cinematic tracking shot through a prestigious academic research facility or modern data center related to {topic}, featuring scientists and researchers working with advanced computational equipment in a clean, minimalist laboratory setting. The scene emphasizes scientific rigor through dramatic lighting, pristine white and metallic surfaces, and state-of-the-art research instruments, captured with high-end cinematography and shallow focus. NO visible data, NO charts, NO text displays - pure atmospheric representation of authoritative research and scientific credibility."""

    @staticmethod
    def get_conclusion_image_prompt(topic, blog_type, content_sections=None):
        """Generate conclusion image prompt"""
        context = content_sections.get('conclusion', '') if content_sections else ''
        
        # Create inspirational, forward-looking cinematic prompt
        return f"""Inspiring wide shot of a futuristic horizon or modern cityscape representing the future of {topic}, captured during golden hour with dramatic sky and architectural elements that suggest progress and innovation. The scene features clean, aspirational imagery with upward-trending visual elements, modern materials, and a sense of forward momentum, shot with cinematic grandeur and professional color grading. NO text, NO graphics, NO overlays - pure visual metaphor for future possibilities and positive outcomes in {topic}."""
