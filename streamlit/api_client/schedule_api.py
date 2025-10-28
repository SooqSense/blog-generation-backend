from typing import Optional, Dict, Any

from .base_client import APIClient


class ScheduleAPI:
    """API client for scheduling endpoints"""

    def __init__(self):
        self.client = APIClient()

    def schedule_post(self, **kwargs) -> Optional[Dict[str, Any]]:
        return self.client.post("schedule/schedule-linkedin-post/", data=kwargs)

    def get_scheduled_posts(self) -> Optional[Dict[str, Any]]:
        return self.client.get("schedule/scheduled-posts/")

    def cancel_post(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        return self.client.delete(f"schedule/cancel-scheduled-post/{schedule_id}/")

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        return self.client.get(endpoint, params=params)


