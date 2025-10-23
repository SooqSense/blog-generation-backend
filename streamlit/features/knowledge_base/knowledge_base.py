import streamlit as st
from typing import Dict, Any, Optional, List

# Import API client
from api_client.api_client import knowledge_base_api

class KnowledgeBaseFeature:
    """Knowledge Base feature for Streamlit UI with Directory Management"""
    
    def __init__(self):
        self.api = knowledge_base_api
        self._init_session_state()
    
    def _init_session_state(self):
        """Initialize session state for knowledge base."""
        if 'kb_directories' not in st.session_state:
            st.session_state.kb_directories = []
        if 'kb_selected_directory' not in st.session_state:
            st.session_state.kb_selected_directory = None
        if 'kb_documents' not in st.session_state:
            st.session_state.kb_documents = []
    
    def render(self):
        """Main render method"""
        st.title("📚 Knowledge Base")
        st.markdown("Upload and manage documents for AI-powered queries with directory organization.")
        
        # Show admin-only notice
        st.info("🛡️ **Admin Access**: This feature is only available to organization administrators.")
        
        # Create tabs for different features
        tab1, tab2, tab3, tab4 = st.tabs([
            "📁 Directories", 
            "📤 Upload Documents",
            "📂 Browse Documents",
            "🗑️ Manage Documents"
        ])
        
        with tab1:
            self.render_directory_management()
        
        with tab2:
            self.render_document_upload()
        
        with tab3:
            self.render_document_browser()
        
        with tab4:
            self.render_document_management()
    
    def render_directory_management(self):
        """Render directory management interface."""
        st.subheader("📁 Directory Management")
        
        # Info about default directories
        st.info("""
        **📋 Default Directories:** The system automatically provides two default directories:
        - **artilence_projects**: For Artilence team projects
        - **client_projects**: For client projects and case studies
        
        These directories are created automatically when you first access the Knowledge Base.
        """)
        
        # Refresh directories button
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🔄 Refresh", key="refresh_directories"):
                self.load_directories()
        
        # Load directories
        self.load_directories()
        
        # Display existing directories
        if st.session_state.kb_directories:
            st.markdown("### Current Directories")
            
            # Separate default and custom directories
            default_dirs = [d for d in st.session_state.kb_directories if d.get('is_default')]
            custom_dirs = [d for d in st.session_state.kb_directories if not d.get('is_default')]
            
            # Show default directories first
            if default_dirs:
                st.markdown("#### 🔒 Default Directories")
                for directory in default_dirs:
                    with st.expander(
                        f"🔒 {directory.get('name')} ({directory.get('document_count', 0)} documents)"
                    ):
                        st.write(f"**Description:** {directory.get('description', 'No description')}")
                        st.write(f"**Type:** Default Directory (Cannot be deleted)")
                        st.write(f"**Created:** {directory.get('created_at', 'Unknown')}")
            
            # Show custom directories
            if custom_dirs:
                st.markdown("#### 📁 Custom Directories")
                for directory in custom_dirs:
                    with st.expander(
                        f"📁 {directory.get('name')} ({directory.get('document_count', 0)} documents)"
                    ):
                        st.write(f"**Description:** {directory.get('description', 'No description')}")
                        st.write(f"**Type:** Custom Directory")
                        st.write(f"**Created:** {directory.get('created_at', 'Unknown')}")
                        
                        # Delete button for custom directories
                        if st.button(f"🗑️ Delete Directory", key=f"delete_dir_{directory.get('id')}"):
                            self.delete_directory(directory.get('id'), directory.get('name'))
        else:
            st.info("No directories found. The default directories will be created automatically when you upload your first document.")
        
        # Create new directory form
        st.markdown("---")
        st.markdown("### ➕ Create Custom Directory")
        
        with st.form("create_directory_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                dir_name = st.text_input(
                    "Directory Name *",
                    placeholder="e.g., my_projects",
                    help="Use lowercase letters, numbers, and underscores only"
                )
            
            with col2:
                dir_description = st.text_input(
                    "Description (Optional)",
                    placeholder="e.g., My personal project portfolio"
                )
            
            submitted = st.form_submit_button("➕ Create Custom Directory", use_container_width=True)
            
            if submitted:
                if not dir_name:
                    st.error("Please enter a directory name.")
                else:
                    self.create_directory(dir_name, dir_description)
    
    def render_document_upload(self):
        """Render document upload form with directory selection."""
        st.subheader("📤 Upload Documents")
        
        # Load directories if not loaded
        if not st.session_state.kb_directories:
            self.load_directories()
        
        if not st.session_state.kb_directories:
            st.warning("⚠️ No directories available. The default directories will be created automatically.")
            return
        
        # Show directory selection with default directories highlighted
        st.markdown("### 📁 Select Directory")
        
        # Separate default and custom directories for better UX
        default_dirs = [d for d in st.session_state.kb_directories if d.get('is_default')]
        custom_dirs = [d for d in st.session_state.kb_directories if not d.get('is_default')]
        
        # Create directory options with better formatting
        directory_options = {}
        
        # Add default directories first (recommended)
        for dir_obj in default_dirs:
            display_name = f"🔒 {dir_obj.get('name')} (Recommended)"
            directory_options[display_name] = dir_obj.get('id')
        
        # Add custom directories
        for dir_obj in custom_dirs:
            display_name = f"📁 {dir_obj.get('name')} (Custom)"
            directory_options[display_name] = dir_obj.get('id')
        
        with st.form("document_upload_form"):
            selected_dir_display = st.selectbox(
                "Select Directory *",
                options=list(directory_options.keys()),
                help="Choose the directory where your documents will be stored. Default directories are recommended for most use cases."
            )
            
            selected_directory_id = directory_options[selected_dir_display]
            
            # Show directory description
            selected_dir_obj = next(
                (d for d in st.session_state.kb_directories if d.get('id') == selected_directory_id), 
                None
            )
            if selected_dir_obj:
                st.info(f"📋 **Selected:** {selected_dir_obj.get('description', 'No description available')}")
            
            # File uploader
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
                self.upload_documents(uploaded_files, selected_directory_id)
    
    def render_document_browser(self):
        """Render document browser with directory filtering."""
        st.subheader("📂 Browse Documents")
        
        # Load directories if not loaded
        if not st.session_state.kb_directories:
            self.load_directories()
        
        # Directory filter
        col1, col2 = st.columns([3, 1])
        
        with col1:
            directory_options = {"All Directories": None}
            directory_options.update({
                dir.get('name'): dir.get('id')
                for dir in st.session_state.kb_directories
            })
            
            selected_dir_display = st.selectbox(
                "Filter by Directory:",
                options=list(directory_options.keys()),
                key="browse_directory_filter"
            )
            
            filter_directory_id = directory_options[selected_dir_display]
        
        with col2:
            if st.button("🔄 Refresh Documents", use_container_width=True):
                self.load_documents(filter_directory_id)
        
        # Load and display documents
        self.load_documents(filter_directory_id)
        
        if st.session_state.kb_documents:
            st.success(f"📊 Found {len(st.session_state.kb_documents)} documents")
            
            for doc in st.session_state.kb_documents:
                with st.expander(
                    f"📄 {doc.get('file_name')} - {doc.get('directory_name', 'Unknown Directory')}"
                ):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Directory:** {doc.get('directory_name', 'N/A')}")
                        st.write(f"**File Type:** {doc.get('file_type', 'N/A').upper()}")
                        st.write(f"**File Size:** {self._format_file_size(doc.get('file_size', 0))}")
                        st.write(f"**Word Count:** {doc.get('word_count', 0):,}")
                    
                    with col2:
                        st.write(f"**Status:** {doc.get('processing_status', 'N/A')}")
                        st.write(f"**Pinecone Indexed:** {'✅ Yes' if doc.get('pinecone_indexed') else '❌ No'}")
                        st.write(f"**Uploaded:** {doc.get('created_at', 'N/A')[:10]}")
                        st.write(f"**Uploaded By:** {doc.get('username', 'N/A')}")
                    
                    # Download link
                    if doc.get('uploaded_url'):
                        st.markdown(f"🔗 [View/Download File]({doc.get('uploaded_url')})")
        else:
            st.info("No documents found. Upload your first document in the 'Upload Documents' tab.")
    
    def render_document_management(self):
        """Render document management interface for deletion."""
        st.subheader("🗑️ Manage Documents")
        
        # Load directories if not loaded
        if not st.session_state.kb_directories:
            self.load_directories()
        
        # Directory filter
        col1, col2 = st.columns([3, 1])
        
        with col1:
            directory_options = {"All Directories": None}
            directory_options.update({
                dir.get('name'): dir.get('id')
                for dir in st.session_state.kb_directories
            })
            
            selected_dir_display = st.selectbox(
                "Filter by Directory:",
                options=list(directory_options.keys()),
                key="manage_directory_filter"
            )
            
            filter_directory_id = directory_options[selected_dir_display]
        
        with col2:
            if st.button("🔄 Refresh", use_container_width=True, key="refresh_manage_docs"):
                self.load_documents(filter_directory_id)
        
        # Load documents
        self.load_documents(filter_directory_id)
        
        if st.session_state.kb_documents:
            st.warning(f"⚠️ **Warning:** Deleting a document will remove it from the database, S3 storage, and Pinecone vector index permanently.")
            
            for doc in st.session_state.kb_documents:
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.write(f"📄 **{doc.get('file_name')}** ({doc.get('directory_name', 'Unknown')})")
                    st.caption(f"Size: {self._format_file_size(doc.get('file_size', 0))} | Words: {doc.get('word_count', 0):,}")
                
                with col2:
                    status_icon = "✅" if doc.get('processing_status') == 'completed' else "⚠️"
                    st.write(f"{status_icon} {doc.get('processing_status', 'Unknown')}")
                
                with col3:
                    if st.button(
                        "🗑️ Delete",
                        key=f"delete_doc_{doc.get('id')}",
                        type="secondary",
                        use_container_width=True
                    ):
                        self.delete_document(doc.get('id'), doc.get('file_name'))
        else:
            st.info("No documents to manage.")
    
    # ==================== Helper Methods ====================
    
    def load_directories(self):
        """Load directories from API."""
        with st.spinner("Loading directories..."):
            response = self.api.list_directories()
            
            if response and response.get("status") == "success":
                st.session_state.kb_directories = response.get("directories", [])
            else:
                st.error("Failed to load directories.")
                st.session_state.kb_directories = []
    
    def create_directory(self, name: str, description: str):
        """Create a new directory."""
        with st.spinner(f"Creating directory '{name}'..."):
            response = self.api.create_directory(name=name, description=description)
            
            if response and response.get("status") == "success":
                st.success(f"✅ Directory '{name}' created successfully!")
                # Refresh directories
                self.load_directories()
                st.rerun()
            else:
                error_msg = response.get("message", "Unknown error") if response else "No response from server"
                st.error(f"❌ Failed to create directory: {error_msg}")
    
    def delete_directory(self, directory_id: int, directory_name: str):
        """Delete a directory."""
        # Confirmation
        if st.button(f"⚠️ Confirm Delete '{directory_name}'?", key=f"confirm_delete_{directory_id}"):
            with st.spinner(f"Deleting directory '{directory_name}'..."):
                response = self.api.delete_directory(directory_id)
                
                if response and response.get("status") == "success":
                    st.success(f"✅ Directory '{directory_name}' deleted successfully!")
                    # Refresh directories
                    self.load_directories()
                    st.rerun()
                else:
                    error_msg = response.get("error", "Unknown error") if response else "No response from server"
                    st.error(f"❌ Failed to delete directory: {error_msg}")
    
    def upload_documents(self, uploaded_files: List, directory_id: int):
        """Upload documents to selected directory."""
        with st.spinner("📤 Uploading and processing documents..."):
            results = []
            
            for uploaded_file in uploaded_files:
                st.write(f"Processing: {uploaded_file.name}")
                
                response = self.api.upload_document(uploaded_file, directory_id=directory_id)
                
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
    
    def display_upload_results(self, results: List[Dict[str, Any]]):
        """Display upload results."""
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
                    st.write(f"**Directory:** {data.get('directory_name', 'N/A')}")
                    st.write(f"**File Type:** {data.get('file_type', 'N/A')}")
                    st.write(f"**File Size:** {self._format_file_size(data.get('file_size', 0))}")
                    st.write(f"**Word Count:** {data.get('word_count', 0):,}")
                    st.write(f"**Pinecone Indexed:** {'Yes' if data.get('pinecone_indexed', False) else 'No'}")
                    st.write(f"**Chunks Indexed:** {data.get('chunks_indexed', 0)}")
                    
                    if data.get('pinecone_error'):
                        st.warning(f"⚠️ Pinecone Warning: {data.get('pinecone_error')}")
            else:
                with st.expander(f"❌ {result['file']}"):
                    st.error(f"Error: {result['error']}")
    
    def load_documents(self, directory_id: Optional[int] = None):
        """Load documents from API."""
        with st.spinner("Loading documents..."):
            response = self.api.list_documents(directory_id=directory_id)
            
            if response and response.get("status") == "success":
                st.session_state.kb_documents = response.get("documents", [])
            else:
                st.error("Failed to load documents.")
                st.session_state.kb_documents = []
    
    def delete_document(self, document_id: int, file_name: str):
        """Delete a document."""
        with st.spinner(f"Deleting '{file_name}' from all systems..."):
            response = self.api.delete_document(document_id)
            
            if response and response.get("status") == "success":
                st.success(f"✅ Document '{file_name}' deleted successfully!")
                
                # Show deletion summary
                if 'deletion_summary' in response:
                    st.info("**Deletion Summary:**")
                    for system, status in response['deletion_summary'].items():
                        st.write(f"- {system}: {status}")
                
                # Show warnings if any
                if response.get('warnings'):
                    st.warning("⚠️ **Warnings:**")
                    for warning in response['warnings']:
                        st.write(f"- {warning}")
                
                # Refresh documents
                selected_dir = st.session_state.get('manage_directory_filter')
                if selected_dir and selected_dir != "All Directories":
                    dir_id = next(
                        (d['id'] for d in st.session_state.kb_directories if d['name'] == selected_dir),
                        None
                    )
                    self.load_documents(dir_id)
                else:
                    self.load_documents(None)
                
                st.rerun()
            else:
                error_msg = response.get("error", "Unknown error") if response else "No response from server"
                st.error(f"❌ Failed to delete document: {error_msg}")
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
