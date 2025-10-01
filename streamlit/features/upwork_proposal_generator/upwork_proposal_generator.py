import streamlit as st
import sys
import os
from pathlib import Path
import time
from datetime import datetime
import json

# Add the project root to the path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import AI tools from Django management app
try:
    from management_app.upwork_proposal_generator.services.agent.agent import upwork_proposal_agent
    from management_app.knowledge_base.service.pinecone_indexing.pinecone_indexing import PineconeService
    
    AI_TOOLS_AVAILABLE = True
    AI_TOOLS_ERROR = None
    print("✅ Upwork Proposal Generator: AI tools imported successfully")
    
except Exception as e:
    AI_TOOLS_AVAILABLE = False
    AI_TOOLS_ERROR = str(e)
    print(f"⚠️ Upwork Proposal Generator: AI tools import failed - {str(e)}")


class UpworkProposalGeneratorFeature:
    """Upwork Proposal Generator feature for Streamlit UI"""
    
    def __init__(self):
        self.ai_tools_available = AI_TOOLS_AVAILABLE
        self.ai_tools_error = AI_TOOLS_ERROR
    
    def display_feature_header(self):
        """Display the feature header with branding and info."""
        st.markdown("""
        <div style='text-align: center; padding: 2rem 0;'>
            <h1 style='color: #2E86AB; margin-bottom: 0.5rem;'>🎯 AI Upwork Proposal Generator</h1>
            <p style='color: #666; font-size: 1.1rem;'>Create winning proposals using GPT-4 and your project portfolio</p>
        </div>
        """, unsafe_allow_html=True)
    
    def display_service_status(self):
        """Display the status of AI services."""
        with st.expander("🔧 Service Status", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                if self.ai_tools_available:
                    st.success("✅ Proposal Generator Available")
                    if upwork_proposal_agent.openai_client:
                        st.success("✅ GPT-4 Connected")
                    else:
                        st.error("❌ OpenAI API Key Missing")
                else:
                    st.error(f"❌ Proposal Generator Error: {self.ai_tools_error}")
            
            with col2:
                try:
                    pinecone_service = PineconeService()
                    if pinecone_service.is_available():
                        st.success("✅ Knowledge Base Connected")
                        # Get index stats
                        stats = pinecone_service.get_index_stats()
                        if 'total_vectors' in stats:
                            st.info(f"📄 {stats['total_vectors']} documents indexed")
                    else:
                        st.warning("⚠️ Knowledge Base Unavailable")
                except Exception as e:
                    st.error(f"❌ Knowledge Base Error: {str(e)}")
    
    def create_proposal_form(self):
        """Create the main proposal generation form."""
        st.markdown("### 📝 Project Details")
        
        with st.form("proposal_form"):
            # Client Information Section
            st.markdown("#### 👤 Client Information")
            col1, col2 = st.columns(2)
            
            with col1:
                client_name = st.text_input(
                    "Client Name (Optional)", 
                    placeholder="e.g., Roberto Martinez",
                    help="Name of the client contact person (optional)"
                )
            
            with col2:
                company_name = st.text_input(
                    "Company Name (Optional)",
                    placeholder="e.g., Advanced AI Solutions",
                    help="Client's company name (optional)"
                )
            
            # Company websites
            company_websites = st.text_area(
                "Company Website Links (Optional)",
                placeholder="https://company.com\nhttps://company.com/portfolio",
                help="One URL per line. These help understand the company better.",
                height=80
            )
            
            # Personal Information Section
            st.markdown("#### ✍️ Your Information")
            
            col1, col2 = st.columns(2)
            
            with col1:
                your_name = st.text_input(
                    "Your Name (Optional)",
                    placeholder="e.g., Sarah Johnson",
                    help="Your full name for the proposal signature"
                )
                upwork_profile_link = st.text_input(
                    "Your Upwork Profile Link (Optional)",
                    placeholder="https://www.upwork.com/freelancers/~your-profile",
                    help="Your Upwork profile URL"
                )
            
            with col2:
                contact_information = st.text_area(
                    "Your Contact Information (Optional)",
                    placeholder="Email: sarah@example.com\nPhone: +1 (555) 987-6543\nLinkedIn: linkedin.com/in/sarahjohnson",
                    help="Your contact details for the proposal signature. Put each contact method on a new line for best formatting. The system will automatically format it properly in the signature.",
                    height=80
                )
            
            # Project Information Section
            st.markdown("#### 🎯 Project Information")
            
            title = st.text_input(
                "Project Title *",
                placeholder="e.g., AI Automation & Agent Expert (Make.com / N8N)",
                help="The exact title from the Upwork job posting"
            )
            
            requirements = st.text_area(
                "Project Requirements *",
                placeholder="Paste the full job description here...\n\nWhat You'll Do:\n- Build automation workflows\n- Develop AI agents\n- Integrate with APIs\n...",
                help="Complete project description and requirements from Upwork",
                height=200
            )
            
            # Generation Options
            st.markdown("#### ⚙️ Generation Options")
            
            col1, col2 = st.columns(2)
            with col1:
                use_knowledge_base = st.checkbox(
                    "Use Knowledge Base", 
                    value=True,
                    help="Include relevant projects from your portfolio. Uncheck to generate proposals without specific project examples."
                )
            
            with col2:
                show_metadata = st.checkbox(
                    "Show Generation Details", 
                    value=False,
                    help="Display token usage and project matches"
                )
            
            # Submit button
            submit_button = st.form_submit_button(
                "🚀 Generate Proposal",
                type="primary",
                use_container_width=True
            )
            
            return {
                'submit': submit_button,
                'client_name': client_name,
                'company_name': company_name,
                'company_websites': company_websites,
                'your_name': your_name,
                'upwork_profile_link': upwork_profile_link,
                'contact_information': contact_information,
                'title': title,
                'requirements': requirements,
                'use_knowledge_base': use_knowledge_base,
                'show_metadata': show_metadata
            }
    
    def validate_form_data(self, form_data):
        """Validate the form input data."""
        errors = []
        
        # Client name and company name are now optional - no validation needed
        
        if not form_data['title'].strip():
            errors.append("Project title is required")
        
        if not form_data['requirements'].strip():
            errors.append("Project requirements are required")
        elif len(form_data['requirements'].strip()) < 20:
            errors.append("Project requirements should be at least 20 characters long")
        
        return errors
    
    def parse_company_websites(self, websites_text):
        """Parse company websites from textarea input."""
        if not websites_text.strip():
            return []
        
        # Split by newlines and clean up URLs
        urls = []
        for line in websites_text.strip().split('\n'):
            url = line.strip()
            if url:
                # Add https:// if missing
                if not url.startswith(('http://', 'https://')):
                    url = f'https://{url}'
                urls.append(url)
        
        return urls
    
    def generate_proposal(self, form_data):
        """Generate the proposal using the AI agent."""
        if not self.ai_tools_available:
            return {
                'success': False,
                'error': f"AI tools not available: {self.ai_tools_error}"
            }
        
        try:
            # Parse company websites
            company_websites = self.parse_company_websites(form_data['company_websites'])
            
            # Generate proposal
            result = upwork_proposal_agent.generate_proposal(
                client_name=form_data['client_name'].strip(),
                company_name=form_data['company_name'].strip(),
                title=form_data['title'].strip(),
                requirements=form_data['requirements'].strip(),
                company_websites=company_websites,
                your_name=form_data.get('your_name', '').strip() if form_data.get('your_name') else None,
                upwork_profile_link=form_data.get('upwork_profile_link', '').strip() if form_data.get('upwork_profile_link') else None,
                contact_information=form_data.get('contact_information', '').strip() if form_data.get('contact_information') else None,
                use_knowledge_base=form_data.get('use_knowledge_base', False)
            )
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Generation failed: {str(e)}"
            }
    
    def display_proposal_result(self, result, form_data, show_metadata=False):
        """Display the generated proposal result."""
        if result.get('success'):
            st.markdown("### ✅ Generated Proposal")
            
            # Display the proposal in a styled container
            proposal_content = result.get('proposal', '')
            
            # Use st.container with border for clean display
            with st.container(border=True):
                st.markdown(proposal_content)
            
            # Action buttons
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                if st.button("📋 Copy to Clipboard", use_container_width=True):
                    st.write("Copy this proposal manually from above")
                    st.success("Ready to copy!")
            
            with col2:
                # Download as text file
                company_name_clean = form_data.get('company_name', 'proposal').replace(' ', '_').lower()
                st.download_button(
                    label="📄 Download Proposal",
                    data=proposal_content,
                    file_name=f"proposal_{company_name_clean}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            
            # Show metadata if requested
            if show_metadata:
                st.markdown("### 📊 Generation Details")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    projects_found = result.get('projects_found', 0)
                    st.metric("Projects Found", projects_found)
                
                with col2:
                    model_used = result.get('model_used', 'Unknown')
                    st.metric("AI Model", model_used)
                
                with col3:
                    knowledge_base_used = form_data.get('use_knowledge_base', False)
                    st.metric("Knowledge Base", "✅ Used" if knowledge_base_used else "⚪ Disabled")
                
                # Second row for additional metrics
                col4, col5, col6 = st.columns(3)
                
                with col4:
                    token_usage = result.get('token_usage', {})
                    total_tokens = token_usage.get('total_tokens', 0)
                    st.metric("Tokens Used", total_tokens)
                
                if token_usage:
                    with st.expander("Token Usage Details"):
                        st.json(token_usage)
        
        else:
            st.markdown("### ❌ Generation Failed")
            error = result.get('error', 'Unknown error occurred')
            st.error(f"Error: {error}")
            
            # Troubleshooting tips
            with st.expander("💡 Troubleshooting Tips"):
                st.markdown("""
                - **OpenAI API Key**: Ensure your OpenAI API key is properly configured
                - **Requirements Length**: Make sure project requirements are detailed enough
                - **Knowledge Base**: Check if your Pinecone knowledge base is accessible
                - **Network**: Verify your internet connection for API calls
                """)
    
    def display_examples_section(self):
        """Display example inputs to help users."""
        with st.expander("💡 Example Input", expanded=False):
            st.markdown("""
            **Example Client Information (Optional):**
            - Client Name: `Sarah Johnson` *(optional)*
            - Company: `Digital Health Solutions` *(optional)*
            - Website: `https://digitalhealthsolutions.com` *(optional)*
            
            **Example Your Information:**
            - Your Name: `Alex Rodriguez`
            - Upwork Profile: `https://www.upwork.com/freelancers/~alexrodriguez`
            - Contact Information (each on new line):
            ```
            Email: alex@freelance.com
            Phone: +1 (555) 123-4567
            LinkedIn: linkedin.com/in/alexrodriguez
            ```
            
            **Example Project Title:**
            `Healthcare Mobile App Development - React Native & FHIR Integration`
            
            **Example Requirements:**
            ```
            We're looking for an experienced mobile app developer to create a patient portal mobile application. The project requirements include:
            
            - React Native development for iOS and Android
            - FHIR API integration for health records
            - User authentication and security compliance
            - Push notifications for appointments
            - Offline data synchronization
            - HIPAA compliance implementation
            
            Timeline: 8-12 weeks
            Budget: $15,000 - $25,000
            ```
            """)
    
    def run(self):
        """Main entry point for the Upwork Proposal Generator feature."""
        # Display header
        self.display_feature_header()
        
        # Service status
        self.display_service_status()
        
        # Main content
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Main form
            form_data = self.create_proposal_form()
            
            # Process form submission
            if form_data['submit']:
                # Validate form
                validation_errors = self.validate_form_data(form_data)
                
                if validation_errors:
                    st.error("Please fix the following errors:")
                    for error in validation_errors:
                        st.error(f"• {error}")
                else:
                    # Generate proposal
                    with st.spinner("🤖 Generating your winning proposal..."):
                        result = self.generate_proposal(form_data)
                    
                    # Display result
                    self.display_proposal_result(result, form_data, form_data['show_metadata'])
        
        with col2:
            # Side panel with tips and examples
            self.display_examples_section()
            
            # Tips section
            st.markdown("### 💡 Pro Tips")
            st.markdown("""
            - **Be Specific**: Include exact technologies and requirements
            - **Show Understanding**: Mention the client's industry or challenges  
            - **Relevant Experience**: The AI will match your portfolio projects automatically
            - **Professional Tone**: Keep it professional but personable
            - **Clear Timeline**: Mention your availability and project timeline
            """)
            
            # Knowledge Base info
            st.markdown("### 📚 Knowledge Base")
            if pinecone_service.is_available():
                stats = pinecone_service.get_index_stats()
                if 'total_vectors' in stats:
                    st.info(f"✅ {stats['total_vectors']} documents available for project matching")
                    st.caption("💡 Uncheck 'Use Knowledge Base' to generate proposals without project examples")
                else:
                    st.info("✅ Knowledge base connected")
                    st.caption("💡 You can disable knowledge base usage in Generation Options")
            else:
                st.warning("⚠️ Knowledge base not available")
                st.caption("Proposals will be generated without project examples until knowledge base is configured")


def main():
    """Main function to run the Upwork Proposal Generator feature"""
    
    # Page configuration
    st.set_page_config(
        page_title="AI Upwork Proposal Generator",
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Custom CSS for better styling
    st.markdown("""
    <style>
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 1200px;
    }
    .stButton > button {
        border-radius: 5px;
    }
    .stTextInput > div > div > input {
        border-radius: 5px;
    }
    .stTextArea > div > div > textarea {
        border-radius: 5px;
    }
    .stForm {
        border: 1px solid #ddd;
        padding: 1rem;
        border-radius: 10px;
        background-color: #fafafa;
    }
    div[data-testid="metric-container"] {
        background-color: #f0f2f6;
        border: 1px solid #cccccc;
        padding: 5% 5% 5% 10%;
        border-radius: 5px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Create and run the feature
    feature = UpworkProposalGeneratorFeature()
    feature.run()


if __name__ == "__main__":
    main()
