"""
Feature router module for Streamlit application.
Handles routing between different features and their execution.
"""

import streamlit as st
from base.auth import AuthHandler
from base.feature_loader import FeatureLoader

class FeatureRouter:
    """Feature router for handling navigation between features"""
    
    def __init__(self, auth_handler: AuthHandler):
        self.auth_handler = auth_handler
        self.feature_loader = FeatureLoader()
    
    def route_feature(self, feature_name: str):
        """Route to the appropriate feature based on selection"""
        if feature_name == "🏠 Home":
            return "home"
        
        # Map feature names to their classes
        feature_mapping = {
            "📝 Blog Generation": ("BlogGenerationFeature", "Blog Generation"),
            "🎨 Image Generation": ("ImageGenerationFeature", "Image Generation"),
            "💼 LinkedIn Posts": ("LinkedInPostFeature", "LinkedIn Posts"),
            "🎯 Upwork Proposals": ("UpworkProposalGeneratorFeature", "Upwork Proposals"),
            "📰 AI News": ("NewsFeature", "AI News"),
            "📚 Knowledge Base": ("KnowledgeBaseFeature", "Knowledge Base"),
            "🤖 AI Chat": ("ChatbotFeature", "AI Chat"),
        }
        
        if feature_name in feature_mapping:
            feature_class_name, auth_feature_name = feature_mapping[feature_name]
            
            # Check authentication
            self.auth_handler.check_auth_for_feature(auth_feature_name)
            
            # Load and render feature
            feature_instance = self.feature_loader.load_feature(feature_class_name)
            
            # Handle special case for UpworkProposalGeneratorFeature
            if feature_class_name == "UpworkProposalGeneratorFeature":
                feature_instance.run()  # Uses run() method instead of render()
            else:
                feature_instance.render()
            
            return "feature"
        
        return "unknown"
    
    def get_feature_info(self, feature_name: str):
        """Get information about a feature"""
        feature_info = {
            "🏠 Home": {
                "description": "Welcome page with overview of all features",
                "requires_auth": False
            },
            "📝 Blog Generation": {
                "description": "Create professional blog posts with AI",
                "requires_auth": True
            },
            "🎨 Image Generation": {
                "description": "Generate and edit images using AI",
                "requires_auth": True
            },
            "💼 LinkedIn Posts": {
                "description": "Create and manage LinkedIn content",
                "requires_auth": True
            },
            "🎯 Upwork Proposals": {
                "description": "Generate tailored Upwork proposals",
                "requires_auth": True
            },
            "📰 AI News": {
                "description": "Generate AI news summaries",
                "requires_auth": True
            },
            "📚 Knowledge Base": {
                "description": "Upload and manage documents",
                "requires_auth": True
            },
            "🤖 AI Chat": {
                "description": "Chat with your documents using AI",
                "requires_auth": True
            }
        }
        
        return feature_info.get(feature_name, {"description": "Unknown feature", "requires_auth": False})
