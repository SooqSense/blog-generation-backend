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
        
        # Initialize connection state
        self.is_connected = True
        self.active_tasks = set()
        
        # Accept the connection
        await self.accept()
        
        # Start keepalive ping to prevent timeouts
        self.keepalive_task = asyncio.create_task(self._keepalive_ping())
    
    async def _keepalive_ping(self):
        """Send periodic pings to keep connection alive"""
        try:
            while self.is_connected:
                await asyncio.sleep(15)  # Ping every 15 seconds for better connection stability
                if self.is_connected:
                    try:
                        await self.send(text_data=json.dumps({
                            'type': 'ping',
                            'timestamp': timezone.now().isoformat()
                        }))
                        print(f"🏓 [KEEPALIVE] Ping sent - Active tasks: {len(self.active_tasks)}")
                    except Exception as e:
                        logger.warning(f"Keepalive ping failed: {e}")
                        self.is_connected = False
                        break
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Keepalive error: {e}")
            self.is_connected = False
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        self.is_connected = False
        
        # Cancel keepalive task
        if hasattr(self, 'keepalive_task'):
            self.keepalive_task.cancel()
            try:
                await self.keepalive_task
            except asyncio.CancelledError:
                pass
        
        # Cancel all active tasks gracefully
        for task in self.active_tasks:
            if not task.done():
                try:
                    task.cancel()
                    # Give tasks a moment to clean up
                    await asyncio.sleep(0.1)
                except Exception as e:
                    logger.warning(f"Error cancelling task: {e}")
        
        logger.info(f"WebSocket disconnected - Code: {close_code}")
    
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
            elif message_type == 'pong':
                # Client responded to our ping
                pass
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
        message_id = data.get('message_id', 'default')
        
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
        """Handle blog generation streaming - KEEP CONNECTION ALIVE"""
        try:
            # Extract blog parameters
            topic = data.get('topic', '').strip()
            blog_type = data.get('blog_type', 'News')
            length_min = int(data.get('length_min', 800))
            length_max = int(data.get('length_max', 1500))
            introduction = data.get('introduction', True)
            faq = data.get('faq', False)
            cta = data.get('cta', False)
            conclusion = data.get('conclusion', True)
            target_audience = data.get('target_audience', [])
            sample_blog_url = data.get('sample_blog_url')
            generate_image_prompts = data.get('generate_image_prompts', True)
            generate_images = data.get('generate_images', True)
            use_custom_llm = data.get('use_custom_llm', False)
            keywords = data.get('keywords', [])
            message_id = data.get('message_id', 'default')

            if not topic:
                await self.send(text_data=json.dumps({
                    'type': 'error', 
                    'message': 'Topic is required',
                    'message_id': message_id
                }))
                return

            # Use the updated BlogWriter with streaming capabilities
            from management_app.blog_generator.service.blog_writing.blog_writer import BlogWriter
            
            # Initialize blog writer
            generator = BlogWriter(
                topic=topic,
                blog_type=blog_type,
                length_min=length_min,
                length_max=length_max,
                keywords=keywords,
                target_audience=target_audience,
                use_custom_llm=use_custom_llm,
                generate_images=generate_images,
                max_image_prompts=5,
            )
            
            # Define streaming callbacks with error handling
            async def safe_send(data_dict):
                """Safely send data, checking connection status"""
                if not self.is_connected:
                    raise ConnectionError("WebSocket connection closed")
                try:
                    await self.send(text_data=json.dumps(data_dict))
                    print(f"📤 [WEBSOCKET] Sent: {data_dict.get('type', 'unknown')}")
                except Exception as e:
                    logger.error(f"Failed to send data: {e}")
                    self.is_connected = False
                    raise
            
            async def on_status(stage, message):
                print(f"📊 [BLOG STREAM] Status: {stage} - {message}")
                try:
                    await safe_send({
                        'type': 'status', 
                        'stage': stage,
                        'message': message,
                        'message_id': message_id
                    })
                except Exception as e:
                    print(f"⚠️ [BLOG STREAM] Status send failed: {e}")
                    # Don't raise - continue with generation
            
            async def on_toc(sections):
                print(f"📋 [BLOG STREAM] TOC Generated: {len(sections)} sections")
                await safe_send({
                    'type': 'toc', 
                    'sections': sections, 
                    'message_id': message_id
                })
            
            async def on_section_start(section, index):
                print(f"🚀 [BLOG STREAM] Starting Section {index}: {section}")
                await safe_send({
                    'type': 'section_start', 
                    'section': section, 
                    'index': index, 
                    'message_id': message_id
                })
            
            async def on_section_token(token):
                # Only log occasionally to reduce overhead
                if len(token) > 0:
                    try:
                        await safe_send({
                            'type': 'section_token', 
                            'content': token, 
                            'message_id': message_id
                        })
                    except Exception as e:
                        print(f"⚠️ [BLOG STREAM] Token send failed: {e}")
                        # Don't raise - continue with generation
            
            async def on_image(section, image_data):
                print(f"🖼️ [BLOG STREAM] Image generated for section: {section}")
                await safe_send({
                    'type': 'image', 
                    'section': section, 
                    'image_url': image_data.get('image_url'),
                    'image_data': image_data,
                    'message_id': message_id
                })
            
            async def on_section_complete(section, content):
                print(f"✅ [BLOG STREAM] Section completed: {section}")
                await safe_send({
                    'type': 'section_complete', 
                    'section': section, 
                    'message_id': message_id
                })
            
            async def on_complete(result_data):
                print(f"🎉 [BLOG STREAM] Blog generation completed!")
                await safe_send({
                    'type': 'complete',
                    'message': '✅ Blog generation completed successfully!',
                    'data': result_data,
                    'message_id': message_id
                })
            
            async def on_error(error_message):
                print(f"❌ [BLOG STREAM] Error: {error_message}")
                await safe_send({
                    'type': 'error', 
                    'message': f'Blog generation failed: {error_message}',
                    'message_id': message_id
                })
            
            # Create and track the generation task
            generation_task = asyncio.create_task(
                generator.generate_streaming_blog(
                    websocket=self,
                    on_status=on_status,
                    on_toc=on_toc,
                    on_section_start=on_section_start,
                    on_section_token=on_section_token,
                    on_image=on_image,
                    on_section_complete=on_section_complete,
                    on_complete=on_complete,
                    on_error=on_error
                )
            )
            
            self.active_tasks.add(generation_task)
            
            try:
                # Wait for generation with a reasonable timeout
                await asyncio.wait_for(generation_task, timeout=1200)  # 20 minutes timeout
                print(f"✅ [BLOG STREAM] Blog generation completed successfully")
                
                # Send completion message
                try:
                    await safe_send({
                        'type': 'complete',
                        'message': 'Blog generation completed successfully',
                        'message_id': message_id
                    })
                except:
                    pass
                
                # KEEP CONNECTION ALIVE - DO NOT CLOSE
                # Client can request more operations or disconnect when ready
                
            except asyncio.TimeoutError:
                print(f"⏰ [BLOG STREAM] Blog generation timed out")
                try:
                    await safe_send({
                        'type': 'error',
                        'message': 'Blog generation timed out after 20 minutes',
                        'message_id': message_id
                    })
                except:
                    pass
            except asyncio.CancelledError:
                print(f"🛑 [BLOG STREAM] Blog generation cancelled")
                try:
                    await safe_send({
                        'type': 'error',
                        'message': 'Blog generation was cancelled',
                        'message_id': message_id
                    })
                except:
                    pass
            except ConnectionError as e:
                print(f"🔌 [BLOG STREAM] Connection lost: {e}")
                # Connection already closed, can't send error
            except Exception as e:
                print(f"❌ [BLOG STREAM] Blog generation failed: {e}")
                try:
                    await safe_send({
                        'type': 'error',
                        'message': f'Blog generation failed: {str(e)}',
                        'message_id': message_id
                    })
                except:
                    pass
            finally:
                self.active_tasks.discard(generation_task)

        except Exception as e:
            logger.error(f"Error handling blog generation: {e}", exc_info=True)
            try:
                await self.send(text_data=json.dumps({
                    'type': 'error', 
                    'message': f'Blog generation failed: {str(e)}',
                    'message_id': message_id
                }))
            except:
                pass
    
    async def handle_linkedin_post(self, data):
        """Handle LinkedIn post generation streaming"""
        try:
            topic = data.get('topic', '')
            tone = data.get('tone', 'professional')
            hashtags = data.get('hashtags', [])
            
            if not topic:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Topic is required for LinkedIn post generation'
                }))
                return
            
            await self.stream_ai_response(
                f"Generate a LinkedIn post about: {topic}, Tone: {tone}, Hashtags: {hashtags}", 
                'linkedin'
            )
            
        except Exception as e:
            logger.error(f"Error handling LinkedIn post generation: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to process LinkedIn post generation'
            }))
    
    async def handle_upwork_proposal(self, data):
        """Handle Upwork proposal generation streaming"""
        try:
            job_description = data.get('job_description', '')
            skills = data.get('skills', [])
            experience = data.get('experience', '')
            
            if not job_description:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Job description is required for Upwork proposal generation'
                }))
                return
            
            await self.stream_ai_response(
                f"Generate an Upwork proposal for: {job_description}, Skills: {skills}, Experience: {experience}", 
                'upwork'
            )
            
        except Exception as e:
            logger.error(f"Error handling Upwork proposal generation: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to process Upwork proposal generation'
            }))
    
    async def stream_ai_response(self, query, feature_type='general', message_id='default'):
        """Stream AI response tokens for any feature"""
        try:
            full_response_parts = []
            
            async for chunk in project_chatbot.ask_stream_async(query):
                if not chunk or not self.is_connected:
                    continue
                
                text = str(chunk)
                if not text or text == "":
                    continue
                
                full_response_parts.append(text)
                
                try:
                    await self.send(text_data=json.dumps({
                        'type': 'token',
                        'content': text,
                        'feature_type': feature_type,
                        'message_id': message_id
                    }))
                except Exception as send_error:
                    logger.error(f"Error sending token: {send_error}")
                    break
            
            # Save complete response
            if (self.user and 
                not (hasattr(self.user, 'is_anonymous') and self.user.is_anonymous) and 
                hasattr(self, 'chat_session') and 
                self.chat_session):
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
        """Get or create chat session"""
        if not self.user or (hasattr(self.user, 'is_anonymous') and self.user.is_anonymous):
            return None
            
        try:
            if session_id:
                session = ChatSession.objects.filter(
                    session_id=session_id,
                    user_id=self.user.id,
                    is_active=True
                ).first()
                
                if session:
                    return session
            
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
        """Save chat message"""
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
        """Update session message count"""
        if not self.chat_session:
            return
            
        try:
            self.chat_session.total_messages += 2
            self.chat_session.updated_at = timezone.now()
            self.chat_session.save()
        except Exception as e:
            logger.error(f"Error updating session: {e}")


# Keep the old class name for backward compatibility
ChatWebSocketConsumer = StreamingWebSocketConsumer