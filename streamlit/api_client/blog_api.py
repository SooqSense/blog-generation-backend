from typing import Optional, Dict, Any, List

from .base_client import APIClient
from base.config import get_api_endpoint


class BlogAPI:
    """API client for blog generation endpoints"""

    def __init__(self):
        self.client = APIClient()
        # Blog generation can take 15-30 minutes, so use long timeout
        self.blog_timeout = self.client.long_timeout  # 30 minutes default

    def generate_blog(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Generate blog via standard REST API
        
        Uses extended timeout (30 minutes) since blog generation can take a long time.
        """
        endpoint = get_api_endpoint('blog_generation')
        return self.client.post(endpoint, data=kwargs, timeout=self.blog_timeout)

    def list_blogs(self) -> Optional[Dict[str, Any]]:
        """List all blogs"""
        endpoint = get_api_endpoint('blog_list')
        return self.client.get(endpoint)

    def delete_blogs(self, ids: List[int]) -> Optional[Dict[str, Any]]:
        """Delete one or more blogs"""
        endpoint = get_api_endpoint('blog_delete')
        if len(ids) == 1:
            return self.client.delete(endpoint, data={'blog_id': ids[0]})
        else:
            return self.client.delete(endpoint, data={'blog_ids': ids})

    def get_blog(self, blog_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific blog"""
        endpoint = f"blogs/get/{blog_id}/"
        return self.client.get(endpoint)

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Generic GET request"""
        return self.client.get(endpoint, params=params)

    def generate_seo_html(self, blog_id: int) -> Optional[Dict[str, Any]]:
        """Generate SEO-optimized HTML content for a blog post
        
        Args:
            blog_id: ID of the blog post to optimize
            
        Returns:
            SEO optimization results including HTML content and metadata
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Use the endpoint from config or construct it
        base_endpoint = get_api_endpoint('blog_seo_html')
        if base_endpoint:
            endpoint = f"{base_endpoint.rstrip('/')}/{blog_id}/"
        else:
            # Fallback to direct construction
            endpoint = f"blogs/generate-seo-html/{blog_id}/"
        
        print(f"🔗 [STREAMLIT] SEO endpoint: {endpoint}")
        print(f"📝 [STREAMLIT] Blog ID: {blog_id}")
        logger.info(f"🔗 SEO endpoint: {endpoint}")
        logger.info(f"📝 Blog ID: {blog_id}")
        
        # SEO generation can take 5-10 minutes, use extended timeout
        # POST request with empty data (blog_id is in URL)
        print(f"📤 [STREAMLIT] Sending SEO generation request to {endpoint} (timeout: {self.blog_timeout}s)")
        response = self.client.post(endpoint, data={}, timeout=self.blog_timeout)
        print(f"📥 [STREAMLIT] SEO API response received: {response is not None}")
        logger.info(f"📥 SEO API response received: {response is not None}")
        if response:
            print(f"📊 [STREAMLIT] Response status: {response.get('status', 'N/A')}")
            logger.info(f"📊 Response status: {response.get('status', 'N/A')}")
        return response
