"""
Pinecone service for PDF document indexing and querying.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI

# Import the shared config
from management_app.pinecone_integration.config.config import config

logger = logging.getLogger(__name__)


class PineconeService:
    """Service for handling Pinecone operations for PDF documents."""

    def __init__(self):
        self.config = config
        self.pc = None
        self.index = None
        self.openai_client = None
        self._initialize_clients()

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _initialize_clients(self):
        """Initialize Pinecone and OpenAI clients."""
        try:
            logger.info("🔄 Initializing Pinecone and OpenAI clients...")

            # Initialize Pinecone
            self.pc = Pinecone(api_key=self.config.PINECONE_API_KEY)
            self._ensure_index_exists()

            index_info = self.pc.describe_index(self.config.INDEX_NAME)
            if index_info.status["ready"]:
                self.index = self.pc.Index(self.config.INDEX_NAME)
                logger.info(f"✅ Connected to Pinecone index: {self.config.INDEX_NAME}")
            else:
                logger.warning(f"⚠️ Pinecone index {self.config.INDEX_NAME} is not ready")

            # Initialize OpenAI
            self.openai_client = OpenAI(api_key=self.config.OPENAI_API_KEY)
            logger.info("✅ OpenAI client initialized")

        except Exception as e:
            logger.error(f"❌ Failed to initialize Pinecone/OpenAI clients: {e}")

    def _ensure_index_exists(self):
        """Ensure the Pinecone index exists, create it if it doesn't."""
        try:
            existing_indexes = [i.name for i in self.pc.list_indexes()]
            if self.config.INDEX_NAME not in existing_indexes:
                logger.info(f"🆕 Creating Pinecone index: {self.config.INDEX_NAME}")
                self.pc.create_index(
                    name=self.config.INDEX_NAME,
                    dimension=self.config.DIMENSION,
                    metric=self.config.METRIC,
                    spec=ServerlessSpec(
                        cloud=self.config.CLOUD,
                        region=self.config.REGION,
                    ),
                )
                logger.info(f"✅ Created Pinecone index: {self.config.INDEX_NAME}")
            else:
                logger.info(f"✅ Pinecone index already exists: {self.config.INDEX_NAME}")
        except Exception as e:
            logger.error(f"❌ Failed to ensure index exists: {e}")
            raise

    # -------------------------------------------------------------------------
    # Utilities
    # -------------------------------------------------------------------------

    def is_available(self) -> bool:
        """Check if Pinecone and OpenAI clients are available."""
        return self.pc is not None and self.index is not None and self.openai_client is not None

    def generate_embeddings(self, text: str) -> List[float]:
        """Generate embeddings using OpenAI."""
        try:
            response = self.openai_client.embeddings.create(
                model=self.config.EMBEDDING_MODEL,
                input=text.strip(),
                dimensions=self.config.EMBEDDING_DIMENSIONS,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"❌ Failed to generate embeddings: {e}")
            raise

    def create_document_chunks(self, content: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks."""
        if len(content) <= chunk_size:
            return [content]

        chunks, start = [], 0
        while start < len(content):
            end = start + chunk_size
            if end < len(content):
                sentence_end = content.rfind(".", start, end)
                if sentence_end > start + chunk_size - 100:
                    end = sentence_end + 1
            chunk = content[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = end - overlap
        return chunks

    # -------------------------------------------------------------------------
    # Indexing
    # -------------------------------------------------------------------------

    def index_document(
        self,
        document_id: str,
        file_name: str,
        file_type: str,
        content: str,
        user_id: int,
        username: str,
        file_url: str,
        directory_name: str = None,
        document_links: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Index a document's content in Pinecone with directory support."""
        try:
            if not self.is_available():
                raise Exception("Pinecone service not available")

            logger.info(f"📄 Indexing document: {file_name} (directory: {directory_name}) in single PDFS namespace")
            chunks = self.create_document_chunks(content)
            vectors = []

            # Always use single PDFS namespace for all documents
            namespace = self.config.PDFS_NAMESPACE

            for i, chunk in enumerate(chunks):
                chunk_id = f"{document_id}_chunk_{i}"
                embeddings = self.generate_embeddings(chunk)
                metadata = {
                    "document_id": document_id,
                    "file_name": file_name,
                    "file_type": file_type,
                    "chunk_index": i,
                    "chunk_content": chunk,
                    "content_length": len(chunk),
                    "user_id": user_id,
                    "username": username,
                    "file_url": file_url,
                    "directory_name": directory_name or "default",
                    "indexed_at": datetime.utcnow().isoformat(),
                    "links": document_links or [],
                }
                vectors.append({"id": chunk_id, "values": embeddings, "metadata": metadata})

            self.index.upsert(vectors=vectors, namespace=namespace)
            logger.info(f"✅ Indexed {len(vectors)} chunks for {file_name} in single PDFS namespace")

            return {
                "success": True, 
                "chunks_indexed": len(vectors), 
                "document_id": document_id,
                "namespace": namespace
            }

        except Exception as e:
            logger.error(f"❌ Failed to index document {file_name}: {e}")
            return {"success": False, "error": str(e), "chunks_indexed": 0, "document_id": document_id}

    # -------------------------------------------------------------------------
    # Search
    # -------------------------------------------------------------------------

    def search_documents(
        self,
        query: str,
        top_k: int = 15,
        include_metadata: bool = True,
    ) -> Dict[str, Any]:
        """Perform semantic search in Pinecone."""
        try:
            if not self.is_available():
                raise Exception("Pinecone service not available")

            query_embeddings = self.generate_embeddings(query)
            search_results = self.index.query(
                vector=query_embeddings,
                top_k=min(top_k, self.config.MAX_TOP_K),
                namespace=self.config.PDFS_NAMESPACE,
                include_metadata=include_metadata,
            )

            relevant_docs = []
            for match in search_results.get("matches", []):
                score = match.get("score", 0)
                if score >= 0.2:
                    meta = match["metadata"]
                    relevant_docs.append({
                        "id": match["id"],
                        "document_id": meta["document_id"],
                        "file_name": meta["file_name"],
                        "chunk_index": meta.get("chunk_index", 0),
                        "chunk_content": meta.get("chunk_content", ""),
                        "score": score,
                        "file_url": meta["file_url"],
                        "username": meta["username"],
                        "links": meta.get("links", []),
                    })

            relevant_docs.sort(key=lambda x: (x["file_name"], x["chunk_index"]))
            logger.info(f"✅ Found {len(relevant_docs)} relevant chunks")
            return {"success": True, "results": relevant_docs, "total_results": len(relevant_docs)}

        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            return {"success": False, "error": str(e), "results": []}

    def delete_document(self, document_id: str, namespace: str = None, file_name: str = None) -> Dict[str, Any]:
        """
        Delete all vectors for a document from Pinecone.
        
        This method safely deletes only the chunks belonging to a specific document,
        NOT the entire namespace. It uses metadata filtering to ensure precise deletion.
        
        Args:
            document_id: The document ID (primary filter)
            namespace: The namespace where the document is indexed
            file_name: Optional file name to filter by (for additional safety/verification)
            
        Returns:
            Dict with success status and message
        """
        try:
            if not self.is_available():
                raise Exception("Pinecone service not available")
            
            # Use provided namespace or default
            ns = namespace if namespace else self.config.PDFS_NAMESPACE
            
            # Build filter criteria - prioritize document_id, add file_name if provided
            filter_criteria = {"document_id": document_id}
            if file_name:
                filter_criteria["file_name"] = file_name
            
            # Query to find all vectors with this document_id (and optionally file_name)
            query_response = self.index.query(
                vector=[0] * self.config.DIMENSION,  # Dummy vector
                filter=filter_criteria,
                top_k=10000,  # Large number to get all chunks
                namespace=ns,
                include_metadata=False
            )
            
            if query_response and 'matches' in query_response:
                vector_ids = [match['id'] for match in query_response['matches']]
                
                if vector_ids:
                    # Delete the vectors
                    self.index.delete(ids=vector_ids, namespace=ns)
                    filter_info = f"document_id={document_id}"
                    if file_name:
                        filter_info += f", file_name={file_name}"
                    logger.info(f"✅ Deleted {len(vector_ids)} vectors for {filter_info} from namespace: {ns}")
                    
                    return {
                        "success": True,
                        "vectors_deleted": len(vector_ids),
                        "document_id": document_id,
                        "file_name": file_name,
                        "namespace": ns
                    }
                else:
                    filter_info = f"document_id={document_id}"
                    if file_name:
                        filter_info += f", file_name={file_name}"
                    logger.warning(f"⚠️ No vectors found for {filter_info} in namespace: {ns}")
                    return {
                        "success": True,
                        "vectors_deleted": 0,
                        "document_id": document_id,
                        "file_name": file_name,
                        "namespace": ns,
                        "message": "No vectors found to delete"
                    }
            else:
                filter_info = f"document_id={document_id}"
                if file_name:
                    filter_info += f", file_name={file_name}"
                logger.warning(f"⚠️ No vectors found for {filter_info}")
                return {
                    "success": True,
                    "vectors_deleted": 0,
                    "document_id": document_id,
                    "file_name": file_name,
                    "namespace": ns,
                    "message": "No vectors found to delete"
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to delete document {document_id} from Pinecone: {e}")
            return {
                "success": False,
                "error": str(e),
                "vectors_deleted": 0,
                "document_id": document_id
            }

    def delete_document_by_filename(self, file_name: str, namespace: str = None) -> Dict[str, Any]:
        """
        Delete all vectors for a document by file name from Pinecone.
        This is an alternative method that filters only by file_name.
        
        Args:
            file_name: The file name to delete
            namespace: The namespace where the document is indexed
            
        Returns:
            Dict with success status and message
        """
        try:
            if not self.is_available():
                raise Exception("Pinecone service not available")
            
            # Use provided namespace or default
            ns = namespace if namespace else self.config.PDFS_NAMESPACE
            
            # Query to find all vectors with this file_name
            query_response = self.index.query(
                vector=[0] * self.config.DIMENSION,  # Dummy vector
                filter={"file_name": file_name},
                top_k=10000,  # Large number to get all chunks
                namespace=ns,
                include_metadata=False
            )
            
            if query_response and 'matches' in query_response:
                vector_ids = [match['id'] for match in query_response['matches']]
                
                if vector_ids:
                    # Delete the vectors
                    self.index.delete(ids=vector_ids, namespace=ns)
                    logger.info(f"✅ Deleted {len(vector_ids)} vectors for file_name={file_name} from namespace: {ns}")
                    
                    return {
                        "success": True,
                        "vectors_deleted": len(vector_ids),
                        "file_name": file_name,
                        "namespace": ns
                    }
                else:
                    logger.warning(f"⚠️ No vectors found for file_name={file_name} in namespace: {ns}")
                    return {
                        "success": True,
                        "vectors_deleted": 0,
                        "file_name": file_name,
                        "namespace": ns,
                        "message": "No vectors found to delete"
                    }
            else:
                logger.warning(f"⚠️ No vectors found for file_name={file_name}")
                return {
                    "success": True,
                    "vectors_deleted": 0,
                    "file_name": file_name,
                    "namespace": ns,
                    "message": "No vectors found to delete"
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to delete document by filename {file_name} from Pinecone: {e}")
            return {
                "success": False,
                "error": str(e),
                "vectors_deleted": 0,
                "file_name": file_name
            }

    # -------------------------------------------------------------------------
    # Maintenance
    # -------------------------------------------------------------------------

    def get_index_stats(self) -> Dict[str, Any]:
        """Return Pinecone index stats."""
        try:
            stats = self.index.describe_index_stats()
            return {
                "total_vectors": stats["total_vector_count"],
                "namespaces": stats["namespaces"],
                "dimension": stats["dimension"],
                "index_name": self.config.INDEX_NAME,
            }
        except Exception as e:
            logger.error(f"❌ Failed to get index stats: {e}")
            return {"error": str(e)}


# Singleton instance
pinecone_service = PineconeService()
