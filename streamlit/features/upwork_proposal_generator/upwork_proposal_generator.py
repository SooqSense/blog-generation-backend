import streamlit as st
from typing import Dict, Any, Optional, List

# Import modular components
from .components.proposal_generation_form import ProposalGenerationForm
from .components.proposal_display import ProposalDisplay

# Import services
from .services.proposal_service import UpworkProposalService

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
            if 'generated_proposal' in st.session_state and st.session_state.generated_proposal:
                st.markdown("---")
                st.markdown("### 📝 Generated Proposal")
                
                # Check if proposal is still generating
                proposal = st.session_state.generated_proposal
                if proposal.get('status') == 'generating':
                    st.info("🔄 Proposal is being generated. Please wait...")
                    
                    # Add a refresh button to check status
                    if st.button("🔄 Check Status", key="check_proposal_status"):
                        # Refresh the proposal data
                        proposals = self.service.list_proposals()
                        if proposals and len(proposals) > 0:
                            latest_proposal = proposals[0]
                            st.session_state.generated_proposal = latest_proposal
                            st.rerun()
                    
                    # Auto-refresh every 3 seconds if waiting for generation
                    if st.session_state.get('waiting_for_generation', False):
                        import time
                        time.sleep(3)
                        st.rerun()
                        
                elif proposal.get('status') == 'completed':
                    self.proposal_display.render(proposal, is_direct=True)
                    # Clear the waiting flag
                    if 'waiting_for_generation' in st.session_state:
                        del st.session_state.waiting_for_generation
                        
                elif proposal.get('status') == 'failed':
                    st.error(f"❌ Proposal generation failed: {proposal.get('error_message', 'Unknown error')}")
                    # Clear the waiting flag
                    if 'waiting_for_generation' in st.session_state:
                        del st.session_state.waiting_for_generation
                else:
                    st.info("⏳ Proposal is being processed...")
                    st.rerun()
        
        with tab2:
            self.data_management.render_data_management_tab()
    
    # Callback handlers for component interactions
    def _handle_generate_proposal(self, **kwargs):
        """Handle proposal generation and display."""
        # Use the create_proposal_saved method since generate_proposal_direct was removed
        success = self.service.create_proposal_saved(**kwargs)
        if success:
            st.success("✅ Proposal created successfully! Generating content...")
            
            # Store the generated proposal in session state for display
            if 'generated_proposal' not in st.session_state:
                st.session_state.generated_proposal = None
            
            # Get the latest proposal (the one just created)
            proposals = self.service.list_proposals()
            if proposals and len(proposals) > 0:
                latest_proposal = proposals[0]  # Most recent proposal
                st.session_state.generated_proposal = latest_proposal
                
                # Set a flag to indicate we're waiting for generation
                st.session_state.waiting_for_generation = True
                st.rerun()
            else:
                st.error("❌ Failed to retrieve generated proposal.")
        else:
            st.error("❌ Failed to create proposal. Please try again.")
    
    def run(self):
        """Main run method for compatibility"""
        self.render()