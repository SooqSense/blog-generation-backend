"""
Simple Authentication module for AI Blog Generator
Handles Clerk authentication using redirect-based flow
"""

from .auth import (
    SimpleClerkAuth,
    get_auth,
    is_authenticated,
    require_auth,
    get_user,
    logout
)

__all__ = [
    'SimpleClerkAuth',
    'get_auth',
    'is_authenticated',
    'require_auth',
    'get_user',
    'logout'
]
