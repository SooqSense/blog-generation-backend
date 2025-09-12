import streamlit as st
import sys
import os
from pathlib import Path
from datetime import datetime, date

# Add the project root to the path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import AI tools directly without Django setup
try:
    from tools.ai.daily_news.ai_daily_news import AIDailyNewsService
    
    AI_TOOLS_AVAILABLE = True
    AI_TOOLS_ERROR = None
    print("✅ News feature: AI tools imported successfully")
    
except Exception as e:
    AI_TOOLS_AVAILABLE = False
    AI_TOOLS_ERROR = str(e)
    print(f"⚠️ News feature: AI tools import failed - {str(e)}")
    
    # Create dummy classes for graceful degradation
    class AIDailyNewsService:
        def __init__(self, **kwargs):
            pass
        def search_news(self, *args, **kwargs):
            raise Exception(f"AI news service not available: {AI_TOOLS_ERROR}")
        def generate_daily_summary(self, *args, **kwargs):
            raise Exception(f"AI news service not available: {AI_TOOLS_ERROR}")

class NewsFeature:
    """AI News feature for Streamlit UI"""
    
    def __init__(self):
        self.ai_tools_available = AI_TOOLS_AVAILABLE
        self.ai_tools_error = AI_TOOLS_ERROR
        try:
            self.news_service = AIDailyNewsService()
        except Exception as e:
            self.news_service = None
            if AI_TOOLS_AVAILABLE:
                # Update error if service creation failed even when tools are available
                self.ai_tools_error = str(e)
        
    def render(self):
        """Render the AI news interface"""
        st.markdown("# 📰 AI Daily News")
        st.markdown("Stay updated with the latest AI news and trends from around the world.")
        
        # Create tabs for different functionalities
        tab1, tab2, tab3 = st.tabs(["📰 Generate News", "🌍 Country News", "📚 News History"])
        
        with tab1:
            self.render_news_generation()
            
        with tab2:
            self.render_country_news()
            
        with tab3:
            self.render_news_history()
    
    def render_news_generation(self):
        """Render the news generation form"""
        st.markdown("### Generate AI Daily News Summary")
        
        # Two column layout
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Basic news settings
            st.markdown("#### 🔍 News Search Settings")
            
            keywords = st.text_area(
                "Keywords (one per line) *",
                placeholder="artificial intelligence\nmachine learning\nAI research\ntech innovation",
                help="Enter keywords to search for in AI news",
                height=100
            )
            
            # Date and location settings
            col_date1, col_date2 = st.columns(2)
            
            with col_date1:
                country = st.selectbox(
                    "Country/Region",
                    ["us", "uk", "in", "ca", "au", "de", "fr", "jp", "kr", "cn", "sg"],
                    format_func=lambda x: {
                        "us": "🇺🇸 United States",
                        "uk": "🇬🇧 United Kingdom", 
                        "in": "🇮🇳 India",
                        "ca": "🇨🇦 Canada",
                        "au": "🇦🇺 Australia",
                        "de": "🇩🇪 Germany",
                        "fr": "🇫🇷 France",
                        "jp": "🇯🇵 Japan",
                        "kr": "🇰🇷 South Korea",
                        "cn": "🇨🇳 China",
                        "sg": "🇸🇬 Singapore"
                    }.get(x, x),
                    help="Select country/region for news search"
                )
                
            with col_date2:
                news_date = st.date_input(
                    "News Date",
                    value=date.today(),
                    help="Date for news compilation"
                )
            
            # Advanced settings
            st.markdown("#### ⚙️ Advanced Settings")
            
            col_adv1, col_adv2 = st.columns(2)
            
            with col_adv1:
                num_articles = st.number_input(
                    "Number of Articles",
                    min_value=5,
                    max_value=50,
                    value=20,
                    help="Number of news articles to analyze"
                )
                
                summary_style = st.selectbox(
                    "Summary Style",
                    ["Professional", "Technical", "Casual", "Academic"],
                    help="Style of the news summary"
                )
                
            with col_adv2:
                include_sources = st.checkbox(
                    "Include Source Links",
                    value=True,
                    help="Include links to original articles"
                )
                
                markdown_format = st.checkbox(
                    "Markdown Format",
                    value=True,
                    help="Format output as markdown"
                )
            
            # Content preferences
            st.markdown("#### 📊 Content Preferences")
            
            content_types = st.multiselect(
                "Content Types",
                ["Breaking News", "Research Papers", "Company Updates", "Product Launches", 
                 "Industry Analysis", "Startup News", "Investment News", "Regulatory Updates"],
                default=["Breaking News", "Research Papers", "Company Updates"],
                help="Types of content to prioritize"
            )
            
            # Quick keyword presets
            st.markdown("#### ⚡ Quick Keyword Presets")
            
            col_preset1, col_preset2, col_preset3 = st.columns(3)
            
            with col_preset1:
                if st.button("🤖 General AI", use_container_width=True):
                    st.session_state.keyword_preset = "artificial intelligence\nAI\nmachine learning\ndeep learning\nneural networks"
                    
            with col_preset2:
                if st.button("🏢 AI Business", use_container_width=True):
                    st.session_state.keyword_preset = "AI startup\nAI investment\nAI company\nAI funding\nAI acquisition"
                    
            with col_preset3:
                if st.button("🔬 AI Research", use_container_width=True):
                    st.session_state.keyword_preset = "AI research\nAI paper\nAI breakthrough\nAI model\nAI algorithm"
            
            # Apply keyword preset
            if 'keyword_preset' in st.session_state:
                st.info(f"Preset applied: {st.session_state.keyword_preset.split(chr(10))[0]}...")
                keywords = st.session_state.keyword_preset
        
        with col2:
            # News preview and controls
            st.markdown("### 🚀 Generation")
            
            # News info
            st.markdown("#### 📊 News Info")
            if keywords:
                keyword_list = [k.strip() for k in keywords.split('\n') if k.strip()]
                st.metric("Keywords", len(keyword_list))
                
                if len(keyword_list) < 2:
                    st.warning("⚠️ Consider adding more keywords")
                elif len(keyword_list) > 10:
                    st.info("ℹ️ Many keywords - very comprehensive search")
                else:
                    st.success("✅ Good keyword coverage")
            
            # Country info
            country_info = {
                "us": {"name": "United States", "timezone": "EST/PST", "lang": "English"},
                "uk": {"name": "United Kingdom", "timezone": "GMT", "lang": "English"},
                "in": {"name": "India", "timezone": "IST", "lang": "English"},
                "ca": {"name": "Canada", "timezone": "EST/PST", "lang": "English"},
                "au": {"name": "Australia", "timezone": "AEST", "lang": "English"},
                "de": {"name": "Germany", "timezone": "CET", "lang": "German/English"},
                "fr": {"name": "France", "timezone": "CET", "lang": "French/English"},
                "jp": {"name": "Japan", "timezone": "JST", "lang": "Japanese/English"},
                "kr": {"name": "South Korea", "timezone": "KST", "lang": "Korean/English"},
                "cn": {"name": "China", "timezone": "CST", "lang": "Chinese/English"},
                "sg": {"name": "Singapore", "timezone": "SGT", "lang": "English"}
            }
            
            if country in country_info:
                info = country_info[country]
                st.markdown(f"""
                **Selected Region:**
                - **Country:** {info['name']}
                - **Timezone:** {info['timezone']}
                - **Language:** {info['lang']}
                """)
            
            # Generation status
            if 'news_generation_status' in st.session_state:
                status = st.session_state.news_generation_status
                if status == 'generating':
                    st.info("🔄 Generating AI news summary...")
                elif status == 'completed':
                    st.success("✅ News generated successfully!")
                elif status == 'error':
                    st.error("❌ Generation failed")
            
            # News tips
            st.markdown("#### 💡 News Tips")
            st.markdown("""
            **Best Practices:**
            - Use specific AI-related keywords
            - Select relevant country for regional news
            - Include diverse content types
            - Check multiple sources
            - Update daily for fresh content
            """)
        
        # Generate button
        st.markdown("---")
        
        col_gen1, col_gen2, col_gen3 = st.columns([1, 2, 1])
        
        with col_gen2:
            if st.button(
                "📰 Generate AI News",
                type="primary",
                use_container_width=True,
                disabled=not keywords.strip()
            ):
                if keywords.strip():
                    keyword_list = [k.strip() for k in keywords.split('\n') if k.strip()]
                    self.generate_news_summary(
                        keywords=keyword_list,
                        country=country,
                        news_date=news_date,
                        num_articles=num_articles,
                        summary_style=summary_style,
                        include_sources=include_sources,
                        markdown_format=markdown_format,
                        content_types=content_types
                    )
                else:
                    st.error("Please enter keywords for news search")
        
        # Display generated news
        if 'generated_news' in st.session_state:
            self.display_generated_news(st.session_state.generated_news)
    
    def generate_news_summary(self, **kwargs):
        """Generate AI news summary using the news service"""
        try:
            st.session_state.news_generation_status = 'generating'
            
            # Show progress
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.text("Searching for AI news articles...")
            progress_bar.progress(20)
            
            # Search for news articles
            news_articles = self.news_service.search_news(
                keywords=kwargs.get('keywords', []),
                country=kwargs.get('country', 'us'),
                num_results=kwargs.get('num_articles', 20)
            )
            
            status_text.text("Generating news summary...")
            progress_bar.progress(60)
            
            # Generate summary
            summary_result = self.news_service.generate_daily_summary(
                articles=news_articles,
                keywords=kwargs.get('keywords', []),
                country=kwargs.get('country', 'us'),
                target_date=kwargs.get('news_date', date.today())
            )
            
            status_text.text("Processing news content...")
            progress_bar.progress(90)
            
            # Store the generated news
            generated_news = {
                'keywords': kwargs.get('keywords', []),
                'country': kwargs.get('country', 'us'),
                'news_date': kwargs.get('news_date', date.today()),
                'articles': news_articles,
                'summary': summary_result.get('summary', ''),
                'content': summary_result.get('content', ''),
                'sources': summary_result.get('sources', []),
                'settings': {
                    'num_articles': kwargs.get('num_articles'),
                    'summary_style': kwargs.get('summary_style'),
                    'include_sources': kwargs.get('include_sources'),
                    'markdown_format': kwargs.get('markdown_format'),
                    'content_types': kwargs.get('content_types')
                },
                'generated_by': st.session_state.get('username', 'Anonymous'),
                'user_email': st.session_state.get('user_email', ''),
                'generated_at': datetime.now()
            }
            
            st.session_state.generated_news = generated_news
            st.session_state.news_generation_status = 'completed'
            
            status_text.text("AI news generation completed!")
            progress_bar.progress(100)
            
            # Clear progress indicators after a short delay
            import time
            time.sleep(1)
            progress_bar.empty()
            status_text.empty()
            
        except Exception as e:
            st.session_state.news_generation_status = 'error'
            st.error(f"Error generating AI news: {str(e)}")
    
    def display_generated_news(self, news_data):
        """Display the generated news summary"""
        st.markdown("---")
        st.markdown("## 📰 AI Daily News Summary")
        
        # News metadata
        col_meta1, col_meta2, col_meta3, col_meta4 = st.columns(4)
        
        with col_meta1:
            st.metric("Articles Found", len(news_data.get('articles', [])))
        with col_meta2:
            st.metric("Keywords", len(news_data.get('keywords', [])))
        with col_meta3:
            country_names = {
                "us": "🇺🇸 US", "uk": "🇬🇧 UK", "in": "🇮🇳 India", "ca": "🇨🇦 Canada",
                "au": "🇦🇺 Australia", "de": "🇩🇪 Germany", "fr": "🇫🇷 France",
                "jp": "🇯🇵 Japan", "kr": "🇰🇷 Korea", "cn": "🇨🇳 China", "sg": "🇸🇬 Singapore"
            }
            st.metric("Region", country_names.get(news_data.get('country', 'us'), news_data.get('country', 'US')))
        with col_meta4:
            news_date = news_data.get('news_date', date.today())
            st.metric("Date", news_date.strftime("%Y-%m-%d"))
        
        # News summary
        st.markdown("### 📋 Executive Summary")
        
        summary = news_data.get('summary', '')
        if summary:
            st.markdown(summary)
        else:
            st.info("No summary available")
        
        # Full content
        st.markdown("### 📄 Detailed News Content")
        
        content = news_data.get('content', '')
        if content:
            # Display content in markdown format
            st.markdown(content)
        else:
            st.info("No detailed content available")
        
        # News sources
        sources = news_data.get('sources', [])
        if sources:
            st.markdown("### 🔗 News Sources")
            
            for i, source in enumerate(sources, 1):
                with st.expander(f"Source {i}: {source.get('title', 'Untitled')[:60]}..."):
                    col_source1, col_source2 = st.columns([2, 1])
                    
                    with col_source1:
                        st.write(f"**Title:** {source.get('title', 'N/A')}")
                        st.write(f"**Source:** {source.get('source', 'N/A')}")
                        if source.get('snippet'):
                            st.write(f"**Snippet:** {source.get('snippet', '')}")
                        
                    with col_source2:
                        if source.get('link'):
                            st.markdown(f"[🔗 Read Article]({source.get('link')})")
                        st.write(f"**Date:** {source.get('date', 'N/A')}")
        
        # Export options
        st.markdown("### 📥 Export Options")
        
        col_export1, col_export2, col_export3 = st.columns(3)
        
        with col_export1:
            if st.button("📋 Copy Summary", use_container_width=True):
                st.code(summary, language="text")
                
        with col_export2:
            # Download full content
            full_content = f"# AI Daily News - {news_date.strftime('%Y-%m-%d')}\n\n"
            full_content += f"## Summary\n{summary}\n\n"
            full_content += f"## Detailed Content\n{content}\n\n"
            if sources:
                full_content += "## Sources\n"
                for i, source in enumerate(sources, 1):
                    full_content += f"{i}. [{source.get('title', 'Untitled')}]({source.get('link', '#')})\n"
            
            st.download_button(
                label="⬇️ Download Report",
                data=full_content,
                file_name=f"ai_news_{news_date.strftime('%Y%m%d')}.md",
                mime="text/markdown",
                use_container_width=True
            )
            
        with col_export3:
            # Export as JSON
            import json
            json_data = json.dumps(news_data, default=str, indent=2)
            st.download_button(
                label="📊 Export JSON",
                data=json_data,
                file_name=f"ai_news_data_{news_date.strftime('%Y%m%d')}.json",
                mime="application/json",
                use_container_width=True
            )
    
    def render_country_news(self):
        """Render country-specific news interface"""
        st.markdown("### 🌍 Country-Specific AI News")
        st.markdown("Get AI news tailored to specific countries and regions.")
        
        # Country selection grid
        st.markdown("#### 🗺️ Select Country/Region")
        
        countries = [
            {"code": "us", "name": "United States", "flag": "🇺🇸", "desc": "Silicon Valley, Tech Giants"},
            {"code": "uk", "name": "United Kingdom", "flag": "🇬🇧", "desc": "London Tech Hub, DeepMind"},
            {"code": "in", "name": "India", "flag": "🇮🇳", "desc": "Bangalore, Tech Services"},
            {"code": "ca", "name": "Canada", "flag": "🇨🇦", "desc": "Toronto-Waterloo, AI Research"},
            {"code": "au", "name": "Australia", "flag": "🇦🇺", "desc": "Sydney, Melbourne Tech"},
            {"code": "de", "name": "Germany", "flag": "🇩🇪", "desc": "Berlin, Industrial AI"},
            {"code": "fr", "name": "France", "flag": "🇫🇷", "desc": "Paris, Station F"},
            {"code": "jp", "name": "Japan", "flag": "🇯🇵", "desc": "Tokyo, Robotics"},
            {"code": "kr", "name": "South Korea", "flag": "🇰🇷", "desc": "Seoul, Samsung, LG"},
            {"code": "cn", "name": "China", "flag": "🇨🇳", "desc": "Beijing, Shenzhen, Baidu"},
            {"code": "sg", "name": "Singapore", "flag": "🇸🇬", "desc": "Southeast Asia Hub"}
        ]
        
        # Create country cards
        cols = st.columns(3)
        for i, country in enumerate(countries):
            col_idx = i % 3
            
            with cols[col_idx]:
                if st.button(
                    f"{country['flag']} {country['name']}\n{country['desc']}", 
                    key=f"country_{country['code']}",
                    use_container_width=True
                ):
                    st.session_state.selected_country = country
                    st.success(f"Selected: {country['name']}")
        
        # Show selected country details
        if 'selected_country' in st.session_state:
            country = st.session_state.selected_country
            
            st.markdown("---")
            st.markdown(f"### {country['flag']} {country['name']} AI News")
            
            col_country1, col_country2 = st.columns([2, 1])
            
            with col_country1:
                st.info(f"**Focus:** {country['desc']}")
                
                # Quick generate for this country
                if st.button(f"🚀 Generate {country['name']} AI News", type="primary"):
                    # Use default AI keywords for this country
                    default_keywords = ["artificial intelligence", "AI", "machine learning", "tech news"]
                    self.generate_news_summary(
                        keywords=default_keywords,
                        country=country['code'],
                        news_date=date.today(),
                        num_articles=15,
                        summary_style="Professional",
                        include_sources=True,
                        markdown_format=True,
                        content_types=["Breaking News", "Company Updates", "Research Papers"]
                    )
                    
            with col_country2:
                st.markdown("**Quick Stats:**")
                # This would ideally come from a database or API
                st.metric("AI Companies", "1000+")
                st.metric("Tech Hubs", "5+")
                st.metric("AI Investment", "$10B+")
    
    def render_news_history(self):
        """Render news generation history"""
        st.markdown("### 📚 AI News History")
        st.markdown("View and manage your previously generated AI news summaries.")
        
        # Show current session's generated news
        if 'generated_news' in st.session_state:
            news = st.session_state.generated_news
            
            with st.expander(f"📰 AI News - {news.get('news_date', 'Unknown Date')}", expanded=True):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"**Country:** {news.get('country', 'N/A').upper()}")
                    st.write(f"**Articles:** {len(news.get('articles', []))}")
                    
                with col2:
                    st.write(f"**Keywords:** {len(news.get('keywords', []))}")
                    st.write(f"**Sources:** {len(news.get('sources', []))}")
                    
                with col3:
                    st.write(f"**Generated By:** {news.get('generated_by', 'Anonymous')}")
                    st.write(f"**Email:** {news.get('user_email', 'N/A')}")
                
                # News preview
                summary = news.get('summary', '')
                if summary:
                    preview = summary[:300] + "..." if len(summary) > 300 else summary
                    st.markdown(f"**Preview:** {preview}")
                
                if st.button("📖 View Full News", key="view_news"):
                    self.display_generated_news(news)
        else:
            st.info("No AI news generated yet. Create your first news summary using the 'Generate News' tab!")
        
        # Placeholder for database integration
        st.markdown("---")
        st.markdown("#### 🔄 Load from Database")
        st.info("Database integration coming soon! This will show all your previously generated AI news summaries.")
