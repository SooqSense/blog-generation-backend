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
