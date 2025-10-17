"""
Proposal analytics dashboard component.
"""

import streamlit as st
from typing import Dict, Any, Optional, List
from .base_component import BaseComponent


class ProposalAnalytics(BaseComponent):
    """Component for proposal analytics dashboard."""
    
    def __init__(self, api_client, service):
        """Initialize with API client and service."""
        super().__init__(api_client)
        self.service = service
    
    def render(self):
        """Render the proposal analytics dashboard."""
        st.subheader("📊 Proposal Analytics")
        
        with self.show_spinner("📊 Loading analytics..."):
            try:
                proposals = self.service.list_proposals()
                
                if proposals is not None:
                    if proposals:
                        self._render_analytics_dashboard(proposals)
                    else:
                        st.info("No proposals found. Generate your first proposal to see analytics!")
                else:
                    self.show_warning("Unable to fetch proposals for analytics.")
                    
            except Exception as e:
                self.show_error(f"Error loading analytics: {str(e)}")
    
    def _render_analytics_dashboard(self, proposals: List[Dict[str, Any]]):
        """Render the analytics dashboard with proposal data."""
        # Calculate statistics
        stats = self._calculate_statistics(proposals)
        
        # Display metrics
        self._render_metrics(stats)
        
        # Recent proposals overview
        self._render_recent_proposals(proposals[:5])
    
    def _calculate_statistics(self, proposals: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate proposal statistics."""
        total_proposals = len(proposals)
        completed_proposals = len([p for p in proposals if p.get('status') == 'completed'])
        pending_proposals = len([p for p in proposals if p.get('status') == 'pending'])
        failed_proposals = len([p for p in proposals if p.get('status') == 'failed'])
        
        success_rate = (completed_proposals / total_proposals * 100) if total_proposals > 0 else 0
        
        return {
            'total': total_proposals,
            'completed': completed_proposals,
            'pending': pending_proposals,
            'failed': failed_proposals,
            'success_rate': success_rate
        }
    
    def _render_metrics(self, stats: Dict[str, int]):
        """Render key metrics."""
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Proposals", stats['total'])
        
        with col2:
            st.metric("Completed", stats['completed'])
        
        with col3:
            st.metric("Pending", stats['pending'])
        
        with col4:
            st.metric("Failed", stats['failed'])
        
        # Success rate
        st.metric("Success Rate", f"{stats['success_rate']:.1f}%")
    
    def _render_recent_proposals(self, recent_proposals: List[Dict[str, Any]]):
        """Render recent proposals overview."""
        st.subheader("📈 Recent Proposals")
        
        for proposal in recent_proposals:
            status = proposal.get('status', 'Unknown')
            status_icon = self.get_status_icon(status)
            
            st.write(f"{status_icon} **{proposal.get('title', 'Untitled')}** - {status}")
