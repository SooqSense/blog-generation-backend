# project_chatbot.py
import asyncio
import logging
from typing import Optional, AsyncGenerator, Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain.schema import Document
from management_app.knowledge_base.service.pinecone_indexing.pinecone_indexing import PineconeService
from ..prompts.prompts import ChatbotPrompts

logger = logging.getLogger(__name__)

class ProjectChatbot:
    def __init__(self):
        self.model_name = "gpt-4o-mini"
        self.llm = ChatOpenAI(
            model=self.model_name,
            temperature=0.3,
            max_tokens=700,
            timeout=20,
        )
        self.pinecone_service = PineconeService()

    def is_available(self) -> bool:
        return self.pinecone_service.is_available() and self.llm is not None

    def _results_to_documents(self, results: List[Dict[str, Any]]) -> List[Document]:
        return [
            Document(
                page_content=r.get("chunk_content", "") or "",
                metadata={
                    "file_name": r.get("file_name"),
                    "file_type": r.get("file_type"),
                    "file_url": r.get("file_url"),
                    "chunk_index": r.get("chunk_index"),
                    "score": r.get("score"),
                    "links": r.get("links", []) or [],
                },
            )
            for r in results
        ]

    async def ask_stream_async(
        self,
        query: str,
        top_k: int = 10,
        user_id: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        if not self.is_available():
            yield "[ERROR] Chatbot is not available. Please check Pinecone and OpenAI."
            return

        try:
            # Run blocking Pinecone search off the event loop
            loop = asyncio.get_running_loop()
            search_result = await loop.run_in_executor(
                None, self.pinecone_service.search_documents, query, top_k
            )

            if not search_result.get("success") or not search_result.get("results"):
                yield "I could not find any relevant information for your query."
                return

            docs = self._results_to_documents(search_result["results"])

            context_parts, all_links = [], []
            for d in docs[:top_k]:
                context_parts.append(d.page_content)
                all_links.extend([l for l in d.metadata.get("links", []) if l not in all_links])

            context_text = "\n\n".join(context_parts)
            links_section = ("\n\nRelevant Links from Documents:\n" +
                             "\n".join(f"- {l}" for l in all_links)) if all_links else ""

            prompt = ChatbotPrompts.get_portfolio_query_prompt(query, context_text, links_section)

            async for chunk in self.llm.astream(prompt):
                content = getattr(chunk, "content", None)
                if content:
                    yield str(content)

            # Optional EOF marker for some clients
            yield ""
        except Exception as e:
            logger.error(f"Chatbot async streaming error: {e}", exc_info=True)
            yield "[ERROR] Something went wrong while processing your request."
