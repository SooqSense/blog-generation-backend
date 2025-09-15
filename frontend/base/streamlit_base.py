import streamlit as st
import sys
import os
from pathlib import Path

# Add the project root to the path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# AI Tools Import State - No Django setup required for frontend
AI_TOOLS_CACHE = {}
AI_IMPORT_ERRORS = []

def import_ai_tools():
    """Import AI tools directly without Django setup conflicts"""
    global AI_TOOLS_CACHE, AI_IMPORT_ERRORS
    
    # Return cached tools if already imported
    if AI_TOOLS_CACHE:
        return AI_TOOLS_CACHE
    
    print("🔧 Importing AI tools directly...")
    tools = {}
    errors = []
    
    # Blog Generation Tools
    try:
        from tools.ai.blog_generator.blog_writing.blog_writer import BlogWriter
        from tools.ai.blog_generator.blog_writing.blog_analyzer.blog_analyzer import analyze_sample_blog
        from tools.ai.blog_generator.blog_writing.images.blog_images import (
            generate_section_specific_images,
            generate_section_image_prompts_only,
            get_section_image_urls_list
        )
        
        tools.update({
            'BlogWriter': BlogWriter,
            'analyze_sample_blog': analyze_sample_blog,
            'generate_section_specific_images': generate_section_specific_images,
            'generate_section_image_prompts_only': generate_section_image_prompts_only,
            'get_section_image_urls_list': get_section_image_urls_list
        })
        print("✅ Blog generation tools imported")
        
    except Exception as e:
        error_msg = f"Blog generation tools: {str(e)}"
        errors.append(error_msg)
        print(f"⚠️ {error_msg}")
    
    # Image Generation Tools
    try:
        from tools.ai.image_generation.image_generator import generate_image_with_flux, generate_image_with_flux_schnell
        from tools.ai.image_generation.edit_images import edit_image_with_flux, convert_image_to_base64
        
        tools.update({
            'generate_image_with_flux': generate_image_with_flux,
            'generate_image_with_flux_schnell': generate_image_with_flux_schnell,
            'edit_image_with_flux': edit_image_with_flux,
            'convert_image_to_base64': convert_image_to_base64
        })
        print("✅ Image generation tools imported")
        
    except Exception as e:
        error_msg = f"Image generation tools: {str(e)}"
        errors.append(error_msg)
        print(f"⚠️ {error_msg}")
    
    # LinkedIn Post Generation Tools
    try:
        from tools.ai.linkedin_post_generator.linkedin_post_generator import LinkedInPostGenerator
        tools['LinkedInPostGenerator'] = LinkedInPostGenerator
        print("✅ LinkedIn post generation tools imported")
        
    except Exception as e:
        error_msg = f"LinkedIn post generation tools: {str(e)}"
        errors.append(error_msg)
        print(f"⚠️ {error_msg}")
    
    # News Generation Tools
    try:
        from tools.ai.daily_news.ai_daily_news import AIDailyNewsService
        tools['AIDailyNewsService'] = AIDailyNewsService
        print("✅ News generation tools imported")
        
    except Exception as e:
        error_msg = f"News generation tools: {str(e)}"
        errors.append(error_msg)
        print(f"⚠️ {error_msg}")
    
    # Trending Queries Tools
    try:
        from tools.ai.trends_ai.trending_queries import fetch_trending_queries
        tools['fetch_trending_queries'] = fetch_trending_queries
        print("✅ Trending queries tools imported")
        
    except Exception as e:
        error_msg = f"Trending queries tools: {str(e)}"
        errors.append(error_msg)
        print(f"⚠️ {error_msg}")
    
    # Store results globally
    AI_TOOLS_CACHE = tools
    AI_IMPORT_ERRORS = errors
    
    return tools

def get_ai_tool(tool_name):
    """Get AI tool with fallback to dummy implementation"""
    tools = import_ai_tools()
    
    if tool_name in tools:
        return tools[tool_name]
    
    # Fallback dummy implementation
    def dummy_function(*args, **kwargs):
        raise Exception(f"AI tool '{tool_name}' is not available")
    
    class DummyClass:
        def __init__(self, *args, **kwargs):
            pass
        def __call__(self, *args, **kwargs):
            return dummy_function(*args, **kwargs)
        def __getattr__(self, name):
            return dummy_function
    
    return DummyClass()

