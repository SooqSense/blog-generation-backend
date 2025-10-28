"""
Configuration module for Streamlit application.
Contains API endpoints, settings, and environment variables.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
API_BASE_URL = os.getenv("BACKEND_API_BASE_URL", "http://localhost:8000")

# WebSocket base URL mirrors API_BASE_URL protocol and host
WS_BASE_URL = (
    API_BASE_URL.replace('http://', 'ws://').replace('https://', 'wss://')
)

# Available API endpoints based on management_app structure
API_ENDPOINTS = {
    # Blog Generation
    'blog_generation': f"{API_BASE_URL}/blogs/generate-blog/",
    'blog_list': f"{API_BASE_URL}/blogs/list/",
    'blog_delete': f"{API_BASE_URL}/blogs/delete/",
    
    # Image Generation
    'image_generation': f"{API_BASE_URL}/image-generation/generate/",
    'image_editing': f"{API_BASE_URL}/image-generation/edit/",
    
    # LinkedIn Posts
    'linkedin_post': f"{API_BASE_URL}/linkedin/generate-linkedin-post/",
    'linkedin_post_direct': f"{API_BASE_URL}/linkedin/post-on-linkedin/",
    'linkedin_list': f"{API_BASE_URL}/linkedin/list-posts/",
    'linkedin_delete': f"{API_BASE_URL}/linkedin/delete-posts/",
    'linkedin_analytics': f"{API_BASE_URL}/linkedin/linkedin-analytics/",
    'linkedin_token_validation': f"{API_BASE_URL}/linkedin/validate-linkedin-token/",
    
    # LinkedIn Posting Content
    'linkedin_posting_content_list': f"{API_BASE_URL}/linkedin/list-posting-content/",
    'linkedin_posting_content_delete': f"{API_BASE_URL}/linkedin/delete-posting-content/",
    
    # Schedule LinkedIn Posts
    'schedule_linkedin_post': f"{API_BASE_URL}/schedule/schedule/",
    'scheduled_posts': f"{API_BASE_URL}/schedule/scheduled-posts/",
    'cancel_scheduled_post': f"{API_BASE_URL}/schedule/cancel/",
    
    # AI News
    'ai_news': f"{API_BASE_URL}/news/daily-ai-news/",
    'ai_news_list': f"{API_BASE_URL}/news/list/",
    'ai_news_delete': f"{API_BASE_URL}/news/delete/",
    
    # AI Trends
    'trending_topics': f"{API_BASE_URL}/trends/fetch-related-topics/",
    'ai_trends_list': f"{API_BASE_URL}/trends/list/",
    'ai_trends_delete': f"{API_BASE_URL}/trends/delete/",
    
    # Knowledge Base
    'knowledge_base_upload': f"{API_BASE_URL}/knowledge-base/upload/",
    'knowledge_base_documents': f"{API_BASE_URL}/knowledge-base/documents/",
    'knowledge_base_directories': f"{API_BASE_URL}/knowledge-base/directories/",
    'knowledge_base_create_directory': f"{API_BASE_URL}/knowledge-base/directories/create/",
    'knowledge_base_delete_directory': f"{API_BASE_URL}/knowledge-base/directories/",
    'knowledge_base_delete_document': f"{API_BASE_URL}/knowledge-base/documents/",
    
    # Chatbot
    'chatbot': f"{API_BASE_URL}/chat/chat/",
    'chatbot_websocket': f"{WS_BASE_URL}/ws/chat/",
    'chatbot_sessions': f"{API_BASE_URL}/chat/sessions/",
    
    # WebSocket Streaming (Centralized)
    'streaming_websocket': f"{WS_BASE_URL}/ws/stream/",
    'blog_websocket': f"{WS_BASE_URL}/ws/blog/",
    'linkedin_websocket': f"{WS_BASE_URL}/ws/linkedin/",
    'upwork_websocket': f"{WS_BASE_URL}/ws/upwork/",
    
    # Upwork Proposals
    'upwork_proposals': f"{API_BASE_URL}/upwork/proposals/",
    'upwork_proposal_get': f"{API_BASE_URL}/upwork/proposals/",
    'upwork_generate': f"{API_BASE_URL}/upwork/generate/",
    'upwork_list': f"{API_BASE_URL}/upwork/list/",
    'upwork_delete': f"{API_BASE_URL}/upwork/delete/",
    
    # Authentication
    'auth_verify': f"{API_BASE_URL}/auth/verify/",
    'auth_profile': f"{API_BASE_URL}/auth/profile/"
}

# Application settings
APP_CONFIG = {
    'version': '1.0.0',
    'title': 'AI Blog Generator',
    'subtitle': 'Professional Content Creation Platform - API Powered',
    'icon': '🤖',
    'layout': 'wide',
    'sidebar_state': 'expanded'
}

# Feature configuration
FEATURES = [
    "🏠 Home",
    "📝 Blog Generation", 
    "🎨 Image Generation",
    "💼 LinkedIn Posts",
    "🎯 Upwork Proposals",
    "📰 AI News",
    "📚 Knowledge Base",
    "🤖 AI Chat"
]

# Statistics configuration (for demo purposes)
DEMO_STATISTICS = {
    'blogs_generated': {"value": "1,234", "delta": "↗️ 12%"},
    'images_created': {"value": "5,678", "delta": "↗️ 8%"},
    'linkedin_posts': {"value": "890", "delta": "↗️ 15%"},
    'upwork_proposals': {"value": "234", "delta": "↗️ 28%"},
    'news_articles': {"value": "456", "delta": "↗️ 5%"},
    'documents_uploaded': {"value": "2,345", "delta": "↗️ 18%"},
    'chat_sessions': {"value": "1,567", "delta": "↗️ 22%"},
    'active_users': {"value": "321", "delta": "↗️ 10%"}
}

def get_api_endpoint(endpoint_name: str) -> str:
    """Get API endpoint URL by name"""
    return API_ENDPOINTS.get(endpoint_name, "")

def get_app_config(key: str) -> str:
    """Get application configuration value"""
    return APP_CONFIG.get(key, "")

def print_config_status():
    """Print configuration status"""
    print(f"🔧 Streamlit base configured for API-based architecture")
    print(f"✅ API endpoints configured for {len(API_ENDPOINTS)} services")
    print(f"🔗 API Base URL: {API_BASE_URL}")
    print(f"📱 App Version: {APP_CONFIG['version']}")
