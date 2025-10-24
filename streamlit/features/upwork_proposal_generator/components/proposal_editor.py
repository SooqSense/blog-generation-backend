"""
Proposal editor component.
"""

import streamlit as st
from typing import Dict, Any, Optional, Callable
from .base_component import BaseComponent


class ProposalEditor(BaseComponent):
    """Component for editing existing proposals."""
    
    def __init__(self, api_client, on_update_proposal: Callable = None, on_cancel_edit: Callable = None):
        """Initialize with API client and callback functions."""
        super().__init__(api_client)
        self.on_update_proposal = on_update_proposal
        self.on_cancel_edit = on_cancel_edit
    
    def render(self):
        """Render the proposal editor."""
        st.subheader("✏️ Edit Proposal")
        
        if st.session_state.selected_proposal:
            self._render_edit_form(st.session_state.selected_proposal)
        else:
            st.info("Select a proposal from the Proposal History tab to edit it.")
    
    def _render_edit_form(self, proposal_id: int):
        """Render edit form for a specific proposal."""
        try:
            # Get proposal details
            response = self.api.get_proposal(proposal_id)
            
            if not response:
                self.show_error("Failed to load proposal details.")
                return
            
            proposal = response
            
            with st.form("edit_proposal_form"):
                st.markdown(f"### Editing: {proposal.get('title', 'Untitled')}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    client_name = st.text_input(
                        "Client Name",
                        value=proposal.get('client_name', ''),
                        help="Name of the client contact person"
                    )
                    
                    company_name = st.text_input(
                        "Company Name",
                        value=proposal.get('company_name', ''),
                        help="Name of the client's company"
                    )
                    
                    title = st.text_input(
                        "Project Title",
                        value=proposal.get('title', ''),
                        help="Project title from Upwork job posting"
                    )
                
                with col2:
                    your_name = st.text_input(
                        "Your Name",
                        value=proposal.get('your_name', ''),
                        help="Your full name for proposal signature"
                    )
                    
                    upwork_profile_link = st.text_input(
                        "Upwork Profile Link",
                        value=proposal.get('upwork_profile_link', ''),
                        help="Your Upwork profile URL"
                    )
                
                requirements = st.text_area(
                    "Project Requirements",
                    value=proposal.get('requirements', ''),
                    height=150,
                    help="Full project requirements and job description"
                )
                
                company_websites = st.text_area(
                    "Company Website Links",
                    value=', '.join(proposal.get('company_website_links', [])),
                    help="Enter company website URLs separated by commas"
                )
                
                contact_information = st.text_area(
                    "Contact Information",
                    value=proposal.get('contact_information', ''),
                    help="Your contact details"
                )
                
                col_save, col_cancel = st.columns([1, 1])
                
                with col_save:
                    if st.form_submit_button("💾 Save Changes", use_container_width=True, type="primary"):
                        self._handle_save(proposal_id, {
                            'client_name': client_name,
                            'company_name': company_name,
                            'title': title,
                            'requirements': requirements,
                            'company_website_links': [url.strip() for url in company_websites.split(',') if url.strip()],
                            'your_name': your_name,
                            'upwork_profile_link': upwork_profile_link,
                            'contact_information': contact_information
                        })
                
                with col_cancel:
                    if st.form_submit_button("❌ Cancel", use_container_width=True):
                        self.on_cancel_edit()
        
        except Exception as e:
            self.show_error(f"Error loading proposal: {str(e)}")
    
    def _handle_save(self, proposal_id: int, data: Dict[str, Any]):
        """Handle save operation."""
        if self.on_update_proposal:
            self.on_update_proposal(proposal_id, data)
        else:
            self.show_error("Update functionality has been disabled")
