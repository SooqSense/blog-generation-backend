"""
LangChain-based ProjectChatbot that uses PineconeService for knowledge base retrieval.
Optimized with async support for real-time streaming.
"""

import time
import logging
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator

from langchain_openai import ChatOpenAI
from langchain.schema import Document

# Import your PineconeService
from management_app.knowledge_base.service.pinecone_indexing.pinecone_indexing import PineconeService
# Import prompts
from ..prompts.prompts import ChatbotPrompts


logger = logging.getLogger(__name__)


class ProjectChatbot:
    """Chatbot that answers portfolio/project queries using PineconeService."""

    def __init__(self):
        self.model_name = "gpt-4o-mini"   # fast and cheap model for QA
        self.llm = ChatOpenAI(model=self.model_name, temperature=0.7)
        self.pinecone_service = PineconeService()

    def is_available(self) -> bool:
        """Check if chatbot service is available (Pinecone + OpenAI)."""
        return self.pinecone_service.is_available() and self.llm is not None

    # --- Helper: Convert Pinecone search results to LangChain Documents ---
    def _results_to_documents(self, results: List[Dict[str, Any]]) -> List[Document]:
        docs = []
        for res in results:
            docs.append(Document(
                page_content=res.get("chunk_content", ""),
                metadata={
                    "file_name": res.get("file_name"),
                    "file_type": res.get("file_type"),
                    "file_url": res.get("file_url"),
                    "chunk_index": res.get("chunk_index"),
                    "score": res.get("score"),
                    "links": res.get("links", [])
                }
            ))
        return docs

    # --- Main query method ---
    def ask(
        self,
        query: str,
        top_k: int = 10,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Answer a query using PineconeService for retrieval + LLM for synthesis."""
        start = time.time()

        if not self.is_available():
            return {
                "success": False,
                "response": "Chatbot is not available. Please check Pinecone and OpenAI.",
                "sources": [],
            }

        try:
            # Step 1: Search Pinecone via PineconeService
            search_result = self.pinecone_service.search_documents(
                query=query,
                top_k=top_k
            )

            if not search_result.get("success") or not search_result.get("results"):
                return {
                    "success": True,
                    "response": "I could not find any relevant information for your query.",
                    "documents_found": 0,
                }

            docs = self._results_to_documents(search_result["results"])

            # Step 2: Build context prompt for the LLM
            context_parts = []
            all_links = []
            for d in docs[:top_k]:
                context_parts.append(d.page_content)
                # Collect unique links from all documents
                doc_links = d.metadata.get("links", [])
                if doc_links:
                    all_links.extend([link for link in doc_links if link not in all_links])
            
            context_text = "\n\n".join(context_parts)
            
            # Add links section to context if available
            links_section = ""
            if all_links:
                links_section = f"\n\nRelevant Links from Documents:\n" + "\n".join([f"- {link}" for link in all_links])
            
            # Use prompt from prompts.py
            prompt = ChatbotPrompts.get_portfolio_query_prompt(query, context_text, links_section)

            # Step 3: Generate response
            llm_response = self.llm.invoke(prompt)

            # Step 4: Build structured return (no sources, links are integrated in response)
            return {
                "success": True,
                "response": llm_response.content,
                "processing_time": round(time.time() - start, 2),
                "query": query,
                "documents_found": len(docs)
            }

        except Exception as e:
            logger.error(f"❌ Chatbot error: {str(e)}")
            return {
                "success": False,
                "response": "Something went wrong while processing your request.",
                "error": str(e),
                "documents_found": 0
            }

    # --- Streaming query method (SYNC - kept for backward compatibility) ---
    def ask_stream(
        self,
        query: str,
        top_k: int = 10,
        user_id: Optional[int] = None
    ):
        """Generator that streams response chunks for a query.

        Yields plain text chunks from the LLM as they arrive. The caller is responsible
        for wrapping these into SSE or any transport format.
        """
        start = time.time()

        if not self.is_available():
            yield "[ERROR] Chatbot is not available. Please check Pinecone and OpenAI."
            return

        try:
            # Step 1: Retrieval
            search_result = self.pinecone_service.search_documents(
                query=query,
                top_k=top_k
            )

            # If no docs, stream a short notice and finish
            if not search_result.get("success") or not search_result.get("results"):
                yield "I could not find any relevant information for your query."
                return

            docs = self._results_to_documents(search_result["results"])

            # Step 2: Build prompt with links aggregated
            context_parts = []
            all_links = []
            for d in docs[:top_k]:
                context_parts.append(d.page_content)
                doc_links = d.metadata.get("links", [])
                if doc_links:
                    all_links.extend([link for link in doc_links if link not in all_links])

            context_text = "\n\n".join(context_parts)
            links_section = ""
            if all_links:
                links_section = "\n\nRelevant Links from Documents:\n" + "\n".join([f"- {link}" for link in all_links])

            prompt = ChatbotPrompts.get_portfolio_query_prompt(query, context_text, links_section)

            # Step 3: Stream from LLM
            accumulated = []
            for chunk in self.llm.stream(prompt):
                content = getattr(chunk, "content", None)
                if content:
                    # Ensure proper UTF-8 encoding
                    content = str(content).encode('utf-8').decode('utf-8')
                    accumulated.append(content)
                    yield content

            # Final marker (optional; caller may not need)
            total = "".join(accumulated)
            yield ""  # Ensure generator completes cleanly

        except Exception as e:
            logger.error(f"❌ Chatbot streaming error: {str(e)}")
            yield "[ERROR] Something went wrong while processing your request."
    
    # --- ASYNC Streaming query method (OPTIMIZED for real-time) ---
    async def ask_stream_async(
        self,
        query: str,
        top_k: int = 10,
        user_id: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        """Async generator that streams response chunks for a query in real-time.
        
        This is optimized to start streaming immediately while doing retrieval in parallel.
        """
        start = time.time()

        if not self.is_available():
            yield "[ERROR] Chatbot is not available. Please check Pinecone and OpenAI."
            return

        try:
            # Step 1: Run retrieval in thread pool (non-blocking)
            loop = asyncio.get_event_loop()
            search_result = await loop.run_in_executor(
                None, 
                self.pinecone_service.search_documents,
                query,
                top_k
            )

            # If no docs, stream a short notice and finish
            if not search_result.get("success") or not search_result.get("results"):
                yield "I could not find any relevant information for your query."
                return

            docs = self._results_to_documents(search_result["results"])
            logger.info(f"✅ Found {len(docs)} relevant chunks")

            # Step 2: Build prompt with links aggregated
            context_parts = []
            all_links = []
            for d in docs[:top_k]:
                context_parts.append(d.page_content)
                doc_links = d.metadata.get("links", [])
                if doc_links:
                    all_links.extend([link for link in doc_links if link not in all_links])

            context_text = "\n\n".join(context_parts)
            links_section = ""
            if all_links:
                links_section = "\n\nRelevant Links from Documents:\n" + "\n".join([f"- {link}" for link in all_links])

            prompt = ChatbotPrompts.get_portfolio_query_prompt(query, context_text, links_section)

            # Step 3: Stream from LLM using async streaming
            accumulated = []
            async for chunk in self.llm.astream(prompt):
                content = getattr(chunk, "content", None)
                if content:
                    # Ensure proper UTF-8 encoding
                    content = str(content).encode('utf-8').decode('utf-8')
                    accumulated.append(content)
                    yield content

            # Final marker
            yield ""

        except Exception as e:
            logger.error(f"❌ Chatbot async streaming error: {str(e)}", exc_info=True)
            yield "[ERROR] Something went wrong while processing your request."


# Create global chatbot instance
project_chatbot = ProjectChatbot()
