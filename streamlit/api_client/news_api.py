from typing import Optional, Dict, Any, List

from .base_client import APIClient
from base.config import get_api_endpoint


class NewsAPI:
    """API client for news endpoints"""

    def __init__(self):
        self.client = APIClient()

    def generate_news(self, **kwargs) -> Optional[Dict[str, Any]]:
        endpoint = get_api_endpoint('ai_news')
        return self.client.post(endpoint, data=kwargs)

    def list_news(self) -> Optional[Dict[str, Any]]:
        endpoint = get_api_endpoint('ai_news_list')
        return self.client.get(endpoint)

    def delete_news(self, ids: List[int]) -> Optional[Dict[str, Any]]:
        endpoint = get_api_endpoint('ai_news_delete')
        if len(ids) == 1:
            return self.client.delete(endpoint, data={'news_id': ids[0]})
        else:
            return self.client.delete(endpoint, data={'news_ids': ids})

    def get_news(self, news_id: int) -> Optional[Dict[str, Any]]:
        endpoint = f"news/get/{news_id}/"
        return self.client.get(endpoint)

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        return self.client.get(endpoint, params=params)


