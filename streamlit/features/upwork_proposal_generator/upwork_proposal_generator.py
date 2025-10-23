import streamlit as st
from typing import Dict, Any, Optional, List

# Import modular components
from .components.proposal_generation_form import ProposalGenerationForm
from .components.proposal_history_manager import ProposalHistoryManager
from .components.proposal_editor import ProposalEditor
from .components.proposal_analytics import ProposalAnalytics
from .components.proposal_display import ProposalDisplay

# Import services and managers
from .services.proposal_service import UpworkProposalService
from .managers.state_manager import UpworkProposalStateManager

# Import API client
from api_client.api_client import upwork_api
# Import data management
from .upwork_data_management import UpworkDataManagement


class UpworkProposalGeneratorFeature:
    """Upwork Proposal Generator feature for Streamlit UI - Modular Architecture"""
    
    def __init__(self):
        """Initialize the feature with modular components."""
        self.api = upwork_api
        self.service = UpworkProposalService()
        self.state_manager = UpworkProposalStateManager()
        self.data_management = UpworkDataManagement(upwork_api)
        
        # Initialize session state
        self.state_manager.init_session_state()
        
        # Initialize components
        self._init_components()
    
    def _init_components(self):
        """Initialize all modular components with callbacks."""
        self.proposal_display = ProposalDisplay(self.api)
        
        self.proposal_generation_form = ProposalGenerationForm(
            self.api,
            on_generate_proposal=self._handle_generate_proposal
        )
        
        self.proposal_history_manager = ProposalHistoryManager(
            self.api,
            self.service,
            on_view_proposal=self._handle_view_proposal,
            on_edit_proposal=self._handle_edit_proposal,
            on_regenerate_proposal=self._handle_regenerate_proposal,
            on_delete_proposal=self._handle_delete_proposal
        )
        
        self.proposal_editor = ProposalEditor(
            self.api,
            on_update_proposal=self._handle_update_proposal,
            on_cancel_edit=self._handle_cancel_edit
        )
        
        self.proposal_analytics = ProposalAnalytics(self.api, self.service)
    
    def render(self):
        """Main render method"""
        st.title("💼 Upwork Proposals")
        st.markdown("Generate tailored proposals for Upwork projects using AI and your knowledge base.")
        
        # Create tabs for different features
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🚀 Generate Proposal", 
            "📚 Proposal History", 
            "✏️ Edit Proposal",
            "📊 Proposal Analytics",
            "🗂️ Data Management"
        ])
        
        with tab1:
            self.proposal_generation_form.render()
            
            # Check if we have a generated proposal to display below the form
            if 'generated_proposal' in st.session_state and st.session_state.generated_proposal:
                st.markdown("---")
                self.proposal_display.render(st.session_state.generated_proposal, is_direct=True)
        
        with tab2:
            self.proposal_history_manager.render()
        
        with tab3:
            self.proposal_editor.render()
        
        with tab4:
            self.proposal_analytics.render()
        
        with tab5:
            self.data_management.render_data_management_tab()
    
    # Callback handlers for component interactions
    def _handle_generate_proposal(self, **kwargs):
        """Handle proposal generation and display."""
        result = self.service.generate_proposal_direct(**kwargs)
        if result:
            # Store the result in session state for display outside the form
            st.session_state.generated_proposal = result
            st.rerun()
    
    def _handle_generate_direct(self, **kwargs):
        """Handle direct proposal generation."""
        result = self.service.generate_proposal_direct(**kwargs)
        if result:
            self.proposal_display.render(result, is_direct=True)
    
    def _handle_generate_saved(self, **kwargs):
        """Handle saved proposal generation."""
        success = self.service.create_proposal_saved(**kwargs)
        if success:
            self.service.refresh_proposals()
    
    def _handle_view_proposal(self, proposal_id: int):
        """Handle view proposal action."""
        self.state_manager.set_selected_proposal(proposal_id)
        st.rerun()
    
    def _handle_edit_proposal(self, proposal_id: int):
        """Handle edit proposal action."""
        self.state_manager.set_selected_proposal(proposal_id)
        self.state_manager.set_edit_mode(True)
        st.rerun()
    
    def _handle_regenerate_proposal(self, proposal_id: int):
        """Handle regenerate proposal action."""
        success = self.service.regenerate_proposal(proposal_id)
        if success:
            self.service.refresh_proposals()
    
    def _handle_delete_proposal(self, proposal_id: int):
        """Handle delete proposal action."""
        success = self.service.delete_proposal(proposal_id)
        if success:
            self.service.refresh_proposals()
    
    def _handle_update_proposal(self, proposal_id: int, data: Dict[str, Any]):
        """Handle update proposal action."""
        success = self.service.update_proposal(proposal_id, data)
        if success:
            self.state_manager.clear_selected_proposal()
            self.service.refresh_proposals()
    
    def _handle_cancel_edit(self):
        """Handle cancel edit action."""
        self.state_manager.clear_selected_proposal()
        st.rerun()
    
    def run(self):
        """Main run method for compatibility"""
        self.render()