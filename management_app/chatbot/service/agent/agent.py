# project_chatbot.py
"""
Async-only ProjectChatbot for streaming answers with Pinecone retrieval.
- Removes sync code (ask / ask_stream)
- Uses run_in_executor for non-async Pinecone
- Dedups links and trims context to a rough token budget
- Keeps the public surface minimal
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, AsyncGenerator, Tuple

from langchain_openai import ChatOpenAI
from langchain.schema import Document

from management_app.knowledge_base.service.pinecone_indexing.pinecone_indexing import PineconeService
from ..prompts.prompts import ChatbotPrompts

logger = logging.getLogger(__name__)

# Optional token counting if tiktoken is available
try:
    import tiktoken
except Exception:
    tiktoken = None


@dataclass
class ModelConfig:
    model: str = "gpt-4o-mini"
    temperature: float = 0.3
    max_output_tokens: int = 700
    request_timeout: int = 20
    # keep input compact so prompts don’t balloon
    max_input_tokens: int = 6000
    max_docs_for_context: int = 12


class ProjectChatbot:
    """Async streaming chatbot using Pinecone + OpenAI."""

    def __init__(
        self,
        pinecone_service: Optional[PineconeService] = None,
        config: Optional[ModelConfig] = None,
    ):
        self.config = config or ModelConfig()
        self.llm = ChatOpenAI(
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_output_tokens,
            timeout=self.config.request_timeout,
        )
        self.pinecone_service = pinecone_service or PineconeService()
        self._encoding = self._get_encoding()

    # ---------- public ----------

    def is_available(self) -> bool:
        return self.pinecone_service.is_available() and self.llm is not None

    async def ask_stream_async(
        self,
        query: str,
        top_k: int = 10,
        user_id: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream the final answer as it’s generated."""
        if not self.is_available():
            yield "[ERROR] Chatbot is not available. Please check Pinecone and OpenAI."
            return

        try:
            # 1) Retrieval off the event loop
            loop = asyncio.get_running_loop()
            search_result = await loop.run_in_executor(
                None, self.pinecone_service.search_documents, query, top_k
            )

            if not search_result.get("success") or not search_result.get("results"):
                yield "I could not find any relevant information for your query."
                return

            docs = self._results_to_documents(search_result["results"])

            # 2) Build compact context + links
            context_text, links_section = self._build_prompt_context(docs, query, top_k)

            # 3) Prompt and stream
            prompt = ChatbotPrompts.get_portfolio_query_prompt(
                query, context_text, links_section
            )

            async for chunk in self.llm.astream(prompt):
                content = getattr(chunk, "content", None)
                if content:
                    yield str(content)

            # Optional EOF marker (some clients expect it)
            yield ""

        except Exception as e:
            logger.error("❌ Chatbot async streaming error", exc_info=True)
            yield "[ERROR] Something went wrong while processing your request."

    # ---------- internals ----------

    @staticmethod
    def _results_to_documents(results: List[Dict[str, Any]]) -> List[Document]:
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

    def _build_prompt_context(
        self, docs: List[Document], query: str, top_k: int
    ) -> Tuple[str, str]:
        """Trim docs to a token budget and attach a deduped links section."""
        # cap how many chunks we even consider
        docs = docs[: min(top_k, self.config.max_docs_for_context)]

        # collect unique links
        seen = set()
        links = []
        for d in docs:
            for l in d.metadata.get("links", []):
                if l and l not in seen:
                    seen.add(l)
                    links.append(l)

        # assemble small labeled blocks so the model can cite implicitly
        blocks = []
        for i, d in enumerate(docs, 1):
            name = d.metadata.get("file_name") or "source"
            blocks.append(f"[{i}] ({name})\n{d.page_content.strip()}")

        # crude token budgeting: keep adding blocks until we hit max_input_tokens
        context_text = self._trim_to_budget(
            blocks, self.config.max_input_tokens, self._encoding
        )
        links_section = ""
        if links:
            links_text = "Relevant Links from Documents:\n" + "\n".join(f"- {u}" for u in links)
            links_section = "\n\n" + self._trim_to_budget(
                [links_text], 800, self._encoding  # small extra budget for links
            )

        return context_text, links_section

    @staticmethod
    def _get_encoding():
        if not tiktoken:
            return None
        try:
            return tiktoken.get_encoding("o200k_base")
        except Exception:
            return None

    @staticmethod
    def _count_tokens(text: str, encoding=None) -> int:
        if not text:
            return 0
        if not encoding:
            # fallback: ~4 chars per token
            return max(1, len(text) // 4)
        return len(encoding.encode(text))

    def _trim_to_budget(
        self, parts: List[str], max_tokens: int, encoding=None
    ) -> str:
        used = 0
        kept: List[str] = []
        for p in parts:
            t = self._count_tokens(p, encoding)
            if used + t > max_tokens:
                break
            kept.append(p)
            used += t
        return "\n\n".join(kept)


# Global instance (kept for your current import pattern)
project_chatbot = ProjectChatbot()
