import os
from typing import Optional, Dict, Any

import requests
import streamlit as st
from dotenv import load_dotenv


load_dotenv()


class APIClient:
    """Centralized API client for making requests to Django backend"""

    def __init__(self):
        self.base_url = os.getenv("BACKEND_API_BASE_URL", "http://localhost:8000")
        self.timeout = 300

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers from Streamlit session state including selected organization"""
        headers = {"Content-Type": "application/json"}

        if hasattr(st.session_state, 'token') and st.session_state.token:
            headers['Authorization'] = f'Bearer {st.session_state.token}'

        if hasattr(st.session_state, 'selected_organization') and st.session_state.selected_organization:
            headers['X-Selected-Organization'] = st.session_state.selected_organization

        return headers

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Make HTTP request with error handling"""
        if endpoint.startswith('http://') or endpoint.startswith('https://'):
            url = endpoint
        else:
            url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        headers = self._get_auth_headers()

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
            st.error("⏰ Request timeout after 5 minutes. Please try again.")
            return None
        except requests.exceptions.ConnectionError:
            st.error("🔌 Connection error. Please check if the backend server is running.")
            return None
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                st.error("🔐 Authentication failed. Please login again.")
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
        if endpoint.startswith('http://') or endpoint.startswith('https://'):
            url = endpoint
        else:
            url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        headers = self._get_auth_headers()

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
            st.error("⏰ Request timeout. Please try again.")
            return None
        except requests.exceptions.ConnectionError:
            st.error("🔌 Connection error. Please check if the backend server is running.")
            return None
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                st.error("🔐 Authentication failed. Please login again.")
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
        return self._make_request('GET', endpoint, params=params)

    def post(self, endpoint: str, data: Optional[Dict] = None, files: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        if files:
            headers = self._get_auth_headers()
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
        return self._make_request('PUT', endpoint, json=data)

    def delete(self, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        return self._make_request('DELETE', endpoint, json=data)


