"""
Service layer for Upwork proposal operations.
"""

import streamlit as st
from typing import Dict, Any, Optional, List
from api_client.api_client import upwork_api


class UpworkProposalService:
    """Service class for handling Upwork proposal operations."""
    
    def __init__(self):
        """Initialize with API client."""
        self.api = upwork_api
    
    def generate_proposal_direct(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Generate proposal directly without saving to database."""
        with st.spinner("💼 Generating Upwork proposal... This may take up to 5 minutes for complex proposals."):
            try:
                response = self.api.generate_proposal_direct(**kwargs)
                
                if response and response.get("success") == True:
                    return response
                else:
                    error_msg = response.get("message", "Unknown error") if response else "No response from server"
                    st.error(f"❌ Proposal generation failed: {error_msg}")
                    return None
                    
            except Exception as e:
                st.error(f"❌ Error generating proposal: {str(e)}")
                return None
    
    def create_proposal_saved(self, **kwargs) -> bool:
        """Create proposal and save to database."""
        with st.spinner("💼 Creating and generating proposal... This may take up to 5 minutes for complex proposals."):
            try:
                response = self.api.create_proposal(**kwargs)
                
                if response:
                    st.success("✅ Proposal created successfully!")
                    st.info("🔄 Proposal is being generated in the background. Check the Proposal History tab to see the progress.")
                    return True
                else:
                    st.error("❌ Failed to create proposal")
                    return False
                    
            except Exception as e:
                st.error(f"❌ Error creating proposal: {str(e)}")
                return False
    
    def regenerate_proposal(self, proposal_id: int) -> bool:
        """Regenerate a proposal."""
        with st.spinner("🔄 Regenerating proposal..."):
            try:
                response = self.api.regenerate_proposal(proposal_id)
                
                if response and response.get("success"):
                    st.success("✅ Proposal regeneration started!")
                    st.info("Check the Proposal History tab to see the progress.")
                    return True
                else:
                    error_msg = response.get("message", "Unknown error") if response else "No response from server"
                    st.error(f"❌ Proposal regeneration failed: {error_msg}")
                    return False
                    
            except Exception as e:
                st.error(f"❌ Error regenerating proposal: {str(e)}")
                return False
    
    def update_proposal(self, proposal_id: int, data: Dict[str, Any]) -> bool:
        """Update a proposal."""
        with st.spinner("💾 Updating proposal..."):
            try:
                response = self.api.update_proposal(proposal_id, **data)
                
                if response:
                    st.success("✅ Proposal updated successfully!")
                    return True
                else:
                    st.error("❌ Failed to update proposal")
                    return False
                    
            except Exception as e:
                st.error(f"❌ Error updating proposal: {str(e)}")
                return False
    
    def delete_proposal(self, proposal_id: int) -> bool:
        """Delete a proposal."""
        try:
            response = self.api.delete_proposal(proposal_id)
            
            if response:
                st.success("✅ Proposal deleted successfully!")
                return True
            else:
                st.error("❌ Failed to delete proposal")
                return False
                
        except Exception as e:
            st.error(f"❌ Error deleting proposal: {str(e)}")
            return False
    
    def get_proposal(self, proposal_id: int) -> Optional[Dict[str, Any]]:
        """Get proposal details."""
        try:
            return self.api.get_proposal(proposal_id)
        except Exception as e:
            st.error(f"❌ Error loading proposal: {str(e)}")
            return None
    
    def list_proposals(self) -> Optional[List[Dict[str, Any]]]:
        """Get list of proposals."""
        try:
            response = self.api.list_proposals()
            if response:
                # Django ListCreateAPIView returns a list directly, not wrapped in "results"
                if isinstance(response, list):
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
