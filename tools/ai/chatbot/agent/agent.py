"""
AI Chatbot agent for project portfolio queries.
"""

import os
import uuid
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from openai import OpenAI
from ..prompts.prompts import ChatbotPrompts

# LangSmith integration for cost tracking  
try:
    from management_app.langsmith_integration.langsmith_integration import (
        log_cost, trace_chatbot
    )
    LANGSMITH_AVAILABLE = True
    print("✅ LangSmith integration successfully imported for chatbot")
except ImportError as e:
    print(f"❌ LangSmith integration import failed for chatbot: {str(e)}")
    # Fallback if LangSmith integration is not available
    def log_cost(operation, model, tokens_used=None, cost_estimate=None, additional_data=None):
        pass
    def trace_chatbot(operation, metadata=None):
        def decorator(func):
            return func
        return decorator
    LANGSMITH_AVAILABLE = False
except Exception as e:
    print(f"❌ Unexpected error importing LangSmith for chatbot: {str(e)}")
    # Fallback functions
    def log_cost(operation, model, tokens_used=None, cost_estimate=None, additional_data=None):
        pass
    def trace_chatbot(operation, metadata=None):
        def decorator(func):
            return func
        return decorator
    LANGSMITH_AVAILABLE = False

logger = logging.getLogger(__name__)