# Frontend uses only AI tools - no Django components needed


def get_feature_class(feature_name):
    """Import feature classes directly without Django setup"""
    try:
        # Import features directly - no Django setup needed
        if feature_name == "BlogGenerationFeature":
            from frontend.features.blog_generation.blog_generation_feat import BlogGenerationFeature
            return BlogGenerationFeature
        elif feature_name == "ImageGenerationFeature":
            from frontend.features.image_generation.image_generation_feat import ImageGenerationFeature
            return ImageGenerationFeature
        elif feature_name == "LinkedInPostFeature":
            from frontend.features.linkedin_post.linkedin_post_feat import LinkedInPostFeature
            return LinkedInPostFeature
        elif feature_name == "NewsFeature":
            from frontend.features.news.news_feat import NewsFeature
            return NewsFeature
        else:
            raise ValueError(f"Unknown feature: {feature_name}")
            
    except Exception as e:
        # Return a dummy feature class if import fails
        error_msg = str(e)
        print(f"⚠️ Feature '{feature_name}' import failed: {error_msg}")
        
        class DummyFeature:
            def __init__(self):
                self.error = error_msg
                
            def render(self):
                st.error(f"⚠️ Feature '{feature_name}' import failed: {self.error}")
                st.info("Please check the system configuration and try again.")
        
        return DummyFeature

class StreamlitApp:
    """Main Streamlit application class for AI Blog Generator"""
    
    def __init__(self):
        self.initialize_session_state()
        # Import AI tools for frontend use - no authentication required
        self.ai_tools = import_ai_tools()
        self.ai_tools_success = len(self.ai_tools) > 0
        
    def initialize_session_state(self):
        """Initialize session state variables - no authentication required"""
        # All features are now accessible without authentication
        pass
            
    def render_header(self):
        """Render the main application header"""
        st.markdown("""
        <div style="background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); 
                    padding: 1rem; margin: -1rem -1rem 2rem -1rem; border-radius: 0px;">
            <h1 style="color: white; text-align: center; margin: 0; font-size: 2.5rem;">
                🤖 AI Blog Generator
            </h1>
            <p style="color: white; text-align: center; margin: 0.5rem 0 0 0; opacity: 0.9;">
                Professional Content Creation Platform
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Show AI tools status only if there are issues
        if not self.ai_tools_success and AI_IMPORT_ERRORS:
            st.warning("⚠️ Some AI features may have limited functionality.")
            with st.expander("📋 Show Details", expanded=False):
                st.info("AI Tools Import Status")
                for error in AI_IMPORT_ERRORS[:3]:  # Show first 3 errors
                    st.code(f"Error: {error}", language="text")
                if len(AI_IMPORT_ERRORS) > 3:
                    st.info(f"... and {len(AI_IMPORT_ERRORS) - 3} more errors")
                st.info("💡 Individual features will show specific error messages if needed.")
        
    def render_sidebar(self):
        """Render the sidebar navigation"""
        with st.sidebar:
            st.markdown("### 🚀 Navigation")
            
            # Feature selection
            feature = st.selectbox(
                "Select Feature:",
                ["🏠 Home", "📝 Blog Generation", "🎨 Image Generation", 
                 "💼 LinkedIn Posts", "📰 AI News"],
                key="feature_selector"
            )
            
            st.markdown("---")
            
            # System information
            st.markdown("### ℹ️ System Info")
            st.caption("Version: 1.0.0")
            
            # Show backend status
            if self.ai_tools_success:
                st.caption("✅ Backend: AI Tools Direct")
            else:
                st.caption("⚠️ Backend: Limited Mode")
            
            st.caption("🤖 AI Models: GPT-3.5, FLUX AI")
            st.caption("🔄 Load Mode: Dynamic Import")
            
        return feature
        
    def render_home(self):
        """Render the home page"""
        st.markdown("## 🏠 Welcome to AI Blog Generator")
        
        # Feature cards
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            ### 📝 Blog Generation
            Create professional blog posts with AI-powered content generation.
            - Multi-agent blog writing
            - SEO optimization
            - Custom topics and keywords
            - Sample blog analysis
            """)
            
            st.markdown("""
            ### 🎨 Image Generation
            Generate stunning images for your content using AI.
            - High-quality FLUX AI generation
            - Image editing capabilities
            - Multiple image formats
            - Professional quality output
            """)
            
        with col2:
            st.markdown("""
            ### 💼 LinkedIn Posts
            Create engaging LinkedIn posts for professional networking.
            - AI-powered content creation
            - Hashtag optimization
            - Professional tone
            - Engagement-focused writing
            """)
            
            st.markdown("""
            ### 📰 AI News
            Stay updated with the latest AI news and trends.
            - Daily AI news compilation
            - Country-specific filtering
            - Trending topics analysis
            - Source verification
            """)
            
        # Statistics section
        st.markdown("---")
        st.markdown("## 📊 Platform Statistics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Blogs Generated", "1,234", "↗️ 12%")
        with col2:
            st.metric("Images Created", "5,678", "↗️ 8%")
        with col3:
            st.metric("LinkedIn Posts", "890", "↗️ 15%")
        with col4:
            st.metric("News Articles", "456", "↗️ 5%")
            
    def run(self):
        """Main application runner"""
        self.render_header()
        
        # Get selected feature from sidebar
        feature = self.render_sidebar()
        
        # Render selected feature - all features are now accessible without authentication
        if feature == "🏠 Home":
            self.render_home()
        elif feature == "📝 Blog Generation":
            BlogFeatureClass = get_feature_class("BlogGenerationFeature")
            blog_feature = BlogFeatureClass()
            blog_feature.render()
        elif feature == "🎨 Image Generation":
            ImageFeatureClass = get_feature_class("ImageGenerationFeature")
            image_feature = ImageFeatureClass()
            image_feature.render()
        elif feature == "💼 LinkedIn Posts":
            LinkedInFeatureClass = get_feature_class("LinkedInPostFeature")
            linkedin_feature = LinkedInFeatureClass()
            linkedin_feature.render()
        elif feature == "📰 AI News":
            NewsFeatureClass = get_feature_class("NewsFeature")
            news_feature = NewsFeatureClass()
            news_feature.render()

