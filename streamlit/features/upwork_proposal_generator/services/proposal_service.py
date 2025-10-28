"""
Service layer for Upwork proposal operations.
"""

import streamlit as st
from typing import Dict, Any, Optional, List
from api_client import upwork_api


class UpworkProposalService:
    """Service class for handling Upwork proposal operations."""
    
    def __init__(self):
        """Initialize with API client."""
        self.api = upwork_api
    
    
    def create_proposal_saved(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Create proposal and return created record (synchronous backend)."""
        with st.spinner("💼 Generating proposal..."):
            try:
                response = self.api.create_proposal(**kwargs)
                if response:
                    st.success("✅ Proposal created successfully!")
                    return response  # Backend returns the full proposal payload
                st.error("❌ Failed to create proposal")
                return None
            except Exception as e:
                st.error(f"❌ Error creating proposal: {str(e)}")
                return None
    
    
    
    
    
    def list_proposals(self) -> Optional[List[Dict[str, Any]]]:
        """Get list of proposals."""
        try:
            response = self.api.list_proposals()
            if response:
                # Handle the new API response format from function-based views
                if isinstance(response, dict) and "data" in response:
                    return response["data"]
                elif isinstance(response, list):
                    return response
                elif isinstance(response, dict) and "results" in response:
                    return response["results"]
                else:
                    # Handle unexpected format
                    st.warning("API returned unexpected response format")
                    return []
            else:
                # If no response, show error
                st.error("No response from API")
                return None
        except Exception as e:
            st.error(f"❌ Error fetching proposals: {str(e)}")
            return None
    
    def refresh_proposals(self):
        """Refresh proposals list in session state."""
        try:
            response = self.api.list_proposals()
            if response:
                # Django ListCreateAPIView returns a list directly, not wrapped in "results"
                if isinstance(response, list):
                    st.session_state.upwork_proposals = response
                elif isinstance(response, dict) and "results" in response:
                    st.session_state.upwork_proposals = response["results"]
                else:
                    st.session_state.upwork_proposals = []
        except Exception as e:
            st.error(f"Error refreshing proposals: {str(e)}")
