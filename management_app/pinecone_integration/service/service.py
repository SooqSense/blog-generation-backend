"""
Pinecone service for PDF document indexing and querying.
"""

import os
import uuid
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging

from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI
from django.conf import settings

from ..config.config import config

logger = logging.getLogger(__name__)

class PineconeService:
    """Service for handling Pinecone operations for PDF documents."""
    
    def __init__(self):
        self.config = config
        self.pc = None
        self.index = None
        self.openai_client = None
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize Pinecone and OpenAI clients."""
        try:
            # Initialize Pinecone
            if self.config.pinecone_api_key:
                self.pc = Pinecone(api_key=self.config.pinecone_api_key)
                self._ensure_index_exists()
                if self.pc.describe_index(self.config.index_name).status['ready']:
                    self.index = self.pc.Index(self.config.index_name)
                    logger.info(f"✅ Connected to Pinecone index: {self.config.index_name}")
                else:
                    logger.warning(f"⚠️ Pinecone index {self.config.index_name} is not ready")
            else:
                logger.error("❌ Pinecone API key not found")
            
            # Initialize OpenAI
            if self.config.openai_api_key:
                self.openai_client = OpenAI(api_key=self.config.openai_api_key)
                logger.info("✅ OpenAI client initialized")
            else:
                logger.error("❌ OpenAI API key not found")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize Pinecone/OpenAI clients: {str(e)}")
    
    def _ensure_index_exists(self):
        """Ensure the Pinecone index exists, create if it doesn't."""
        try:
            # Check if index exists
            existing_indexes = [index.name for index in self.pc.list_indexes()]
            
            if self.config.index_name not in existing_indexes:
                logger.info(f"Creating Pinecone index: {self.config.index_name}")
                self.pc.create_index(
                    name=self.config.index_name,
                    dimension=self.config.DIMENSION,
                    metric=self.config.METRIC,
                    spec=ServerlessSpec(
                        cloud=self.config.CLOUD,
                        region=self.config.REGION
                    )
                )
                logger.info(f"✅ Created Pinecone index: {self.config.index_name}")
            else:
                logger.info(f"✅ Pinecone index already exists: {self.config.index_name}")
                
        except Exception as e:
            logger.error(f"❌ Failed to ensure index exists: {str(e)}")
            raise
    
    def is_available(self) -> bool:
        """Check if Pinecone service is available."""
        return self.pc is not None and self.index is not None and self.openai_client is not None
    
    def generate_embeddings(self, text: str) -> List[float]:
        """Generate embeddings for text using OpenAI."""
        try:
            if not self.openai_client:
                raise Exception("OpenAI client not initialized")
            
            response = self.openai_client.embeddings.create(
                model=self.config.EMBEDDING_MODEL,
                input=text.strip(),
                dimensions=self.config.EMBEDDING_DIMENSIONS
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"❌ Failed to generate embeddings: {str(e)}")
            raise
    
    def create_document_chunks(self, content: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split document content into chunks for better indexing."""
        if len(content) <= chunk_size:
            return [content]
        
        chunks = []
        start = 0
        
        while start < len(content):
            end = start + chunk_size
            
            # Try to break at sentence boundaries
            if end < len(content):
                # Look for sentence ending within the last 100 characters
                sentence_end = content.rfind('.', start, end)
                if sentence_end > start + chunk_size - 100:
                    end = sentence_end + 1
            
            chunk = content[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
            
        return chunks
    
    def index_document(
        self, 
        document_id: str, 
        file_name: str, 
        file_type: str,
        content: str, 
        user_id: int,
        username: str,
        file_url: str
    ) -> Dict[str, Any]:
        """Index a document in Pinecone."""
        try:
            if not self.is_available():
                raise Exception("Pinecone service not available")
            
            logger.info(f"🔄 Indexing document: {file_name}")
            
            # Create document chunks
            chunks = self.create_document_chunks(content)
            logger.info(f"📄 Created {len(chunks)} chunks for document")
            
            # Prepare vectors for upsert
            vectors = []
            
            for i, chunk in enumerate(chunks):
                # Generate unique ID for each chunk
                chunk_id = f"{document_id}_chunk_{i}"
                
                # Generate embeddings
                embeddings = self.generate_embeddings(chunk)
                
                # Prepare metadata
                metadata = {
                    'document_id': document_id,
                    'file_name': file_name,
                    'file_type': file_type,
                    'chunk_index': i,
                    'chunk_content': chunk[:500],  # Store first 500 chars for preview
                    'content_length': len(chunk),
                    'user_id': user_id,
                    'username': username,
                    'file_url': file_url,
                    'indexed_at': datetime.utcnow().isoformat()
                }
                
                vectors.append({
                    'id': chunk_id,
                    'values': embeddings,
                    'metadata': metadata
                })
            
            # Upsert vectors to Pinecone
            self.index.upsert(
                vectors=vectors,
                namespace=self.config.PDFS_NAMESPACE
            )
            
            logger.info(f"✅ Successfully indexed {len(vectors)} chunks for document: {file_name}")
            
            return {
                'success': True,
                'chunks_indexed': len(vectors),
                'document_id': document_id,
                'namespace': self.config.PDFS_NAMESPACE
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to index document {file_name}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'chunks_indexed': 0
            }
    
    def search_documents(
        self, 
        query: str, 
        user_id: Optional[int] = None,
        top_k: int = 10,  # Increased from 5 to get more chunks
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """Search comprehensively across all document chunks based on query."""
        try:
            if not self.is_available():
                raise Exception("Pinecone service not available")
            
            logger.info(f"🔍 Searching ALL document chunks for query: {query[:50]}...")
            
            # Generate query embeddings
            query_embeddings = self.generate_embeddings(query)
            
            # Prepare filter for user-specific search
            filter_dict = {}
            if user_id:
                filter_dict['user_id'] = user_id
            
            # Search in Pinecone with broader parameters for comprehensive search
            search_results = self.index.query(
                vector=query_embeddings,
                top_k=min(top_k, self.config.MAX_TOP_K),
                namespace=self.config.PDFS_NAMESPACE,
                include_metadata=include_metadata,
                filter=filter_dict if filter_dict else None
            )
            
            # Process results with lower threshold to get more chunks
            relevant_docs = []
            for match in search_results['matches']:
                # Lowered threshold from 0.7 to 0.6 to include more potentially relevant chunks
                if match['score'] >= 0.6:  # More inclusive threshold for comprehensive search
                    doc_info = {
                        'document_id': match['metadata']['document_id'],
                        'file_name': match['metadata']['file_name'],
                        'file_type': match['metadata']['file_type'],
                        'chunk_content': match['metadata']['chunk_content'],
                        'score': match['score'],
                        'file_url': match['metadata']['file_url'],
                        'username': match['metadata']['username']
                    }
                    relevant_docs.append(doc_info)
            
            logger.info(f"✅ Found {len(relevant_docs)} relevant document chunks from comprehensive search")
            
            return {
                'success': True,
                'query': query,
                'results': relevant_docs,
                'total_results': len(relevant_docs)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to search document chunks: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'results': [],
                'total_results': 0
            }
    
    def delete_document(self, document_id: str) -> Dict[str, Any]:
        """Delete a document and all its chunks from Pinecone."""
        try:
            if not self.is_available():
                raise Exception("Pinecone service not available")
            
            logger.info(f"🗑️ Deleting document: {document_id}")
            
            # Delete all chunks for this document
            # First, find all chunk IDs for this document
            search_results = self.index.query(
                vector=[0] * self.config.DIMENSION,  # Dummy vector
                top_k=10000,  # Large number to get all chunks
                namespace=self.config.PDFS_NAMESPACE,
                include_metadata=True,
                filter={'document_id': document_id}
            )
            
            # Extract chunk IDs
            chunk_ids = [match['id'] for match in search_results['matches']]
            
            if chunk_ids:
                # Delete chunks
                self.index.delete(
                    ids=chunk_ids,
                    namespace=self.config.PDFS_NAMESPACE
                )
                
                logger.info(f"✅ Deleted {len(chunk_ids)} chunks for document: {document_id}")
                
                return {
                    'success': True,
                    'chunks_deleted': len(chunk_ids),
                    'document_id': document_id
                }
            else:
                logger.warning(f"⚠️ No chunks found for document: {document_id}")
                return {
                    'success': True,
                    'chunks_deleted': 0,
                    'document_id': document_id
                }
            
        except Exception as e:
            logger.error(f"❌ Failed to delete document {document_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'chunks_deleted': 0
            }
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the Pinecone index."""
        try:
            if not self.is_available():
                return {'error': 'Pinecone service not available'}
            
            stats = self.index.describe_index_stats()
            
            return {
                'total_vectors': stats['total_vector_count'],
                'namespaces': stats['namespaces'],
                'dimension': stats['dimension'],
                'index_name': self.config.index_name
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get index stats: {str(e)}")
            return {'error': str(e)}


# Create a global service instance
pinecone_service = PineconeService()
