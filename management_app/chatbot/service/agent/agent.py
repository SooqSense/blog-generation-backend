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
                    "score": res.get("score")
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
                    "sources": [],
                }

            docs = self._results_to_documents(search_result["results"])

            # Step 2: Build context prompt for the LLM
            context_text = "\n\n".join([d.page_content for d in docs[:top_k]])
            prompt = f"""
You are an AI assistant helping sales teams explore project portfolios.

User question: {query}

Relevant project information (from company documents):
{context_text}

Answer the question based on the information above.
- Be clear and professional.
- Highlight project names, technologies, challenges, or results if available.
- If there are multiple projects, summarize them.
- At the end, list the sources used (file names).
"""

            # Step 3: Generate response
            llm_response = self.llm.invoke(prompt)

            # Step 4: Build structured return
            sources = [
                {
                    "file_name": d.metadata.get("file_name", "Unknown"),
                    "file_type": d.metadata.get("file_type", "Unknown"),
                    "file_url": d.metadata.get("file_url", ""),
                    "score": d.metadata.get("score", 0)
                }
                for d in docs
            ]

            return {
                "success": True,
                "response": llm_response.content,
                "sources": sources,
                "processing_time": round(time.time() - start, 2),
                "query": query
            }

        except Exception as e:
            logger.error(f"❌ Chatbot error: {str(e)}")
            return {
                "success": False,
                "response": "Something went wrong while processing your request.",
                "error": str(e),
                "sources": []
            }


# Create global chatbot instance
project_chatbot = ProjectChatbot()
