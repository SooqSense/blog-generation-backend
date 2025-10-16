import streamlit as st
import sys
import os
from pathlib import Path
import time
from datetime import datetime
import io

# Authentication will be checked via session state

# Add the project root to the path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# API-based knowledge base (no direct Django imports)
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API base URL from environment
API_BASE_URL = os.getenv("BACKEND_API_BASE_URL", "http://localhost:8000")

# API service class for knowledge base
class KnowledgeBaseAPI:
    """API service for knowledge base operations"""
    
    def __init__(self):
        self.base_url = API_BASE_URL
        self.auth_headers = self._get_auth_headers()
    
    def _get_auth_headers(self):
        """Get authentication headers from session state"""
        import streamlit as st
        headers = {"Content-Type": "application/json"}
        
        # Get JWT token from session state
        if hasattr(st, 'session_state') and 'jwt_token' in st.session_state:
            headers["Authorization"] = f"Bearer {st.session_state.jwt_token}"
        
        return headers
    
    def upload_document(self, **kwargs):
        """Upload document via API"""
        try:
            response = requests.post(
                f"{self.base_url}/knowledge-base/upload/",
                json=kwargs,
                headers=self.auth_headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_documents(self):
        """Get documents via API"""
        try:
            response = requests.get(
                f"{self.base_url}/knowledge-base/documents/",
                headers=self.auth_headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}

# Initialize API service
try:
    kb_api = KnowledgeBaseAPI()
    AI_TOOLS_AVAILABLE = True
    AI_TOOLS_ERROR = None
    print("✅ Knowledge Base feature: API service initialized successfully")
except Exception as e:
    AI_TOOLS_AVAILABLE = False
    AI_TOOLS_ERROR = str(e)
    print(f"⚠️ Knowledge Base feature: API service initialization failed - {str(e)}")
    kb_api = None

class KnowledgeBaseFeature:
    """Knowledge Base (PDF Upload) feature for Streamlit UI"""
    
    def __init__(self):
        self.ai_tools_available = AI_TOOLS_AVAILABLE
        self.ai_tools_error = AI_TOOLS_ERROR
        self.kb_api = kb_api
        self.document_extractor = None  # Not needed for API-based approach
        self.pinecone_service = None  # Not needed for API-based approach
        self.pdf_service = None
    
    def _check_admin_permissions(self):
        """Check if user has admin permissions for Knowledge Base access"""
        try:
            # Get current user data from session
            user_data = st.session_state.get('user_data', {})
            
            if not user_data:
                st.error("🔒 Not authenticated")
                st.info("Please log in to access the Knowledge Base.")
                return False
            
            # Check if user is admin
            is_admin = user_data.get('is_admin', False)
            permissions = user_data.get('permissions', 'user')
            
            if not is_admin and permissions != 'admin':
                st.error("🚫 Admin Access Required")
                st.warning("Only administrators can access the Knowledge Base.")
                st.info("Contact your administrator to request access.")
                return False
            
            # Admin access granted
            st.success("✅ Admin access confirmed")
            return True
            
        except Exception as e:
            st.error(f"🔒 Permission check failed: {str(e)}")
            return False
        
    def render(self):
        """Render the knowledge base interface"""
        st.markdown("# 📚 Knowledge Base")
        st.markdown("Upload and manage your project documents, PDFs, and files to build a searchable knowledge base.")
        
        # Check admin permissions first
        if not self._check_admin_permissions():
            return
        
        # Check if AI tools are available
        if not self.ai_tools_available:
            st.error("🚫 Knowledge Base Tools Not Available")
            st.error(f"Error: {self.ai_tools_error}")
            st.info("Please ensure the AI tools and dependencies are properly configured.")
            return
        
        # Create tabs for different functionalities
        tab1, tab2, tab3 = st.tabs(["📤 Upload Documents", "📋 Document Library", "⚙️ Settings"])
        
        with tab1:
            self.render_document_upload()
            
        with tab2:
            self.render_document_library()
            
        with tab3:
            self.render_settings()
    
    def render_document_upload(self):
        """Render the document upload interface"""
        st.markdown("### Upload Project Documents")
        st.markdown("Upload PDF, Word, Markdown, or text files to build your searchable knowledge base.")
        
        # File upload section
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("#### 📁 File Upload")
            
            # Supported file types for API
            allowed_extensions = ['pdf', 'docx', 'md', 'txt']
            
            uploaded_files = st.file_uploader(
                "Choose document files",
                type=allowed_extensions,
                accept_multiple_files=True,
                help=f"Supported formats: {', '.join(allowed_extensions).upper()}"
            )
            
            if uploaded_files:
                st.success(f"✅ {len(uploaded_files)} file(s) selected for upload")
                
                # Display file information
                for file in uploaded_files:
                    file_size_mb = len(file.read()) / (1024 * 1024)
                    file.seek(0)  # Reset file pointer
                    
                    with st.expander(f"📄 {file.name} ({file_size_mb:.2f} MB)", expanded=False):
                        col_file1, col_file2, col_file3 = st.columns(3)
                        
                        with col_file1:
                            st.write(f"**Type:** {file.type}")
                            st.write(f"**Size:** {file_size_mb:.2f} MB")
                            
                        with col_file2:
                            st.write(f"**Extension:** {file.name.split('.')[-1].upper()}")
                            
                        with col_file3:
                            if file_size_mb > 50:
                                st.warning("⚠️ File too large")
                            else:
                                st.success("✅ Valid size")
            
            # Upload options
            st.markdown("#### ⚙️ Upload Settings")
            
            col_opt1, col_opt2 = st.columns(2)
            
            with col_opt1:
                extract_images = st.checkbox(
                    "Extract Images", 
                    value=True,
                    help="Extract images from documents when possible"
                )
                
                chunk_documents = st.checkbox(
                    "Enable Document Chunking",
                    value=True,
                    help="Split large documents into searchable chunks"
                )
                
            with col_opt2:
                index_to_pinecone = st.checkbox(
                    "Index to Vector Database",
                    value=True,
                    help="Add to searchable vector database for AI chat"
                )
                
                overwrite_existing = st.checkbox(
                    "Overwrite Existing",
                    value=False,
                    help="Replace files with the same name"
                )
        
        with col2:
            st.markdown("### 🚀 Upload Status")
            
            # Show service status
            st.markdown("#### 🔧 Service Status")
            if self.kb_api:
                st.success("✅ Knowledge Base API Ready")
            else:
                st.error("❌ Knowledge Base API Unavailable")
            
            if self.ai_tools_available:
                st.success("✅ AI Tools Available")
            else:
                st.error("❌ AI Tools Unavailable")
            
            # Upload statistics
            if 'upload_stats' in st.session_state:
                stats = st.session_state.upload_stats
                st.markdown("#### 📊 Upload Statistics")
                st.metric("Files Uploaded", stats.get('total_uploaded', 0))
                st.metric("Total Size", f"{stats.get('total_size_mb', 0):.1f} MB")
                st.metric("Success Rate", f"{stats.get('success_rate', 0):.1f}%")
            
            # Upload tips
            st.markdown("#### 💡 Upload Tips")
            st.markdown("""
            **Best Practices:**
            - Use descriptive file names
            - Keep files under 50MB
            - PDF files work best for text extraction
            - Ensure text is not in image format
            - Use original documents when possible
            """)
        
        # Upload button and processing
        st.markdown("---")
        
        col_upload1, col_upload2, col_upload3 = st.columns([1, 2, 1])
        
        with col_upload2:
            if st.button(
                "🚀 Upload Documents",
                type="primary",
                use_container_width=True,
                disabled=not uploaded_files or not self.ai_tools_available
            ):
                if uploaded_files:
                    self.process_document_uploads(
                        uploaded_files,
                        extract_images=extract_images,
                        chunk_documents=chunk_documents,
                        index_to_pinecone=index_to_pinecone,
                        overwrite_existing=overwrite_existing
                    )
                else:
                    st.error("Please select files to upload")
        
        # Display upload results
        if 'upload_results' in st.session_state:
            self.display_upload_results(st.session_state.upload_results)
    
    def process_document_uploads(self, uploaded_files, **options):
        """Process document uploads using AI tools"""
        try:
            st.session_state.upload_status = 'processing'
            
            # Initialize progress tracking
            total_files = len(uploaded_files)
            processed_files = 0
            upload_results = []
            
            # Show progress
            progress_container = st.container()
            with progress_container:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i, uploaded_file in enumerate(uploaded_files):
                    file_name = uploaded_file.name
                    status_text.text(f"Processing {file_name}...")
                    progress_bar.progress((i) / total_files)
                    
                    try:
                        # Read file content
                        file_content = uploaded_file.read()
                        uploaded_file.seek(0)  # Reset for potential re-reading
                        
                        # Get user info from session
                        user_id = st.session_state.get('user_id', 1)
                        username = st.session_state.get('username', 'Anonymous')
                        email = st.session_state.get('user_email', 'user@example.com')
                        
                        # Process document using API
                        import base64
                        file_base64 = base64.b64encode(file_content).decode('utf-8')
                        
                        api_response = self.kb_api.upload_document(
                            filename=file_name,
                            file_content=file_base64,
                            file_type=file_name.split('.')[-1].lower(),
                            user_id=user_id,
                            username=username,
                            extract_images=options.get('extract_images', True),
                            chunk_documents=options.get('chunk_documents', True),
                            index_to_pinecone=options.get('index_to_pinecone', True),
                            overwrite_existing=options.get('overwrite_existing', False)
                        )
                        
                        if not api_response.get('success'):
                            raise Exception(api_response.get('error', 'Document upload failed'))
                        
                        result = api_response.get('result', {})
                        
                        # Enhanced result tracking with Pinecone indexing status
                        upload_status = 'success' if result.get('success') else 'failed'
                        
                        upload_results.append({
                            'filename': file_name,
                            'status': upload_status,
                            'result': result,
                            'size_mb': len(file_content) / (1024 * 1024),
                            'processed_at': datetime.now(),
                            'pinecone_indexed': result.get('pinecone_indexed', False),
                            'pinecone_error': result.get('pinecone_error')
                        })
                        
                        if result.get('success'):
                            processed_files += 1
                        
                    except Exception as e:
                        upload_results.append({
                            'filename': file_name,
                            'status': 'error',
                            'error': str(e),
                            'size_mb': len(file_content) / (1024 * 1024) if 'file_content' in locals() else 0,
                            'processed_at': datetime.now()
                        })
                
                status_text.text("Upload processing completed!")
                progress_bar.progress(1.0)
                
                # Update statistics
                total_size_mb = sum(r.get('size_mb', 0) for r in upload_results)
                success_count = sum(1 for r in upload_results if r['status'] == 'success')
                success_rate = (success_count / total_files) * 100 if total_files > 0 else 0
                
                if 'upload_stats' not in st.session_state:
                    st.session_state.upload_stats = {
                        'total_uploaded': 0,
                        'total_size_mb': 0,
                        'success_rate': 0
                    }
                
                st.session_state.upload_stats.update({
                    'total_uploaded': st.session_state.upload_stats['total_uploaded'] + success_count,
                    'total_size_mb': st.session_state.upload_stats['total_size_mb'] + total_size_mb,
                    'success_rate': success_rate
                })
                
                st.session_state.upload_results = upload_results
                st.session_state.upload_status = 'completed'
                
                # Clear progress indicators after showing summary
                time.sleep(2)
                progress_container.empty()
                
                # Show summary
                st.success(f"✅ Processed {total_files} files. {success_count} successful, {total_files - success_count} failed.")
                
        except Exception as e:
            st.session_state.upload_status = 'error'
            st.error(f"❌ Upload processing failed: {str(e)}")
    
    def display_upload_results(self, upload_results):
        """Display the results of document uploads"""
        st.markdown("---")
        st.markdown("## 📋 Upload Results")
        
        # Results summary
        total_files = len(upload_results)
        successful = sum(1 for r in upload_results if r['status'] == 'success')
        failed = total_files - successful
        indexed = sum(1 for r in upload_results if r.get('pinecone_indexed', False))
        
        col_summary1, col_summary2, col_summary3, col_summary4 = st.columns(4)
        
        with col_summary1:
            st.metric("Total Files", total_files)
        with col_summary2:
            st.metric("Successful", successful, delta=f"{(successful/total_files)*100:.1f}%" if total_files > 0 else "0%")
        with col_summary3:
            st.metric("Failed", failed, delta=f"-{(failed/total_files)*100:.1f}%" if failed > 0 else "0%")
        with col_summary4:
            st.metric("Vector Indexed", indexed, delta=f"🔍 {(indexed/total_files)*100:.1f}%" if total_files > 0 else "0%")
        
        # Detailed results
        st.markdown("### 📄 File Details")
        
        for result in upload_results:
            status_icon = "✅" if result['status'] == 'success' else "❌"
            
            with st.expander(f"{status_icon} {result['filename']} ({result['size_mb']:.2f} MB)", expanded=False):
                col_detail1, col_detail2 = st.columns(2)
                
                with col_detail1:
                    st.write(f"**Status:** {result['status'].title()}")
                    st.write(f"**Size:** {result['size_mb']:.2f} MB")
                    st.write(f"**Processed:** {result['processed_at'].strftime('%Y-%m-%d %H:%M:%S')}")
                    
                with col_detail2:
                    if result['status'] == 'success' and 'result' in result:
                        upload_result = result['result']
                        st.write(f"**Word Count:** {upload_result.get('word_count', 'N/A')}")
                        if upload_result.get('uploaded_url'):
                            st.markdown(f"**S3 URL:** [View File]({upload_result.get('uploaded_url')})")
                        
                        # Display Pinecone indexing status
                        pinecone_indexed = result.get('pinecone_indexed', False)
                        if pinecone_indexed:
                            st.write("**Vector Search:** ✅ Indexed")
                        else:
                            st.write("**Vector Search:** ❌ Not Indexed")
                            pinecone_error = result.get('pinecone_error')
                            if pinecone_error:
                                st.caption(f"⚠️ Indexing Error: {pinecone_error}")
                                
                    elif result['status'] == 'error':
                        st.error(f"**Error:** {result.get('error', 'Unknown error')}")
                
                # Show extracted content preview if available
                if result['status'] == 'success' and 'result' in result:
                    upload_result = result['result']
                    content = upload_result.get('content', '')
                    if content:
                        st.markdown("**Content Preview:**")
                        preview = content[:300] + "..." if len(content) > 300 else content
                        st.text_area("Content", preview, height=100, key=f"preview_{result['filename']}")
        
        # Clear results button
        if st.button("🗑️ Clear Results", use_container_width=True):
            if 'upload_results' in st.session_state:
                del st.session_state.upload_results
                st.rerun()
    
    def render_document_library(self):
        """Render document library interface"""
        st.markdown("### 📚 Document Library")
        st.info("📝 Document library integration with database coming soon! This will show all your uploaded documents with search and filter capabilities.")
        
        # Show session documents if available
        if 'upload_results' in st.session_state:
            results = st.session_state.upload_results
            successful_docs = [r for r in results if r['status'] == 'success']
            
            if successful_docs:
                st.markdown(f"#### 📄 Session Documents ({len(successful_docs)} files)")
                
                for doc in successful_docs:
                    with st.expander(f"📄 {doc['filename']}", expanded=False):
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.write(f"**Size:** {doc['size_mb']:.2f} MB")
                            st.write(f"**Status:** Uploaded")
                            
                        with col2:
                            if 'result' in doc and doc['result'].get('s3_url'):
                                st.markdown(f"[🔗 View File]({doc['result']['s3_url']})")
                            st.write(f"**Word Count:** {doc['result'].get('word_count', 'N/A') if 'result' in doc else 'N/A'}")
                            
                        with col3:
                            st.write(f"**Uploaded:** {doc['processed_at'].strftime('%H:%M:%S')}")
                            indexed = doc['result'].get('pinecone_ready', False) if 'result' in doc else False
                            st.write(f"**Searchable:** {'✅' if indexed else '❌'}")
            else:
                st.info("No documents uploaded in this session. Use the Upload tab to add documents.")
        else:
            st.info("No documents uploaded yet. Use the Upload Documents tab to get started.")
        
        # Library management
        st.markdown("#### 🔧 Library Management")
        
        col_mgmt1, col_mgmt2, col_mgmt3 = st.columns(3)
        
        with col_mgmt1:
            if st.button("🔍 Search Documents", use_container_width=True):
                st.info("🔍 Advanced search functionality coming soon!")
                
        with col_mgmt2:
            if st.button("📊 View Statistics", use_container_width=True):
                if 'upload_stats' in st.session_state:
                    stats = st.session_state.upload_stats
                    st.json(stats)
                else:
                    st.info("No statistics available. Upload some documents first.")
                    
        with col_mgmt3:
            if st.button("🗂️ Organize Files", use_container_width=True):
                st.info("📁 File organization features coming soon!")
    
    def render_settings(self):
        """Render settings interface"""
        st.markdown("### ⚙️ Knowledge Base Settings")
        
        # Service configuration
        st.markdown("#### 🔧 Service Configuration")
        
        col_config1, col_config2 = st.columns(2)
        
        with col_config1:
            st.markdown("**Document Processing:**")
            
            max_file_size = st.slider(
                "Max File Size (MB)",
                min_value=1,
                max_value=100,
                value=50,
                help="Maximum allowed file size for uploads"
            )
            
            extract_metadata = st.checkbox(
                "Extract Metadata",
                value=True,
                help="Extract document metadata (author, creation date, etc.)"
            )
            
            enable_ocr = st.checkbox(
                "Enable OCR",
                value=False,
                help="Extract text from images in documents (experimental)"
            )
            
        with col_config2:
            st.markdown("**Vector Database:**")
            
            chunk_size = st.slider(
                "Chunk Size",
                min_value=100,
                max_value=2000,
                value=1000,
                help="Size of text chunks for vector search"
            )
            
            chunk_overlap = st.slider(
                "Chunk Overlap",
                min_value=0,
                max_value=200,
                value=100,
                help="Overlap between consecutive chunks"
            )
            
            embedding_model = st.selectbox(
                "Embedding Model",
                ["text-embedding-ada-002", "text-embedding-3-small", "text-embedding-3-large"],
                help="OpenAI embedding model for vector search"
            )
        
        # Storage settings
        st.markdown("#### 💾 Storage Settings")
        
        col_storage1, col_storage2 = st.columns(2)
        
        with col_storage1:
            st.markdown("**S3 Configuration:**")
            if self.pdf_service and hasattr(self.pdf_service, 'is_s3_available') and self.pdf_service.is_s3_available():
                st.success("✅ S3 Connected")
                st.write("**Bucket:** Available")
                st.write("**Region:** Configured")
            else:
                st.warning("⚠️ S3 Service Not Available")
                st.write("PDF service is not configured. S3 functionality is disabled.")
                st.write("To enable S3, configure the PDF service in the knowledge base settings.")
                
        with col_storage2:
            st.markdown("**Vector Database:**")
            st.info("Pinecone configuration status will be shown here")
            st.write("**Index:** PDFS namespace")
            st.write("**Dimensions:** 1536 (OpenAI)")
        
        # Advanced settings
        st.markdown("#### 🔬 Advanced Settings")
        
        with st.expander("🔧 Advanced Configuration", expanded=False):
            col_adv1, col_adv2 = st.columns(2)
            
            with col_adv1:
                enable_debug = st.checkbox("Enable Debug Logging", value=False)
                parallel_processing = st.checkbox("Parallel Processing", value=True)
                cache_embeddings = st.checkbox("Cache Embeddings", value=True)
                
            with col_adv2:
                api_timeout = st.slider("API Timeout (seconds)", 30, 300, 120)
                retry_attempts = st.slider("Retry Attempts", 1, 5, 3)
                batch_size = st.slider("Processing Batch Size", 1, 20, 5)
        
        # Save settings
        if st.button("💾 Save Settings", type="primary", use_container_width=True):
            settings = {
                'max_file_size_mb': max_file_size,
                'extract_metadata': extract_metadata,
                'enable_ocr': enable_ocr,
                'chunk_size': chunk_size,
                'chunk_overlap': chunk_overlap,
                'embedding_model': embedding_model,
                'enable_debug': enable_debug if 'enable_debug' in locals() else False,
                'parallel_processing': parallel_processing if 'parallel_processing' in locals() else True,
                'cache_embeddings': cache_embeddings if 'cache_embeddings' in locals() else True,
                'api_timeout': api_timeout if 'api_timeout' in locals() else 120,
                'retry_attempts': retry_attempts if 'retry_attempts' in locals() else 3,
                'batch_size': batch_size if 'batch_size' in locals() else 5
            }
            
            st.session_state.knowledge_base_settings = settings
            st.success("✅ Settings saved successfully!")
            
            # Show saved settings
            with st.expander("📋 Saved Settings", expanded=False):
                st.json(settings)
