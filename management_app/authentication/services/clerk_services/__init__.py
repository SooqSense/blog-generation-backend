"""
Clerk Services Module

This module provides a modular approach to Clerk authentication services,
organized into separate concerns for better maintainability and testing.

Available Services:
- ClerkJWTAuthService: JWT token verification and validation (use ClerkUserService for authentication)
- ClerkAPIService: Direct API interactions with Clerk
- ClerkUserService: User management, synchronization, and authentication
- BaseClerkService: Base class with common functionality
"""

from .jwt_service import ClerkJWTAuthService
from .api_service import ClerkAPIService
from .user_service import ClerkUserService
from .base_service import BaseClerkService

__all__ = [
    'ClerkJWTAuthService',  # For JWT operations only
    'ClerkAPIService',      # For Clerk API interactions
    'ClerkUserService',     # For user authentication and management
    'BaseClerkService',     # Base class for extending services
]

# Version information
__version__ = '1.0.0'
__author__ = 'AI Blog Generator Team'
