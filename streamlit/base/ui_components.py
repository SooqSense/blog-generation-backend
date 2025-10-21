"""
UI Components module for Streamlit application.
Contains reusable UI components, styling, and layout functions.
"""

import streamlit as st
from base.config import APP_CONFIG, FEATURES, DEMO_STATISTICS, API_ENDPOINTS
from base.feature_ui_components import FeatureUIComponents

class UIComponents:
    """Reusable UI components for the Streamlit application"""
    
    @staticmethod
    def render_header(api_base_url: str):
        """Render the main application header"""
        st.markdown(f"""
        <div style="background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); 
                    padding: 1rem; margin: -1rem -1rem 2rem -1rem; border-radius: 0px;">
            <h1 style="color: white; text-align: center; margin: 0; font-size: 2.5rem;">
                {APP_CONFIG['icon']} {APP_CONFIG['title']}
            </h1>
            <p style="color: white; text-align: center; margin: 0.5rem 0 0 0; opacity: 0.9;">
                {APP_CONFIG['subtitle']}
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Show API status
        st.success(f"✅ Connected to Django API at {api_base_url}")
        st.info(f"📡 {len(API_ENDPOINTS)} API endpoints available")
        
        # Render organization selector if user is authenticated
        try:
            from authentication.ui_components import SidebarAuth
            sidebar_auth = SidebarAuth()
            if sidebar_auth.auth_manager.is_authenticated():
                from authentication.ui_components import AuthUI
                auth_ui = AuthUI()
                org_info = auth_ui.render_organization_selector()
                if org_info:
                    st.markdown("---")
        except Exception as e:
            # Silently handle if authentication components are not available
            pass
    
    @staticmethod
    def render_sidebar(auth_handler, api_endpoints_count: int):
        """Render the sidebar navigation"""
        with st.sidebar:
            # Authentication section
            auth_handler.render_auth_section()
            
            st.markdown("### 🚀 Navigation")
            
            # Feature selection
            feature = st.selectbox(
                "Select Feature:",
                FEATURES,
                key="feature_selector"
            )
            
            st.markdown("---")
            
            # System information
            st.markdown("### ℹ️ System Info")
            st.caption(f"Version: {APP_CONFIG['version']} - API Powered")
            
            # Show API status
            st.caption("✅ Django API: Connected")
            st.caption(f"📡 {api_endpoints_count} endpoints available")

            # Show authentication status
            auth_status = auth_handler.get_auth_status()
            st.caption(f"Auth: {auth_status}")
            
            # Quick actions
            st.markdown("---")
            st.markdown("### ⚡ Quick Actions")
            if st.button("🔄 Refresh Page"):
                st.rerun()
            
            if st.button("🔐 Clear Auth State"):
                # Clear authentication state
                keys_to_clear = ['auth_token', 'user_info', 'clerk_session']
                for key in keys_to_clear:
                    if key in st.session_state:
                        del st.session_state[key]
                st.success("Authentication state cleared! Please refresh the page.")
                st.rerun()
            
            if st.button("📊 View API Status"):
                with st.expander("API Endpoints", expanded=False):
                    for name, url in API_ENDPOINTS.items():
                        st.code(f"{name}: {url}")
            
        return feature
    
    @staticmethod
    def render_home(api_base_url: str):
        """Render the home page"""
        st.markdown("## 🏠 Welcome to AI Blog Generator")
        st.markdown(f"**{APP_CONFIG['subtitle']}**")
        
        # API Status
        st.success(f"✅ Connected to Django API at {api_base_url}")
        st.info(f"📡 {len(API_ENDPOINTS)} API endpoints available for content generation")
        
        # Feature cards
        UIComponents._render_feature_cards()
        
        # Statistics section - REMOVED
        # UIComponents._render_statistics()
    
    @staticmethod
    def _render_feature_cards():
        """Render feature cards"""
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
            ### 🎯 Upwork Proposals
            Generate winning Upwork proposals using GPT-4 and your portfolio.
            - Tailored proposals based on job requirements
            - Uses your knowledge base for relevant project examples
            - Follows proven proposal writing strategies
            - Professional formatting and call-to-action
            - **NEW**: Upload template documents to fill instead of generating from scratch
            """)
            
            st.markdown("""
            ### 📰 AI News
            Stay updated with the latest AI news and trends.
            - Daily AI news compilation
            - Country-specific filtering
            - Trending topics analysis
            - Source verification
            """)
            
            st.markdown("""
            ### 📚 Knowledge Base
            Upload and manage your project documents and portfolio files.
            - PDF, Word, Markdown, and text file support
            - Automatic content extraction and indexing
            - S3 cloud storage integration
            - Vector database for AI-powered search
            """)
            
            st.markdown("""
            ### 🤖 AI Portfolio Chat
            Chat with your uploaded documents using AI.
            - Ask questions about your projects
            - Get intelligent responses from document content
            - Context-aware conversations
            - Source attribution and references
            """)
    
    @staticmethod
    def _render_statistics():
        """Render platform statistics"""
        st.markdown("---")
        st.markdown("## 📊 Platform Statistics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Blogs Generated", DEMO_STATISTICS['blogs_generated']['value'], DEMO_STATISTICS['blogs_generated']['delta'])
        with col2:
            st.metric("Images Created", DEMO_STATISTICS['images_created']['value'], DEMO_STATISTICS['images_created']['delta'])
        with col3:
            st.metric("LinkedIn Posts", DEMO_STATISTICS['linkedin_posts']['value'], DEMO_STATISTICS['linkedin_posts']['delta'])
        with col4:
            st.metric("Upwork Proposals", DEMO_STATISTICS['upwork_proposals']['value'], DEMO_STATISTICS['upwork_proposals']['delta'])
        
        # Second row for new features
        col5, col6, col7, col8 = st.columns(4)
        
        with col5:
            st.metric("News Articles", DEMO_STATISTICS['news_articles']['value'], DEMO_STATISTICS['news_articles']['delta'])
        with col6:
            st.metric("Documents Uploaded", DEMO_STATISTICS['documents_uploaded']['value'], DEMO_STATISTICS['documents_uploaded']['delta'])
        with col7:
            st.metric("Chat Sessions", DEMO_STATISTICS['chat_sessions']['value'], DEMO_STATISTICS['chat_sessions']['delta'])
        with col8:
            st.metric("Active Users", DEMO_STATISTICS['active_users']['value'], DEMO_STATISTICS['active_users']['delta'])

class CustomCSS:
    """Custom CSS styling for the Streamlit application"""
    
    @staticmethod
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
