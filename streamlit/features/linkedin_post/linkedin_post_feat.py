import streamlit as st
import sys
import os
from pathlib import Path

# Add the project root to the path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import AI tools from Django management app
try:
    from management_app.linkedin_post_generator.service.linkedin_post_generator import LinkedInPostGenerator
    from management_app.ai_trends.service.trending_queries import fetch_trending_queries
    
    AI_TOOLS_AVAILABLE = True
    AI_TOOLS_ERROR = None
    print("✅ LinkedIn post feature: AI tools imported successfully")
    
except Exception as e:
    AI_TOOLS_AVAILABLE = False
    AI_TOOLS_ERROR = str(e)
    print(f"⚠️ LinkedIn post feature: AI tools import failed - {str(e)}")
    
    # Create dummy classes for graceful degradation
    class LinkedInPostGenerator:
        def __init__(self, **kwargs):
            pass
        def generate_post(self, *args, **kwargs):
            raise Exception(f"LinkedIn post generation not available: {AI_TOOLS_ERROR}")
    
    def fetch_trending_queries(*args, **kwargs):
        return {"rising": [], "top": []}

class LinkedInPostFeature:
    """LinkedIn Post Generation feature for Streamlit UI"""
    
    def __init__(self):
        self.post_generator = None
        self.ai_tools_available = AI_TOOLS_AVAILABLE
        self.ai_tools_error = AI_TOOLS_ERROR
        
    def render(self):
        """Render the LinkedIn post generation interface"""
        st.markdown("# 💼 LinkedIn Post Generation")
        st.markdown("Create engaging LinkedIn posts for professional networking and thought leadership.")
        
        # Create tabs for different functionalities
        tab1, tab2, tab3 = st.tabs(["✍️ Generate Post", "📈 Trending Topics", "📝 Generated Posts"])
        
        with tab1:
            self.render_post_generation()
            
        with tab2:
            self.render_trending_topics()
            
        with tab3:
            self.render_post_history()
    
    def render_post_generation(self):
        """Render the LinkedIn post generation form"""
        st.markdown("### Create Professional LinkedIn Post")
        
        # Two column layout
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Basic post settings
            st.markdown("#### 📝 Post Content")
            
            topic = st.text_input(
                "Post Topic *",
                placeholder="e.g., The Future of Remote Work in Tech Industry",
                help="Main topic for your LinkedIn post"
            )
            
            keywords = st.text_area(
                "Keywords (one per line)",
                placeholder="remote work\ntech industry\nproductivity\ninnovation",
                help="Enter relevant keywords, one per line",
                height=80
            )
            
            # Post style and tone
            st.markdown("#### 🎯 Post Style")
            
            col_style1, col_style2 = st.columns(2)
            
            with col_style1:
                post_style = st.selectbox(
                    "Post Style",
                    ["Professional", "Thought Leadership", "Educational", "Personal Story", "Industry Insight"],
                    help="Style and tone of the LinkedIn post"
                )
                
                
            with col_style2:
                engagement_focus = st.selectbox(
                    "Engagement Focus",
                    ["Discussion", "Advice", "News/Update", "Question", "Story"],
                    help="Primary engagement strategy"
                )
                
                include_cta = st.checkbox(
                    "Include Call-to-Action",
                    value=True,
                    help="Add a call-to-action at the end"
                )
            
            # Advanced options
            st.markdown("#### ⚙️ Advanced Options")
            
            col_adv1, col_adv2 = st.columns(2)
            
            with col_adv1:
                hashtag_count = st.slider(
                    "Number of Hashtags",
                    min_value=3,
                    max_value=8,
                    value=4,
                    help="Number of hashtags to include"
                )
                
            with col_adv2:
                emoji_style = st.selectbox(
                    "Emoji Style",
                    ["Professional", "Moderate", "Minimal"],
                    help="How many emojis to include"
                )
            
            # Industry/Niche selection
            st.markdown("#### 🏢 Industry Context")
            
            industry = st.selectbox(
                "Industry/Niche",
                ["Technology", "Marketing", "Finance", "Healthcare", "Education", "Consulting", 
                 "Entrepreneurship", "AI/ML", "Sales", "HR", "General Business"],
                help="Industry context for the post"
            )
            
            # Content inspiration
            st.markdown("#### 💡 Content Templates")
            
            col_temp1, col_temp2, col_temp3 = st.columns(3)
            
            with col_temp1:
                if st.button("🚀 Startup Insight", use_container_width=True):
                    st.session_state.content_template = {
                        'style': 'Thought Leadership',
                        'focus': 'Discussion',
                        'industry': 'Entrepreneurship',
                        'sample_keywords': ['startup', 'innovation', 'growth', 'leadership']
                    }
                    
            with col_temp2:
                if st.button("📊 Data Insight", use_container_width=True):
                    st.session_state.content_template = {
                        'style': 'Educational',
                        'focus': 'News/Update',
                        'industry': 'Technology',
                        'sample_keywords': ['data', 'analytics', 'insights', 'trends']
                    }
                    
            with col_temp3:
                if st.button("🤝 Career Advice", use_container_width=True):
                    st.session_state.content_template = {
                        'style': 'Professional',
                        'focus': 'Advice',
                        'industry': 'HR',
                        'sample_keywords': ['career', 'professional development', 'skills', 'growth']
                    }
        
        with col2:
            # Generation preview and controls
            st.markdown("### 🚀 Generation")
            
            # Post preview info
            st.markdown("#### 📊 Post Preview")
            if topic:
                word_count = len(topic.split())
                st.metric("Topic Words", word_count)
                
                if word_count < 3:
                    st.warning("⚠️ Consider a more detailed topic")
                elif word_count > 10:
                    st.info("ℹ️ Very specific topic - good for targeted content")
                else:
                    st.success("✅ Good topic length")
            
            # LinkedIn best practices
            st.markdown("#### 💡 LinkedIn Tips")
            st.markdown("""
            **Best Practices:**
            - Keep posts under 1,300 characters
            - Use 3-5 relevant hashtags
            - Ask questions to drive engagement
            - Share personal insights or stories
            - Include a clear call-to-action
            """)
            
            # Generation status
            if 'linkedin_generation_status' in st.session_state:
                status = st.session_state.linkedin_generation_status
                if status == 'generating':
                    st.info("🔄 Generating LinkedIn post...")
                elif status == 'completed':
                    st.success("✅ Post generated successfully!")
                elif status == 'error':
                    st.error("❌ Generation failed")
            
            # Trending topics suggestion
            st.markdown("#### 📈 Quick Trending")
            if st.button("🔥 Get Trending Topics", use_container_width=True):
                if topic:
                    try:
                        with st.spinner("Fetching trending topics..."):
                            trending = fetch_trending_queries(topic, limit=5)
                            if trending.get('top') or trending.get('rising'):
                                st.success("Found trending topics!")
                                st.session_state.quick_trending = trending
                            else:
                                st.warning("No trending topics found")
                    except Exception as e:
                        st.error(f"Error fetching trends: {str(e)}")
                else:
                    st.error("Enter a topic first")
            
            if 'quick_trending' in st.session_state:
                trending = st.session_state.quick_trending
                if trending.get('top'):
                    st.markdown("**Top Trends:**")
                    for trend in trending['top'][:3]:
                        st.caption(f"• {trend.get('query', '')}")
        
        # Generate button
        st.markdown("---")
        
        col_gen1, col_gen2, col_gen3 = st.columns([1, 2, 1])
        
        with col_gen2:
            if st.button(
                "💼 Generate LinkedIn Post",
                type="primary",
                use_container_width=True,
                disabled=not topic.strip()
            ):
                if topic.strip():
                    self.generate_linkedin_post(
                        topic=topic,
                        keywords=keywords.split('\n') if keywords else [],
                        post_style=post_style,
                        engagement_focus=engagement_focus,
                        industry=industry,
                        hashtag_count=hashtag_count,
                        emoji_style=emoji_style,
                        include_cta=include_cta
                    )
                else:
                    st.error("Please enter a post topic")
        
        # Display generated post
        if 'generated_linkedin_post' in st.session_state:
            self.display_generated_post(st.session_state.generated_linkedin_post)
    
    def generate_linkedin_post(self, **kwargs):
        """Generate a LinkedIn post using the AI tools"""
        try:
            st.session_state.linkedin_generation_status = 'generating'
            
            # Show progress
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.text("Initializing LinkedIn post generator...")
            progress_bar.progress(20)
            
            # Initialize post generator
            self.post_generator = LinkedInPostGenerator(
                topic=kwargs.get('topic'),
                keywords=kwargs.get('keywords', [])
            )
            
            status_text.text("Generating LinkedIn post content...")
            progress_bar.progress(60)
            
            # Generate the post
            try:
                post_result = self.post_generator.generate_post(
                    topic=kwargs.get('topic'),
                    keywords=kwargs.get('keywords', [])
                )
                
                # Handle different return formats from the generator
                if isinstance(post_result, tuple):
                    post_content, file_path = post_result
                elif isinstance(post_result, dict):
                    post_content = post_result.get('content', post_result.get('post', ''))
                    file_path = post_result.get('file_path', '')
                else:
                    post_content = str(post_result) if post_result else ''
                    file_path = ''
                    
                # Ensure we have valid content
                if not post_content or not post_content.strip():
                    post_content = f"Generated LinkedIn post about {kwargs.get('topic')} (content generation in progress...)"
                    st.warning("Post content appears empty, using fallback text")
                    
            except Exception as gen_error:
                st.error(f"Post generation failed: {str(gen_error)}")
                post_content = f"Error generating post about {kwargs.get('topic')}. Please try again."
                file_path = ''
            
            status_text.text("Processing generated post...")
            progress_bar.progress(90)
            
            # Store the generated post
            generated_post = {
                'topic': kwargs.get('topic'),
                'content': post_content,
                'keywords': kwargs.get('keywords', []),
                'settings': {
                    'post_style': kwargs.get('post_style'),
                    'engagement_focus': kwargs.get('engagement_focus'),
                    'industry': kwargs.get('industry'),
                    'hashtag_count': kwargs.get('hashtag_count'),
                    'emoji_style': kwargs.get('emoji_style'),
                    'include_cta': kwargs.get('include_cta')
                },
                'character_count': len(post_content) if post_content else 0,
                'generated_by': st.session_state.get('username', 'Anonymous'),
                'user_email': st.session_state.get('user_email', ''),
                'file_path': file_path
            }
            
            st.session_state.generated_linkedin_post = generated_post
            st.session_state.linkedin_generation_status = 'completed'
            
            status_text.text("LinkedIn post generation completed!")
            progress_bar.progress(100)
            
            # Clear progress indicators after a short delay
            import time
            time.sleep(1)
            progress_bar.empty()
            status_text.empty()
            
        except Exception as e:
            st.session_state.linkedin_generation_status = 'error'
            st.error(f"Error generating LinkedIn post: {str(e)}")
    
    def display_generated_post(self, post_data):
        """Display the generated LinkedIn post"""
        st.markdown("---")
        st.markdown("## 💼 Generated LinkedIn Post")
        
        # Post metadata
        col_meta1, col_meta2, col_meta3 = st.columns(3)
        
        with col_meta1:
            char_count = post_data.get('character_count', 0)
            st.metric("Characters", char_count)
            if char_count > 1300:
                st.warning("⚠️ Post may be too long for optimal engagement")
            else:
                st.success("✅ Good length")
                
        with col_meta2:
            st.metric("Keywords", len(post_data.get('keywords', [])))
            
        with col_meta3:
            st.metric("Style", post_data.get('settings', {}).get('post_style', 'N/A'))
        
        # Post content
        st.markdown("### 📝 LinkedIn Post Content")
        
        content = post_data.get('content', '')
        if content:
            # Display post in a styled container with better visibility
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%); 
                border: 2px solid #0077b5; 
                border-left: 6px solid #0077b5;
                padding: 24px; 
                border-radius: 12px;
                margin: 15px 0;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                color: #2d3748;
                font-size: 16px;
                box-shadow: 0 2px 8px rgba(0, 119, 181, 0.1);
                white-space: pre-wrap;
                word-wrap: break-word;
            ">
                {content.replace(chr(10), '<br>').replace('\n', '<br>')}
            </div>
            """, unsafe_allow_html=True)
            
            # Alternative plain text display as fallback
            st.markdown("#### 📄 Plain Text Version:")
            st.text_area(
                "LinkedIn Post Content (Copy from here if needed)",
                value=content,
                height=200,
                help="Use this if the styled version above doesn't display properly"
            )
            
            # Debug information - can be removed in production
            with st.expander("🔧 Debug Info", expanded=False):
                st.write("**Content Length:**", len(content))
                st.write("**Content Type:**", type(content))
                st.write("**Has Content:**", bool(content and content.strip()))
                if content:
                    st.write("**First 100 characters:**", repr(content[:100]))
                    st.write("**Line count:**", len(content.split('\n')))
                    st.json({"content_preview": content[:200] if content else "No content"})
            
            # Character count analysis
            lines = content.split('\n')
            paragraph_count = len([line for line in lines if line.strip()])
            hashtag_lines = [line for line in lines if '#' in line]
            hashtag_count = len([word for line in hashtag_lines for word in line.split() if word.startswith('#')])
            
            col_analysis1, col_analysis2, col_analysis3 = st.columns(3)
            
            with col_analysis1:
                st.metric("Paragraphs", paragraph_count)
            with col_analysis2:
                st.metric("Hashtags", hashtag_count)
            with col_analysis3:
                emoji_count = len([char for char in content if ord(char) > 127])
                st.metric("Emojis", emoji_count)
        else:
            st.error("No content generated")
        
        # Export and sharing options
        st.markdown("### 📤 Export & Share")
        
        col_export1, col_export2, col_export3 = st.columns(3)
        
        with col_export1:
            if st.button("📋 Copy to Clipboard", use_container_width=True):
                st.code(content, language="text")
                
        with col_export2:
            # Download as text
            st.download_button(
                label="⬇️ Download Post",
                data=content,
                file_name=f"linkedin_post_{post_data.get('topic', 'post').replace(' ', '_')}.txt",
                mime="text/plain",
                use_container_width=True
            )
            
        with col_export3:
            # LinkedIn direct link (opens LinkedIn with pre-filled text)
            if st.button("🔗 Open LinkedIn", use_container_width=True):
                import urllib.parse
                encoded_text = urllib.parse.quote(content)
                linkedin_url = f"https://www.linkedin.com/sharing/share-offsite/?text={encoded_text}"
                st.markdown(f"[Open in LinkedIn]({linkedin_url})")
        
        # Post optimization suggestions
        st.markdown("### 💡 Optimization Suggestions")
        
        suggestions = []
        
        if char_count < 500:
            suggestions.append("✅ Good length for high engagement")
        elif char_count > 1300:
            suggestions.append("⚠️ Consider shortening for better engagement")
        else:
            suggestions.append("📝 Good length, consider adding more personal insights")
        
        if hashtag_count < 3:
            suggestions.append("🔖 Consider adding more relevant hashtags")
        elif hashtag_count > 5:
            suggestions.append("🔖 Consider reducing hashtags to 3-5 for better reach")
        else:
            suggestions.append("✅ Good hashtag count")
        
        if '?' not in content:
            suggestions.append("❓ Consider adding a question to drive engagement")
        else:
            suggestions.append("✅ Great! Questions help drive engagement")
        
        for suggestion in suggestions:
            st.markdown(f"- {suggestion}")
    
    def render_trending_topics(self):
        """Render trending topics interface"""
        st.markdown("### 📈 Trending Topics & Keywords")
        st.markdown("Discover trending topics related to your industry or interests.")
        
        # Search for trending topics
        col_search1, col_search2 = st.columns([3, 1])
        
        with col_search1:
            search_topic = st.text_input(
                "Search Topic",
                placeholder="e.g., artificial intelligence, remote work, digital marketing",
                help="Enter a topic to find related trending queries"
            )
            
        with col_search2:
            search_limit = st.number_input(
                "Results",
                min_value=5,
                max_value=50,
                value=20,
                help="Number of trending topics to fetch"
            )
        
        if st.button("🔍 Find Trending Topics", type="primary", disabled=not search_topic):
            if search_topic:
                try:
                    with st.spinner("Fetching trending topics..."):
                        trending_data = fetch_trending_queries(
                            topic=search_topic,
                            limit=search_limit
                        )
                        
                        st.session_state.trending_data = trending_data
                        st.session_state.trending_search_topic = search_topic
                        
                except Exception as e:
                    st.error(f"Error fetching trending topics: {str(e)}")
        
        # Display trending topics
        if 'trending_data' in st.session_state:
            trending = st.session_state.trending_data
            search_topic = st.session_state.get('trending_search_topic', '')
            
            st.markdown(f"### 🔥 Trending Topics for: **{search_topic}**")
            
            # Create tabs for different types of trends
            if trending.get('top') or trending.get('rising'):
                trend_tab1, trend_tab2 = st.tabs(["🔝 Top Trends", "📈 Rising Trends"])
                
                with trend_tab1:
                    if trending.get('top'):
                        st.markdown("#### 🔝 Top Trending Topics")
                        
                        for i, trend in enumerate(trending['top'], 1):
                            col_trend1, col_trend2, col_trend3 = st.columns([3, 1, 1])
                            
                            with col_trend1:
                                st.markdown(f"**{i}.** {trend.get('query', '')}")
                                
                            with col_trend2:
                                st.metric("Score", f"{trend.get('value', 0):.1f}")
                                
                            with col_trend3:
                                if st.button("Use Topic", key=f"use_top_{i}", use_container_width=True):
                                    st.session_state.selected_trending_topic = trend.get('query', '')
                                    st.success(f"Selected: {trend.get('query', '')}")
                    else:
                        st.info("No top trending topics found")
                
                with trend_tab2:
                    if trending.get('rising'):
                        st.markdown("#### 📈 Rising Trending Topics")
                        
                        for i, trend in enumerate(trending['rising'], 1):
                            col_trend1, col_trend2, col_trend3 = st.columns([3, 1, 1])
                            
                            with col_trend1:
                                st.markdown(f"**{i}.** {trend.get('query', '')}")
                                
                            with col_trend2:
                                st.metric("Score", f"{trend.get('value', 0):.1f}")
                                
                            with col_trend3:
                                if st.button("Use Topic", key=f"use_rising_{i}", use_container_width=True):
                                    st.session_state.selected_trending_topic = trend.get('query', '')
                                    st.success(f"Selected: {trend.get('query', '')}")
                    else:
                        st.info("No rising trending topics found")
            else:
                st.warning("No trending topics found for this search term.")
        
        # Show selected trending topic
        if 'selected_trending_topic' in st.session_state:
            st.markdown("---")
            st.markdown("### ✅ Selected Trending Topic")
            st.info(f"**Selected:** {st.session_state.selected_trending_topic}")
            
            if st.button("🚀 Create Post with This Topic", type="primary"):
                # Switch to post generation tab with pre-filled topic
                st.session_state.auto_fill_topic = st.session_state.selected_trending_topic
                st.success("Topic ready! Go to 'Generate Post' tab to create your LinkedIn post.")
    
    def render_post_history(self):
        """Render LinkedIn post generation history"""
        st.markdown("### 📝 Generated LinkedIn Posts History")
        st.markdown("View and manage your previously generated LinkedIn posts.")
        
        # Show current session's generated post
        if 'generated_linkedin_post' in st.session_state:
            post = st.session_state.generated_linkedin_post
            
            with st.expander(f"💼 {post.get('topic', 'Untitled Post')}", expanded=True):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"**Style:** {post.get('settings', {}).get('post_style', 'N/A')}")
                    st.write(f"**Characters:** {post.get('character_count', 0)}")
                    
                with col2:
                    st.write(f"**Keywords:** {len(post.get('keywords', []))}")
                    st.write(f"**Industry:** {post.get('settings', {}).get('industry', 'N/A')}")
                    
                with col3:
                    st.write(f"**Author:** {post.get('generated_by', 'Anonymous')}")
                    st.write(f"**Email:** {post.get('user_email', 'N/A')}")
                
                # Post preview
                content = post.get('content', '')
                if content:
                    preview = content[:200] + "..." if len(content) > 200 else content
                    st.markdown(f"**Preview:** {preview}")
                
                if st.button("📖 View Full Post", key="view_linkedin_post"):
                    self.display_generated_post(post)
        else:
            st.info("No LinkedIn posts generated yet. Create your first post using the 'Generate Post' tab!")
        
        # Placeholder for database integration
        st.markdown("---")
        st.markdown("#### 🔄 Load from Database")
        st.info("Database integration coming soon! This will show all your previously generated LinkedIn posts.")
