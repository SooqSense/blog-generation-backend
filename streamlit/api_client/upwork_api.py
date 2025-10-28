from typing import Optional, Dict, Any, List

from .base_client import APIClient
from base.config import get_api_endpoint


class UpworkAPI:
    """API client for Upwork proposal endpoints"""

    def __init__(self):
        self.client = APIClient()

    def list_proposals(self) -> Optional[Dict[str, Any]]:
        endpoint = get_api_endpoint('upwork_list')
        return self.client.get(endpoint)

    def create_proposal(self, **kwargs) -> Optional[Dict[str, Any]]:
        endpoint = get_api_endpoint('upwork_proposals')
        return self.client.post(endpoint, data=kwargs)

    def list_upwork_proposals(self) -> Optional[Dict[str, Any]]:
        endpoint = get_api_endpoint('upwork_list')
        return self.client.get(endpoint)

    def delete_upwork_proposals(self, ids: List[int]) -> Optional[Dict[str, Any]]:
        endpoint = get_api_endpoint('upwork_delete')
        if len(ids) == 1:
            return self.client.delete(endpoint, data={'proposal_id': ids[0]})
        else:
            return self.client.delete(endpoint, data={'proposal_ids': ids})

    def get_upwork_proposal(self, proposal_id: int) -> Optional[Dict[str, Any]]:
        endpoint = get_api_endpoint('upwork_proposal_get')
        return self.client.get(f"{endpoint}{proposal_id}/")

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        return self.client.get(endpoint, params=params)


