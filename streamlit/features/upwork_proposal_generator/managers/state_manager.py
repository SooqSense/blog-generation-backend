"""
State manager for Upwork proposal generator session state.
"""

import streamlit as st
from typing import Dict, Any, Optional, List


class UpworkProposalStateManager:
    """Manages session state for Upwork proposal generator."""
    
    @staticmethod
    def init_session_state():
        """Initialize session state variables."""
        if 'upwork_proposals' not in st.session_state:
            st.session_state.upwork_proposals = []
        if 'selected_proposal' not in st.session_state:
            st.session_state.selected_proposal = None
        if 'generation_mode' not in st.session_state:
            st.session_state.generation_mode = 'direct'  # 'direct' or 'saved'
        if 'edit_mode' not in st.session_state:
            st.session_state.edit_mode = False
    
    @staticmethod
    def set_selected_proposal(proposal_id: int):
        """Set the selected proposal ID."""
        st.session_state.selected_proposal = proposal_id
    
    @staticmethod
    def clear_selected_proposal():
        """Clear the selected proposal."""
        st.session_state.selected_proposal = None
    
    @staticmethod
    def set_edit_mode(enabled: bool):
        """Set edit mode."""
        st.session_state.edit_mode = enabled
    
    @staticmethod
    def get_selected_proposal() -> Optional[int]:
        """Get the selected proposal ID."""
        return st.session_state.selected_proposal
    
    @staticmethod
    def is_edit_mode() -> bool:
        """Check if in edit mode."""
        return st.session_state.edit_mode
    
    @staticmethod
    def update_proposals_list(proposals: List[Dict[str, Any]]):
        """Update the proposals list in session state."""
        st.session_state.upwork_proposals = proposals
    
    @staticmethod
    def get_proposals_list() -> List[Dict[str, Any]]:
        """Get the proposals list from session state."""
        return st.session_state.upwork_proposals
