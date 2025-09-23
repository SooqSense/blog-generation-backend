import streamlit as st
import sys
import os
from pathlib import Path
import time
from datetime import datetime
import io

# Add the project root to the path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import AI tools directly without Django setup
try:
    from tools.ai.pdf_uploader.pdf_uploader import PDFUploaderService
    from tools.ai.pdf_uploader.pdf_extractor.pdf_extractor import DocumentExtractor
    
    AI_TOOLS_AVAILABLE = True
    AI_TOOLS_ERROR = None
    print("✅ Knowledge Base feature: AI tools imported successfully")
    
except Exception as e:
    AI_TOOLS_AVAILABLE = False
    AI_TOOLS_ERROR = str(e)
    print(f"⚠️ Knowledge Base feature: AI tools import failed - {str(e)}")
    
    # Create dummy classes for graceful degradation
    class PDFUploaderService:
        def __init__(self):
            pass
        def process_document(self, *args, **kwargs):
            raise Exception(f"PDF upload service not available: {AI_TOOLS_ERROR}")
        def is_s3_available(self):
            return False
    
    class DocumentExtractor:
        def __init__(self):
            pass
        def extract_content(self, *args, **kwargs):
            raise Exception(f"Document extraction not available: {AI_TOOLS_ERROR}")
        def get_supported_types(self):
            return ['pdf', 'docx', 'md', 'txt']

class KnowledgeBaseFeature:
    """Knowledge Base (PDF Upload) feature for Streamlit UI"""
    
    def __init__(self):
        self.ai_tools_available = AI_TOOLS_AVAILABLE
        self.ai_tools_error = AI_TOOLS_ERROR
        try:
            self.pdf_service = PDFUploaderService()
            self.document_extractor = DocumentExtractor()
        except Exception as e:
            self.pdf_service = None
            self.document_extractor = None
            if AI_TOOLS_AVAILABLE:
                self.ai_tools_error = str(e)
        
    def render(self):
        """Render the knowledge base interface"""
        st.markdown("# 📚 Knowledge Base")
        st.markdown("Upload and manage your project documents, PDFs, and files to build a searchable knowledge base.")
        
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
            
            # Get supported file types
            if self.document_extractor:
                supported_types = self.document_extractor.get_supported_types()
                type_extensions = {
                    'pdf': 'pdf',
                    'docx': 'docx', 
                    'md': 'md',
                    'txt': 'txt'
                }
                allowed_extensions = [type_extensions.get(t) for t in supported_types if t in type_extensions]
            else:
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
            if self.pdf_service and self.pdf_service.is_s3_available():
                st.success("✅ S3 Storage Connected")
            else:
                st.error("❌ S3 Storage Unavailable")
            
            if self.document_extractor:
                st.success("✅ Document Extractor Ready")
            else:
                st.error("❌ Document Extractor Unavailable")
            
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
                        
                        # Process document using PDFUploaderService
                        result = self.pdf_service.process_document(
                            file_content=file_content,
                            filename=file_name,
                            user_id=user_id,
                            username=username,
                            email=email
                        )
                        
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
            if self.pdf_service and self.pdf_service.is_s3_available():
                st.success("✅ S3 Connected")
                st.write("**Bucket:** Available")
                st.write("**Region:** Configured")
            else:
                st.error("❌ S3 Not Connected")
                st.write("Check environment variables:")
                st.code("AWS_ACCESS_KEY_ID\nAWS_SECRET_ACCESS_KEY\nAWS_S3_BUCKET_NAME")
                
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
