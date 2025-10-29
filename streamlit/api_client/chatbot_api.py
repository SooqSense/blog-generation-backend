import asyncio
import json
import threading
import queue
from typing import Optional, Dict, Any, Callable

import websockets

from .base_client import APIClient
from base.config import get_api_endpoint


class PersistentWebSocketManager:
    """Manages a persistent WebSocket connection for real-time chatbot streaming"""
    
    def __init__(self, ws_url: str, headers: Dict[str, str]):
        self.ws_url = ws_url
        self.headers = headers
        self.websocket = None
        self.loop = None
        self.thread = None
        self.message_queue = queue.Queue()
        self.response_callbacks = {}  # message_id -> callbacks
        self.is_running = False
        self.connection_lock = threading.Lock()
        
    def start(self):
        """Start the persistent WebSocket connection in a background thread"""
        with self.connection_lock:
            if self.is_running and self.thread and self.thread.is_alive():
                print("⚠️ WebSocket already running")
                return
                
            # Clean up any existing thread
            if self.thread and not self.thread.is_alive():
                self.thread = None
                
            self.is_running = True
            self.thread = threading.Thread(target=self._run_websocket_loop, daemon=True)
            self.thread.start()
            print("✅ Persistent WebSocket connection started")
    
    def _run_websocket_loop(self):
        """Run the WebSocket event loop in a separate thread"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._maintain_connection())
        except Exception as e:
            print(f"❌ WebSocket loop error: {e}")
        finally:
            self.is_running = False
    
    async def _maintain_connection(self):
        """Maintain persistent WebSocket connection and handle messages"""
        # Format headers for WebSocket
        websocket_headers = []
        for key, value in self.headers.items():
            if key.lower() != 'content-type' and value:
                websocket_headers.append((key.lower(), value))
        
        print(f"🔗 Connecting to WebSocket: {self.ws_url}")
        print(f"🔑 Headers: {dict(websocket_headers)}")
        
        try:
            # Increased timeouts for long-running operations like blog generation
            async with websockets.connect(
                self.ws_url, 
                additional_headers=websocket_headers,
                ping_interval=20,  # Send ping every 20 seconds
                ping_timeout=20,   # Wait 20 seconds for pong (more lenient)
                close_timeout=10,  # Wait 10 seconds for close
                max_size=10 * 1024 * 1024,  # 10MB max message size
                max_queue=100  # Allow more queued messages
            ) as websocket:
                self.websocket = websocket
                print("✅ WebSocket connected successfully!")
                
                # Handle incoming and outgoing messages concurrently with keep-alive
                try:
                    await asyncio.gather(
                        self._send_messages(websocket),
                        self._receive_messages(websocket),
                        self._keep_alive(websocket),
                        return_exceptions=False
                    )
                except Exception as e:
                    print(f"⚠️ Error in WebSocket message handlers: {e}")
                    import traceback
                    traceback.print_exc()
                    
        except websockets.exceptions.ConnectionClosed as e:
            print(f"🔌 WebSocket connection closed: {e}")
        except Exception as e:
            print(f"❌ WebSocket connection error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.websocket = None
            self.is_running = False
            print(f"🔌 WebSocket manager stopped. Active callbacks at close: {len(self.response_callbacks)}")
    
    async def _keep_alive(self, websocket):
        """Send periodic application-level ping messages to keep connection alive
        Note: This is in addition to the websocket library's built-in ping/pong mechanism
        """
        while self.is_running:
            try:
                await asyncio.sleep(15)  # Ping every 15 seconds (less than websocket ping_interval)
                if self.is_running:
                    # Send application-level ping
                    await websocket.send(json.dumps({'type': 'ping'}))
                    # Don't print on every ping to reduce noise
            except websockets.exceptions.ConnectionClosed:
                print("🔌 Keep-alive: Connection closed")
                self.is_running = False
                break
            except Exception as e:
                print(f"❌ Keep-alive error: {e}")
                self.is_running = False
                break
    
    async def _send_messages(self, websocket):
        """Send queued messages to WebSocket - runs continuously"""
        while self.is_running:
            try:
                # Check queue for messages to send
                try:
                    message_data = self.message_queue.get(timeout=0.1)
                    message_json = json.dumps(message_data)
                    await websocket.send(message_json)
                    msg_type = message_data.get('type', 'unknown')
                    msg_id = message_data.get('message_id', 'unknown')
                    print(f"📤 Sent message: type={msg_type}, id={msg_id}")
                except queue.Empty:
                    # Keep connection alive with small sleep
                    await asyncio.sleep(0.1)
            except websockets.exceptions.ConnectionClosed as e:
                print(f"🔌 Send loop: Connection closed - {e}")
                self.is_running = False
                break
            except Exception as e:
                print(f"❌ Error sending message: {e}")
                import traceback
                traceback.print_exc()
                # Don't break immediately, might be transient error
                await asyncio.sleep(0.5)
    
    async def _receive_messages(self, websocket):
        """Receive and dispatch WebSocket messages - runs continuously"""
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    message_type = data.get('type')
                    message_id = data.get('message_id', 'default')
                    
                    # Log received message for debugging
                    if message_type not in ['ping', 'pong']:
                        print(f"📥 [WS Manager] Received: type={message_type}, id={message_id}")
                    
                    # Handle ping IMMEDIATELY - critical for keeping connection alive
                    if message_type == 'ping':
                        try:
                            await websocket.send(json.dumps({'type': 'pong'}))
                            print(f"🏓 [WS Manager] Responded to server ping")
                        except Exception as e:
                            print(f"⚠️ [WS Manager] Failed to send pong: {e}")
                        continue
                    
                    # Handle pong - ignore
                    if message_type == 'pong':
                        continue
                    
                    # Get callbacks for this message
                    callbacks = self.response_callbacks.get(message_id, {})
                    
                    # Handle chatbot token messages
                    if message_type == 'token':
                        content = data.get('content', '')
                        if content and callbacks.get('on_token'):
                            try:
                                callbacks['on_token'](content)
                            except Exception as callback_error:
                                # Ignore callback errors (likely Streamlit context issues)
                                pass
                    
                    # Handle blog-specific events (status, toc, section_start, section_token, image, section_complete)
                    elif message_type in ['status', 'toc', 'section_start', 'section_token', 'section_complete', 'image']:
                        if callbacks.get('on_event'):
                            try:
                                callbacks['on_event'](data)
                            except Exception as callback_error:
                                # Silently ignore callback errors
                                pass
                            
                    elif message_type == 'complete':
                        print(f"✅ [WS Manager] Complete received for {message_id}")
                        if callbacks.get('on_complete'):
                            try:
                                # For blog generation, pass the data dict
                                complete_data = data.get('data', data.get('message', ''))
                                callbacks['on_complete'](complete_data)
                            except Exception as callback_error:
                                print(f"⚠️ [WS Manager] Complete callback error: {callback_error}")
                        # Clean up callbacks after completion, but DON'T close connection
                        self.response_callbacks.pop(message_id, None)
                        print(f"✅ Message {message_id} complete, connection stays open")
                        
                    elif message_type == 'error':
                        error_msg = data.get('message', 'Unknown error')
                        print(f"❌ [WS Manager] Error received for {message_id}: {error_msg}")
                        if callbacks.get('on_error'):
                            try:
                                callbacks['on_error'](error_msg)
                            except Exception as callback_error:
                                pass
                        self.response_callbacks.pop(message_id, None)
                    
                    else:
                        # Unknown message type - try to dispatch as event
                        print(f"⚠️ [WS Manager] Unknown message type: {message_type}")
                        if callbacks.get('on_event'):
                            try:
                                callbacks['on_event'](data)
                            except Exception:
                                pass
                        
                except json.JSONDecodeError as e:
                    print(f"⚠️ [WS Manager] JSON decode error: {e}")
                    # Continue receiving other messages
                except Exception as e:
                    print(f"⚠️ [WS Manager] Message processing error: {e}")
                    import traceback
                    traceback.print_exc()
                    # Continue receiving other messages
        except websockets.exceptions.ConnectionClosed as e:
            print(f"🔌 Receive loop: Connection closed - {e}")
            self.is_running = False
        except Exception as e:
            print(f"❌ Receive loop error: {e}")
            import traceback
            traceback.print_exc()
            self.is_running = False
    
    def send_message(self, query: str, session_id: str, message_id: str, on_token=None, on_complete=None, on_error=None):
        """Queue a message to be sent via WebSocket"""
        if not self.is_running:
            print("❌ WebSocket not running, starting...")
            self.start()
            # Wait a bit for connection to establish
            import time
            time.sleep(1.5)  # Slightly longer wait for connection stability
        
        # Register callbacks for this message
        self.response_callbacks[message_id] = {
            'on_token': on_token,
            'on_complete': on_complete,
            'on_error': on_error
        }
        
        # Queue the message
        message_data = {
            'type': 'chat_message',
            'query': query,
            'session_id': session_id or '',
            'message_id': message_id
        }
        self.message_queue.put(message_data)
        print(f"📨 Queued message: {message_id} (Connection running: {self.is_running})")
    
    def stop(self):
        """Stop the WebSocket connection"""
        self.is_running = False
        
        # Close WebSocket if it exists
        if self.websocket:
            try:
                # Schedule the close operation in the event loop
                if self.loop and not self.loop.is_closed():
                    self.loop.call_soon_threadsafe(self._close_websocket)
            except Exception as e:
                print(f"⚠️ Error closing WebSocket: {e}")
        
        # Stop the event loop
        if self.loop and not self.loop.is_closed():
            try:
                self.loop.call_soon_threadsafe(self.loop.stop)
            except Exception as e:
                print(f"⚠️ Error stopping event loop: {e}")
        
        # Wait for thread to finish
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        
        print("🛑 WebSocket connection stopped")
    
    def _close_websocket(self):
        """Close the WebSocket connection"""
        if self.websocket:
            try:
                # Close the WebSocket connection
                asyncio.create_task(self.websocket.close())
            except Exception as e:
                print(f"⚠️ Error in WebSocket close: {e}")


class ChatbotAPI:
    """API client for chatbot endpoints with persistent WebSocket support"""

    def __init__(self):
        self.client = APIClient()
        self.websocket_url = get_api_endpoint('chatbot_websocket')
        self.ws_manager = None

    def ask_question(self, **kwargs) -> Optional[Dict[str, Any]]:
        return self.client.post("chat/chat/", data=kwargs)

    def init_persistent_connection(self):
        """Initialize persistent WebSocket connection"""
        # Always check if existing connection is still running
        if self.ws_manager and self.ws_manager.is_running:
            print("🔄 Reusing existing WebSocket connection")
            return self.ws_manager
        
        # Create new connection only if needed
        print("🆕 Creating new WebSocket connection")
        headers = self.client._get_auth_headers()
        self.ws_manager = PersistentWebSocketManager(self.websocket_url, headers)
        self.ws_manager.start()
        return self.ws_manager
    
    def close_persistent_connection(self):
        """Close persistent WebSocket connection"""
        if self.ws_manager:
            self.ws_manager.stop()
            self.ws_manager = None
    
    def ask_question_stream_websocket(self, query: str, session_id: str = None, on_token=None, on_complete=None, on_error=None):
        """Send a message via persistent WebSocket connection"""
        try:
            # Initialize persistent connection if needed
            manager = self.init_persistent_connection()
            
            # Generate unique message ID
            import time
            message_id = f"msg_{int(time.time() * 1000)}"
            
            # Send message via persistent connection
            manager.send_message(
                query=query,
                session_id=session_id,
                message_id=message_id,
                on_token=on_token,
                on_complete=on_complete,
                on_error=on_error
            )
        except Exception as e:
            if on_error:
                on_error(str(e))