class ProjectChatbot:
    """AI Chatbot for project portfolio queries."""
    
    def __init__(self, use_custom_llm=False):
        self.use_custom_llm = use_custom_llm
        self.openai_client = None
        self.model_name = "gpt-4o-mini"  # Use efficient model for chat
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize OpenAI client."""
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment variables")
            
            self.openai_client = OpenAI(api_key=api_key)
            logger.info("✅ OpenAI client initialized for chatbot")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize OpenAI client: {str(e)}")
            raise
    
    def is_available(self) -> bool:
        """Check if chatbot service is available."""
        return self.openai_client is not None
    
    def generate_session_id(self, user_id: int) -> str:
        """Generate a unique session ID."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        return f"chat_{user_id}_{timestamp}_{unique_id}"
    
    @trace_chatbot("generate_session_title", metadata={"type": "session_management", "platform": "portfolio_chat"})
    def generate_session_title(self, first_message: str) -> str:
        """Generate a descriptive title for the chat session."""
        try:
            if not self.is_available():
                return "Project Chat Session"
            
            prompt = ChatbotPrompts.get_session_title_prompt(first_message)
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",  # Use cheaper model for title generation
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=100
            )
            
            title = response.choices[0].message.content.strip()
            
            # Clean up the title
            title = title.replace("Title:", "").strip()
            if len(title) > 50:
                title = title[:47] + "..."
            
            return title if title else "Project Chat Session"
            
        except Exception as e:
            logger.error(f"❌ Failed to generate session title: {str(e)}")
            return "Project Chat Session"
    
    @trace_chatbot("generate_response", metadata={"type": "chat_response", "platform": "portfolio_chat"})
    def generate_response(
        self, 
        query: str, 
        relevant_documents: List[Dict[str, Any]] = None,
        conversation_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Generate AI response based on query and relevant documents."""
        start_time = time.time()
        
        try:
            if not self.is_available():
                raise Exception("Chatbot service not available")
            
            logger.info(f"💬 Generating response for query: {query[:50]}...")
            
            # Build conversation context
            messages = []
            
            # Add system prompt
            system_prompt = ChatbotPrompts.get_system_prompt()
            messages.append({"role": "system", "content": system_prompt})
            
            # Add conversation history if available
            if conversation_history:
                for msg in conversation_history[-10:]:  # Last 10 messages for context
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            # Add current query with context
            if relevant_documents:
                context_prompt = ChatbotPrompts.get_context_prompt(query, relevant_documents)
                messages.append({"role": "user", "content": context_prompt})
            else:
                messages.append({"role": "user", "content": query})
            
            # Log cost estimation
            if LANGSMITH_AVAILABLE:
                estimated_tokens = sum(len(msg["content"].split()) * 1.3 for msg in messages)  # Rough estimation
                estimated_cost = estimated_tokens * 0.00001  # GPT-4o-mini cost
                
                log_cost(
                    operation="chatbot_query_start",
                    model=self.model_name,
                    tokens_used=int(estimated_tokens),
                    cost_estimate=estimated_cost,
                    additional_data={
                        "query": query[:100],
                        "relevant_docs_count": len(relevant_documents) if relevant_documents else 0,
                        "estimated_tokens": int(estimated_tokens)
                    }
                )
            
            # Generate response
            response = self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            ai_response = response.choices[0].message.content.strip()
            tokens_used = response.usage.total_tokens
            
            processing_time = time.time() - start_time
            
            # Extract sources used from relevant documents
            sources_used = []
            if relevant_documents:
                for doc in relevant_documents:
                    sources_used.append({
                        'file_name': doc['file_name'],
                        'file_type': doc['file_type'],
                        'file_url': doc['file_url'],
                        'relevance_score': doc['score']
                    })
            
            # Log final cost
            if LANGSMITH_AVAILABLE:
                actual_cost = tokens_used * 0.00001  # GPT-4o-mini cost
                
                log_cost(
                    operation="chatbot_query_complete",
                    model=self.model_name,
                    tokens_used=tokens_used,
                    cost_estimate=actual_cost,
                    additional_data={
                        "query": query[:100],
                        "response_length": len(ai_response),
                        "processing_time": processing_time,
                        "sources_used": len(sources_used),
                        "success": True
                    }
                )
            
            logger.info(f"✅ Generated response in {processing_time:.2f}s using {tokens_used} tokens")
            
            return {
                'success': True,
                'response': ai_response,
                'sources_used': sources_used,
                'processing_time': processing_time,
                'tokens_used': tokens_used,
                'model_used': self.model_name
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"❌ Failed to generate response: {str(e)}")
            
            # Log error
            if LANGSMITH_AVAILABLE:
                log_cost(
                    operation="chatbot_query_error",
                    model=self.model_name,
                    tokens_used=0,
                    cost_estimate=0,
                    additional_data={
                        "query": query[:100],
                        "error": str(e),
                        "processing_time": processing_time,
                        "success": False
                    }
                )
            
            return {
                'success': False,
                'error': str(e),
                'response': "I'm sorry, I encountered an error while processing your query. Please try again or rephrase your question.",
                'sources_used': [],
                'processing_time': processing_time,
                'tokens_used': 0
            }
    
    def generate_follow_up_suggestions(self, query: str, response: str) -> List[str]:
        """Generate follow-up question suggestions."""
        try:
            if not self.is_available():
                return []
            
            prompt = ChatbotPrompts.get_follow_up_suggestions_prompt(query, response)
            
            ai_response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",  # Use cheaper model for suggestions
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            suggestions_text = ai_response.choices[0].message.content.strip()
            
            # Parse suggestions
            suggestions = []
            for line in suggestions_text.split('\n'):
                line = line.strip()
                if line and (line.startswith('1.') or line.startswith('2.') or line.startswith('3.')):
                    question = line[2:].strip()  # Remove numbering
                    if question:
                        suggestions.append(question)
            
            return suggestions[:3]  # Return max 3 suggestions
            
        except Exception as e:
            logger.error(f"❌ Failed to generate follow-up suggestions: {str(e)}")
            return []
    
    def validate_query(self, query: str) -> Dict[str, Any]:
        """Validate user query."""
        if not query or not query.strip():
            return {
                'valid': False,
                'error': 'Query cannot be empty'
            }
        
        if len(query) > 2000:
            return {
                'valid': False,
                'error': 'Query too long (maximum 2000 characters)'
            }
        
        if len(query.strip()) < 3:
            return {
                'valid': False,
                'error': 'Query too short (minimum 3 characters)'
            }
        
        return {'valid': True}


# Create global chatbot instance
project_chatbot = ProjectChatbot()
