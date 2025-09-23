"""
PDF uploader service that handles file upload, content extraction, and indexing.
"""

import os
import uuid
import boto3
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from io import BytesIO

from .pdf_extractor.pdf_extractor import document_extractor

# Import Pinecone service for document indexing
try:
    from management_app.pinecone_integration.service.service import pinecone_service
    PINECONE_AVAILABLE = True
    print("✅ Pinecone service imported successfully in PDF uploader")
except Exception as e:
    PINECONE_AVAILABLE = False
    pinecone_service = None
    print(f"⚠️ Pinecone service not available: {str(e)}")

logger = logging.getLogger(__name__)

class PDFUploaderService:
    """Service for handling PDF upload, extraction, and S3 storage."""
    
    def __init__(self):
        self.s3_client = None
        self.bucket_name = os.getenv('S3_BUCKET_NAME')
        self.aws_region = os.getenv('AWS_REGION', 'us-east-1')
        self._initialize_s3()
    
    def _initialize_s3(self):
        """Initialize S3 client."""
        try:
            aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
            aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
            
            if aws_access_key and aws_secret_key and self.bucket_name:
                self.s3_client = boto3.client(
                    's3',
                    region_name=self.aws_region,
                    aws_access_key_id=aws_access_key,
                    aws_secret_access_key=aws_secret_key
                )
                logger.info("✅ S3 client initialized successfully")
            else:
                logger.warning("⚠️ S3 credentials not complete - file upload will be disabled")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize S3 client: {str(e)}")
    
    def is_s3_available(self) -> bool:
        """Check if S3 service is available."""
        return self.s3_client is not None and self.bucket_name is not None
    
    def upload_to_s3(self, file_content: bytes, filename: str, content_type: str = None) -> Dict[str, Any]:
        """Upload file to S3 bucket."""
        try:
            if not self.is_s3_available():
                return {
                    'success': False,
                    'error': 'S3 service not available',
                    'url': None
                }
            
            # Generate unique filename to avoid conflicts
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_id = str(uuid.uuid4())[:8]
            file_extension = os.path.splitext(filename)[1]
            unique_filename = f"documents/{timestamp}_{unique_id}_{filename}"
            
            logger.info(f"📤 Uploading to S3: {unique_filename}")
            
            # Upload file
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            
            self.s3_client.upload_fileobj(
                BytesIO(file_content),
                self.bucket_name,
                unique_filename,
                ExtraArgs=extra_args
            )
            
            # Generate S3 URL
            s3_url = f"https://{self.bucket_name}.s3.{self.aws_region}.amazonaws.com/{unique_filename}"
            
            logger.info(f"✅ File uploaded to S3: {s3_url}")
            
            return {
                'success': True,
                'url': s3_url,
                'bucket': self.bucket_name,
                'key': unique_filename
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to upload to S3: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'url': None
            }
    
    def process_document(
        self, 
        file_content: bytes, 
        filename: str,
        user_id: int,
        username: str,
        email: str
    ) -> Dict[str, Any]:
        """Process document: extract content, upload to S3."""
        try:
            logger.info(f"📄 Processing document: {filename} for user {username}")
            
            # Validate file
            validation = document_extractor.validate_file(file_content, filename)
            if not validation['valid']:
                return {
                    'success': False,
                    'error': validation['error'],
                    'stage': 'validation'
                }
            
            file_type = validation['file_type']
            file_size = validation['file_size']
            
            # Extract content
            logger.info(f"🔄 Extracting content from {filename}")
            extraction_result = document_extractor.extract_content(file_content, filename)
            
            if not extraction_result['success']:
                return {
                    'success': False,
                    'error': f"Content extraction failed: {extraction_result['error']}",
                    'stage': 'extraction'
                }
            
            content = extraction_result['content']
            word_count = extraction_result['word_count']
            
            if not content.strip():
                return {
                    'success': False,
                    'error': 'No readable content found in file',
                    'stage': 'extraction'
                }
            
            # Upload to S3
            logger.info(f"📤 Uploading {filename} to S3")
            s3_result = self.upload_to_s3(file_content, filename)
            
            if not s3_result['success']:
                return {
                    'success': False,
                    'error': f"S3 upload failed: {s3_result['error']}",
                    'stage': 'upload'
                }
            
            uploaded_url = s3_result['url']
            
            # Generate document ID
            document_id = str(uuid.uuid4())
            
            # Index document in Pinecone for vector search
            pinecone_success = False
            pinecone_error = None
            
            if PINECONE_AVAILABLE and pinecone_service and pinecone_service.is_available():
                try:
                    logger.info(f"🔍 Indexing document in Pinecone: {filename}")
                    indexing_result = pinecone_service.index_document(
                        document_id=document_id,
                        file_name=filename,
                        file_type=file_type,
                        content=content,
                        user_id=user_id,
                        username=username,
                        file_url=uploaded_url
                    )
                    
                    if indexing_result.get('success'):
                        pinecone_success = True
                        logger.info(f"✅ Document successfully indexed in Pinecone: {filename}")
                    else:
                        pinecone_error = indexing_result.get('error', 'Unknown indexing error')
                        logger.warning(f"⚠️ Pinecone indexing failed for {filename}: {pinecone_error}")
                        
                except Exception as e:
                    pinecone_error = str(e)
                    logger.error(f"❌ Pinecone indexing error for {filename}: {str(e)}")
            else:
                pinecone_error = "Pinecone service not available"
                logger.warning(f"⚠️ Pinecone service not available for indexing: {filename}")
            
            logger.info(f"✅ Successfully processed document: {filename}")
            
            return {
                'success': True,
                'document_id': document_id,
                'file_name': filename,
                'file_type': file_type,
                'content': content,
                'uploaded_url': uploaded_url,
                'file_size': file_size,
                'word_count': word_count,
                'extraction_method': extraction_result.get('method', 'unknown'),
                'pinecone_indexed': pinecone_success,
                'pinecone_error': pinecone_error
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to process document {filename}: {str(e)}")
            return {
                'success': False,
                'error': f'Document processing error: {str(e)}',
                'stage': 'processing'
            }
    
    def get_content_type(self, filename: str) -> str:
        """Get MIME type for filename."""
        file_extension = os.path.splitext(filename.lower())[1]
        
        content_types = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.doc': 'application/msword',
            '.md': 'text/markdown',
            '.txt': 'text/plain'
        }
        
        return content_types.get(file_extension, 'application/octet-stream')
    
    def delete_from_s3(self, s3_url: str) -> Dict[str, Any]:
        """Delete file from S3 bucket."""
        try:
            if not self.is_s3_available():
                return {
                    'success': False,
                    'error': 'S3 service not available'
                }
            
            # Extract key from S3 URL
            # URL format: https://bucket-name.s3.region.amazonaws.com/key
            if self.bucket_name in s3_url:
                key = s3_url.split(f"{self.bucket_name}.s3.{self.aws_region}.amazonaws.com/")[1]
                
                self.s3_client.delete_object(
                    Bucket=self.bucket_name,
                    Key=key
                )
                
                logger.info(f"🗑️ Deleted file from S3: {key}")
                
                return {
                    'success': True,
                    'key': key
                }
            else:
                return {
                    'success': False,
                    'error': 'Invalid S3 URL format'
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to delete from S3: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


# Create global uploader service instance
pdf_uploader_service = PDFUploaderService()
