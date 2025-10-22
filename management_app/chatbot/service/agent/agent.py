"""
LangChain-based ProjectChatbot that uses PineconeService for knowledge base retrieval.
"""

import time
import logging
from typing import Dict, Any, List, Optional

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


# Create global chatbot instance
project_chatbot = ProjectChatbot()
