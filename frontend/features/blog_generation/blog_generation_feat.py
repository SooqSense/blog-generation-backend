import streamlit as st
import sys
import os
from pathlib import Path
import time
from datetime import datetime

# Add the project root to the path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import AI tools directly without Django setup
try:
    from tools.ai.blog_generator.blog_writing.blog_writer import BlogWriter
    from tools.ai.blog_generator.blog_writing.blog_analyzer.blog_analyzer import analyze_sample_blog
    from tools.ai.blog_generator.blog_writing.images.blog_images import (
        generate_section_specific_images, 
        generate_section_image_prompts_only, 
        get_section_image_urls_list
    )
    from tools.ai.trends_ai.trending_queries import fetch_trending_queries
    
    AI_TOOLS_AVAILABLE = True
    AI_TOOLS_ERROR = None
    print("✅ Blog generation: AI tools imported successfully")
    
except Exception as e:
    AI_TOOLS_AVAILABLE = False
    AI_TOOLS_ERROR = str(e)
    print(f"⚠️ Blog generation: AI tools import failed - {str(e)}")
    
    # Create dummy classes for graceful degradation
    class BlogWriter:
        def __init__(self, **kwargs):
            pass
        def generate_blog(self, **kwargs):
            raise Exception("AI tools not available")
    
    def generate_section_specific_images(*args, **kwargs):
        raise Exception("AI section-wise image generation tools not available")
    
    def generate_section_image_prompts_only(*args, **kwargs):
        raise Exception("AI section-wise image generation tools not available")
    
    def get_section_image_urls_list(*args, **kwargs):
        return []
    
    def analyze_sample_blog(*args, **kwargs):
        return None, "Blog analysis tools not available"
    
    def fetch_trending_queries(*args, **kwargs):
        return {"rising": [], "top": []}

