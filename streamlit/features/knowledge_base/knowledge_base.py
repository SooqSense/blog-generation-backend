import streamlit as st
from typing import Dict, Any, Optional

# Import API client
from api_client.api_client import knowledge_base_api

class KnowledgeBaseFeature:
    """Knowledge Base feature for Streamlit UI - API-based"""
    
    def __init__(self):
        self.api = knowledge_base_api
    
    def render(self):
        """Main render method"""
        st.title("📚 Knowledge Base")
        st.markdown("Upload and manage documents for AI-powered queries.")
        
        # Render document upload directly without tabs
        self.render_document_upload()
    
    def render_document_upload(self):
        """Render document upload form"""
        st.subheader("📤 Upload Documents")
        
        with st.form("document_upload_form"):
            uploaded_files = st.file_uploader(
                "Choose files",
                type=['pdf', 'docx', 'md', 'txt'],
                accept_multiple_files=True,
                help="Upload PDF, DOCX, Markdown, or text files (max 50MB each)"
            )
            
            submitted = st.form_submit_button("📤 Upload Documents", use_container_width=True)
            
            if submitted:
                if not uploaded_files:
                    st.error("Please select files to upload.")
                    return
                
                # Upload documents
                self.upload_documents(uploaded_files)
    
    def upload_documents(self, uploaded_files):
        """Upload documents using API"""
        with st.spinner("📤 Uploading and processing documents..."):
            try:
                results = []
                
                for uploaded_file in uploaded_files:
                    st.write(f"Processing: {uploaded_file.name}")
                    
                    response = self.api.upload_document(uploaded_file)
                    
                    if response and response.get("status") == "success":
                        results.append({
                            "file": uploaded_file.name,
                            "status": "success",
                            "data": response
                        })
                    else:
                        error_msg = response.get("message", "Unknown error") if response else "No response from server"
                        results.append({
                            "file": uploaded_file.name,
                            "status": "error",
                            "error": error_msg
                        })
                
                # Display results
                self.display_upload_results(results)
                
            except Exception as e:
                st.error(f"❌ Error uploading documents: {str(e)}")
    
    def display_upload_results(self, results):
        """Display upload results"""
        st.subheader("📊 Upload Results")
        
        success_count = sum(1 for r in results if r["status"] == "success")
        error_count = sum(1 for r in results if r["status"] == "error")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Successfully Uploaded", success_count)
        
        with col2:
            st.metric("Failed Uploads", error_count)
        
        # Display detailed results
        for result in results:
            if result["status"] == "success":
                with st.expander(f"✅ {result['file']}"):
                    data = result["data"]
                    st.write(f"**File Type:** {data.get('file_type', 'N/A')}")
                    st.write(f"**File Size:** {data.get('file_size', 0)} bytes")
                    st.write(f"**Word Count:** {data.get('word_count', 0)}")
                    st.write(f"**Processing Status:** {data.get('processing_status', 'N/A')}")
                    st.write(f"**Pinecone Indexed:** {'Yes' if data.get('pinecone_indexed', False) else 'No'}")
                    
                    if data.get('content'):
                        content_preview = data['content'][:500] + "..." if len(data['content']) > 500 else data['content']
                        st.markdown("**Content Preview:**")
                        st.text(content_preview)
            else:
                with st.expander(f"❌ {result['file']}"):
                    st.error(f"Error: {result['error']}")
    