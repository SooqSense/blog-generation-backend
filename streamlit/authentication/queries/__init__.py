"""
SQL Queries module for authentication system
Contains all database queries organized by functionality
"""

from .user_queries import UserQueries
from .session_queries import SessionQueries

__all__ = ['UserQueries', 'SessionQueries']
