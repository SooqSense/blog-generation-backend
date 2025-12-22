"""
Celery package initialization.

Exposes the Celery app instance for use throughout the application.
"""

from .celery_config import app

# Don't import tasks here - they will be auto-discovered by Celery
# Importing them causes Django AppRegistryNotReady errors because
# tasks import models before Django apps are fully loaded

__all__ = ['app']
