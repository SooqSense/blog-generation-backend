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
        # Default timeout: 5 minutes for regular requests
        # Blog generation can take 15-20 minutes, so we use a longer timeout
        self.timeout = int(os.getenv("API_TIMEOUT", "300"))  # Default 5 minutes
        self.long_timeout = int(os.getenv("API_LONG_TIMEOUT", "1800"))  # 30 minutes for long operations

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers from Streamlit session state including selected organization"""
        headers = {"Content-Type": "application/json"}

        if hasattr(st.session_state, 'token') and st.session_state.token:
            headers['Authorization'] = f'Bearer {st.session_state.token}'

        if hasattr(st.session_state, 'selected_organization') and st.session_state.selected_organization:
            headers['X-Selected-Organization'] = st.session_state.selected_organization

        return headers

    def _make_request(self, method: str, endpoint: str, timeout: Optional[int] = None, **kwargs) -> Optional[Dict[str, Any]]:
        """Make HTTP request with error handling
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            timeout: Optional timeout override (in seconds). If None, uses default timeout.
            **kwargs: Additional request parameters
        """
        if endpoint.startswith('http://') or endpoint.startswith('https://'):
            url = endpoint
        else:
            url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        headers = self._get_auth_headers()

        if 'headers' in kwargs:
            headers.update(kwargs.pop('headers'))

        # Use provided timeout or default
        request_timeout = timeout if timeout is not None else self.timeout

        # Log request details for SEO endpoint
        if 'generate-seo-html' in endpoint:
            print(f"🌐 [STREAMLIT] Making {method} request to: {url}")
            print(f"🌐 [STREAMLIT] Headers: {list(headers.keys())}")
            print(f"🌐 [STREAMLIT] Timeout: {request_timeout}s")
            print(f"🌐 [STREAMLIT] Request kwargs: {list(kwargs.keys())}")

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                timeout=request_timeout,
                **kwargs
            )
            
            # Log response for SEO endpoint
            if 'generate-seo-html' in endpoint:
                print(f"📡 [STREAMLIT] Response status code: {response.status_code}")
                print(f"📡 [STREAMLIT] Response headers: {dict(response.headers)}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            timeout_minutes = request_timeout // 60
            error_msg = f"⏰ Request timeout after {timeout_minutes} minutes. AI content generation can take time. Please try again."
            print(f"❌ [STREAMLIT] Request timeout: {url}")
            st.error(error_msg)
            return None
        except requests.exceptions.ConnectionError as e:
            error_msg = "🔌 Connection error. Please check if the backend server is running."
            print(f"❌ [STREAMLIT] Connection error: {url} - {str(e)}")
            st.error(error_msg)
            return None
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                st.error("🔐 Authentication failed. Please login again.")
                if hasattr(st.session_state, 'authenticated'):
                    st.session_state.authenticated = False
                st.rerun()
            else:
                error_msg = f"❌ API request failed: {e.response.status_code} - {e.response.text}"
                print(f"❌ [STREAMLIT] HTTP error: {url} - Status: {e.response.status_code}")
                print(f"❌ [STREAMLIT] Response text: {e.response.text[:500]}")
                st.error(error_msg)
            return None
        except Exception as e:
            error_msg = f"❌ Unexpected error: {str(e)}"
            print(f"❌ [STREAMLIT] Unexpected error: {url} - {type(e).__name__}: {str(e)}")
            st.error(error_msg)
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

    def get(self, endpoint: str, params: Optional[Dict] = None, timeout: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Make GET request with optional timeout override"""
        return self._make_request('GET', endpoint, params=params, timeout=timeout)

    def post(self, endpoint: str, data: Optional[Dict] = None, files: Optional[Dict] = None, timeout: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Make POST request with optional timeout override
        
        Args:
            endpoint: API endpoint
            data: Request data (JSON)
            files: Files to upload (multipart/form-data)
            timeout: Optional timeout override (in seconds). If None, uses default timeout.
        """
        if files:
            headers = self._get_auth_headers()
            if 'Content-Type' in headers:
                del headers['Content-Type']

            url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
            request_timeout = timeout if timeout is not None else self.timeout
            try:
                response = requests.post(
                    url=url,
                    files=files,
                    headers=headers,
                    timeout=request_timeout
                )
                response.raise_for_status()
                return response.json()
            except requests.exceptions.Timeout:
                timeout_minutes = request_timeout // 60
                st.error(f"⏰ Request timeout after {timeout_minutes} minutes. AI content generation can take time. Please try again.")
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
            return self._make_request('POST', endpoint, json=data, timeout=timeout)

    def put(self, endpoint: str, data: Optional[Dict] = None, timeout: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Make PUT request with optional timeout override"""
        return self._make_request('PUT', endpoint, json=data, timeout=timeout)

    def delete(self, endpoint: str, data: Optional[Dict] = None, timeout: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Make DELETE request with optional timeout override"""
        return self._make_request('DELETE', endpoint, json=data, timeout=timeout)


