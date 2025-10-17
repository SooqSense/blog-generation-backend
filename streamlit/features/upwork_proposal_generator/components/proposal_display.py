"""
Proposal display component for showing generated proposals.
"""

import streamlit as st
from typing import Dict, Any, Optional
from .base_component import BaseComponent
from base.markdown_processor import MarkdownProcessor


class ProposalDisplay(BaseComponent):
    """Component for displaying generated proposals."""
    
    def render(self, proposal_data: Dict[str, Any], is_direct: bool = False):
        """Display the generated proposal."""
        self.show_success("Upwork proposal generated successfully!")
        
        # Add clear button at the top
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🗑️ Clear", help="Clear the generated proposal"):
                if 'generated_proposal' in st.session_state:
                    del st.session_state.generated_proposal
                st.rerun()
        
        # Display proposal metadata
        self._render_metadata(proposal_data, is_direct)
        
        # Display proposal content
        self._render_content(proposal_data)
        
        # Display metadata
        self._render_generation_metadata(proposal_data)
    
    def _render_metadata(self, proposal_data: Dict[str, Any], is_direct: bool):
        """Render proposal metadata."""
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if is_direct:
                st.metric("Generation Mode", "Direct")
            else:
                st.metric("Proposal ID", proposal_data.get("proposal_id", "N/A"))
        
        with col2:
            st.metric("Status", proposal_data.get("status", "Completed"))
        
        with col3:
            if "metadata" in proposal_data and "projects_found" in proposal_data["metadata"]:
                st.metric("Projects Found", proposal_data["metadata"]["projects_found"])
    
    def _render_content(self, proposal_data: Dict[str, Any]):
        """Render proposal content."""
        st.subheader("📝 Generated Proposal")
        
        # Try different possible content field names
        content_fields = ["proposal_content", "content", "proposal", "text", "message", "response"]
        content_found = False
        
        for field in content_fields:
            if field in proposal_data and proposal_data[field]:
                content = proposal_data[field]
                if isinstance(content, str):
                    st.markdown(content)
                    content_found = True
                    
                    # Copy to clipboard functionality
                    if st.button("📋 Copy to Clipboard"):
                        st.code(content, language=None)
                        self.show_success("Proposal copied! You can now paste it into Upwork.")
                    break
                else:
                    # Handle other content formats
                    MarkdownProcessor.display_content({"content": content})
                    content_found = True
                    break
        
        # If no content found, show available fields
        if not content_found:
            st.warning("⚠️ No proposal content found in the response.")
            st.info("Available fields in response:")
            for key, value in proposal_data.items():
                st.write(f"- **{key}:** {type(value).__name__}")
    
    def _render_generation_metadata(self, proposal_data: Dict[str, Any]):
        """Render generation metadata."""
        if "metadata" in proposal_data:
            with st.expander("📊 Generation Metadata"):
                metadata = proposal_data["metadata"]
                for key, value in metadata.items():
                    st.write(f"**{key.replace('_', ' ').title()}:** {value}")
