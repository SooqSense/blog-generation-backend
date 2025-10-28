import asyncio
import json
import threading
import queue
from typing import Optional, Dict, Any, List

import websockets

from .base_client import APIClient
from base.config import get_api_endpoint


class BlogAPI:
    """API client for blog generation endpoints"""

    def __init__(self):
        self.client = APIClient()
        self.websocket_url = get_api_endpoint('blog_websocket')

    def generate_blog(self, **kwargs) -> Optional[Dict[str, Any]]:
        endpoint = get_api_endpoint('blog_generation')
        return self.client.post(endpoint, data=kwargs)

    def generate_blog_stream(self, blog_data: Dict[str, Any], on_status=None, on_complete=None, on_error=None):
        """Stream blog generation via WebSocket with status updates"""
        try:
            # CRITICAL: Capture headers BEFORE thread (session state not available in threads)
            headers = self.client._get_auth_headers()
            result_queue = queue.Queue()

            def websocket_thread():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self._websocket_connect(
                        self.websocket_url, blog_data, headers, on_status, on_complete, on_error, result_queue
                    ))
                    # Signal successful completion
                    result_queue.put(('complete', None))
                except Exception as e:
                    result_queue.put(('error', str(e)))

            thread = threading.Thread(target=websocket_thread)
            thread.daemon = True
            thread.start()

            while thread.is_alive():
                try:
                    result_type, result_data = result_queue.get(timeout=0.1)
                    if result_type == 'error':
                        if on_error:
                            on_error(result_data)
                        break
                    elif result_type == 'complete':
                        # Successful completion, no error
                        break
                except queue.Empty:
                    continue

            thread.join(timeout=1)
        except Exception as e:
            if on_error:
                on_error(str(e))

    async def _websocket_connect(self, ws_url, blog_data, headers, on_status, on_complete, on_error, result_queue):
        try:
            # Check if we have authentication token
            has_auth = 'Authorization' in headers and headers['Authorization']
            print(f"🔐 Blog Stream Auth Token Present: {has_auth}")
            
            if not has_auth:
                error_msg = "Authentication token not found. Please ensure you're logged in."
                result_queue.put(('error', error_msg))
                if on_error:
                    on_error(error_msg)
                return
            
            # Format headers for WebSocket
            websocket_headers = []
            for key, value in headers.items():
                # Skip Content-Type header for WebSocket
                if key.lower() == 'content-type':
                    continue
                if value:  # Only add non-empty headers
                    header_key = key.lower() if isinstance(key, str) else key
                    websocket_headers.append((header_key, value))

            async with websockets.connect(ws_url, additional_headers=websocket_headers) as websocket:
                # Send blog generation request
                message = {
                    'type': 'blog_generation',
                    **blog_data  # Include all blog parameters
                }
                await websocket.send(json.dumps(message))

                async for message in websocket:
                    try:
                        data = json.loads(message)
                        message_type = data.get('type')

                        if message_type == 'status' and on_status:
                            on_status(data.get('stage', ''), data.get('message', ''))
                        elif message_type == 'complete':
                            if on_complete:
                                on_complete(data.get('data', {}))
                            # Exit cleanly after completion
                            break
                        elif message_type == 'error' and on_error:
                            on_error(data.get('message', 'Unknown error'))
                            break
                    except json.JSONDecodeError:
                        if on_error:
                            on_error('Invalid JSON received from server')
                        break
        except websockets.exceptions.ConnectionClosed:
            # Normal connection closure after completion - not an error
            pass
        except websockets.exceptions.WebSocketException as e:
            error_msg = str(e)
            if 'ConnectionClosed' not in error_msg:
                result_queue.put(('error', f'WebSocket error: {error_msg}'))
        except Exception as e:
            error_msg = str(e)
            if 'ConnectionClosed' not in error_msg:
                result_queue.put(('error', error_msg))

    def list_blogs(self) -> Optional[Dict[str, Any]]:
        endpoint = get_api_endpoint('blog_list')
        return self.client.get(endpoint)

    def delete_blogs(self, ids: List[int]) -> Optional[Dict[str, Any]]:
        endpoint = get_api_endpoint('blog_delete')
        if len(ids) == 1:
            return self.client.delete(endpoint, data={'blog_id': ids[0]})
        else:
            return self.client.delete(endpoint, data={'blog_ids': ids})

    def get_blog(self, blog_id: int) -> Optional[Dict[str, Any]]:
        endpoint = f"blogs/get/{blog_id}/"
        return self.client.get(endpoint)

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        return self.client.get(endpoint, params=params)


