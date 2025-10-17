"""
Feature loader module for Streamlit application.
Handles dynamic loading of feature classes.
"""

import streamlit as st

# Simple import mapping
FEATURE_IMPORTS = {
    "BlogGenerationFeature": "features.blog_generation.blog_generation_feat.BlogGenerationFeature",
    "ImageGenerationFeature": "features.image_generation.image_generation_feat.ImageGenerationFeature",
    "LinkedInPostFeature": "features.linkedin_post.linkedin_post_feat.LinkedInPostFeature",
    "NewsFeature": "features.news.news_feat.NewsFeature",
    "KnowledgeBaseFeature": "features.knowledge_base.knowledge_base.KnowledgeBaseFeature",
    "ChatbotFeature": "features.chatbot.chatbot.ChatbotFeature",
    "UpworkProposalGeneratorFeature": "features.upwork_proposal_generator.upwork_proposal_generator.UpworkProposalGeneratorFeature",
}

class FeatureLoader:
    """Feature loader for dynamic import of feature classes"""
    
    @staticmethod
    def get_feature_class(feature_name: str):
        """Get feature class for API-based architecture"""
        try:
            if feature_name not in FEATURE_IMPORTS:
                raise ValueError(f"Unknown feature: {feature_name}")
            
            # Simple import
            module_path, class_name = FEATURE_IMPORTS[feature_name].rsplit('.', 1)
            module = __import__(module_path, fromlist=[class_name])
            return getattr(module, class_name)
                
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
    
    @staticmethod
    def get_available_features():
        """Get list of available feature names"""
        return list(FEATURE_IMPORTS.keys())
    
    @staticmethod
    def load_feature(feature_name: str):
        """Load and instantiate a feature"""
        FeatureClass = FeatureLoader.get_feature_class(feature_name)
        return FeatureClass()
