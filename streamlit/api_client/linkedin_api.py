from typing import Optional, Dict, Any, List

from .base_client import APIClient
from base.config import get_api_endpoint


class LinkedInAPI:
    """API client for LinkedIn endpoints"""

    def __init__(self):
        self.client = APIClient()

    def generate_post(self, **kwargs) -> Optional[Dict[str, Any]]:
        endpoint = get_api_endpoint('linkedin_post')
        return self.client.post(endpoint, data=kwargs)

    def post_content(self, **kwargs) -> Optional[Dict[str, Any]]:
        endpoint = get_api_endpoint('linkedin_post_direct')
        return self.client.post(endpoint, data=kwargs)

    def get_analytics(self) -> Optional[Dict[str, Any]]:
        endpoint = get_api_endpoint('linkedin_analytics')
        return self.client.get(endpoint)

    def validate_token(self) -> Optional[Dict[str, Any]]:
        endpoint = get_api_endpoint('linkedin_token_validation')
        return self.client.get(endpoint)

    def list_posts(self) -> Optional[Dict[str, Any]]:
        endpoint = get_api_endpoint('linkedin_list')
        return self.client.get(endpoint)

    def delete_posts(self, ids: List[int]) -> Optional[Dict[str, Any]]:
        endpoint = get_api_endpoint('linkedin_delete')
        if len(ids) == 1:
            return self.client.delete(endpoint, data={'post_id': ids[0]})
        else:
            return self.client.delete(endpoint, data={'post_ids': ids})

    def get_post(self, post_id: int) -> Optional[Dict[str, Any]]:
        endpoint = f"linkedin/get-post/{post_id}/"
        return self.client.get(endpoint)

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        return self.client.get(endpoint, params=params)


