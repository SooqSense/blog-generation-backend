"""
Proposal history and management component.
"""

import streamlit as st
from typing import Dict, Any, Optional, List, Callable
from .base_component import BaseComponent


class ProposalHistoryManager(BaseComponent):
    """Component for managing proposal history."""
    
    def __init__(self, api_client, service, on_view_proposal: Callable, on_edit_proposal: Callable, 
                 on_regenerate_proposal: Callable, on_delete_proposal: Callable):
        """Initialize with API client, service, and callback functions."""
        super().__init__(api_client)
        self.service = service
        self.on_view_proposal = on_view_proposal
        self.on_edit_proposal = on_edit_proposal
        self.on_regenerate_proposal = on_regenerate_proposal
        self.on_delete_proposal = on_delete_proposal
    
    def render(self):
        """Render the proposal history manager."""
        st.subheader("📚 Proposal History")
        
        # Refresh button and filter
        col_refresh, col_filter = st.columns([1, 3])
        with col_refresh:
            if st.button("🔄 Refresh", use_container_width=True):
                self._refresh_proposals()
        
        with col_filter:
            status_filter = st.selectbox(
                "Filter by Status:",
                ["All", "Pending", "Generating", "Completed", "Failed"],
                key="status_filter"
            )
        
        with self.show_spinner("📚 Loading proposals..."):
            try:
                # Use the service layer instead of direct API call
                proposals = self.service.list_proposals()
                
                if proposals is not None:
                    # Filter proposals by status
                    if status_filter != "All":
                        proposals = [p for p in proposals if p.get('status', '').lower() == status_filter.lower()]
                    
                    if proposals:
                        self.show_success(f"Found {len(proposals)} proposals")
                        
                        for proposal in proposals:
                            self._render_proposal_card(proposal)
                    else:
                        st.info("No proposals found. Generate your first proposal!")
                else:
                    self.show_warning("Unable to fetch proposals.")
                    
            except Exception as e:
                self.show_error(f"Error fetching proposals: {str(e)}")
    
    def _render_proposal_card(self, proposal: Dict[str, Any]):
        """Render individual proposal card with actions."""
        status = proposal.get('status', 'Unknown')
        status_icon = self.get_status_icon(status)
        
        with st.expander(f"{status_icon} {proposal.get('title', 'Untitled')} - {self.format_date(proposal.get('created_at', 'Unknown date'))}"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                self._render_proposal_info(proposal)
            
            with col2:
                self._render_proposal_actions(proposal)
    
    def _render_proposal_info(self, proposal: Dict[str, Any]):
        """Render proposal information."""
        st.write(f"**Client:** {proposal.get('client_name', 'N/A')}")
        st.write(f"**Company:** {proposal.get('company_name', 'N/A')}")
        st.write(f"**Status:** {proposal.get('status', 'N/A')}")
        st.write(f"**Created:** {self.format_date(proposal.get('created_at', 'N/A'))}")
        
        if proposal.get('proposal_content'):
            content_preview = proposal['proposal_content'][:300] + "..." if len(proposal['proposal_content']) > 300 else proposal['proposal_content']
            st.markdown("**Content Preview:**")
            st.text(content_preview)
    
    def _render_proposal_actions(self, proposal: Dict[str, Any]):
        """Render proposal action buttons."""
        proposal_id = proposal.get('id')
        status = proposal.get('status', '').lower()
        
        if proposal_id:
            # Action buttons
            if st.button("👁️ View Full", key=f"view_{proposal_id}"):
                self.on_view_proposal(proposal_id)
            
            if st.button("✏️ Edit", key=f"edit_{proposal_id}"):
                self.on_edit_proposal(proposal_id)
            
            if status == 'completed':
                if st.button("🔄 Regenerate", key=f"regen_{proposal_id}"):
                    self.on_regenerate_proposal(proposal_id)
            
            if st.button("🗑️ Delete", key=f"delete_{proposal_id}"):
                self.on_delete_proposal(proposal_id)
    
    def _refresh_proposals(self):
        """Refresh proposals list."""
        try:
            proposals = self.service.list_proposals()
            if proposals is not None:
                st.session_state.upwork_proposals = proposals
        except Exception as e:
            self.show_error(f"Error refreshing proposals: {str(e)}")