# Custom CSS for better styling
def load_custom_css():
    """Load custom CSS for better UI styling"""
    st.markdown("""
    <style>
    /* Main container styling */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 1200px;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        padding-top: 1rem;
    }
    
    /* Feature cards */
    .feature-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 4px solid #667eea;
    }
    
    /* Success/Error messages */
    .stSuccess {
        background-color: #d4edda !important;
        border-color: #c3e6cb !important;
        color: #155724 !important;
    }
    
    .stError {
        background-color: #f8d7da !important;
        border-color: #f5c6cb !important;
        color: #721c24 !important;
    }
    
    .stInfo {
        background-color: #d1ecf1 !important;
        border-color: #bee5eb !important;
        color: #0c5460 !important;
    }
    
    .stWarning {
        background-color: #fff3cd !important;
        border-color: #ffeaa7 !important;
        color: #856404 !important;
    }
    
    /* Button styling */
    .stButton > button {
        border-radius: 8px;
        border: none;
        transition: all 0.3s ease;
        font-weight: 500;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* Primary button styling */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
    }
    
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #5a67d8 0%, #6b46c1 100%);
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
    }
    
    /* Metric styling */
    .metric-container {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border: 1px solid #e2e8f0;
    }
    
    /* Text area styling */
    .stTextArea > div > div > textarea {
        background-color: #ffffff;
        color: #2d3748;
        border: 2px solid #e2e8f0;
        border-radius: 8px;
        font-family: 'Segoe UI', system-ui, sans-serif;
    }
    
    .stTextArea > div > div > textarea:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    /* Content display containers */
    .content-container {
        background: #ffffff;
        border: 2px solid #0077b5;
        border-left: 6px solid #0077b5;
        border-radius: 12px;
        padding: 24px;
        margin: 15px 0;
        color: #2d3748;
        line-height: 1.6;
        font-size: 16px;
        box-shadow: 0 2px 8px rgba(0, 119, 181, 0.1);
    }
    
    /* Dark theme adjustments */
    @media (prefers-color-scheme: dark) {
        .content-container {
            background: #2d3748;
            color: #e2e8f0;
            border-color: #4299e1;
        }
        
        .stTextArea > div > div > textarea {
            background-color: #2d3748;
            color: #e2e8f0;
        }
    }
    </style>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    # Load custom CSS
    load_custom_css()
    
    # Initialize and run the app
    app = StreamlitApp()
    app.run()
