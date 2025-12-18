"""
ASGI config for management_app project.

It exposes the ASGI callable as a module-level variable named ``application``.
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import re_path
from management_app.extras.consumers import StreamingWebSocketConsumer
from management_app.authentication.middleware import ClerkWebSocketAuthMiddleware

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'management_app.config.settings')

# Initialize Django ASGI application early
django_asgi_app = get_asgi_application()

# WebSocket URL patterns for centralized streaming
websocket_urlpatterns = [
    # Main streaming endpoint for all features
    re_path(r"^ws/stream/$", StreamingWebSocketConsumer.as_asgi()),
]

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": ClerkWebSocketAuthMiddleware(
        URLRouter(websocket_urlpatterns)
    ),
})


