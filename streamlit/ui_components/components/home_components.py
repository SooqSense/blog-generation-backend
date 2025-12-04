"""
Home Page Components Module
Handles home page rendering and feature cards display
"""

import streamlit as st
from base.config import APP_CONFIG, API_ENDPOINTS
from ui_components.feature_ui_components import FeatureUIComponents


class HomeComponents:
    """Components for rendering the home page"""
    
    @staticmethod
    def render_welcome_section(api_base_url: str):
        """Render welcome section with API status"""
        st.markdown("## 🏠 Welcome to AI Blog Generator")
        st.markdown(f"**{APP_CONFIG['subtitle']}**")
        
        FeatureUIComponents.display_success_message(
            f"Connected to Django API at {api_base_url}"
        )
        FeatureUIComponents.display_info_message(
            f"{len(API_ENDPOINTS)} API endpoints available for content generation"
        )
    
    @staticmethod
    def render_feature_cards():
        """Render feature cards in a grid layout"""
        col1, col2 = st.columns(2)
        
        with col1:
            HomeComponents._render_feature_card(
                "📝 Blog Generation",
                "Create professional blog posts with AI-powered content generation.",
                [
                    "Multi-agent blog writing",
                    "SEO optimization",
                    "Custom topics and keywords",
                    "Sample blog analysis"
                ]
            )
            
            HomeComponents._render_feature_card(
                "🎨 Image Generation",
                "Generate stunning images for your content using AI.",
                [
                    "High-quality FLUX AI generation",
                    "Image editing capabilities",
                    "Multiple image formats",
                    "Professional quality output"
                ]
            )
        
        with col2:
            HomeComponents._render_feature_card(
                "💼 LinkedIn Posts",
                "Create engaging LinkedIn posts for professional networking.",
                [
                    "AI-powered content creation",
                    "Hashtag optimization",
                    "Professional tone",
                    "Engagement-focused writing"
                ]
            )
            
            HomeComponents._render_feature_card(
                "🎯 Upwork Proposals",
                "Generate winning Upwork proposals using GPT-4 and your portfolio.",
                [
                    "Tailored proposals based on job requirements",
                    "Uses your knowledge base for relevant project examples",
                    "Follows proven proposal writing strategies",
                    "Professional formatting and call-to-action",
                    "**NEW**: Upload template documents to fill instead of generating from scratch"
                ]
            )
            
            HomeComponents._render_feature_card(
                "📰 AI News",
                "Stay updated with the latest AI news and trends.",
                [
                    "Daily AI news compilation",
                    "Country-specific filtering",
                    "Trending topics analysis",
                    "Source verification"
                ]
            )
            
            HomeComponents._render_feature_card(
                "📚 Knowledge Base 🔐",
                "Upload and manage your project documents and portfolio files. **[Admin Only]**",
                [
                    "PDF, Word, Markdown, and text file support",
                    "Automatic content extraction and indexing",
                    "S3 cloud storage integration",
                    "Vector database for AI-powered search",
                    "🛡️ Requires administrator privileges"
                ]
            )
            
            HomeComponents._render_feature_card(
                "🤖 AI Portfolio Chat",
                "Chat with your uploaded documents using AI.",
                [
                    "Ask questions about your projects",
                    "Get intelligent responses from document content",
                    "Context-aware conversations",
                    "Source attribution and references"
                ]
            )
    
    @staticmethod
    def _render_feature_card(title: str, description: str, features: list):
        """Render a single feature card"""
        st.markdown(f"### {title}")
        st.markdown(description)
        if features:
            for feature in features:
                st.markdown(f"- {feature}")
        st.markdown("")  # Add spacing
    
    @staticmethod
    def render_home(api_base_url: str):
        """Main home page rendering method"""
        HomeComponents.render_welcome_section(api_base_url)
        HomeComponents.render_feature_cards()

