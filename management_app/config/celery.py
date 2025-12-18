"""
Backward compatibility module for Celery configuration.

This module maintains backward compatibility by importing the Celery app
from the new modular structure.

DEPRECATED: Import from management_app.config.celery instead.
"""

from management_app.config.celery import app

__all__ = ['app']