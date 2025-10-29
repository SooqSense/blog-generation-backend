import asyncio
import json
import threading
import time
from typing import Optional, Dict, Any, List, Callable

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from .base_client import APIClient
from .chatbot_api import PersistentWebSocketManager
from base.config import get_api_endpoint


class BlogAPI:
    """API client for blog generation endpoints with persistent WebSocket support"""

    def __init__(self):
        self.client = APIClient()
        self.websocket_url = get_api_endpoint('blog_websocket')
        self.ws_manager: Optional[PersistentWebSocketManager] = None
        self._ws_connection = None
        self._ws_lock = threading.Lock()
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5
        self._reconnect_delay = 2  # seconds

    def generate_blog(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Non-streaming blog generation"""
        endpoint = get_api_endpoint('blog_generation')
        return self.client.post(endpoint, data=kwargs)

    def init_persistent_connection(self, headers=None):
        """Initialize persistent WebSocket connection for blog streaming"""
        # Use provided headers or get fresh headers
        if headers is None:
            headers = self.client._get_auth_headers()
        
        # If manager exists and is running, check if headers have changed
        if self.ws_manager and self.ws_manager.is_running:
            # If headers have changed, stop old connection and create new one
            if self.ws_manager.headers != headers:
                print("🔄 Headers changed, recreating WebSocket connection...")
                self.ws_manager.stop()
                self.ws_manager = PersistentWebSocketManager(self.websocket_url, headers)
                self.ws_manager.start()
            return self.ws_manager
        
        # Create new WebSocket manager with fresh headers
        print(f"🔑 Initializing WebSocket with auth headers: {list(headers.keys())}")
        self.ws_manager = PersistentWebSocketManager(self.websocket_url, headers)
        self.ws_manager.start()
        return self.ws_manager

    def generate_blog_stream_websocket(
        self, 
        blog_data: Dict[str, Any], 
        on_event: Optional[Callable] = None, 
        on_complete: Optional[Callable] = None, 
        on_error: Optional[Callable] = None
    ) -> Optional[str]:
        """Send a blog generation message via persistent WebSocket"""
        try:
            # Initialize persistent connection if needed
            manager = self.init_persistent_connection()
            
            # Give connection more time to establish and stabilize
            max_wait_attempts = 20  # 10 seconds max wait
            wait_count = 0
            while wait_count < max_wait_attempts:
                if manager.websocket and manager.is_running:
                    break
                import time as time_module
                time_module.sleep(0.5)
                wait_count += 1
            
            # Verify connection is ready
            if not manager.websocket or not manager.is_running:
                error_msg = "WebSocket connection not established after waiting"
                print(f"❌ [BLOG API] {error_msg}")
                if on_error:
                    on_error(error_msg)
                return None
            
            # Generate unique message ID
            message_id = f"blog_{int(time.time() * 1000)}"
            
            print(f"📤 [BLOG API] Preparing to send blog generation request: {message_id}")
            print(f"🔌 [BLOG API] WebSocket status - running: {manager.is_running}, connected: {manager.websocket is not None}")

            # Attach callbacks for this specific message
            manager.response_callbacks[message_id] = {
                'on_token': lambda token: None,  # Tokens come as section_token events
                'on_complete': on_complete,
                'on_error': on_error,
                'on_event': on_event
            }

            # Queue the blog generation message
            message = {
                'type': 'blog_generation',
                'message_id': message_id,
                **blog_data
            }
            
            manager.message_queue.put(message)
            print(f"✅ [BLOG API] Message queued successfully: {message_id}")
            print(f"📋 [BLOG API] Blog data: topic={blog_data.get('topic')}, type={blog_data.get('blog_type')}")
            print(f"🔍 [BLOG API] Active callbacks: {len(manager.response_callbacks)}")
            
            return message_id
            
        except Exception as e:
            error_msg = f"Failed to queue blog generation: {str(e)}"
            print(f"❌ [BLOG API] {error_msg}")
            import traceback
            traceback.print_exc()
            if on_error:
                on_error(error_msg)
            return None

    def generate_blog_stream(
        self, 
        blog_data: Dict[str, Any], 
        on_status: Optional[Callable] = None, 
        on_complete: Optional[Callable] = None, 
        on_error: Optional[Callable] = None, 
        on_event: Optional[Callable] = None
    ):
        """
        Stream blog generation via WebSocket with real-time updates.
        Connection stays alive throughout the entire process.
        """
        try:
            # Capture headers before threading
            headers = self.client._get_auth_headers()
            
            # Use event loop in main thread if possible
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is already running, use a thread
                    self._stream_in_thread(
                        blog_data, headers, on_status, on_complete, on_error, on_event
                    )
                else:
                    # Run directly in the current thread
                    loop.run_until_complete(
                        self._websocket_stream_with_reconnect(
                            blog_data, headers, on_status, on_complete, on_error, on_event
                        )
                    )
            except RuntimeError:
                # No event loop, create one
                asyncio.run(
                    self._websocket_stream_with_reconnect(
                        blog_data, headers, on_status, on_complete, on_error, on_event
                    )
                )
                
        except Exception as e:
            print(f"❌ [BLOG API] Stream error: {str(e)}")
            if on_error:
                on_error(str(e))

    def _stream_in_thread(
        self,
        blog_data: Dict[str, Any],
        headers: Dict[str, str],
        on_status: Optional[Callable],
        on_complete: Optional[Callable],
        on_error: Optional[Callable],
        on_event: Optional[Callable]
    ):
        """Run streaming in a separate thread"""
        def thread_target():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(
                    self._websocket_stream_with_reconnect(
                        blog_data, headers, on_status, on_complete, on_error, on_event
                    )
                )
            except Exception as e:
                print(f"❌ [BLOG API THREAD] Error: {str(e)}")
                if on_error:
                    on_error(str(e))
            finally:
                loop.close()

        thread = threading.Thread(target=thread_target, daemon=False)
        thread.start()
        # Don't join - let it run independently

    async def _websocket_stream_with_reconnect(
        self,
        blog_data: Dict[str, Any],
        headers: Dict[str, str],
        on_status: Optional[Callable],
        on_complete: Optional[Callable],
        on_error: Optional[Callable],
        on_event: Optional[Callable]
    ):
        """Main WebSocket streaming with automatic reconnection"""
        self._reconnect_attempts = 0
        
        while self._reconnect_attempts < self._max_reconnect_attempts:
            try:
                print(f"🔌 [BLOG API] Connecting to WebSocket (attempt {self._reconnect_attempts + 1})...")
                
                await self._websocket_connect(
                    self.websocket_url,
                    blog_data,
                    headers,
                    on_status,
                    on_complete,
                    on_error,
                    on_event
                )
                
                # If we get here, connection completed successfully
                print(f"✅ [BLOG API] Stream completed successfully")
                self._reconnect_attempts = 0
                return
                
            except (ConnectionClosed, WebSocketException) as e:
                self._reconnect_attempts += 1
                error_msg = f"Connection lost: {str(e)}"
                print(f"⚠️ [BLOG API] {error_msg} (attempt {self._reconnect_attempts}/{self._max_reconnect_attempts})")
                
                if self._reconnect_attempts < self._max_reconnect_attempts:
                    print(f"🔄 [BLOG API] Reconnecting in {self._reconnect_delay} seconds...")
                    await asyncio.sleep(self._reconnect_delay)
                    self._reconnect_delay = min(self._reconnect_delay * 2, 30)  # Exponential backoff
                else:
                    if on_error:
                        on_error(f"Failed after {self._max_reconnect_attempts} reconnection attempts")
                    return
                    
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                print(f"❌ [BLOG API] {error_msg}")
                if on_error:
                    on_error(error_msg)
                return

    async def _websocket_connect(
        self,
        ws_url: str,
        blog_data: Dict[str, Any],
        headers: Dict[str, str],
        on_status: Optional[Callable],
        on_complete: Optional[Callable],
        on_error: Optional[Callable],
        on_event: Optional[Callable]
    ):
        """Establish WebSocket connection and handle streaming"""
        # Check authentication
        has_auth = 'Authorization' in headers and headers['Authorization']
        print(f"🔐 [BLOG API] Auth Token Present: {has_auth}")
        
        if not has_auth:
            error_msg = "Authentication token not found. Please ensure you're logged in."
            if on_error:
                on_error(error_msg)
            raise ValueError(error_msg)
        
        # Format headers for WebSocket
        websocket_headers = []
        for key, value in headers.items():
            if key.lower() != 'content-type' and value:
                header_key = key.lower() if isinstance(key, str) else key
                websocket_headers.append((header_key, value))

        # Connect with increased timeout and ping settings
        async with websockets.connect(
            ws_url,
            additional_headers=websocket_headers,
            ping_interval=20,  # Send ping every 20 seconds
            ping_timeout=20,   # Wait 20 seconds for pong (more lenient for slow networks)
            close_timeout=10,  # Wait 10 seconds for close
            max_size=10 * 1024 * 1024  # 10MB max message size
        ) as websocket:
            
            print(f"✅ [BLOG API] WebSocket connected")
            
            # Send blog generation request
            message = {
                'type': 'blog_generation',
                **blog_data
            }
            await websocket.send(json.dumps(message))
            print(f"📤 [BLOG API] Sent blog generation request")
            
            # Start application-level ping sender to keep connection alive
            async def send_pings():
                """Send application-level pings to keep connection active during long operations"""
                try:
                    while True:
                        await asyncio.sleep(15)  # Send every 15 seconds
                        try:
                            await websocket.send(json.dumps({'type': 'ping'}))
                        except websockets.exceptions.ConnectionClosed:
                            break
                        except Exception as e:
                            print(f"⚠️ [BLOG API] Ping send error: {e}")
                            break
                except asyncio.CancelledError:
                    pass
            
            ping_task = asyncio.create_task(send_pings())
            
            try:
                # Process messages in real-time
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        message_type = data.get('type')
                        
                        print(f"📨 [BLOG API] Received: {message_type}")

                        if message_type == 'ping':
                            # Respond to server ping
                            await websocket.send(json.dumps({'type': 'pong'}))
                            continue
                            
                        elif message_type == 'status' and on_status:
                            on_status(data.get('stage', ''), data.get('message', ''))
                            
                        elif message_type in ('toc', 'section_start', 'section_token', 'section_complete', 'image'):
                            if on_event:
                                on_event(data)
                                
                        elif message_type == 'complete':
                            print(f"🎉 [BLOG API] Generation completed")
                            if on_complete:
                                on_complete(data.get('data', {}))
                            # Exit gracefully after completion
                            break
                            
                        elif message_type == 'error':
                            error_msg = data.get('message', 'Unknown error')
                            print(f"❌ [BLOG API] Error from server: {error_msg}")
                            if on_error:
                                on_error(error_msg)
                            break
                            
                    except json.JSONDecodeError as e:
                        error_msg = f'Invalid JSON received: {str(e)}'
                        print(f"❌ [BLOG API] {error_msg}")
                        if on_error:
                            on_error(error_msg)
                        break
                        
            finally:
                ping_task.cancel()
                try:
                    await ping_task
                except asyncio.CancelledError:
                    pass
                print(f"🔌 [BLOG API] WebSocket connection closed")

    def list_blogs(self) -> Optional[Dict[str, Any]]:
        """List all blogs"""
        endpoint = get_api_endpoint('blog_list')
        return self.client.get(endpoint)

    def delete_blogs(self, ids: List[int]) -> Optional[Dict[str, Any]]:
        """Delete one or more blogs"""
        endpoint = get_api_endpoint('blog_delete')
        if len(ids) == 1:
            return self.client.delete(endpoint, data={'blog_id': ids[0]})
        else:
            return self.client.delete(endpoint, data={'blog_ids': ids})

    def get_blog(self, blog_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific blog"""
        endpoint = f"blogs/get/{blog_id}/"
        return self.client.get(endpoint)

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Generic GET request"""
        return self.client.get(endpoint, params=params)

    def close(self):
        """Close WebSocket connection and cleanup"""
        if self.ws_manager:
            self.ws_manager.stop()
            self.ws_manager = None
        self._ws_connection = None
        print(f"🔌 [BLOG API] Connections closed")