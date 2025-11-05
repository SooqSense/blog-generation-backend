from typing import Optional, Dict, Any

from .base_client import APIClient


class ChatbotAPI:
    """API client for chatbot endpoints"""

    def __init__(self):
        self.client = APIClient()

    def ask_question(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Ask a question via standard REST API"""
        return self.client.post("chat/chat/", data=kwargs)
