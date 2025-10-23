"""
S3 service for uploading and managing files with directory support.
"""

import os
import logging
import boto3
from datetime import datetime
from typing import Dict, Any, Optional
from django.conf import settings
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class S3Service:
    """Service for handling S3 operations with directory support."""
    
    def __init__(self):
        self.s3_client = None
        self.bucket_name = settings.S3_BUCKET_NAME
        self.region = settings.AWS_REGION
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize S3 client."""
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=self.region
            )
            logger.info("✅ S3 client initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize S3 client: {str(e)}")
            self.s3_client = None
    
    def is_available(self) -> bool:
        """Check if S3 client is available."""
        return self.s3_client is not None and self.bucket_name is not None
    
    def upload_file(
        self, 
        file_content: bytes, 
        filename: str, 
        directory_name: str,
        content_type: str = 'application/octet-stream'
    ) -> Dict[str, Any]:
        """
        Upload file to S3 bucket in specified directory.
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            directory_name: Directory name for organization
            content_type: MIME type of the file
            
        Returns:
            Dict with success status, url, and key
        """
        if not self.is_available():
            return {
                'success': False,
                'error': 'S3 service not available. Check AWS credentials.',
                'url': None,
                'key': None
            }
        
        try:
            # Generate S3 key with directory structure
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_filename = filename.replace(' ', '_')
            s3_key = f"knowledge-base/{directory_name}/{timestamp}_{safe_filename}"
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type
            )
            
            # Generate URL
            file_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"
            
            logger.info(f"✅ Successfully uploaded {filename} to {s3_key}")
            
            return {
                'success': True,
                'url': file_url,
                'key': s3_key,
                'bucket': self.bucket_name
            }
            
        except ClientError as e:
            error_msg = f"S3 upload failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'url': None,
                'key': None
            }
        except Exception as e:
            error_msg = f"Unexpected error during S3 upload: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'url': None,
                'key': None
            }
    
    def delete_file(self, s3_key: str) -> Dict[str, Any]:
        """
        Delete file from S3 bucket.
        
        Args:
            s3_key: S3 object key
            
        Returns:
            Dict with success status and message
        """
        if not self.is_available():
            return {
                'success': False,
                'error': 'S3 service not available. Check AWS credentials.'
            }
        
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            logger.info(f"✅ Successfully deleted {s3_key} from S3")
            
            return {
                'success': True,
                'message': f'File deleted from S3: {s3_key}'
            }
            
        except ClientError as e:
            error_msg = f"S3 delete failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                'success': False,
                'error': error_msg
            }
        except Exception as e:
            error_msg = f"Unexpected error during S3 delete: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                'success': False,
                'error': error_msg
            }
    
    def list_files_in_directory(self, directory_name: str) -> Dict[str, Any]:
        """
        List all files in a specific directory.
        
        Args:
            directory_name: Directory name
            
        Returns:
            Dict with success status and list of files
        """
        if not self.is_available():
            return {
                'success': False,
                'error': 'S3 service not available.',
                'files': []
            }
        
        try:
            prefix = f"knowledge-base/{directory_name}/"
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    files.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat(),
                        'url': f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{obj['Key']}"
                    })
            
            return {
                'success': True,
                'files': files,
                'count': len(files)
            }
            
        except Exception as e:
            error_msg = f"Error listing files: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'files': []
            }
    
    def file_exists(self, s3_key: str) -> bool:
        """
        Check if file exists in S3.
        
        Args:
            s3_key: S3 object key
            
        Returns:
            True if file exists, False otherwise
        """
        if not self.is_available():
            return False
        
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return True
        except ClientError:
            return False


# Singleton instance
s3_service = S3Service()