class BlogGenerationFeature:
    """Blog Generation feature for Streamlit UI"""
    
    def __init__(self):
        self.blog_writer = None
        self.ai_tools_available = AI_TOOLS_AVAILABLE
        # Create a unique identifier for this instance using session state
        if 'blog_feature_instance_id' not in st.session_state:
            self.instance_id = str(int(time.time() * 1000))[-6:]
            st.session_state.blog_feature_instance_id = self.instance_id
        else:
            self.instance_id = st.session_state.blog_feature_instance_id
        
    def render(self):
        """Render the blog generation interface"""
        st.markdown("# 📝 Blog Generation")
        st.markdown("Generate professional blog posts with AI-powered content creation.")
        
        # Check if AI tools are available
        if not self.ai_tools_available:
            st.error("🚫 AI Blog Generation Tools Not Available")
            st.error(f"Error: {AI_TOOLS_ERROR}")
            st.info("Please ensure the AI tools and dependencies are properly configured.")
            st.markdown("### 📋 Requirements:")
            st.markdown("- Environment variables set (OPENAI_API_KEY, SERPER_API_KEY)")
            st.markdown("- All required Python packages installed")
            st.markdown("- AI tools modules accessible in tools/ai/ directory")
            return
        
        # Create tabs for different functionalities
        tab1, tab2, tab3 = st.tabs(["✍️ Generate Blog", "📊 Blog Analysis", "📚 Generated Blogs"])
        
        with tab1:
            self.render_blog_generation()
            
        with tab2:
            self.render_blog_analysis()
            
        with tab3:
            self.render_blog_history()
    
    def render_blog_generation(self):
        """Render the blog generation form"""
        st.markdown("### Create Your Blog Post")
        
        # Two column layout for form
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Basic blog settings
            st.markdown("#### 📋 Basic Settings")
            
            topic = st.text_input(
                "Blog Topic *",
                placeholder="e.g., The Future of Artificial Intelligence",
                help="Main topic for your blog post"
            )
            
            # Keywords with count functionality
            st.markdown("#### 🔑 Keywords Configuration")
            
            col_kw1, col_kw2 = st.columns([3, 1])
            
            with col_kw1:
                keywords_input = st.text_area(
                    "Keywords (format: keyword:count or just keyword)",
                    placeholder="AI:3\nmachine learning:2\nautomation\nartificial intelligence:4",
                    help="Enter keywords with optional counts. Format: 'keyword:count' or just 'keyword' (default count: 1)",
                    height=100
                )
                
            with col_kw2:
                st.markdown("**Format Examples:**")
                st.code("AI:3\nmachine learning:2\nautomation", language="text")
                st.caption("Keywords with counts will be used exactly that many times in the blog content")
            
            # Process keywords with counts
            processed_keywords = []
            if keywords_input:
                for line in keywords_input.split('\n'):
                    line = line.strip()
                    if ':' in line:
                        keyword, count_str = line.split(':', 1)
                        try:
                            count = int(count_str.strip())
                            processed_keywords.append({'keyword': keyword.strip(), 'count': count})
                        except ValueError:
                            # If count is not a valid integer, treat as count 1
                            processed_keywords.append({'keyword': line, 'count': 1})
                    elif line:
                        processed_keywords.append({'keyword': line, 'count': 1})
                        
                # Display processed keywords summary
                if processed_keywords:
                    with st.expander("📊 Keywords Summary", expanded=False):
                        for kw in processed_keywords:
                            st.write(f"• **{kw['keyword']}**: {kw['count']} time(s)")
                        total_usage = sum(kw['count'] for kw in processed_keywords)
                        st.info(f"Total keyword usage: {total_usage} times across {len(processed_keywords)} unique keywords")
            
            # Blog configuration
            st.markdown("#### ⚙️ Blog Configuration")
            
            col_config1, col_config2 = st.columns(2)
            
            with col_config1:
                blog_type = st.selectbox(
                    "Blog Type",
                    ["News", "Tutorial", "Opinion", "Review", "Analysis", "Guide"],
                    help="Type of blog post to generate"
                )
                
                target_audience = st.multiselect(
                    "Target Audience",
                    ["Beginners", "Professionals", "Students", "Researchers", "General Public"],
                    default=["General Public"]
                )
                
            with col_config2:
                length_range = st.slider(
                    "Word Count Range",
                    min_value=500,
                    max_value=3000,
                    value=(800, 1500),
                    step=100,
                    help="Minimum and maximum word count"
                )
                
                use_custom_llm = st.checkbox(
                    "Use Google Gemini (Custom LLM)",
                    help="Use Google Gemini instead of OpenAI GPT-3.5"
                )
            
            # Blog structure options
            st.markdown("#### 🏗️ Blog Structure")
            
            col_struct1, col_struct2 = st.columns(2)
            
            with col_struct1:
                introduction = st.checkbox("Include Introduction", value=True)
                table_of_content = st.checkbox("Include Table of Contents", value=False)
                conclusion = st.checkbox("Include Conclusion", value=True)
                
            with col_struct2:
                faq = st.checkbox("Include FAQ Section", value=False)
                cta = st.checkbox("Include Call-to-Action", value=False)
                
            # Image generation settings
            st.markdown("#### 🎨 Image Generation Settings")
            
            col_img1, col_img2 = st.columns(2)
            
            with col_img1:
                generate_image_prompts = st.checkbox(
                    "Generate Image Prompts",
                    value=True,
                    help="Generate AI image prompts based on blog sections and content"
                )
                
                generate_actual_images = st.checkbox(
                    "Generate Actual Images",
                    value=False,
                    help="Generate actual images using AI and upload to S3 (requires image prompts enabled)"
                )
                
            with col_img2:
                # Fixed number of section-wise images (5 sections: banner, main_content, supporting_details, evidence, conclusion)
                max_image_prompts = 5  # Fixed value, no user input needed
                st.info("🖼️ **5 section-specific images** will be generated (Banner, Main Content, Supporting Details, Evidence, Conclusion)")
                
                if generate_actual_images:
                    # Model selection for image generation
                    image_model = st.selectbox(
                        "FLUX AI Model",
                        [
                            ("flux_dev", "FLUX Dev - High Quality (28 steps)"),
                            ("flux_schnell", "FLUX Schnell - Fast Generation (4 steps)")
                        ],
                        format_func=lambda x: x[1],
                        help="Choose between FLUX Dev for highest quality or FLUX Schnell for faster generation"
                    )
                    selected_image_model = image_model[0]
                    image_generation_method = image_model[1]
                else:
                    # Default when not generating actual images
                    selected_image_model = "flux_dev"
                    image_generation_method = "FLUX Dev - High Quality (28 steps)"
            
            # Status messages
            if generate_actual_images:
                if not generate_image_prompts:
                    st.warning("⚠️ Image prompts will be auto-enabled for actual image generation.")
                    generate_image_prompts = True  # Auto-enable prompts for image generation
                st.info(f"🖼️ **{max_image_prompts} actual images** will be generated using {image_generation_method} and uploaded to S3.")
            elif generate_image_prompts:
                st.info(f"🎨 **{max_image_prompts} section-wise image prompts** will be generated based on your blog content.")
            else:
                st.warning("⚠️ Both image prompt and image generation are disabled.")
            
            # Sample blog URL (optional)
            st.markdown("#### 🔗 Reference Blog (Optional)")
            sample_url = st.text_input(
                "Sample Blog URL",
                placeholder="https://example.com/sample-blog",
                help="Optional: URL of a blog to analyze for style and structure"
            )
        
        with col2:
            # Generation settings and preview
            st.markdown("### 🚀 Generation")
            
            # Quick settings presets
            st.markdown("#### ⚡ Quick Presets")
            
            # Ensure page_load_id is available
            if 'page_load_id' not in st.session_state:
                import time
                st.session_state.page_load_id = str(int(time.time() * 1000000))[-8:]
                
            page_id = st.session_state.page_load_id
            
            if st.button("📰 News Article", key=f"news_preset_{self.instance_id}_{page_id}", use_container_width=True):
                st.session_state.blog_preset = {
                    'blog_type': 'News',
                    'length': (800, 1200),
                    'introduction': True,
                    'conclusion': True,
                    'faq': False,
                    'cta': False
                }
                st.success("✅ News Article preset applied!")
                
            if st.button("📚 Tutorial Guide", key=f"tutorial_preset_{self.instance_id}_{page_id}", use_container_width=True):
                st.session_state.blog_preset = {
                    'blog_type': 'Tutorial',
                    'length': (1500, 2500),
                    'introduction': True,
                    'conclusion': True,
                    'faq': True,
                    'cta': True
                }
                st.success("✅ Tutorial Guide preset applied!")
                
            if st.button("💭 Opinion Piece", key=f"opinion_preset_{self.instance_id}_{page_id}", use_container_width=True):
                st.session_state.blog_preset = {
                    'blog_type': 'Opinion',
                    'length': (1000, 1800),
                    'introduction': True,
                    'conclusion': True,
                    'faq': False,
                    'cta': True
                }
                st.success("✅ Opinion Piece preset applied!")
            
            st.markdown("---")
            
            # Generation status
            if 'blog_generation_status' in st.session_state:
                status = st.session_state.blog_generation_status
                if status == 'generating':
                    st.info("🔄 Generating blog post...")
                elif status == 'completed':
                    st.success("✅ Blog generated successfully!")
                elif status == 'error':
                    st.error("❌ Generation failed")
        
        # Generate button
        st.markdown("---")
        
        col_gen1, col_gen2, col_gen3 = st.columns([1, 2, 1])
        
        with col_gen2:
            # Ensure page_load_id is available for unique keys
            if 'page_load_id' not in st.session_state:
                import time
                st.session_state.page_load_id = str(int(time.time() * 1000000))[-8:]
                
            page_id = st.session_state.page_load_id
            
            if st.button(
                "🚀 Generate Blog Post",
                key=f"generate_blog_{self.instance_id}_{page_id}",
                type="primary",
                use_container_width=True,
                disabled=not topic or not self.ai_tools_available
            ):
                if topic:
                    self.generate_blog_post(
                        topic=topic,
                        keywords=processed_keywords,  # Use processed keywords with counts
                        blog_type=blog_type,
                        length_min=length_range[0],
                        length_max=length_range[1],
                        introduction=introduction,
                        table_of_content=table_of_content,
                        faq=faq,
                        cta=cta,
                        conclusion=conclusion,
                        target_audience=target_audience,
                        sample_blog_url=sample_url if sample_url else None,
                        use_custom_llm=use_custom_llm,
                        generate_image_prompts=generate_image_prompts,
                        max_image_prompts=max_image_prompts,
                        generate_actual_images=generate_actual_images,
                        image_model=selected_image_model
                    )
                else:
                    st.error("Please enter a blog topic")
        
        # Display generated content
        if 'generated_blog' in st.session_state:
            self.display_generated_blog(st.session_state.generated_blog)
    
    def generate_blog_post(self, **kwargs):
        """Generate a blog post using the AI tools"""
        if not self.ai_tools_available:
            st.error("❌ AI tools are not available for blog generation")
            return
            
        try:
            st.session_state.blog_generation_status = 'generating'
            
            # Show progress with more detailed steps
            progress_container = st.container()
            with progress_container:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                status_text.text("🔧 Initializing AI Blog Writer...")
                progress_bar.progress(5)
                time.sleep(0.5)
                
                # Ensure minimum SEO-compliant word counts
                length_min = max(kwargs.get('length_min', 800), 800)  # Minimum 800 words for SEO
                length_max = max(kwargs.get('length_max', 1500), length_min + 500)  # Ensure range
                
                # Get image generation settings from kwargs
                generate_image_prompts = kwargs.get('generate_image_prompts', True)
                max_image_prompts = kwargs.get('max_image_prompts', 5)
                generate_actual_images = kwargs.get('generate_actual_images', False)
                # Always use FLUX AI for image generation
                image_generation_method = 'FLUX AI'
                
                # Initialize blog writer with enhanced parameters for SEO
                status_text.text("⚙️ Configuring SEO and image generation parameters...")
                progress_bar.progress(10)
                
                # Debug: Print initialization parameters
                init_params = {
                    'use_custom_llm': kwargs.get('use_custom_llm', False),
                    'topic': kwargs.get('topic'),
                    'keywords': kwargs.get('keywords', []),
                    'blog_type': kwargs.get('blog_type', 'News'),
                    'length_min': length_min,
                    'length_max': length_max,
                    'introduction': kwargs.get('introduction', True),
                    'table_of_content': kwargs.get('table_of_content', False),
                    'faq': kwargs.get('faq', False),
                    'cta': kwargs.get('cta', False),
                    'conclusion': kwargs.get('conclusion', True),
                    'target_audience': kwargs.get('target_audience', []),
                    'sample_blog_url': kwargs.get('sample_blog_url'),
                    'generate_image_prompts': generate_image_prompts,
                    'max_image_prompts': max_image_prompts
                }
                print(f"DEBUG: Initializing BlogWriter with params: {init_params}")
                
                self.blog_writer = BlogWriter(
                    use_custom_llm=kwargs.get('use_custom_llm', False),
                    topic=kwargs.get('topic'),
                    keywords=kwargs.get('keywords', []),
                    blog_type=kwargs.get('blog_type', 'News'),
                    length_min=length_min,
                    length_max=length_max,
                    introduction=kwargs.get('introduction', True),
                    table_of_content=kwargs.get('table_of_content', False),
                    faq=kwargs.get('faq', False),
                    cta=kwargs.get('cta', False),
                    conclusion=kwargs.get('conclusion', True),
                    target_audience=kwargs.get('target_audience', []),
                    sample_blog_url=kwargs.get('sample_blog_url'),
                    generate_image_prompts=generate_image_prompts,
                    generate_images=generate_actual_images
                )
                
                print(f"DEBUG: BlogWriter initialized successfully")
                
                status_text.text("📊 Analyzing sample blog (if provided)...")
                progress_bar.progress(15)
                
                # Analyze sample blog if provided
                if kwargs.get('sample_blog_url'):
                    try:
                        sample_analysis = analyze_sample_blog(kwargs.get('sample_blog_url'))
                        if sample_analysis:
                            self.blog_writer.sample_blog_analysis = sample_analysis
                            status_text.text("✅ Sample blog analyzed successfully!")
                        else:
                            st.warning("Blog analysis returned empty results")
                    except Exception as e:
                        st.warning(f"Could not analyze sample blog: {str(e)}")
                
                progress_bar.progress(20)
                time.sleep(0.5)
                
                status_text.text("🔍 Starting research phase...")
                progress_bar.progress(25)
                
                status_text.text("📝 Generating comprehensive blog content...")
                progress_bar.progress(40)
                
                # Generate the blog using the proper BlogWriter method which handles everything including images
                if generate_actual_images:
                    status_text.text(f"🖼️ Generating blog with {max_image_prompts} section-wise images using FLUX AI...")
                elif generate_image_prompts:
                    status_text.text(f"🎨 Generating blog with {max_image_prompts} section-wise image prompts...")
                else:
                    status_text.text("📝 Generating blog content...")
                progress_bar.progress(70)
                
                try:
                    # Use the BlogWriter's generate_blog method which handles EVERYTHING including images
                    blog_content = self.blog_writer.generate_blog(
                        topic=kwargs.get('topic'),
                        keywords=kwargs.get('keywords', []),
                        blog_type=kwargs.get('blog_type', 'News'),
                        length_min=length_min,
                        length_max=length_max,
                        introduction=kwargs.get('introduction', True),
                        table_of_content=kwargs.get('table_of_content', False),
                        faq=kwargs.get('faq', False),
                        cta=kwargs.get('cta', False),
                        conclusion=kwargs.get('conclusion', True),
                        target_audience=kwargs.get('target_audience', []),
                        sample_blog_url=kwargs.get('sample_blog_url'),
                        generate_image_prompts=generate_image_prompts,
                        generate_images=generate_actual_images,
                        image_model=kwargs.get('image_model', 'flux_dev')
                    )
                    
                    if not blog_content or len(blog_content.strip()) < 100:
                        raise Exception("Blog generation returned insufficient content")
                    
                    status_text.text("✅ Blog generation completed with images!")
                    progress_bar.progress(85)
                        
                except Exception as generation_error:
                    status_text.text("❌ Blog generation failed")
                    progress_bar.progress(100)
                    st.error(f"Blog generation failed: {str(generation_error)}")
                    st.session_state.blog_generation_status = 'error'
                    return
                
                # Get image data from the blog writer (images already generated by BlogWriter)
                generated_images = []
                section_images_data = {}
                image_prompts = []
                
                # Extract image data from BlogWriter - NO DUPLICATE GENERATION
                try:
                    if hasattr(self.blog_writer, 'section_images') and self.blog_writer.section_images:
                        section_images_data = self.blog_writer.section_images
                        status_text.text(f"✅ Retrieved {len(section_images_data)} section images from BlogWriter!")
                        print(f"DEBUG: Retrieved section images: {list(section_images_data.keys())}")
                        
                        # Convert section images to UI display format
                        for section_name, section_data in section_images_data.items():
                            generated_images.append({
                                'prompt': section_data.get('prompt'),
                                'image_url': section_data.get('image_url'),
                                'enhanced_prompt': section_data.get('enhanced_prompt'),
                                'section': section_name,
                                'generation_method': section_data.get('generation_method')
                            })
                    
                    # Extract image prompts from BlogWriter
                    if hasattr(self.blog_writer, 'image_prompts') and self.blog_writer.image_prompts:
                        image_prompts = self.blog_writer.image_prompts
                        status_text.text(f"✅ Retrieved {len(image_prompts)} image prompts from BlogWriter!")
                        print(f"DEBUG: Retrieved image prompts: {len(image_prompts)} prompts")
                
                except Exception as e:
                    print(f"DEBUG: Error retrieving image data from BlogWriter: {str(e)}")
                    st.warning(f"Could not retrieve image data: {str(e)}")
                    # Continue without images rather than failing
                
                status_text.text("📚 Collecting research sources...")
                progress_bar.progress(85)
                
                # Get research sources
                research_sources = []
                try:
                    if hasattr(self.blog_writer, 'research_sources') and self.blog_writer.research_sources:
                        research_sources = self.blog_writer.research_sources
                        status_text.text(f"✅ Found {len(research_sources)} research sources!")
                        print(f"DEBUG: Found {len(research_sources)} research sources")
                    else:
                        status_text.text("⚠️ No research sources found - checking attributes...")
                        print(f"DEBUG: research_sources attribute exists: {hasattr(self.blog_writer, 'research_sources')}")
                        if hasattr(self.blog_writer, 'research_sources'):
                            print(f"DEBUG: research_sources value: {self.blog_writer.research_sources}")
                except Exception as e:
                    st.warning(f"Could not extract research sources: {str(e)}")
                    print(f"DEBUG: Exception extracting research sources: {e}")
                
                status_text.text("📊 Finalizing blog post...")
                progress_bar.progress(95)
                
                # Calculate actual word count
                word_count = len(blog_content.split()) if blog_content else 0
                
                # Debug information about the generated content
                print(f"DEBUG: Generated blog content length: {len(blog_content) if blog_content else 0} characters")
                print(f"DEBUG: Generated blog word count: {word_count} words")
                print(f"DEBUG: Blog content preview: {blog_content[:200] if blog_content else 'No content'}...")
                print(f"DEBUG: Target length was: {length_min}-{length_max} words")
                
                # Store the generated blog with enhanced metadata
                generated_blog = {
                    'topic': kwargs.get('topic'),
                    'content': blog_content,
                    'keywords': kwargs.get('keywords', []),
                    'blog_type': kwargs.get('blog_type'),
                    'image_prompts': image_prompts,
                    'generated_images': generated_images,
                    'research_sources': research_sources,
                    'word_count': word_count,
                    'target_length': f"{length_min}-{length_max}",
                    'seo_optimized': word_count >= 800,
                    'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'user': st.session_state.get('username', 'Anonymous'),
                    'user_email': st.session_state.get('user_email', ''),
                    'generation_settings': {
                        'use_custom_llm': kwargs.get('use_custom_llm', False),
                        'introduction': kwargs.get('introduction', True),
                        'table_of_content': kwargs.get('table_of_content', False),
                        'faq': kwargs.get('faq', False),
                        'cta': kwargs.get('cta', False),
                        'conclusion': kwargs.get('conclusion', True),
                        'target_audience': kwargs.get('target_audience', []),
                        'sample_blog_url': kwargs.get('sample_blog_url'),
                        'generate_image_prompts': generate_image_prompts,
                        'max_image_prompts': max_image_prompts,
                        'generate_actual_images': generate_actual_images,
                        'image_generation_method': 'FLUX AI'
                    }
                }
                
                st.session_state.generated_blog = generated_blog
                st.session_state.blog_generation_status = 'completed'
                
                status_text.text("🎉 Blog generation completed successfully!")
                progress_bar.progress(100)
                
                # Show success metrics
                if generate_actual_images:
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("📝 Words Generated", word_count, f"Target: {length_min}-{length_max}")
                    with col2:
                        st.metric("🎨 Image Prompts", len(image_prompts))
                    with col3:
                        st.metric("🖼️ Generated Images", len(generated_images))
                    with col4:
                        st.metric("📚 Sources", len(research_sources))
                elif generate_image_prompts:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("📝 Words Generated", word_count, f"Target: {length_min}-{length_max}")
                    with col2:
                        st.metric("🎨 Section-wise Image Prompts", len(image_prompts))
                    with col3:
                        st.metric("📚 Sources", len(research_sources))
                else:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("📝 Words Generated", word_count, f"Target: {length_min}-{length_max}")
                    with col2:
                        st.metric("📚 Sources", len(research_sources))
                
                # Clear progress indicators after showing metrics
                time.sleep(2)
                progress_container.empty()
                
                # Auto-scroll to results
                st.success("✅ Blog post generated successfully! Scroll down to view your content.")
                
        except Exception as e:
            st.session_state.blog_generation_status = 'error'
            st.error(f"❌ Error generating blog: {str(e)}")
            
            # Show debugging information
            with st.expander("🔧 Debug Information"):
                st.text(f"Error type: {type(e).__name__}")
                st.text(f"Error message: {str(e)}")
                st.text(f"AI Tools Available: {self.ai_tools_available}")
                if not self.ai_tools_available:
                    st.text(f"AI Tools Error: {AI_TOOLS_ERROR}")
                    
            st.info("💡 **Troubleshooting Tips:**")
            st.markdown("- Check your internet connection")
            st.markdown("- Verify API keys are set correctly")
            st.markdown("- Try with a simpler topic or fewer keywords")
            st.markdown("- Ensure the topic is specific and clear")
    
    def display_generated_blog(self, blog_data):
        """Display the generated blog content with enhanced information"""
        st.markdown("---")
        st.markdown("## 📄 Generated Blog Post")
        
        # Enhanced metadata with SEO information
        col_meta1, col_meta2, col_meta3, col_meta4 = st.columns(4)
        
        word_count = blog_data.get('word_count', 0)
        seo_optimized = blog_data.get('seo_optimized', False)
        
        with col_meta1:
            delta_color = "normal" if seo_optimized else "inverse"
            st.metric("Word Count", word_count, 
                     delta="SEO Optimized" if seo_optimized else "Too Short", 
                     delta_color=delta_color)
        with col_meta2:
            st.metric("Image Prompts", len(blog_data.get('image_prompts', [])))
        with col_meta3:
            st.metric("Research Sources", len(blog_data.get('research_sources', [])))
        with col_meta4:
            st.metric("Blog Type", blog_data.get('blog_type', 'N/A'))
        
        # SEO and Generation Info
        col_info1, col_info2 = st.columns(2)
        
        with col_info1:
            st.markdown("#### 📊 SEO Information")
            st.info(f"**Target Length:** {blog_data.get('target_length', 'N/A')} words")
            st.info(f"**SEO Status:** {'✅ Optimized' if seo_optimized else '⚠️ Needs Improvement'}")
            if blog_data.get('keywords'):
                keywords_data = blog_data.get('keywords', [])
                # Handle both string and dict formats
                if keywords_data and isinstance(keywords_data[0], dict):
                    keywords_text = ", ".join([kw.get('keyword', str(kw)) for kw in keywords_data])[:100]
                else:
                    keywords_text = ", ".join([str(kw) for kw in keywords_data])[:100]
                if len(keywords_text) == 100:
                    keywords_text += "..."
                st.info(f"**Keywords:** {keywords_text}")
            
        with col_info2:
            st.markdown("#### 🔧 Generation Details")
            st.info(f"**Generated:** {blog_data.get('generated_at', 'N/A')}")
            st.info(f"**User:** {blog_data.get('user', 'Anonymous')}")
            generation_settings = blog_data.get('generation_settings', {})
            llm_used = "Google Gemini" if generation_settings.get('use_custom_llm', False) else "OpenAI GPT"
            st.info(f"**LLM Used:** {llm_used}")
        
        # Initialize variables first before using them
        generated_images = blog_data.get('generated_images', [])
        image_prompts = blog_data.get('image_prompts', [])
        settings = blog_data.get('generation_settings', {})
        
        # Blog content with enhanced display
        st.markdown("### 📝 Blog Content")
        
        # Add explanation for image display
        if generated_images:
            st.info("ℹ️ **Note:** Any images appearing in the blog content below are embedded. The section-specific images are displayed separately in the gallery below the content.")
        
        # Display the blog content in a nice format
        content = blog_data.get('content', '')
        if content:
            # Add a container for better content display
            with st.container():
                st.markdown(content)
        else:
            st.warning("No content available to display")
        
        # Enhanced Generated Images section (priority display)
        
        if generated_images:
            st.markdown("---")
            st.markdown("### 🖼️ Section-Specific Generated Images")
            
            # Get the model used for generation
            generation_model = "FLUX AI"
            if generated_images:
                first_image_method = generated_images[0].get('generation_method', 'flux')
                if first_image_method == 'flux_schnell':
                    generation_model = "FLUX Schnell"
                else:
                    generation_model = "FLUX Dev"
            
            st.markdown(f"*{len(generated_images)} section-specific images generated using **{generation_model}** and uploaded to S3*")
            st.info("ℹ️ **Important:** These are section-specific images designed for different parts of your blog content. Each image corresponds to a specific blog section.")
            
            # Display images in a grid layout
            if len(generated_images) == 1:
                cols = st.columns(1)
            elif len(generated_images) == 2:
                cols = st.columns(2)
            elif len(generated_images) <= 4:
                cols = st.columns(2)
            else:
                cols = st.columns(3)
            
            for i, img_data in enumerate(generated_images):
                col_idx = i % len(cols)
                
                with cols[col_idx]:
                    # Display the section-wise generated image
                    image_url = img_data.get('image_url', '')
                    section_name = img_data.get('section', 'Unknown')
                    section_display_name = section_name.replace('_', ' ').title()
                    
                    if image_url:
                        st.image(
                            image_url,
                            caption=f"{section_display_name} Section Image",
                            use_container_width=True
                        )
                        
                        # Section image details in expander
                        with st.expander(f"🖼️ {section_display_name} Section Details", expanded=False):
                            st.markdown(f"**Blog Section:** {section_display_name}")
                            st.markdown(f"**Section-Specific Prompt:**")
                            st.write(img_data.get('prompt', 'N/A'))
                            
                            enhanced_prompt = img_data.get('enhanced_prompt')
                            if enhanced_prompt and enhanced_prompt != img_data.get('prompt'):
                                st.markdown(f"**Enhanced Prompt:**")
                                st.write(enhanced_prompt)
                            
                            # Show model-specific information
                            generation_method = img_data.get('generation_method', 'flux')
                            if generation_method == 'flux_schnell':
                                model_info = "FLUX Schnell - Fast Generation (4 steps)"
                            elif generation_method == 'flux_dev':
                                model_info = "FLUX Dev - High Quality (28 steps)"
                            else:
                                model_info = f"FLUX AI ({generation_method})"
                                
                            st.markdown(f"**Model Used:** {model_info}")
                            st.markdown(f"**Section Purpose:** This image is specifically generated for the '{section_display_name}' section of your blog")
                            st.markdown(f"**Image URL:** [View Full Size]({image_url})")
                            
                            # Add timestamp information if available
                            if 'timestamp' in img_data:
                                st.markdown(f"**Generated At:** {img_data.get('timestamp')}")
                        
                        # Download/Copy buttons
                        col_img1, col_img2 = st.columns(2)
                        with col_img1:
                            if st.button(f"📋 Copy URL", key=f"copy_img_url_{i}_{self.instance_id}", use_container_width=True):
                                st.code(image_url, language="text")
                                st.success("URL copied!")
                        with col_img2:
                            st.markdown(f"[⬇️ Download]({image_url})", unsafe_allow_html=True)
            
            # Batch operations for generated images
            st.markdown("#### 📥 Batch Image Operations")
            col_batch_img1, col_batch_img2, col_batch_img3 = st.columns(3)
            
            with col_batch_img1:
                if st.button("📋 Copy All URLs", key=f"copy_all_img_urls_{self.instance_id}", use_container_width=True):
                    all_urls = [img.get('image_url', '') for img in generated_images if img.get('image_url')]
                    urls_text = '\n'.join(all_urls)
                    st.code(urls_text, language="text")
                    st.success("All image URLs copied!")
            
            with col_batch_img2:
                # Export image data as JSON
                images_json = str(generated_images).replace("'", '"')
                st.download_button(
                    label="📊 Export JSON",
                    data=images_json,
                    file_name=f"{blog_data.get('topic', 'blog').replace(' ', '_')}_images.json",
                    mime="application/json",
                    use_container_width=True
                )
            
            with col_batch_img3:
                # Export prompts used for image generation
                prompts_used = [img.get('prompt', '') for img in generated_images if img.get('prompt')]
                if prompts_used:
                    prompts_text = "\n\n".join([f"Image {i+1} Prompt:\n{prompt}" for i, prompt in enumerate(prompts_used)])
                    st.download_button(
                        label="🎨 Export Prompts",
                        data=prompts_text,
                        file_name=f"{blog_data.get('topic', 'blog').replace(' ', '_')}_generation_prompts.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
            
            # Debug information panel
            with st.expander("🔍 Image Generation Debug Info", expanded=False):
                st.markdown("**Section Image Mapping:**")
                for i, img in enumerate(generated_images):
                    section = img.get('section', 'Unknown')
                    url = img.get('image_url', 'No URL')
                    method = img.get('generation_method', 'Unknown')
                    st.markdown(f"- **{section.replace('_', ' ').title()}**: {method} | URL: `{url[:50]}...`")
                
                st.markdown(f"**Total Images Generated:** {len(generated_images)}")
                st.markdown(f"**Generation Session:** {blog_data.get('generated_at', 'Unknown')}")
        
        # Image prompts section (show if no images were generated but prompts exist)
        elif generated_images and not any(img.get('image_url') for img in generated_images):
            st.markdown("### 🎨 Section-wise AI Image Generation Prompts")
            st.markdown(f"*{len(generated_images)} section-based prompts generated for your blog images*")
            
            # Display section-wise prompts
            for i, img_data in enumerate(generated_images):
                section_name = img_data.get('section', 'Unknown')
                section_display_name = section_name.replace('_', ' ').title()
                prompt = img_data.get('prompt', 'N/A')
                
                with st.expander(f"🖼️ {section_display_name} Section Prompt - Click to view", expanded=False):
                    st.markdown(f"**Blog Section:** {section_display_name}")
                    st.markdown(f"**Section-Specific Prompt:**")
                    st.write(prompt)
                    
                    enhanced_prompt = img_data.get('enhanced_prompt')
                    if enhanced_prompt and enhanced_prompt != prompt:
                        st.markdown(f"**Enhanced Prompt:**")
                        st.write(enhanced_prompt)
                    
                    st.markdown(f"**Purpose:** This prompt is optimized for the '{section_display_name}' section of your blog")
                    
                    # Add copy button for each prompt
                    col_prompt1, col_prompt2 = st.columns([3, 1])
                    with col_prompt2:
                        if st.button(f"📋 Copy", key=f"copy_section_prompt_{section_name}_{i}_{self.instance_id}", use_container_width=True):
                            st.code(prompt, language="text")
                            st.success("Section prompt copied!")
        elif settings.get('generate_image_prompts') == False:
            st.info("🚫 Section-wise image prompt generation was disabled by user preference.")
        elif not generated_images:
            st.info("No section-wise image prompts were generated for this blog post.")
        
        # Enhanced Research sources
        research_sources = blog_data.get('research_sources', [])
        if research_sources:
            st.markdown("### 🔍 Research Sources")
            st.markdown(f"*{len(research_sources)} sources used for research*")
            
            for i, source in enumerate(research_sources, 1):
                if isinstance(source, dict):
                    # Handle dictionary format with title and URL
                    title = source.get('title', 'Source')
                    url = source.get('url', '#')
                    st.markdown(f"**{i}.** [{title}]({url})", unsafe_allow_html=True)
                elif isinstance(source, str):
                    # Handle string format like "(Source: Fingent)" or "Source: Company Name"
                    import re
                    
                    # Extract source name from different patterns
                    source_match = re.search(r'\(Source:\s*([^)]+)\)', source)
                    if source_match:
                        # Pattern: "(Source: Fingent)"
                        source_name = source_match.group(1).strip()
                        # Create a Google search URL for the source
                        search_url = f"https://www.google.com/search?q={source_name.replace(' ', '+')}"
                        st.markdown(f"**{i}.** [{source}]({search_url})", unsafe_allow_html=True)
                    elif source.lower().startswith('source:'):
                        # Pattern: "Source: Company Name"
                        source_name = source.split(':', 1)[1].strip()
                        search_url = f"https://www.google.com/search?q={source_name.replace(' ', '+')}"
                        st.markdown(f"**{i}.** [Source: {source_name}]({search_url})", unsafe_allow_html=True)
                    elif 'http' in source:
                        # If source contains a URL, extract and make it clickable
                        url_match = re.search(r'(https?://[^\s]+)', source)
                        if url_match:
                            url = url_match.group(1)
                            source_text = source.replace(url, '').strip()
                            if source_text:
                                st.markdown(f"**{i}.** [{source_text}]({url})", unsafe_allow_html=True)
                            else:
                                st.markdown(f"**{i}.** [View Source]({url})", unsafe_allow_html=True)
                        else:
                            st.markdown(f"**{i}.** {source}")
                    else:
                        # For any other string format, create a search link
                        search_url = f"https://www.google.com/search?q={source.replace(' ', '+')}"
                        st.markdown(f"**{i}.** [{source}]({search_url})", unsafe_allow_html=True)
                else:
                    st.markdown(f"**{i}.** {source}")
        else:
            st.markdown("### 🔍 Research Sources")
            st.info("No research sources available for this blog post.")
        
        # Enhanced Export options
        st.markdown("### 📥 Export & Share Options")
        
        col_export1, col_export2, col_export3, col_export4 = st.columns(4)
        
        with col_export1:
            if st.button("📋 Copy Content", key=f"copy_content_{self.instance_id}", use_container_width=True):
                st.code(content, language="markdown")
                st.success("Content copied!")
                
        with col_export2:
            # Download as markdown
            st.download_button(
                label="⬇️ Markdown",
                data=content,
                file_name=f"{blog_data.get('topic', 'blog').replace(' ', '_').replace('/', '-')}.md",
                mime="text/markdown",
                use_container_width=True
            )
            
        with col_export3:
            # Download as text
            st.download_button(
                label="⬇️ Text File",
                data=content,
                file_name=f"{blog_data.get('topic', 'blog').replace(' ', '_').replace('/', '-')}.txt",
                mime="text/plain",
                use_container_width=True
            )
            
        with col_export4:
            # Export images or prompts (prioritize generated images)
            generated_images = blog_data.get('generated_images', [])
            image_prompts = blog_data.get('image_prompts', [])
            
            if generated_images:
                # Export generated images URLs
                image_urls = [img.get('image_url', '') for img in generated_images if img.get('image_url')]
                if image_urls:
                    urls_text = "\n".join([f"Image {i+1}: {url}" for i, url in enumerate(image_urls)])
                    st.download_button(
                        label="🖼️ Image URLs",
                        data=urls_text,
                        file_name=f"{blog_data.get('topic', 'blog').replace(' ', '_').replace('/', '-')}_image_urls.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                else:
                    st.button("🖼️ No URLs", disabled=True, use_container_width=True, key=f"no_urls_{self.instance_id}")
            elif image_prompts:
                # Export image prompts if no images were generated
                prompts_text = "\n\n".join([f"Section-based Prompt {i+1}:\n{prompt}" for i, prompt in enumerate(image_prompts)])
                st.download_button(
                    label="🎨 Image Prompts",
                    data=prompts_text,
                    file_name=f"{blog_data.get('topic', 'blog').replace(' ', '_').replace('/', '-')}_image_prompts.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            else:
                st.button(
                    "🎨 No Content",
                    disabled=True,
                    use_container_width=True,
                    help="No images or prompts generated for this blog",
                    key=f"no_content_{self.instance_id}"
                )
        
        # Additional actions
        st.markdown("### 🔄 Additional Actions")
        col_action1, col_action2, col_action3 = st.columns(3)
        
        with col_action1:
            if st.button("🔄 Generate New Version", key=f"regenerate_{self.instance_id}", use_container_width=True):
                st.info("Use the 'Generate Blog' tab to create a new version with different settings")
                
        with col_action2:
            if st.button("📊 Analyze This Blog", key=f"analyze_generated_{self.instance_id}", use_container_width=True):
                st.info("Switch to 'Blog Analysis' tab to analyze this generated content")
                
        with col_action3:
            generated_images = blog_data.get('generated_images', [])
            image_prompts = blog_data.get('image_prompts', [])
            
            if generated_images:
                if st.button("🖼️ View Images", key=f"view_images_{self.instance_id}", use_container_width=True):
                    st.info(f"Scroll up to view {len(generated_images)} generated images with S3 URLs")
            elif image_prompts:
                if st.button("🎨 Generate Images", key=f"generate_images_{self.instance_id}", use_container_width=True):
                    st.info("Enable 'Generate Actual Images' in blog settings to create images from these prompts")
            else:
                if st.button("🎨 No Images", key=f"no_images_{self.instance_id}", disabled=True, use_container_width=True):
                    st.warning("No images or prompts available")
    
    def render_blog_analysis(self):
        """Render blog analysis interface"""
        st.markdown("### 🔍 Blog Analysis")
        st.markdown("Analyze existing blogs for style, structure, and content patterns.")
        
        # URL input for analysis
        blog_url = st.text_input(
            "Blog URL to Analyze",
            placeholder="https://example.com/blog-post",
            help="Enter the URL of a blog post you want to analyze"
        )
        
        if st.button("🔍 Analyze Blog", key=f"analyze_blog_{self.instance_id}", type="primary", disabled=not blog_url):
            if blog_url:
                try:
                    with st.spinner("Analyzing blog..."):
                        analysis = analyze_sample_blog(blog_url)
                        
                        if analysis:
                            st.success("Blog analysis completed!")
                            
                            # Display analysis results
                            st.markdown("#### 📊 Analysis Results")
                            
                            # Basic info
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.metric("Word Count", analysis.get('word_count', 'N/A'))
                                st.metric("Paragraphs", analysis.get('paragraph_count', 'N/A'))
                                
                            with col2:
                                st.metric("Headings", analysis.get('heading_count', 'N/A'))
                                st.metric("Reading Time", f"{analysis.get('reading_time_minutes', 'N/A')} min")
                            
                            # Content structure
                            if analysis.get('structure'):
                                st.markdown("#### 🏗️ Content Structure")
                                for item in analysis.get('structure', []):
                                    st.markdown(f"- {item}")
                            
                            # Key insights
                            if analysis.get('insights'):
                                st.markdown("#### 💡 Key Insights")
                                st.markdown(analysis.get('insights'))
                        else:
                            st.error("Could not analyze the blog. Please check the URL.")
                            
                except Exception as e:
                    st.error(f"Error analyzing blog: {str(e)}")
    
    def render_blog_history(self):
        """Render blog generation history"""
        st.markdown("### 📚 Generated Blogs History")
        st.markdown("View and manage your previously generated blog posts.")
        
        # This would typically connect to a database or session storage
        # For now, we'll show the current session's generated blog
        
        if 'generated_blog' in st.session_state:
            blog = st.session_state.generated_blog
            
            with st.expander(f"📝 {blog.get('topic', 'Untitled Blog')}", expanded=True):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"**Type:** {blog.get('blog_type', 'N/A')}")
                    st.write(f"**Words:** {blog.get('word_count', 0)}")
                    
                with col2:
                    st.write(f"**Keywords:** {len(blog.get('keywords', []))}")
                    st.write(f"**Images:** {len(blog.get('image_prompts', []))}")
                    
                with col3:
                    st.write(f"**Author:** {blog.get('generated_at', 'Anonymous')}")
                    st.write(f"**Email:** {blog.get('user_email', 'N/A')}")
                
                if st.button(f"📖 View Full Content", key=f"view_blog_{self.instance_id}"):
                    self.display_generated_blog(blog)
        else:
            st.info("No blogs generated yet. Create your first blog using the 'Generate Blog' tab!")
            
        # Placeholder for database integration
        st.markdown("---")
        st.markdown("#### 🔄 Load from Database")
        st.info("Database integration coming soon! This will show all your previously generated blogs.")
