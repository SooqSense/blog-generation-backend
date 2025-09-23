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
from pinecone import Pinecone, ServerlessSpec
from ..prompts.prompts import ChatbotPrompts

# Import the enhanced Pinecone service
try:
    from management_app.pinecone_integration.service.service import pinecone_service
    PINECONE_SERVICE_AVAILABLE = True
    print("✅ Enhanced Pinecone service integration available for chatbot")
except ImportError as e:
    print(f"❌ Enhanced Pinecone service not available: {str(e)}")
    PINECONE_SERVICE_AVAILABLE = False
    pinecone_service = None

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
        self.pinecone_client = None
        self.pinecone_index = None
        self.model_name = "gpt-4o-mini"  # Use efficient model for chat
        self.embedding_model = "text-embedding-3-small"  # For query embeddings
        self._initialize_client()
        self._initialize_pinecone()
    
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
    
    def _initialize_pinecone(self):
        """Initialize Pinecone client and connect to index."""
        try:
            pinecone_api_key = os.getenv("PINECONE_API_KEY")
            if not pinecone_api_key:
                raise ValueError("PINECONE_API_KEY not found in environment variables")
            
            # Initialize Pinecone client
            self.pinecone_client = Pinecone(api_key=pinecone_api_key)
            
            # Connect to the index - assuming the index name is stored in environment variable
            index_name = os.getenv("PINECONE_INDEX_NAME", "portfolio-documents")
            
            # Check if index exists, if not create it
            existing_indexes = [index_info["name"] for index_info in self.pinecone_client.list_indexes()]
            
            if index_name not in existing_indexes:
                logger.warning(f"⚠️ Pinecone index '{index_name}' does not exist. Please create it first.")
                # You might want to create the index here or handle this case differently
                self.pinecone_index = None
            else:
                self.pinecone_index = self.pinecone_client.Index(index_name)
                logger.info(f"✅ Pinecone client initialized and connected to index: {index_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Pinecone client: {str(e)}")
            self.pinecone_index = None
    
    def is_available(self) -> bool:
        """Check if chatbot service is available."""
        return self.openai_client is not None and self.pinecone_index is not None
    
    def generate_session_id(self, user_id: int) -> str:
        """Generate a unique session ID."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        return f"chat_{user_id}_{timestamp}_{unique_id}"
    
    def _create_query_embedding(self, query: str) -> List[float]:
        """Create embedding for the user query using OpenAI."""
        try:
            response = self.openai_client.embeddings.create(
                input=query,
                model=self.embedding_model
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"❌ Failed to create query embedding: {str(e)}")
            raise
    
    def search_pinecone_documents(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search Pinecone index for relevant documents in PDFS namespace."""
        try:
            if not self.pinecone_index:
                logger.error("❌ Pinecone index not available")
                return []
            
            # Create embedding for the query
            query_embedding = self._create_query_embedding(query)
            
            # Search Pinecone index in PDFS namespace
            search_results = self.pinecone_index.query(
                vector=query_embedding,
                top_k=top_k,
                namespace="PDFS",
                include_metadata=True,
                include_values=False
            )
            
            # Format results
            relevant_documents = []
            for match in search_results.matches:
                metadata = match.metadata or {}
                
                document = {
                    'id': match.id,
                    'score': match.score,
                    'file_name': metadata.get('file_name', 'Unknown'),
                    'file_type': metadata.get('file_type', 'Unknown'),
                    'file_url': metadata.get('file_url', ''),
                    'chunk_content': metadata.get('chunk_content', ''),
                    'chunk_index': metadata.get('chunk_index', 0)
                }
                relevant_documents.append(document)
            
            logger.info(f"✅ Retrieved {len(relevant_documents)} documents from Pinecone PDFS namespace")
            return relevant_documents
            
        except Exception as e:
            logger.error(f"❌ Failed to search Pinecone documents: {str(e)}")
            return []
    
    def get_all_document_chunks(self, file_names: List[str], max_chunks_per_file: int = 100) -> List[Dict[str, Any]]:
        """Retrieve all chunks for specific documents from Pinecone PDFS namespace."""
        try:
            if not self.pinecone_index:
                logger.error("❌ Pinecone index not available")
                return []
            
            all_chunks = []
            
            for file_name in file_names:
                logger.info(f"🔍 Retrieving all chunks for document: {file_name}")
                
                # Use multiple semantic queries with different keywords from the file name
                # This is more reliable than dummy vector approach
                search_terms = [
                    file_name.replace('.pdf', '').replace('.docx', '').replace('.txt', ''),
                    f"{file_name} content",
                    f"{file_name} information",
                    f"{file_name} document"
                ]
                
                document_chunks = []
                seen_chunk_ids = set()
                
                for search_term in search_terms:
                    try:
                        # Create embedding for search term
                        query_embedding = self._create_query_embedding(search_term)
                        
                        # Search with high top_k to get many chunks
                        search_results = self.pinecone_index.query(
                            vector=query_embedding,
                            top_k=max_chunks_per_file,
                            namespace="PDFS",
                            include_metadata=True,
                            include_values=False
                        )
                        
                        # Filter results to only include chunks from the target file
                        for match in search_results.matches:
                            metadata = match.metadata or {}
                            
                            # Only include chunks from the specific file we want
                            if (metadata.get('file_name') == file_name and 
                                match.id not in seen_chunk_ids):
                                
                                chunk = {
                                    'id': match.id,
                                    'score': match.score,
                                    'file_name': metadata.get('file_name', 'Unknown'),
                                    'file_type': metadata.get('file_type', 'Unknown'),
                                    'file_url': metadata.get('file_url', ''),
                                    'chunk_content': metadata.get('chunk_content', ''),
                                    'chunk_index': metadata.get('chunk_index', 0)
                                }
                                document_chunks.append(chunk)
                                seen_chunk_ids.add(match.id)
                                
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to search with term '{search_term}': {str(e)}")
                        continue
                
                # Sort chunks by index to maintain document order
                document_chunks.sort(key=lambda x: x.get('chunk_index', 0))
                all_chunks.extend(document_chunks)
                
                logger.info(f"✅ Retrieved {len(document_chunks)} unique chunks for {file_name}")
            
            return all_chunks
            
        except Exception as e:
            logger.error(f"❌ Failed to retrieve document chunks: {str(e)}")
            return []
    
    def comprehensive_document_search(self, query: str, initial_top_k: int = 50, user_id: int = None) -> List[Dict[str, Any]]:
        """Simple comprehensive search using the Pinecone service."""
        try:
            logger.info(f"🔍 Searching for: {query[:100]}...")
            
            # Use the simple Pinecone service search
            if PINECONE_SERVICE_AVAILABLE and pinecone_service:
                search_result = pinecone_service.search_documents(
                    query=query,
                    user_id=user_id,
                    top_k=initial_top_k
                )
                
                if search_result['success'] and search_result.get('results'):
                    logger.info(f"✅ Found {len(search_result['results'])} relevant chunks")
                    
                    # Convert to expected format
                    results = []
                    for doc in search_result['results']:
                        results.append({
                            'id': doc.get('id', ''),
                            'score': doc['score'],
                            'file_name': doc['file_name'],
                            'file_type': doc['file_type'],
                            'file_url': doc['file_url'],
                            'chunk_content': doc['chunk_content'],
                            'chunk_index': doc.get('chunk_index', 0)
                        })
                    
                    return results
                else:
                    logger.info("⚠️ No results found from search")
                    return []
            
            # Fallback to direct search if service unavailable
            logger.info("📊 Using fallback direct search")
            return self.search_pinecone_documents(query, top_k=initial_top_k)
            
        except Exception as e:
            logger.error(f"❌ Search failed: {str(e)}")
            return []
    
    
    def _clean_content(self, content: str) -> str:
        """Clean and validate content to remove corrupted or inappropriate text."""
        if not content:
            return ""
        
        # Remove various types of corrupted or inappropriate content
        import re
        
        # List of patterns to filter out (be more conservative)
        filter_patterns = [
            r'\bniggers?\b',  # Remove any offensive language
            r'^\s*[^a-zA-Z0-9\s]+\s*$',  # Remove lines with only special characters
        ]
        
        cleaned_content = content
        
        # Apply filters
        for pattern in filter_patterns:
            cleaned_content = re.sub(pattern, '', cleaned_content, flags=re.IGNORECASE)
        
        # Clean up extra whitespace but preserve structure
        cleaned_content = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned_content)  # Normalize excessive line breaks
        cleaned_content = re.sub(r'[ \t]+', ' ', cleaned_content)  # Normalize spaces/tabs but not newlines
        cleaned_content = cleaned_content.strip()
        
        return cleaned_content
    
    
    def _generate_contextual_search_query(self, query: str, conversation_history: List[Dict[str, str]] = None) -> str:
        """
        Generate a more relevant search query based on conversation context.
        This solves the problem where users ask vague questions like 'tell me about this project'
        but chunks contain specific project information.
        """
        try:
            if not self.openai_client:
                logger.warning("OpenAI client not available, using original query")
                return query
            
            # If no conversation history, try to enhance the query anyway
            if not conversation_history:
                conversation_history = []
            
            # Build context from conversation history
            context_messages = []
            
            # Add the last few messages for context (limit to avoid token overflow)
            recent_history = conversation_history[-6:] if conversation_history else []
            
            context_text = ""
            if recent_history:
                context_text = "Previous conversation:\n"
                for msg in recent_history:
                    role = "User" if msg.get("role") == "user" else "Assistant"
                    context_text += f"{role}: {msg.get('content', '')}\n"
                context_text += "\n"
            
            # Create a prompt for query enhancement
            enhancement_prompt = f"""
You are a search query optimizer for a knowledge base containing project portfolios and technical documentation. 

Your task is to transform user queries into more effective search terms that will find relevant content in a document database.

{context_text}Current user query: "{query}"

The knowledge base contains chunks of text about various projects with information like:
- Project descriptions and overviews
- Technical requirements and challenges  
- Client testimonials and results
- Technology stacks and implementation details
- Project names like "2456.ai", "Leads by Kari", "IVitamin Clinic", "Viclinic"

Transform the user's query into 2-3 specific search terms that would match the actual content in the documents. Focus on:
1. Extracting specific project names mentioned or implied
2. Identifying what type of information the user wants (requirements, challenges, technology, results, etc.)
3. Using terminology that would actually appear in technical project documentation

If the user refers to "this project" or "that project", determine which project from context.
If asking about general topics, use specific technical terms.

Return only the enhanced search query, nothing else. Make it concise but comprehensive.

Examples:
- "tell me about this project" → "2456.ai project overview features requirements challenges results"
- "what technologies were used" → "technology stack implementation tools frameworks backend frontend"
- "how did they solve the challenges" → "challenges solutions approach implementation methodology"

Enhanced search query:"""

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Fast model for query enhancement
                messages=[
                    {"role": "user", "content": enhancement_prompt}
                ],
                temperature=0.0,  # Deterministic results for consistent search queries
                max_tokens=100
            )
            
            enhanced_query = response.choices[0].message.content.strip()
            
            # Fallback to original if enhancement failed
            if not enhanced_query or len(enhanced_query) < 3:
                logger.warning("Query enhancement failed, using original query")
                return query
            
            logger.info(f"🔄 Query enhanced: '{query}' → '{enhanced_query}'")
            return enhanced_query
            
        except Exception as e:
            logger.error(f"❌ Failed to enhance query: {str(e)}")
            return query  # Fallback to original query
    
    def _is_conversational_query(self, query: str) -> bool:
        """Check if the query is a conversational/general query rather than document-specific."""
        query_lower = query.lower().strip()
        
        # Greetings and basic conversation
        conversational_patterns = [
            # Greetings
            'hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening',
            # How are you variations
            'how are you', 'how do you do', 'how\'s it going', 'what\'s up',
            # Thank you
            'thank you', 'thanks', 'appreciate it',
            # Goodbyes
            'bye', 'goodbye', 'see you', 'talk to you later',
            # About the bot
            'who are you', 'what are you', 'what can you do', 'help me',
            'what is this', 'introduce yourself',
            # General pleasantries
            'nice to meet you', 'pleasure to meet you'
        ]
        
        # Check for exact matches or if query starts with these patterns
        for pattern in conversational_patterns:
            if (query_lower == pattern or 
                query_lower.startswith(pattern + ' ') or
                query_lower.startswith(pattern + ',') or
                query_lower.startswith(pattern + '!')):
                return True
        
        # Check for very short queries that are likely conversational
        if len(query_lower) <= 15 and not any(word in query_lower for word in 
                                              ['project', 'document', 'file', 'pdf', 'about', 'tell me']):
            return True
            
        # Check for capability questions
        if any(phrase in query_lower for phrase in ['what can you do', 'what do you do', 'help me', 'can you help']):
            return True
            
        return False
    
    def _generate_conversational_response(self, query: str, conversation_history: List[Dict[str, str]] = None) -> str:
        """Generate appropriate conversational response for general queries."""
        query_lower = query.lower().strip()
        
        # Greetings
        if any(greeting in query_lower for greeting in ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening']):
            return "Hello! I'm your AI assistant for exploring project portfolios and documents. I can help you find information about projects, analyze documents, and answer questions based on your indexed content. How can I assist you today?"
        
        # How are you
        if any(phrase in query_lower for phrase in ['how are you', 'how do you do', 'how\'s it going', 'what\'s up']):
            return "I'm doing well, thank you for asking! I'm ready to help you explore your project portfolio and documentation. What would you like to know about?"
        
        # Thank you
        if any(thanks in query_lower for thanks in ['thank you', 'thanks', 'appreciate it']):
            return "You're very welcome! I'm here to help whenever you need information about your projects or documents. Is there anything else I can assist you with?"
        
        # Goodbyes
        if any(bye in query_lower for bye in ['bye', 'goodbye', 'see you', 'talk to you later']):
            return "Goodbye! Feel free to come back anytime you need help exploring your project documentation or have questions about your portfolio. Have a great day!"
        
        # About the bot
        if any(about in query_lower for about in ['who are you', 'what are you', 'what can you do', 'introduce yourself']):
            return "I'm your AI-powered project portfolio assistant! I can help you:\n\n• Search through your project documentation\n• Answer questions about specific projects\n• Find technical details and requirements\n• Explore your knowledge base of PDFs and documents\n• Provide insights based on your indexed content\n\nJust ask me anything about your projects or documents, and I'll search through your knowledge base to find the relevant information!"
        
        # Help requests
        if 'help' in query_lower and len(query_lower) < 20:
            return "I'm here to help! I can search through your project portfolio and documentation to answer questions like:\n\n• \"Tell me about the 2456.ai project\"\n• \"What technologies were used in my projects?\"\n• \"Show me project requirements and challenges\"\n• \"How many projects do I have?\"\n• \"Find information about [specific topic]\"\n\nWhat would you like to explore in your project documentation?"
        
        # Default conversational response
        return "I understand you're looking to chat! While I'm primarily designed to help you explore your project portfolio and documentation, I'm happy to assist. Is there anything specific about your projects or documents you'd like to know about?"
    
    def _analyze_query_intent(self, query: str) -> Dict[str, Any]:
        """Analyze the user query to determine intent and required information."""
        query_lower = query.lower()
        
        # First check if it's conversational
        if self._is_conversational_query(query):
            return {'type': 'conversational', 'target': 'general'}
        
        # Count queries
        if any(word in query_lower for word in ['how many', 'count', 'number of']):
            if 'project' in query_lower:
                return {'type': 'count', 'target': 'projects'}
            elif 'document' in query_lower:
                return {'type': 'count', 'target': 'documents'}
        
        # List queries
        if any(word in query_lower for word in ['list', 'show me', 'what are']):
            if 'project' in query_lower:
                return {'type': 'list', 'target': 'projects'}
        
        # Specific project queries
        project_names = ['2456.ai', 'leads by kari', 'ivitamin', 'viclinic']
        for project in project_names:
            if project in query_lower:
                return {'type': 'specific', 'target': 'project', 'project_name': project}
        
        # Default: general information query
        return {'type': 'general', 'target': 'information'}
    
    def _extract_project_names(self, content: str) -> List[str]:
        """Extract project names from the content."""
        import re
        
        project_names = []
        
        # Common patterns for project names
        patterns = [
            r'(?:^|\n)([A-Z][a-zA-Z0-9\.\s\-&]+)(?:\n|\s*:|\s*\n)',  # Title-like patterns
            r'(?:Project|Website|Platform|Solution):\s*([A-Za-z0-9\.\s\-&]+)',  # After "Project:" etc.
            r'([0-9]+\.[a-z]+)',  # Domain names like 2456.ai
            r'([A-Z][a-z]+\s+by\s+[A-Z][a-z]+)',  # "Leads by Kari" pattern
            r'(I[A-Z][a-z]+\s+[A-Z][a-z]+)',  # "IVitamin Clinic" pattern
            r'([A-Z][a-z]+clinic)',  # "Viclinic" pattern
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                cleaned_name = match.strip()
                # Filter out obvious non-project names
                if (len(cleaned_name) > 2 and 
                    not cleaned_name.lower() in ['the', 'and', 'or', 'but', 'with', 'for', 'from', 'our', 'team'] and
                    not re.match(r'^\d+$', cleaned_name) and  # Just numbers
                    cleaned_name not in project_names):
                    project_names.append(cleaned_name)
        
        # Known project names from domain knowledge
        known_projects = []
        known_patterns = ['2456.ai', 'Leads by Kari', 'IVitamin Clinic', 'Viclinic']
        
        for known in known_patterns:
            if known.lower() in content.lower():
                known_projects.append(known)
        
        # Combine and deduplicate
        all_projects = list(set(known_projects + project_names))
        
        # Sort by length to prefer more complete names
        all_projects.sort(key=len, reverse=True)
        
        # Remove duplicates based on similarity
        filtered_projects = []
        for project in all_projects:
            is_duplicate = False
            for existing in filtered_projects:
                if (project.lower() in existing.lower() or 
                    existing.lower() in project.lower()):
                    is_duplicate = True
                    break
            if not is_duplicate:
                filtered_projects.append(project)
        
        return filtered_projects[:10]  # Limit to top 10
    
    def _generate_contextual_response(self, query: str, retrieved_content: str, conversation_history: List[Dict[str, str]] = None, intent: Dict[str, Any] = None) -> str:
        """
        Generate a human-like, context-specific response by analyzing the knowledge base
        and understanding what the user asked vs what the document contains.
        """
        try:
            if not self.openai_client:
                return retrieved_content[:1500] + "..." if len(retrieved_content) > 1500 else retrieved_content
            
            # Build conversation context
            context_text = ""
            if conversation_history:
                recent_history = conversation_history[-4:]  # Last 4 messages for context
                if recent_history:
                    context_text = "Previous conversation:\n"
                    for msg in recent_history:
                        role = "User" if msg.get("role") == "user" else "Assistant"
                        context_text += f"{role}: {msg.get('content', '')[:200]}...\n"
                    context_text += "\n"
            
            # Create a sophisticated response generation prompt
            response_prompt = f"""
You are an AI assistant that specializes in explaining technical projects and portfolio information. You have access to detailed project documentation and need to provide human-like, contextual responses.

{context_text}User's current question: "{query}"

Retrieved knowledge from documents:
{retrieved_content}

Your task:
1. Analyze what the user is specifically asking about
2. Extract the most relevant information from the retrieved content
3. Present it in a conversational, human-like way
4. Be specific and detailed, like someone who knows the project well
5. If referencing previous conversation, acknowledge the context
6. Structure your response clearly with key points

Guidelines:
- Don't just repeat the document content verbatim
- Explain like a knowledgeable team member would
- Use natural language and conversational tone
- Highlight key achievements, challenges, and technical details
- If the user asked about "this project" or similar, identify which project and explain it
- Keep it comprehensive but not overwhelming
- Use bullet points or structured format when appropriate

Respond naturally and conversationally:"""

            response = self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "user", "content": response_prompt}
                ],
                temperature=0.7,  # Slightly higher for more natural responses
                max_tokens=1200   # Allow longer, more detailed responses
            )
            
            contextual_response = response.choices[0].message.content.strip()
            
            if not contextual_response or len(contextual_response) < 50:
                logger.warning("Contextual response generation failed, using fallback")
                return retrieved_content[:1500] + "..." if len(retrieved_content) > 1500 else retrieved_content
            
            logger.info(f"✨ Generated contextual response ({len(contextual_response)} chars)")
            return contextual_response
            
        except Exception as e:
            logger.error(f"❌ Failed to generate contextual response: {str(e)}")
            return retrieved_content[:1500] + "..." if len(retrieved_content) > 1500 else retrieved_content
    
    @trace_chatbot("rag_query", metadata={"type": "rag_query", "platform": "portfolio_chat"})
    def rag_query(self, query: str, use_comprehensive_search: bool = True, top_k: int = 30, user_id: int = None, conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """Enhanced RAG query that analyzes intent and provides better answers."""
        start_time = time.time()
        
        try:
            if not self.is_available():
                return {
                    'success': False,
                    'error': 'RAG system not available',
                    'response': 'RAG system not available. Please check Pinecone and OpenAI connections.',
                    'documents': [],
                    'processing_time': 0
                }
            
            logger.info(f"🔍 RAG Query: {query[:100]}...")
            
            # Step 1: Analyze query intent first to detect conversational queries
            intent = self._analyze_query_intent(query)
            logger.info(f"🎯 Query intent: {intent['type']} - {intent['target']}")
            
            # Step 2: Handle conversational queries immediately without document search
            if intent['type'] == 'conversational':
                logger.info("💬 Detected conversational query, providing direct response")
                conversational_response = self._generate_conversational_response(query, conversation_history)
                processing_time = time.time() - start_time
                
                return {
                    'success': True,
                    'response': conversational_response,
                    'documents': [],
                    'sources_used': [],
                    'processing_time': processing_time,
                    'tokens_used': 0,  # No AI tokens used for pre-defined responses
                    'model_used': 'CONVERSATIONAL_RESPONSE',
                    'strategy_used': 'conversational',
                    'query_enhanced': False,
                    'original_query': query,
                    'enhanced_query': None
                }
            
            # Step 3: For document queries, generate contextual search query for better retrieval
            enhanced_query = self._generate_contextual_search_query(query, conversation_history)
            
            # Step 4: Use enhanced query for search but keep original for intent
            search_query = enhanced_query if enhanced_query != query else query
            
            # Use search strategy for information retrieval with enhanced query
            if use_comprehensive_search:
                logger.info("🚀 Using comprehensive document search with enhanced query")
                relevant_documents = self.comprehensive_document_search(search_query, initial_top_k=top_k, user_id=user_id)
            else:
                logger.info("🔍 Using simple semantic search with enhanced query")
                relevant_documents = self.search_pinecone_documents(search_query, top_k)
            
            if not relevant_documents:
                processing_time = time.time() - start_time
                return {
                    'success': True,
                    'response': 'No relevant information found in the indexed documents for this query.',
                    'documents': [],
                    'processing_time': processing_time,
                    'tokens_used': 0,
                    'model_used': None
                }
            
            # Group chunks by document for better organization
            documents_by_file = {}
            for doc in relevant_documents:
                file_name = doc['file_name']
                if file_name not in documents_by_file:
                    documents_by_file[file_name] = []
                documents_by_file[file_name].append(doc)
            
            # Sort chunks within each document by chunk_index
            for file_name in documents_by_file:
                documents_by_file[file_name].sort(key=lambda x: x['chunk_index'])
            
            # Format the complete retrieved content
            response_parts = []
            sources = []
            
            # Limit to top relevant chunks but ensure we get complete information
            max_chunks = min(top_k, len(relevant_documents))
            selected_documents = relevant_documents[:max_chunks]
            
            # Build response with proper project structure and sequence
            logger.info("📝 Building structured response from project-specific chunks")
            
            if not selected_documents:
                logger.warning("⚠️ No documents selected for response building")
                return {
                    'success': True,
                    'response': 'No relevant information found in the indexed documents for this query.',
                    'documents': [],
                    'sources_used': [],
                    'processing_time': processing_time,
                    'tokens_used': 0,
                    'model_used': 'ENHANCED_RAG_RETRIEVAL'
                }
            
            # Build response from retrieved chunks
            response_parts = []
            sources = []
            
            # Sort chunks by file and chunk index for proper reading order
            selected_documents.sort(key=lambda x: (x['file_name'], x.get('chunk_index', 0)))
            
            # Group by document for better organization
            documents_by_file = {}
            for doc in selected_documents:
                file_name = doc['file_name']
                if file_name not in documents_by_file:
                    documents_by_file[file_name] = []
                
                content = doc['chunk_content'].strip()
                if content:
                    # Clean content
                    content = self._clean_content(content)
                    if content and len(content) > 20:  # Minimum content length
                        documents_by_file[file_name].append({
                            'content': content,
                            'score': doc['score'],
                            'chunk_index': doc.get('chunk_index', 0)
                        })
            
            # Build response from each document
            for file_name, chunks in documents_by_file.items():
                if not chunks:
                    continue
                
                logger.info(f"📊 Building content from: {file_name}")
                
                # Sort chunks by index to maintain document order
                chunks.sort(key=lambda x: x.get('chunk_index', 0))
                
                # Combine chunk content
                document_content = []
                for chunk in chunks:
                    if chunk['content'] and chunk['content'] not in document_content:
                        document_content.append(chunk['content'])
                
                if document_content:
                    # Join document content
                    combined_content = "\n\n".join(document_content)
                    response_parts.append(combined_content)
                    
                    # Add to sources (avoid duplicates)
                    if not any(s.get('file_name') == file_name for s in sources):
                        # Find representative chunk with highest score
                        best_chunk = max(chunks, key=lambda x: x['score'])
                        sources.append({
                            'file_name': file_name,
                            'file_type': selected_documents[0]['file_type'],  # Get from any doc
                            'file_url': selected_documents[0]['file_url'],  # Get from any doc
                            'relevance_score': best_chunk['score']
                        })
            
            logger.info(f"📋 Built response from {len(documents_by_file)} documents")
            
            # Build final response using contextual AI generation
            if response_parts:
                response_content = "\n\n".join(response_parts)
                
                # Handle different query intents with contextual responses
                if intent['type'] == 'count' and intent['target'] == 'projects':
                    # Extract project names from content for count queries
                    project_names = self._extract_project_names(response_content)
                    if project_names:
                        final_response = f"Based on the indexed documents, I found {len(project_names)} projects:\n\n"
                        for i, project in enumerate(project_names, 1):
                            final_response += f"{i}. {project}\n"
                        final_response += f"\nTotal: {len(project_names)} projects"
                    else:
                        final_response = "I couldn't identify specific project names in the content."
                
                elif intent['type'] == 'list' and intent['target'] == 'projects':
                    # Extract project names for list queries
                    project_names = self._extract_project_names(response_content)
                    if project_names:
                        final_response = f"Here are the projects I found:\n\n"
                        for i, project in enumerate(project_names, 1):
                            final_response += f"{i}. {project}\n"
                        final_response += f"\nFor detailed information about any specific project, please ask about it directly."
                    else:
                        # Use contextual response generation for complex lists
                        final_response = self._generate_contextual_response(query, response_content, conversation_history, intent)
                
                else:
                    # For general queries, use intelligent contextual response generation
                    logger.info("🧠 Generating contextual AI response")
                    final_response = self._generate_contextual_response(query, response_content, conversation_history, intent)
                
                # Add sources section (only if not already added by contextual response)
                if "Sources:" not in final_response:
                    sources_section = "\n\nSources:\n"
                    for source in sources:
                        sources_section += f"- {source['file_name']} ({source['file_type']}) - Score: {source['relevance_score']:.2f}\n"
                        sources_section += f"  URL: {source['file_url']}\n"
                    
                    final_response = final_response + sources_section
            else:
                final_response = "No relevant information found in the indexed documents for this query."
            
            processing_time = time.time() - start_time
            
            logger.info(f"✅ RAG Query completed in {processing_time:.2f}s with {len(selected_documents)} chunks from {len(sources)} documents")
            
            # Calculate tokens used (contextual response generation uses tokens)
            tokens_used = 0
            if intent['type'] not in ['count', 'list'] or "I couldn't identify" in final_response:
                # Estimate tokens used for contextual response generation (rough estimate)
                tokens_used = len(final_response.split()) * 1.5  # Rough estimate for input + output
            
            return {
                'success': True,
                'response': final_response,
                'documents': selected_documents,
                'sources_used': sources,
                'processing_time': processing_time,
                'tokens_used': int(tokens_used),
                'model_used': 'CONTEXTUAL_RAG_RETRIEVAL',
                'strategy_used': 'comprehensive' if use_comprehensive_search else 'simple',
                'query_enhanced': enhanced_query != query,
                'original_query': query,
                'enhanced_query': enhanced_query if enhanced_query != query else None
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"❌ Enhanced RAG Query failed: {str(e)}")
            
            return {
                'success': False,
                'error': str(e),
                'response': 'Failed to retrieve information from the indexed documents.',
                'documents': [],
                'processing_time': processing_time,
                'tokens_used': 0
            }
    
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
        conversation_history: List[Dict[str, str]] = None,
        top_k: int = 50,
        user_id: int = None
    ) -> Dict[str, Any]:
        """Generate AI response based on query and relevant documents."""
        start_time = time.time()
        
        try:
            if not self.is_available():
                raise Exception("Chatbot service not available")
            
            logger.info(f"💬 Generating response for query: {query[:50]}...")
            
            # Search Pinecone for relevant documents if not provided - use enhanced RAG method directly
            if relevant_documents is None:
                logger.info(f"🔍 Using enhanced RAG search with contextual query enhancement for: {query[:50]}...")
                # Use the enhanced RAG query method with user context and conversation history
                rag_result = self.rag_query(query, use_comprehensive_search=True, top_k=top_k, user_id=user_id, conversation_history=conversation_history)
                
                # If RAG query was successful and in retrieval-only mode, return RAG response directly
                if (rag_result.get('success') and 
                    rag_result.get('model_used') in ['CONTEXTUAL_RAG_RETRIEVAL', 'SIMPLE_RAG_RETRIEVAL', 'RAG_RETRIEVAL_ONLY'] and 
                    rag_result.get('response')):
                    
                    # Return enhanced RAG response directly without additional AI processing
                    processing_time = time.time() - start_time
                    logger.info(f"✅ Returning enhanced contextual RAG response in {processing_time:.2f}s")
                    
                    return {
                        'success': True,
                        'response': rag_result['response'],
                        'sources_used': rag_result.get('sources_used', []),
                        'processing_time': processing_time,
                        'tokens_used': rag_result.get('tokens_used', 0),  # Include tokens from contextual generation
                        'model_used': 'CONTEXTUAL_RAG_RETRIEVAL_DIRECT',
                        'search_strategy': rag_result.get('strategy_used', 'comprehensive'),
                        'query_enhanced': rag_result.get('query_enhanced', False),
                        'original_query': rag_result.get('original_query', query),
                        'enhanced_query': rag_result.get('enhanced_query', None)
                    }
                
                relevant_documents = rag_result.get('documents', [])
            
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
