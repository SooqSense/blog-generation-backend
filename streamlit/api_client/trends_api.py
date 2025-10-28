from typing import Optional, Dict, Any, List

from .base_client import APIClient
from base.config import get_api_endpoint


class TrendsAPI:
    """API client for trending topics endpoints"""

    def __init__(self):
        self.client = APIClient()

    def fetch_trending_topics(self, **kwargs) -> Optional[Dict[str, Any]]:
        endpoint = get_api_endpoint('trending_topics')
        return self.client.post(endpoint, data=kwargs)

    def list_trends(self) -> Optional[Dict[str, Any]]:
        endpoint = get_api_endpoint('ai_trends_list')
        return self.client.get(endpoint)

    def delete_trends(self, ids: List[int]) -> Optional[Dict[str, Any]]:
        endpoint = get_api_endpoint('ai_trends_delete')
        if len(ids) == 1:
            return self.client.delete(endpoint, data={'topic_id': ids[0]})
        else:
            return self.client.delete(endpoint, data={'topic_ids': ids})

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        return self.client.get(endpoint, params=params)


