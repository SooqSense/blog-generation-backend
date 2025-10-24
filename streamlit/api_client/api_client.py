import streamlit as st
import requests
import os
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import config for centralized endpoints
from base.config import API_ENDPOINTS, get_api_endpoint

class APIClient:
    """Centralized API client for making requests to Django backend"""
    
    def __init__(self):
        self.base_url = os.getenv("BACKEND_API_BASE_URL", "http://localhost:8000")
        self.timeout = 300  # Increased to 5 minutes for AI content generation
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers from Streamlit session state including selected organization"""
        headers = {"Content-Type": "application/json"}
        
        # Try to get auth token from session state
        if hasattr(st.session_state, 'token') and st.session_state.token:
            headers['Authorization'] = f'Bearer {st.session_state.token}'
        
        # Add selected organization header
        if hasattr(st.session_state, 'selected_organization') and st.session_state.selected_organization:
            headers['X-Selected-Organization'] = st.session_state.selected_organization
        
        return headers
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Make HTTP request with error handling"""
        # Check if endpoint is already a full URL
        if endpoint.startswith('http://') or endpoint.startswith('https://'):
            url = endpoint
        else:
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
    
    def _make_pdf_request(self, method: str, endpoint: str, **kwargs):
        """Make HTTP request for PDF downloads - returns raw response"""
        # Check if endpoint is already a full URL
        if endpoint.startswith('http://') or endpoint.startswith('https://'):
            url = endpoint
        else:
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
            return response
        except requests.exceptions.Timeout:
            st.error("⏰ Request timeout after 5 minutes. PDF generation can take time. Please try again.")
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
    
    def delete(self, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Make DELETE request"""
        return self._make_request('DELETE', endpoint, json=data)

# Blog Generation API
class BlogAPI:
    """API client for blog generation endpoints"""
    
    def __init__(self):
        self.client = APIClient()
    
    def generate_blog(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Generate a blog post"""
        endpoint = get_api_endpoint('blog_generation')
        return self.client.post(endpoint, data=kwargs)
    
    def list_blogs(self) -> Optional[Dict[str, Any]]:
        """List blog posts"""
        endpoint = get_api_endpoint('blog_list')
        return self.client.get(endpoint)
    
    def delete_blogs(self, ids: List[int]) -> Optional[Dict[str, Any]]:
        """Delete blog posts"""
        endpoint = get_api_endpoint('blog_delete')
        if len(ids) == 1:
            # Single deletion
            return self.client.delete(endpoint, data={'blog_id': ids[0]})
        else:
            # Bulk deletion
            return self.client.delete(endpoint, data={'blog_ids': ids})
    
    def get_blog(self, blog_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific blog post by ID"""
        endpoint = f"blogs/get/{blog_id}/"
        return self.client.get(endpoint)
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Make GET request - generic method for data management compatibility"""
        return self.client.get(endpoint, params=params)

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
    
    def list_images(self) -> Optional[Dict[str, Any]]:
        """List generated images"""
        return self.client.get("image-generation/images/")
    
    def delete_images(self, ids: List[int]) -> Optional[Dict[str, Any]]:
        """Delete images"""
        return self.client.delete("image-generation/delete/", data={'ids': ids})
    
    def get_image(self, image_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific image by ID"""
        # Note: Django doesn't have a get individual image endpoint
        # We'll need to get it from the list and filter
        response = self.client.get("image-generation/images/")
        if response and 'data' in response:
            for image in response['data']:
                if image.get('id') == image_id:
                    return {'success': True, 'data': image}
        return None
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Make GET request - generic method for data management compatibility"""
        return self.client.get(endpoint, params=params)

# LinkedIn API
class LinkedInAPI:
    """API client for LinkedIn endpoints"""
    
    def __init__(self):
        self.client = APIClient()
    
    def generate_post(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Generate LinkedIn post"""
        endpoint = get_api_endpoint('linkedin_post')
        return self.client.post(endpoint, data=kwargs)
    
    def post_content(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Post content to LinkedIn"""
        endpoint = get_api_endpoint('linkedin_post_direct')
        return self.client.post(endpoint, data=kwargs)
    
    def get_analytics(self) -> Optional[Dict[str, Any]]:
        """Get LinkedIn analytics"""
        endpoint = get_api_endpoint('linkedin_analytics')
        return self.client.get(endpoint)
    
    def validate_token(self) -> Optional[Dict[str, Any]]:
        """Validate LinkedIn token"""
        endpoint = get_api_endpoint('linkedin_token_validation')
        return self.client.get(endpoint)
    
    def list_posts(self) -> Optional[Dict[str, Any]]:
        """List LinkedIn posts"""
        endpoint = get_api_endpoint('linkedin_list')
        return self.client.get(endpoint)
    
    def delete_posts(self, ids: List[int]) -> Optional[Dict[str, Any]]:
        """Delete LinkedIn posts"""
        endpoint = get_api_endpoint('linkedin_delete')
        if len(ids) == 1:
            # Single deletion
            return self.client.delete(endpoint, data={'post_id': ids[0]})
        else:
            # Bulk deletion
            return self.client.delete(endpoint, data={'post_ids': ids})
    
    def get_post(self, post_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific LinkedIn post by ID"""
        endpoint = f"linkedin/get-post/{post_id}/"
        return self.client.get(endpoint)
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Make GET request - generic method for data management compatibility"""
        return self.client.get(endpoint, params=params)

# News API
class NewsAPI:
    """API client for news endpoints"""
    
    def __init__(self):
        self.client = APIClient()
    
    def generate_news(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Generate AI news"""
        endpoint = get_api_endpoint('ai_news')
        return self.client.post(endpoint, data=kwargs)
    
    def list_news(self) -> Optional[Dict[str, Any]]:
        """List AI news"""
        endpoint = get_api_endpoint('ai_news_list')
        return self.client.get(endpoint)
    
    def delete_news(self, ids: List[int]) -> Optional[Dict[str, Any]]:
        """Delete AI news"""
        endpoint = get_api_endpoint('ai_news_delete')
        if len(ids) == 1:
            # Single deletion
            return self.client.delete(endpoint, data={'news_id': ids[0]})
        else:
            # Bulk deletion
            return self.client.delete(endpoint, data={'news_ids': ids})
    
    def get_news(self, news_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific AI news by ID"""
        endpoint = f"news/get/{news_id}/"
        return self.client.get(endpoint)
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Make GET request - generic method for data management compatibility"""
        return self.client.get(endpoint, params=params)

# Knowledge Base API
class KnowledgeBaseAPI:
    """API client for knowledge base endpoints"""
    
    def __init__(self):
        self.client = APIClient()
    
    def list_directories(self) -> Optional[Dict[str, Any]]:
        """Get list of directories"""
        return self.client.get("knowledge-base/directories/")
    
    def create_directory(self, name: str, description: str = "") -> Optional[Dict[str, Any]]:
        """Create a new directory"""
        return self.client.post("knowledge-base/directories/create/", data={
            "name": name,
            "description": description
        })
    
    def delete_directory(self, directory_id: int) -> Optional[Dict[str, Any]]:
        """Delete a directory"""
        return self.client.delete(f"knowledge-base/directories/{directory_id}/delete/")
    
    def upload_document(self, file, directory_id: int, **kwargs) -> Optional[Dict[str, Any]]:
        """Upload document to knowledge base in a specific directory"""
        files = {'file': file}
        
        # Add directory_id as form data
        # We need to send it as multipart form data along with the file
        url = f"{self.client.base_url.rstrip('/')}/knowledge-base/upload-document/"
        headers = self.client._get_auth_headers()
        
        # Remove Content-Type to let requests set it for multipart
        if 'Content-Type' in headers:
            del headers['Content-Type']
        
        try:
            import requests
            response = requests.post(
                url=url,
                files=files,
                data={'directory_id': directory_id},  # Send directory_id as form data
                headers=headers,
                timeout=self.client.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            st.error("⏰ Request timeout. Please try again.")
            return None
        except requests.exceptions.ConnectionError:
            st.error("🔌 Connection error. Please check if the backend server is running.")
            return None
        except requests.exceptions.HTTPError as e:
            st.error(f"❌ API request failed: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            st.error(f"❌ Unexpected error: {str(e)}")
            return None
    
    def list_documents(self, directory_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """List documents, optionally filtered by directory"""
        params = {}
        if directory_id:
            params['directory_id'] = directory_id
        return self.client.get("knowledge-base/documents/", params=params)
    
    def delete_document(self, document_id: int) -> Optional[Dict[str, Any]]:
        """Delete a document (from DB, S3, and Pinecone)"""
        return self.client.delete(f"knowledge-base/documents/{document_id}/delete/")
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Make GET request - generic method for data management compatibility"""
        return self.client.get(endpoint, params=params)

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
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Make GET request - generic method for data management compatibility"""
        return self.client.get(endpoint, params=params)

# Upwork API
class UpworkAPI:
    """API client for Upwork proposal endpoints"""
    
    def __init__(self):
        self.client = APIClient()
    
    def list_proposals(self) -> Optional[Dict[str, Any]]:
        """List user's proposals"""
        return self.client.get("upwork/proposals/")
    
    def create_proposal(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Create new proposal generation request"""
        return self.client.post("upwork/proposals/", data=kwargs)
    
    def list_upwork_proposals(self) -> Optional[Dict[str, Any]]:
        """List Upwork proposals for data management"""
        endpoint = get_api_endpoint('upwork_list')
        return self.client.get(endpoint)
    
    def delete_upwork_proposals(self, ids: List[int]) -> Optional[Dict[str, Any]]:
        """Delete Upwork proposals"""
        endpoint = get_api_endpoint('upwork_delete')
        if len(ids) == 1:
            # Single deletion
            return self.client.delete(endpoint, data={'proposal_id': ids[0]})
        else:
            # Bulk deletion
            return self.client.delete(endpoint, data={'proposal_ids': ids})
    
    def get_upwork_proposal(self, proposal_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific Upwork proposal by ID"""
        endpoint = f"upwork/proposals/{proposal_id}/"
        return self.client.get(endpoint)
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Make GET request - generic method for data management compatibility"""
        return self.client.get(endpoint, params=params)

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
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Make GET request - generic method for data management compatibility"""
        return self.client.get(endpoint, params=params)

# Trends API
class TrendsAPI:
    """API client for trending topics endpoints"""
    
    def __init__(self):
        self.client = APIClient()
    
    def fetch_trending_topics(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Fetch trending topics"""
        endpoint = get_api_endpoint('trending_topics')
        return self.client.post(endpoint, data=kwargs)
    
    def list_trends(self) -> Optional[Dict[str, Any]]:
        """List AI trends"""
        endpoint = get_api_endpoint('ai_trends_list')
        return self.client.get(endpoint)
    
    def delete_trends(self, ids: List[int]) -> Optional[Dict[str, Any]]:
        """Delete AI trends"""
        endpoint = get_api_endpoint('ai_trends_delete')
        if len(ids) == 1:
            # Single deletion
            return self.client.delete(endpoint, data={'topic_id': ids[0]})
        else:
            # Bulk deletion
            return self.client.delete(endpoint, data={'topic_ids': ids})
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Make GET request - generic method for data management compatibility"""
        return self.client.get(endpoint, params=params)

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
