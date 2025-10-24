import streamlit as st
from typing import Dict, Any, Optional

# Import API client
from api_client.api_client import linkedin_api
# Import data management
from .linkedin_data_management import LinkedInDataManagement

class LinkedInPostFeature:
    """LinkedIn Post Generation feature for Streamlit UI - API-based"""
    
    def __init__(self):
        self.api = linkedin_api
        self.data_management = LinkedInDataManagement(linkedin_api)
    
    def render(self):
        """Main render method"""
        st.title("💼 LinkedIn Posts")
        st.markdown("Create engaging LinkedIn posts for professional networking.")
        
        # Create tabs for different features
        tab1, tab2 = st.tabs([
            "🚀 Generate Post", 
            "📊 Data Management"
        ])
        
        with tab1:
            self.render_post_generation()
        
        with tab2:
            self.data_management.render_data_management_tab()
    
    def render_post_generation(self):
        """Render LinkedIn post generation form"""
        st.subheader("🚀 Generate LinkedIn Post")
        
        with st.form("linkedin_post_form"):
            topic = st.text_input(
                "Post Topic *",
                placeholder="e.g., The Future of Remote Work",
                help="Enter the main topic for your LinkedIn post"
            )
            
            keywords = st.text_area(
                "Keywords (Optional)",
                placeholder="remote work, productivity, collaboration",
                help="Enter keywords separated by commas"
            )
            
            submitted = st.form_submit_button("💼 Generate Post", use_container_width=True)
            
            if submitted:
                if not topic:
                    st.error("Please enter a post topic.")
                    return
                
                # Process keywords
                keyword_list = []
                if keywords:
                    keyword_list = [k.strip() for k in keywords.split(',') if k.strip()]
                
                # Generate post
                self.generate_linkedin_post(topic, keyword_list)
    
    def generate_linkedin_post(self, topic: str, keywords: list):
        """Generate LinkedIn post using API"""
        with st.spinner("💼 Generating LinkedIn post..."):
            try:
                response = self.api.generate_post(topic=topic, keywords=keywords)
                
                if response and response.get("status") == "success":
                    self.display_generated_post(response)
                else:
                    error_msg = response.get("message", "Unknown error") if response else "No response from server"
                    st.error(f"❌ Post generation failed: {error_msg}")
                    
            except Exception as e:
                st.error(f"❌ Error generating post: {str(e)}")
    
    def display_generated_post(self, post_data: Dict[str, Any]):
        """Display the generated LinkedIn post"""
        st.success("✅ LinkedIn post generated successfully!")
        
        # Debug: Show the actual response structure
        with st.expander("🔍 Debug - API Response", expanded=False):
            st.json(post_data)
        
        # Display the post content
        st.subheader("📝 Generated LinkedIn Post")
        
        # Try different possible content field names
        content_fields = ["content", "post_content", "linkedin_post", "text", "message", "response"]
        content_found = False
        
        for field in content_fields:
            if field in post_data and post_data[field]:
                st.markdown("**Post Content:**")
                st.markdown(post_data[field])
                st.markdown("---")  # Add separator
                content_found = True
                break
        
        # If no content found, show available fields
        if not content_found:
            st.warning("⚠️ No post content found in the response.")
            st.info("Available fields in response:")
            for key, value in post_data.items():
                st.write(f"- **{key}:** {type(value).__name__}")
        
        # Display metadata
        if "topic" in post_data:
            st.info(f"**Topic:** {post_data['topic']}")
        
        if "keywords" in post_data:
            st.info(f"**Keywords:** {', '.join(post_data['keywords'])}")