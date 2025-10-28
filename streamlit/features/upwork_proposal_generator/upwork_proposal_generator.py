import streamlit as st
from typing import Dict, Any, Optional, List

# Import modular components
from .components.proposal_generation_form import ProposalGenerationForm
from .components.proposal_display import ProposalDisplay

# Import services
from .services.proposal_service import UpworkProposalService

# Import API client
from api_client import upwork_api
# Import data management
from .upwork_data_management import UpworkDataManagement


class UpworkProposalGeneratorFeature:
    """Upwork Proposal Generator feature for Streamlit UI - Modular Architecture"""
    
    def __init__(self):
        """Initialize the feature with modular components."""
        self.api = upwork_api
        self.service = UpworkProposalService()
        self.data_management = UpworkDataManagement(upwork_api)
        
        # Initialize components
        self._init_components()
    
    def _init_components(self):
        """Initialize all modular components with callbacks."""
        self.proposal_display = ProposalDisplay(self.api)
        
        self.proposal_generation_form = ProposalGenerationForm(
            self.api,
            on_generate_proposal=self._handle_generate_proposal
        )
        
        # Removed: proposal_history_manager, proposal_editor, proposal_analytics
    
    def render(self):
        """Main render method"""
        st.title("💼 Upwork Proposals")
        st.markdown("Generate tailored proposals for Upwork projects using AI and your knowledge base.")
        
        # Create tabs for different features - only Generate Proposal and Data Management
        tab1, tab2 = st.tabs([
            "🚀 Generate Proposal", 
            "🗂️ Data Management"
        ])
        
        with tab1:
            self.proposal_generation_form.render()
            
            # Check if we have a generated proposal to display below the form
            self._render_generated_proposal()
        
        with tab2:
            self.data_management.render_data_management_tab()
    
    def _render_generated_proposal(self):
        """Render the generated proposal section below the form"""
        if 'generated_proposal' not in st.session_state or not st.session_state.generated_proposal:
            return
        
        st.markdown("---")
        st.markdown("### 📝 Generated Proposal")
        
        # Get the proposal data
        proposal = st.session_state.generated_proposal
        
        # Display immediately (backend is synchronous now)
        if proposal.get('proposal_content'):
            self.proposal_display.render(proposal, is_direct=True)
        elif proposal.get('status') == 'failed':
            st.error(f"❌ Proposal generation failed: {proposal.get('error_message', 'Unknown error')}")
        else:
            st.info("ℹ️ Proposal created. Content not present in response.")
            with st.expander("Raw response"):
                st.json(proposal)
    
    # Callback handlers for component interactions
    def _handle_generate_proposal(self, **kwargs):
        """Handle proposal generation and display (synchronous)."""
        result = self.service.create_proposal_saved(**kwargs)
        if result:
            if 'generated_proposal' not in st.session_state:
                st.session_state.generated_proposal = None
            # Backend returns created proposal; some endpoints wrap as {'status':..., 'data': {...}}
            proposal = result.get('data') if isinstance(result, dict) and result.get('data') else result
            st.session_state.generated_proposal = proposal
            st.success("✅ Proposal generated!")
        else:
            st.error("❌ Failed to create proposal. Please try again.")
    
    def run(self):
        """Main run method for compatibility"""
        self.render()