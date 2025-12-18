"""
Celery tasks package.

Contains modular task definitions organized by feature/domain.
"""

# Import all task modules here for easy discovery
from .blog_generator_tasks import *

__all__ = []
