import streamlit as st
from typing import Dict, Any, Optional

# Import API client
from api_client.api_client import news_api
# Import markdown processor
from base.markdown_processor import MarkdownProcessor

class NewsFeature:
    """AI News feature for Streamlit UI - API-based"""
    
    def __init__(self):
        self.api = news_api
    
    def render(self):
        """Main render method"""
        st.title("📰 AI News")
        st.markdown("Stay updated with the latest AI news and trends.")
        
        # Render news generation directly without tabs
        self.render_news_generation()
    
    def render_news_generation(self):
        """Render news generation form"""
        st.subheader("🚀 Generate AI News Summary")
        
        with st.form("news_generation_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                country = st.selectbox(
                    "Country",
                    ["us", "uk", "in", "ca", "au", "de", "fr", "jp"],
                    index=0,
                    help="Select country for news filtering"
                )
                
                num_results = st.number_input(
                    "Number of Articles",
                    min_value=3,
                    max_value=20,
                    value=5,
                    help="Number of articles to analyze"
                )
            
            with col2:
                keywords_input = st.text_area(
                    "Keywords",
                    value="artificial intelligence, machine learning",
                    help="Enter keywords separated by commas"
                )
            
            submitted = st.form_submit_button("📰 Generate News Summary", use_container_width=True)
            
            if submitted:
                # Process keywords
                keywords = [k.strip() for k in keywords_input.split(',') if k.strip()]
                
                # Generate news
                self.generate_news_summary(country, keywords, num_results)
    
    def generate_news_summary(self, country: str, keywords: list, num_results: int):
        """Generate news summary using API"""
        with st.spinner("📰 Generating AI news summary... This may take up to 5 minutes for comprehensive analysis."):
            try:
                response = self.api.generate_news(
                    country=country,
                    keywords=keywords,
                    num_results=num_results
                )
                
                if response and response.get("status") == "success":
                    self.display_generated_news(response)
                else:
                    error_msg = response.get("message", "Unknown error") if response else "No response from server"
                    st.error(f"❌ News generation failed: {error_msg}")
                    
            except Exception as e:
                st.error(f"❌ Error generating news: {str(e)}")
    
    def display_generated_news(self, news_data: Dict[str, Any]):
        """Display the generated news summary"""
        st.success("✅ AI news summary generated successfully!")
        
        # Display metadata
        metadata_fields = [
            ("country_name", "Country"),
            ("articles_count", "Articles Analyzed"),
            ("news_date", "News Date")
        ]
        
        # Display keywords used
        if "keywords" in news_data:
            st.info(f"🔍 Keywords: {', '.join(news_data['keywords'])}")
        
        # Display content with metadata using the modular processor
        MarkdownProcessor.display_with_metadata(
            news_data,
            "📰 Generated News Summary",
            metadata_fields,
            ["raw_content", "content", "sections"]
        )
        
        # Display sources
        MarkdownProcessor.display_sources(news_data.get("sources", []), "📚 News Sources")