from typing import Optional, Dict, Any

import requests

from .base_client import APIClient


class KnowledgeBaseAPI:
    """API client for knowledge base endpoints"""

    def __init__(self):
        self.client = APIClient()

    def list_directories(self) -> Optional[Dict[str, Any]]:
        return self.client.get("knowledge-base/directories/")

    def create_directory(self, name: str, description: str = "") -> Optional[Dict[str, Any]]:
        return self.client.post("knowledge-base/directories/create/", data={
            "name": name,
            "description": description
        })

    def delete_directory(self, directory_id: int) -> Optional[Dict[str, Any]]:
        return self.client.delete(f"knowledge-base/directories/{directory_id}/delete/")

    def upload_document(self, file, directory_id: int, **kwargs) -> Optional[Dict[str, Any]]:
        files = {'file': file}
        url = f"{self.client.base_url.rstrip('/')}/knowledge-base/upload-document/"
        headers = self.client._get_auth_headers()

        if 'Content-Type' in headers:
            del headers['Content-Type']

        try:
            response = requests.post(
                url=url,
                files=files,
                data={'directory_id': directory_id},
                headers=headers,
                timeout=self.client.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            import streamlit as st
            st.error("⏰ Request timeout. Please try again.")
            return None
        except requests.exceptions.ConnectionError:
            import streamlit as st
            st.error("🔌 Connection error. Please check if the backend server is running.")
            return None
        except requests.exceptions.HTTPError as e:
            import streamlit as st
            st.error(f"❌ API request failed: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            import streamlit as st
            st.error(f"❌ Unexpected error: {str(e)}")
            return None

    def list_documents(self, directory_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        params = {}
        if directory_id:
            params['directory_id'] = directory_id
        return self.client.get("knowledge-base/documents/", params=params)

    def delete_document(self, document_id: int) -> Optional[Dict[str, Any]]:
        return self.client.delete(f"knowledge-base/documents/{document_id}/delete/")

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        return self.client.get(endpoint, params=params)


