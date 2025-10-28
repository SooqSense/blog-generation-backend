import uuid
import json
import logging
import asyncio
from django.utils import timezone
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

# Import models
from management_app.chatbot.models import ChatSession, ChatMessage

# Set up logging
logger = logging.getLogger(__name__)
User = get_user_model()

# Import local services
from management_app.chatbot.service.agent.agent import project_chatbot


class StreamingWebSocketConsumer(AsyncWebsocketConsumer):
    """Centralized WebSocket consumer for real-time streaming across all features"""
    
    async def connect(self):
        """Handle WebSocket connection - Authentication handled by middleware"""
        path = self.scope.get('path', 'unknown')
        logger.info(f"WebSocket connection attempt - Path: {path}")
        
        # Get user from scope (set by ClerkWebSocketAuthMiddleware)
        self.user = self.scope.get("user")
        
        # Get organization from headers if available
        headers = dict(self.scope.get("headers", []))
        self.organization = headers.get(b"x-selected-organization", b"").decode()
        
        # Check if user is authenticated
        is_authenticated = self.user and not self.user.is_anonymous
        
        logger.info(f"WebSocket connected - Path: {path}, User: {getattr(self.user, 'username', 'Anonymous')}, Authenticated: {is_authenticated}, Org: {self.organization}")
        
        # Store connection info for reuse
        self.connection_info = {
            'path': path,
            'user_id': getattr(self.user, 'id', None),
            'username': getattr(self.user, 'username', 'Anonymous'),
            'is_authenticated': is_authenticated,
            'organization': self.organization
        }
        
        # Accept the connection
        await self.accept()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        logger.info(f"WebSocket disconnected for streaming - Code: {close_code}")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'blog_generation':
                await self.handle_blog_generation(data)
            elif message_type == 'linkedin_post':
                await self.handle_linkedin_post(data)
            elif message_type == 'upwork_proposal':
                await self.handle_upwork_proposal(data)
            elif message_type == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Unknown message type'
                }))
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Internal server error'
            }))
    
    async def handle_chat_message(self, data):
        """Handle chat message and stream response"""
        query = data.get('query', '').strip()
        session_id = data.get('session_id', '').strip()
        message_id = data.get('message_id', 'default')  # Track message ID for multiplexing
        
        if not query:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Query is required',
                'message_id': message_id
            }))
            return
        
        try:
            # Get or create chat session (only if user is authenticated)
            if self.user and not (hasattr(self.user, 'is_anonymous') and self.user.is_anonymous):
                self.chat_session = await self.get_or_create_session(session_id)
                if self.chat_session:
                    await self.save_message('user', query)
            
            # Stream AI response
            await self.stream_ai_response(query, 'chatbot', message_id)
            
        except Exception as e:
            logger.error(f"Error handling chat message: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to process chat message'
            }))
    
    async def handle_blog_generation(self, data):
        """Handle blog generation streaming with real-time stage updates"""
        try:
            # Extract blog generation parameters
            topic = data.get('topic', '')
            keywords = data.get('keywords', [])
            blog_type = data.get('blog_type', 'News')
            length_min = data.get('length_min', 800)
            length_max = data.get('length_max', 1500)
            
            if not topic:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Topic is required for blog generation'
                }))
                return
            
            logger.info(f"Starting blog generation stream: topic={topic}, blog_type={blog_type}")
            
            # Send stage updates for blog generation process
            stages = [
                {'stage': 'initialization', 'message': '🚀 Initializing blog generation...'},
                {'stage': 'research', 'message': '🔍 Researching topic and gathering information...'},
                {'stage': 'planning', 'message': '📋 Planning blog structure and outline...'},
                {'stage': 'writing', 'message': '✍️ Writing blog content...'},
                {'stage': 'editing', 'message': '✨ Editing and polishing content...'},
                {'stage': 'finalizing', 'message': '🎯 Finalizing blog post...'}
            ]
            
            for stage_info in stages:
                await self.send(text_data=json.dumps({
                    'type': 'status',
                    'stage': stage_info['stage'],
                    'message': stage_info['message']
                }))
                # Small delay to make stages visible
                await asyncio.sleep(0.5)
            
            # Import blog writer service (async)
            from management_app.blog_generator.service.blog_writing.blog_writer import BlogWriter
            
            # Generate blog content (note: this is a blocking operation)
            # In a production system, this would be refactored to support true streaming
            blog_writer = BlogWriter(
                use_custom_llm=False,
                topic=topic,
                keywords=keywords,
                blog_type=blog_type,
                length_min=length_min,
                length_max=length_max,
                introduction=data.get('introduction', True),
                table_of_content=data.get('table_of_content', False),
                faq=data.get('faq', False),
                cta=data.get('cta', False),
                conclusion=data.get('conclusion', True),
                target_audience=data.get('target_audience', []),
                sample_blog_url=data.get('sample_blog_url'),
                generate_image_prompts=data.get('generate_image_prompts', True),
                generate_images=data.get('generate_images', True)
            )
            
            # Run blog generation in thread pool to avoid blocking
            result = await database_sync_to_async(blog_writer.generate_blog)(
                topic=topic,
                keywords=keywords,
                blog_type=blog_type,
                length_min=length_min,
                length_max=length_max
            )
            
            # Send completion with result
            await self.send(text_data=json.dumps({
                'type': 'complete',
                'message': '✅ Blog generation completed successfully!',
                'data': {
                    'topic': topic,
                    'content': result.get('raw_content', result.get('content', '')),
                    'word_count': len(result.get('raw_content', '').split()) if result.get('raw_content') else 0,
                    'images_count': result.get('images_count', 0),
                    'sources_count': result.get('sources_count', 0)
                }
            }))
            
        except Exception as e:
            logger.error(f"Error handling blog generation: {e}", exc_info=True)
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Blog generation failed: {str(e)}'
            }))
    
    async def handle_linkedin_post(self, data):
        """Handle LinkedIn post generation streaming"""
        try:
            # Extract LinkedIn post parameters
            topic = data.get('topic', '')
            tone = data.get('tone', 'professional')
            hashtags = data.get('hashtags', [])
            
            if not topic:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Topic is required for LinkedIn post generation'
                }))
                return
            
            # Stream LinkedIn post generation response
            await self.stream_ai_response(f"Generate a LinkedIn post about: {topic}, Tone: {tone}, Hashtags: {hashtags}", 'linkedin')
            
        except Exception as e:
            logger.error(f"Error handling LinkedIn post generation: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to process LinkedIn post generation'
            }))
    
    async def handle_upwork_proposal(self, data):
        """Handle Upwork proposal generation streaming"""
        try:
            # Extract Upwork proposal parameters
            job_description = data.get('job_description', '')
            skills = data.get('skills', [])
            experience = data.get('experience', '')
            
            if not job_description:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Job description is required for Upwork proposal generation'
                }))
                return
            
            # Stream Upwork proposal generation response
            await self.stream_ai_response(f"Generate an Upwork proposal for: {job_description}, Skills: {skills}, Experience: {experience}", 'upwork')
            
        except Exception as e:
            logger.error(f"Error handling Upwork proposal generation: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to process Upwork proposal generation'
            }))
    
    async def stream_ai_response(self, query, feature_type='general', message_id='default'):
        """Stream AI response tokens for any feature using fully async approach"""
        try:
            full_response_parts = []
            
            # Use the new async streaming method for real-time performance
            async for chunk in project_chatbot.ask_stream_async(query):
                if not chunk:
                    continue
                
                # Convert to string but preserve spaces and formatting
                text = str(chunk)
                
                # Only skip completely empty chunks
                if not text or text == "":
                    continue
                
                # Accumulate for saving (preserve original text)
                full_response_parts.append(text)
                
                # Send token to client immediately (with all formatting preserved)
                try:
                    token_data = {
                        'type': 'token',
                        'content': text,  # Send as-is to preserve spaces
                        'feature_type': feature_type,
                        'message_id': message_id
                    }
                    # Reduce logging frequency for better performance
                    if len(full_response_parts) % 10 == 0:  # Log every 10th token
                        logger.debug(f"🔄 Sending token batch: {len(full_response_parts)} tokens")
                    await self.send(text_data=json.dumps(token_data))
                except Exception as send_error:
                    logger.error(f"Error sending token: {send_error}")
                    # If we can't send, the connection is likely closed
                    break
            
            # Save complete response (only for authenticated users with chat sessions)
            if self.user and not (hasattr(self.user, 'is_anonymous') and self.user.is_anonymous) and hasattr(self, 'chat_session') and self.chat_session:
                full_response = "".join(full_response_parts)
                await self.save_message('assistant', full_response)
                await self.update_session_messages()
            
            # Send completion signal
            try:
                await self.send(text_data=json.dumps({
                    'type': 'complete',
                    'message': 'Response completed',
                    'feature_type': feature_type,
                    'message_id': message_id
                }))
            except Exception as send_error:
                logger.warning(f"Could not send completion signal: {send_error}")
            
        except Exception as e:
            logger.error(f"Error streaming AI response: {e}", exc_info=True)
            try:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Error generating response',
                    'feature_type': feature_type
                }))
            except Exception:
                logger.error("Could not send error message to closed connection")
    
    @database_sync_to_async
    def get_or_create_session(self, session_id):
        """Get or create chat session (only for authenticated users)"""
        if not self.user or (hasattr(self.user, 'is_anonymous') and self.user.is_anonymous):
            return None
            
        try:
            if session_id:
                # Try to find existing session
                session = ChatSession.objects.filter(
                    session_id=session_id,
                    user_id=self.user.id,
                    is_active=True
                ).first()
                
                if session:
                    return session
            
            # Create new session
            new_session_id = session_id or str(uuid.uuid4())
            session = ChatSession.objects.create(
                session_id=new_session_id,
                user_id=self.user.id,
                username=self.user.username,
                email=self.user.email,
                is_active=True,
                created_at=timezone.now(),
            )
            return session
            
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return None
    
    @database_sync_to_async
    def save_message(self, message_type, content):
        """Save chat message (only for authenticated users)"""
        if not self.chat_session:
            return
            
        try:
            ChatMessage.objects.create(
                session_id=self.chat_session,
                message_type=message_type,
                content=content,
                created_at=timezone.now(),
            )
        except Exception as e:
            logger.error(f"Error saving message: {e}")
    
    @database_sync_to_async
    def update_session_messages(self):
        """Update session message count (only for authenticated users)"""
        if not self.chat_session:
            return
            
        try:
            self.chat_session.total_messages += 2  # User + Assistant messages
            self.chat_session.updated_at = timezone.now()
            self.chat_session.save()
        except Exception as e:
            logger.error(f"Error updating session: {e}")


# Keep the old class name for backward compatibility
ChatWebSocketConsumer = StreamingWebSocketConsumer
