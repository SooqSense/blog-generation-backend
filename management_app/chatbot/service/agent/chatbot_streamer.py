"""
ChatbotStreamer - Async streaming service for real-time chatbot responses.

This service mirrors the BlogWriter architecture, providing token-by-token
streaming of AI responses via Django Channels and WebSocket.
"""

import time
import asyncio
import logging
from typing import Dict, Any, List, Optional
from channels.layers import get_channel_layer
from langchain_openai import ChatOpenAI
from langchain.schema import Document, HumanMessage, SystemMessage
from django.conf import settings
from django.utils import timezone

from management_app.knowledge_base.service.pinecone_indexing.pinecone_indexing import pinecone_service
from ..prompts.prompts import ChatbotPrompts

logger = logging.getLogger(__name__)

# Optional token counting
try:
    import tiktoken
except Exception:
    tiktoken = None


class ChatbotStreamer:
    """Async chatbot with token-by-token streaming via Django Channels."""

    def __init__(
        self,
        query: str,
        session_id: str,
        task_id: str,
        user_id: int,
        username: str = "Anonymous",
        email: str = "",
        top_k: int = 10,
        model: str = "gpt-4o-mini",
        temperature: float = 0.3,
        max_tokens: int = 700,
    ):
        self.query = query
        self.session_id = session_id
        self.task_id = task_id
        self.user_id = user_id
        self.username = username
        self.email = email
        self.top_k = top_k

        # Initialize LLM with streaming enabled
        openai_key = getattr(settings, "OPENAI_API_KEY", None)
        if not openai_key:
            raise ValueError("OPENAI_API_KEY not found in settings")

        self.llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=openai_key,
            streaming=True,  # CRITICAL: Enable streaming
        )

        # Use pre-initialized singleton (CRITICAL for performance!)
        # This eliminates the 5-second Pinecone connection overhead
        self.pinecone_service = pinecone_service
        self.channel_layer = get_channel_layer()

        # Runtime state
        self.response_content: str = ""
        self.documents_found: int = 0
        self.relevant_docs: List[Dict[str, Any]] = []
        self.processing_time: float = 0.0
        self.tokens_generated: int = 0

        # Token counting
        self._encoding = self._get_encoding()

    async def _publish(self, event_type: str, payload: Dict[str, Any]):
        """Helper to publish events to Django Channels Group."""
        try:
            await self.channel_layer.group_send(
                f"chat_{self.task_id}",
                {
                    "type": "stream_message",
                    "data": {
                        "type": event_type,
                        "session_id": self.session_id,
                        **payload
                    }
                }
            )
        except Exception as e:
            logger.error(f"Group send failed for chat_{self.task_id}: {e}")

    async def _retrieve_context(self) -> tuple[str, List[Dict[str, Any]]]:
        """Retrieve relevant documents from Pinecone with optimized timing."""
        # Publish status immediately (non-blocking)
        status_task = asyncio.create_task(
            self._publish("status", {
                "status": "retrieving",
                "message": "Searching knowledge base..."
            })
        )

        try:
            # Run Pinecone search in thread pool (prevents event loop blocking)
            # The PineconeService singleton is already initialized, so this is fast
            search_result = await asyncio.to_thread(
                self.pinecone_service.search_documents,
                query=self.query,
                top_k=self.top_k
            )

            # Ensure status was published
            await status_task

            if not search_result.get("success") or not search_result.get("results"):
                logger.warning(f"No documents found for query: {self.query[:50]}")
                return "", []

            results = search_result["results"]
            self.documents_found = len(results)

            # Convert to Document objects
            docs = self._results_to_documents(results)

            # Build context and extract sources
            context_text, sources = self._build_context(docs)

            # Publish context found event (non-blocking)
            asyncio.create_task(
                self._publish("context_found", {
                    "documents_found": self.documents_found,
                    "sources": sources[:5]  # Top 5 sources
                })
            )

            return context_text, sources

        except Exception as e:
            logger.error(f"Context retrieval failed: {e}", exc_info=True)
            await status_task  # Ensure status task completes
            return "", []

    @staticmethod
    def _results_to_documents(results: List[Dict[str, Any]]) -> List[Document]:
        """Convert Pinecone results to LangChain Documents."""
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
                    "loom_links": r.get("loom_links", []) or [],
                },
            )
            for r in results
        ]

    def _build_context(self, docs: List[Document]) -> tuple[str, List[Dict[str, str]]]:
        """Build context text and extract sources from documents."""
        # Limit documents
        docs = docs[:min(self.top_k, 12)]

        # Collect unique sources
        sources = []
        seen_files = set()

        for d in docs:
            file_name = d.metadata.get("file_name")
            if file_name and file_name not in seen_files:
                seen_files.add(file_name)
                sources.append({
                    "file_name": file_name,
                    "file_type": d.metadata.get("file_type", "unknown"),
                    "score": d.metadata.get("score", 0.0)
                })

        # Build context blocks
        blocks = []
        for i, d in enumerate(docs, 1):
            name = d.metadata.get("file_name") or "source"
            blocks.append(f"[{i}] ({name})\n{d.page_content.strip()}")

        context_text = "\n\n".join(blocks)
        return context_text, sources

    async def generate_streaming_response(self):
        """Main orchestration method for streaming chat response with instant acknowledgement."""
        start_time = time.time()
        first_token_time = None

        try:
            # Step 1: INSTANT acknowledgement - publish immediately
            await self._publish("status", {
                "status": "starting",
                "message": f"Processing: {self.query[:50]}..."
            })

            # Step 2: Rapid RAG - Run Pinecone search in parallel with status update
            # This uses the pre-initialized singleton, avoiding connection overhead
            context_text, sources = await self._retrieve_context()
            self.relevant_docs = sources

            # Step 3: Build optimized prompt
            if context_text:
                links_section = self._build_links_section(sources)
                prompt_text = ChatbotPrompts.get_portfolio_query_prompt(
                    self.query, context_text, links_section
                )
            else:
                # Fallback prompt when no context found
                prompt_text = f"""You are a helpful AI assistant. The user asked: "{self.query}"

Unfortunately, I couldn't find any relevant information in the knowledge base to answer this question. 
Please provide a helpful response explaining that you don't have specific information about this topic."""

            # Step 4: Publish generating status (right before LLM call)
            await self._publish("status", {
                "status": "generating",
                "message": "Generating response..."
            })

            # Step 5: Stream tokens word-by-word from LLM
            # This is the critical path for "instant" feel - tokens go directly to Redis
            messages = [HumanMessage(content=prompt_text)]
            
            async for chunk in self.llm.astream(messages):
                token = chunk.content
                if token:
                    # Track first token timing for performance monitoring
                    if first_token_time is None:
                        first_token_time = time.time() - start_time
                        logger.info(f"⚡ First token in {first_token_time:.3f}s")
                    
                    self.response_content += token
                    self.tokens_generated += 1

                    # Publish token event immediately to Redis Pub/Sub
                    await self._publish("token", {
                        "content": token
                    })

            # Step 6: Calculate final processing time
            self.processing_time = round(time.time() - start_time, 2)

            # Step 7: Publish complete event with metadata
            await self._publish("complete", {
                "response": self.response_content,
                "documents_found": self.documents_found,
                "processing_time": self.processing_time,
                "tokens_generated": self.tokens_generated,
                "sources": self.relevant_docs,
                "first_token_time": first_token_time
            })

            logger.info(
                f"✅ Chat streaming complete: {self.tokens_generated} tokens, "
                f"{self.processing_time}s, {self.documents_found} docs, "
                f"TTFT: {first_token_time:.3f}s"
            )

        except Exception as e:
            logger.error(f"Streaming generation failed: {e}", exc_info=True)
            await self._publish("error", {
                "message": f"Failed to generate response: {str(e)}"
            })
            raise

    def _build_links_section(self, sources: List[Dict[str, str]]) -> str:
        """Build links section from sources."""
        if not sources:
            return ""

        links = []
        for src in sources[:5]:
            file_name = src.get("file_name", "Unknown")
            links.append(f"- {file_name}")

        return "\n\nRelevant Sources:\n" + "\n".join(links)

    @staticmethod
    def _get_encoding():
        """Get tiktoken encoding for token counting."""
        if not tiktoken:
            return None
        try:
            return tiktoken.get_encoding("o200k_base")
        except Exception:
            return None

    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata about the generated response."""
        return {
            "session_id": self.session_id,
            "task_id": self.task_id,
            "query": self.query,
            "response": self.response_content,
            "documents_found": self.documents_found,
            "processing_time": self.processing_time,
            "tokens_generated": self.tokens_generated,
            "relevant_docs": self.relevant_docs,
        }
