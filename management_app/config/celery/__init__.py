"""
Celery package initialization.

Exposes the Celery app instance for use throughout the application.
"""

from .celery_config import app

__all__ = ['app']
