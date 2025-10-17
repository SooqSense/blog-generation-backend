import streamlit as st
import requests
import os
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class APIClient:
    """Centralized API client for making requests to Django backend"""
    
    def __init__(self):
        self.base_url = os.getenv("BACKEND_API_BASE_URL", "http://localhost:8000")
        self.timeout = 300  # Increased to 5 minutes for AI content generation
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers from Streamlit session state"""
        headers = {"Content-Type": "application/json"}
        
        # Try to get auth token from session state
        if hasattr(st.session_state, 'token') and st.session_state.token:
            headers['Authorization'] = f'Bearer {st.session_state.token}'
        
        return headers
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Make HTTP request with error handling"""
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = self._get_auth_headers()
        
        # Update headers if provided
        if 'headers' in kwargs:
            headers.update(kwargs.pop('headers'))
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                timeout=self.timeout,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            st.error("⏰ Request timeout after 5 minutes. AI content generation can take time. Please try again.")
            return None
        except requests.exceptions.ConnectionError:
            st.error("🔌 Connection error. Please check if the backend server is running.")
            return None
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                st.error("🔐 Authentication failed. Please login again.")
                # Clear session state
                if hasattr(st.session_state, 'authenticated'):
                    st.session_state.authenticated = False
                st.rerun()
            else:
                st.error(f"❌ API request failed: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            st.error(f"❌ Unexpected error: {str(e)}")
            return None
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Make GET request"""
        return self._make_request('GET', endpoint, params=params)
    
    def post(self, endpoint: str, data: Optional[Dict] = None, files: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Make POST request"""
        if files:
            # For file uploads, use requests directly to ensure proper multipart handling
            headers = self._get_auth_headers()
            # Remove Content-Type to let requests set it for multipart
            if 'Content-Type' in headers:
                del headers['Content-Type']
            
            url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
            try:
                response = requests.post(
                    url=url,
                    files=files,
                    headers=headers,
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response.json()
            except requests.exceptions.Timeout:
                st.error("⏰ Request timeout after 5 minutes. AI content generation can take time. Please try again.")
                return None
            except requests.exceptions.ConnectionError:
                st.error("🔌 Connection error. Please check if the backend server is running.")
                return None
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 401:
                    st.error("🔐 Authentication failed. Please login again.")
                    # Clear session state
                    if hasattr(st.session_state, 'authenticated'):
                        st.session_state.authenticated = False
                    st.rerun()
                else:
                    st.error(f"❌ API request failed: {e.response.status_code} - {e.response.text}")
                return None
            except Exception as e:
                st.error(f"❌ Unexpected error: {str(e)}")
                return None
        else:
            return self._make_request('POST', endpoint, json=data)
    
    def put(self, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Make PUT request"""
        return self._make_request('PUT', endpoint, json=data)
    
    def delete(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """Make DELETE request"""
        return self._make_request('DELETE', endpoint)

# Blog Generation API
class BlogAPI:
    """API client for blog generation endpoints"""
    
    def __init__(self):
        self.client = APIClient()
    
    def generate_blog(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Generate a blog post"""
        return self.client.post("blogs/generate-blog/", data=kwargs)

# Image Generation API
class ImageAPI:
    """API client for image generation endpoints"""
    
    def __init__(self):
        self.client = APIClient()
    
    def generate_image(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Generate images"""
        return self.client.post("image-generation/generate-image/", data=kwargs)
    
    def edit_image(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Edit an image"""
        return self.client.post("image-generation/edit-image/", data=kwargs)

# LinkedIn API
class LinkedInAPI:
    """API client for LinkedIn endpoints"""
    
    def __init__(self):
        self.client = APIClient()
    
    def generate_post(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Generate LinkedIn post"""
        return self.client.post("linkedin/generate-linkedin-post/", data=kwargs)
    
    def post_content(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Post content to LinkedIn"""
        return self.client.post("linkedin/post-on-linkedin/", data=kwargs)
    
    def get_analytics(self) -> Optional[Dict[str, Any]]:
        """Get LinkedIn analytics"""
        return self.client.get("linkedin/linkedin-analytics/")
    
    def validate_token(self) -> Optional[Dict[str, Any]]:
        """Validate LinkedIn token"""
        return self.client.get("linkedin/validate-linkedin-token/")

# News API
class NewsAPI:
    """API client for news endpoints"""
    
    def __init__(self):
        self.client = APIClient()
    
    def generate_news(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Generate AI news"""
        return self.client.post("news/daily-ai-news/", data=kwargs)

# Knowledge Base API
class KnowledgeBaseAPI:
    """API client for knowledge base endpoints"""
    
    def __init__(self):
        self.client = APIClient()
    
    def upload_document(self, file, **kwargs) -> Optional[Dict[str, Any]]:
        """Upload document to knowledge base"""
        files = {'file': file}
        # For file uploads, don't pass any additional data to avoid content-type conflicts
        return self.client.post("knowledge-base/upload-pdf/", files=files)

# Chatbot API
class ChatbotAPI:
    """API client for chatbot endpoints"""
    
    def __init__(self):
        self.client = APIClient()
    
    def ask_question(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Ask question to chatbot"""
        return self.client.post("chat/chat/", data=kwargs)
    
    def get_sessions(self) -> Optional[Dict[str, Any]]:
        """Get user's chat sessions"""
        return self.client.get("chat/sessions/")

# Upwork API
class UpworkAPI:
    """API client for Upwork proposal endpoints"""
    
    def __init__(self):
        self.client = APIClient()
    
    def generate_proposal_direct(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Generate Upwork proposal directly (without saving to database)"""
        return self.client.post("upwork/generate/", data=kwargs)
    
    def list_proposals(self) -> Optional[Dict[str, Any]]:
        """List user's proposals"""
        return self.client.get("upwork/proposals/")
    
    def create_proposal(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Create new proposal generation request"""
        return self.client.post("upwork/proposals/", data=kwargs)
    
    def get_proposal(self, proposal_id: int) -> Optional[Dict[str, Any]]:
        """Get proposal details"""
        return self.client.get(f"upwork/proposals/{proposal_id}/")
    
    def update_proposal(self, proposal_id: int, **kwargs) -> Optional[Dict[str, Any]]:
        """Update proposal"""
        return self.client.put(f"upwork/proposals/{proposal_id}/", data=kwargs)
    
    def patch_proposal(self, proposal_id: int, **kwargs) -> Optional[Dict[str, Any]]:
        """Partially update proposal"""
        return self.client.put(f"upwork/proposals/{proposal_id}/", data=kwargs)
    
    def delete_proposal(self, proposal_id: int) -> Optional[Dict[str, Any]]:
        """Delete proposal"""
        return self.client.delete(f"upwork/proposals/{proposal_id}/")
    
    def regenerate_proposal(self, proposal_id: int) -> Optional[Dict[str, Any]]:
        """Regenerate existing proposal"""
        return self.client.post(f"upwork/proposals/{proposal_id}/regenerate/")
    
    def get_proposal_status(self, proposal_id: int) -> Optional[Dict[str, Any]]:
        """Get proposal status"""
        return self.client.get(f"upwork/proposals/{proposal_id}/status/")

# Schedule API
class ScheduleAPI:
    """API client for scheduling endpoints"""
    
    def __init__(self):
        self.client = APIClient()
    
    def schedule_post(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Schedule LinkedIn post"""
        return self.client.post("schedule/schedule-linkedin-post/", data=kwargs)
    
    def get_scheduled_posts(self) -> Optional[Dict[str, Any]]:
        """Get scheduled posts"""
        return self.client.get("schedule/scheduled-posts/")
    
    def cancel_post(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        """Cancel scheduled post"""
        return self.client.delete(f"schedule/cancel-scheduled-post/{schedule_id}/")

# Trends API
class TrendsAPI:
    """API client for trending topics endpoints"""
    
    def __init__(self):
        self.client = APIClient()
    
    def fetch_trending_topics(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Fetch trending topics"""
        return self.client.post("trends/fetch-related-topics/", data=kwargs)

# Initialize API clients
blog_api = BlogAPI()
image_api = ImageAPI()
linkedin_api = LinkedInAPI()
news_api = NewsAPI()
knowledge_base_api = KnowledgeBaseAPI()
chatbot_api = ChatbotAPI()
upwork_api = UpworkAPI()
schedule_api = ScheduleAPI()
trends_api = TrendsAPI()
