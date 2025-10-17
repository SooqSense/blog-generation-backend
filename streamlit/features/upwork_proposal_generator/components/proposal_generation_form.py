"""
Proposal generation form component.
"""

import streamlit as st
from typing import Dict, Any, Optional, Callable
from .base_component import BaseComponent


class ProposalGenerationForm(BaseComponent):
    """Component for proposal generation form."""
    
    def __init__(self, api_client, on_generate_proposal: Callable):
        """Initialize with API client and callback function."""
        super().__init__(api_client)
        self.on_generate_proposal = on_generate_proposal
    
    def render(self):
        """Render the proposal generation form."""
        st.subheader("🚀 Generate Upwork Proposal")
        
        # Knowledge base option
        use_knowledge_base = st.checkbox(
            "Use Knowledge Base",
            value=True,
            help="Search your uploaded documents for relevant project examples"
        )
        
        with st.form("proposal_generation_form"):
            # Client Information Section
            st.markdown("### 👤 Client Information")
            col1, col2 = st.columns(2)
            
            with col1:
                client_name = st.text_input(
                    "Client Name (Optional)",
                    placeholder="John Smith",
                    help="Name of the client contact person"
                )
                
                company_name = st.text_input(
                    "Company Name (Optional)",
                    placeholder="TechCorp Inc.",
                    help="Name of the client's company"
                )
            
            with col2:
                company_websites = st.text_area(
                    "Company Website Links (Optional)",
                    placeholder="https://techcorp.com, https://techcorp.com/about",
                    help="Enter company website URLs separated by commas",
                    height=100
                )
            
            # Project Details Section
            st.markdown("### 📋 Project Details")
            title = st.text_input(
                "Project Title *",
                placeholder="Need a Full-Stack Developer for E-commerce Platform",
                help="Project title from Upwork job posting"
            )
            
            requirements = st.text_area(
                "Project Requirements *",
                placeholder="We need a developer to build a modern e-commerce platform with React frontend and Django backend. Must have experience with payment integrations and responsive design...",
                height=150,
                help="Full project requirements and job description"
            )
            
            # Personal Information Section
            st.markdown("### 👨‍💻 Your Information")
            col3, col4 = st.columns(2)
            
            with col3:
                your_name = st.text_input(
                    "Your Name (Optional)",
                    placeholder="Sarah Johnson",
                    help="Your full name for proposal signature"
                )
                
                upwork_profile_link = st.text_input(
                    "Upwork Profile Link (Optional)",
                    placeholder="https://www.upwork.com/freelancers/~your-profile",
                    help="Your Upwork profile URL"
                )
            
            with col4:
                contact_information = st.text_area(
                    "Contact Information (Optional)",
                    placeholder="Email: your.email@example.com\nPhone: +1-234-567-8900",
                    help="Your contact details",
                    height=100
                )
            
            # Submit button
            submitted = st.form_submit_button(
                "💼 Generate Proposal", 
                use_container_width=True,
                type="primary"
            )
            
            if submitted:
                if not self._validate_form(title, requirements):
                    return
                
                # Process company websites
                website_list = self._process_websites(company_websites)
                
                # Prepare form data
                form_data = {
                    'client_name': client_name,
                    'company_name': company_name,
                    'title': title,
                    'requirements': requirements,
                    'company_website_links': website_list,
                    'your_name': your_name,
                    'upwork_profile_link': upwork_profile_link,
                    'contact_information': contact_information,
                    'use_knowledge_base': use_knowledge_base
                }
                
                # Generate proposal
                self.on_generate_proposal(**form_data)
    
    def _validate_form(self, title: str, requirements: str) -> bool:
        """Validate form inputs."""
        if not title:
            self.show_error("Please enter a project title.")
            return False
        
        if not requirements:
            self.show_error("Please enter project requirements.")
            return False
        
        return True
    
    def _process_websites(self, company_websites: str) -> list:
        """Process company websites string into list."""
        if not company_websites:
            return []
        return [url.strip() for url in company_websites.split(',') if url.strip()]
