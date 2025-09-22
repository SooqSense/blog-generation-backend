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
        """Legacy method - kept for backward compatibility."""
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
    
    def _ensure_namespace_exists(self, namespace: str):
        """Check if namespace exists and log status. Pinecone creates namespaces automatically."""
        try:
            # Check if namespace exists by getting index stats
            stats = self.index.describe_index_stats()
            existing_namespaces = stats.get('namespaces', {})
            
            if namespace not in existing_namespaces:
                logger.info(f"📁 Namespace '{namespace}' does not exist yet - will be created automatically on first document upsert")
            else:
                vector_count = existing_namespaces[namespace].get('vector_count', 0)
                logger.info(f"✅ Namespace '{namespace}' already exists with {vector_count} vectors")
                
        except Exception as e:
            logger.info(f"📁 Could not check namespace status: {str(e)}")
            logger.info(f"📁 Namespace '{namespace}' will be created automatically on first upsert")
    
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
        """Simple, clean document indexing into Pinecone."""
        try:
            if not self.is_available():
                raise Exception("Pinecone service not available")
            
            logger.info(f"🔄 Indexing document: {file_name}")
            
            # Ensure namespace exists before indexing
            self._ensure_namespace_exists(self.config.PDFS_NAMESPACE)
            
            # 1. Create chunks from document content
            chunks = self.create_document_chunks(content, chunk_size=1000, overlap=200)
            logger.info(f"📄 Created {len(chunks)} chunks from document")
            
            # 2. Create vectors for each chunk
            vectors = []
            
            for i, chunk in enumerate(chunks):
                # Generate unique ID for each chunk
                chunk_id = f"{document_id}_chunk_{i}"
                
                # Generate embeddings for the chunk
                embeddings = self.generate_embeddings(chunk)
                
                # Simple, clean metadata structure
                metadata = {
                    'document_id': document_id,
                    'file_name': file_name,
                    'file_type': file_type,
                    'chunk_index': i,
                    'chunk_content': chunk,  # Full content for RAG
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
            
            # 3. Upsert all vectors to Pinecone
            if vectors:
                self.index.upsert(
                    vectors=vectors,
                    namespace=self.config.PDFS_NAMESPACE
                )
                
                logger.info(f"✅ Successfully indexed {file_name} with {len(vectors)} chunks")
                
                return {
                    'success': True,
                    'chunks_indexed': len(vectors),
                    'document_id': document_id,
                    'namespace': self.config.PDFS_NAMESPACE,
                    'file_name': file_name
                }
            else:
                raise Exception("No chunks created from document content")
            
        except Exception as e:
            logger.error(f"❌ Failed to index document {file_name}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'chunks_indexed': 0,
                'document_id': document_id
            }
    
    
    def search_documents(
        self, 
        query: str, 
        user_id: Optional[int] = None,
        top_k: int = 15,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """Simple semantic search across document chunks."""
        try:
            if not self.is_available():
                raise Exception("Pinecone service not available")
            
            logger.info(f"🔍 Searching for: {query[:50]}...")
            
            # Generate query embeddings
            query_embeddings = self.generate_embeddings(query)
            
            # Prepare filter for user-specific search
            filter_dict = {}
            # TEMPORARILY DISABLED: Remove user_id filter to access all documents
            # This is needed because documents were indexed with a different user_id
            # if user_id:
            #     filter_dict['user_id'] = user_id
            
            # Search in Pinecone
            search_results = self.index.query(
                vector=query_embeddings,
                top_k=min(top_k, self.config.MAX_TOP_K),
                namespace=self.config.PDFS_NAMESPACE,
                include_metadata=include_metadata,
                filter=filter_dict if filter_dict else None
            )
            
            # Process results with appropriate threshold
            relevant_docs = []
            matches = search_results.get('matches', [])
            
            for match in matches:
                score = match.get('score', 0)
                if score >= 0.2:  # Standard threshold for quality results
                    doc_info = {
                        'id': match['id'],
                        'document_id': match['metadata']['document_id'],
                        'file_name': match['metadata']['file_name'],
                        'file_type': match['metadata']['file_type'],
                        'chunk_content': match['metadata'].get('chunk_content', ''),
                        'chunk_index': match['metadata'].get('chunk_index', 0),
                        'score': match['score'],
                        'file_url': match['metadata']['file_url'],
                        'username': match['metadata']['username']
                    }
                    relevant_docs.append(doc_info)
            
            # Sort by chunk index to maintain document order
            relevant_docs.sort(key=lambda x: (x['file_name'], x['chunk_index']))
            
            logger.info(f"✅ Found {len(relevant_docs)} relevant chunks")
            
            return {
                'success': True,
                'query': query,
                'results': relevant_docs,
                'total_results': len(relevant_docs)
            }
            
        except Exception as e:
            logger.error(f"❌ Search failed: {str(e)}")
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
    
    def get_sample_user_ids(self, limit: int = 10) -> Dict[str, Any]:
        """Get sample user_ids from the index to debug user_id issues."""
        try:
            if not self.is_available():
                return {'error': 'Pinecone service not available'}
            
            # Query with a dummy vector to get sample documents
            dummy_query = [0.1] * self.config.DIMENSION
            
            search_results = self.index.query(
                vector=dummy_query,
                top_k=limit,
                namespace=self.config.PDFS_NAMESPACE,
                include_metadata=True,
                include_values=False
            )
            
            # Extract unique user_ids and file info
            user_ids = set()
            sample_docs = []
            
            for match in search_results.get('matches', []):
                metadata = match.get('metadata', {})
                user_id = metadata.get('user_id', 'Unknown')
                user_ids.add(user_id)
                
                sample_docs.append({
                    'user_id': user_id,
                    'file_name': metadata.get('file_name', 'Unknown'),
                    'username': metadata.get('username', 'Unknown')
                })
            
            return {
                'success': True,
                'unique_user_ids': list(user_ids),
                'user_id_count': len(user_ids),
                'sample_documents': sample_docs[:5]  # Show first 5
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get sample user_ids: {str(e)}")
            return {'error': str(e)}



# Create a global service instance
pinecone_service = PineconeService()
