"""
Celery configuration for Blog Generation Backend.

This module initializes the Celery application with Django integration
and configures task discovery for modular task organization.
"""

import os
import time
import sys
from celery import Celery

def log_with_timestamp(message):
    """Log with timestamp for debugging startup timing."""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}", flush=True)
    sys.stdout.flush()

log_with_timestamp("Celery config: Starting import...")

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'management_app.config.settings')

log_with_timestamp("Celery config: Importing Django...")

# Initialize Django before creating Celery app (with comprehensive safety check)
import django
from django.conf import settings

log_with_timestamp("Celery config: Django imported successfully")

def is_celery_safe_to_setup():
    """Check if it's safe to setup Django in Celery context"""
    
    # If Django apps are already loading or ready, skip
    if hasattr(django, 'apps') and django.apps:
        if django.apps.apps.loading or django.apps.apps.ready:
            return False
    
    # If we're in a Django management command context, skip
    if 'django.core.management' in sys.modules:
        return False
    
    # If settings are configured and apps exist, be cautious
    if settings.configured:
        try:
            if hasattr(django, 'apps') and django.apps.apps.ready:
                return False
        except:
            pass
    
    return True

# Only setup Django if safe and necessary
try:
    log_with_timestamp("Celery config: Checking if safe to setup Django...")
    if is_celery_safe_to_setup():
        if not settings.configured:
            log_with_timestamp("Celery: Setting up Django...")
            django.setup()
            log_with_timestamp("Celery: Django setup complete!")
        elif not hasattr(django, 'apps') or not django.apps.apps.ready:
            if not django.apps.apps.loading:  # Extra check to avoid loading conflicts
                log_with_timestamp("Celery: Completing Django setup...")
                django.setup()
                log_with_timestamp("Celery: Django setup complete!")
            else:
                log_with_timestamp("Celery: Django apps loading, skipping setup")
    else:
        log_with_timestamp("Celery: Not safe to setup Django or already configured")
except RuntimeError as e:
    # Django might already be set up in the main process
    if "populate() isn't reentrant" in str(e):
        log_with_timestamp("Celery: Django already initialized, using existing setup")
    else:
        log_with_timestamp(f"Celery: Runtime error during Django setup: {e}")
        raise e
except Exception as e:
    log_with_timestamp(f"Celery: Unexpected error during Django setup: {e}")
    # Don't raise - let Celery continue with existing Django state

log_with_timestamp("Celery config: Creating Celery app...")

# Create Celery application
app = Celery('blog_generation_backend')

log_with_timestamp("Celery config: Loading config from Django settings...")

# Load configuration from Django settings
# Using namespace='CELERY' means all celery-related settings 
# in settings.py should have a 'CELERY_' prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

log_with_timestamp("Celery config: Auto-discovering tasks...")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

log_with_timestamp("Celery config: Manually including task packages...")

# Manually include modular task packages
app.conf.include = [
    'management_app.config.celery.tasks.blog_generator_tasks.blog_generation_task',
]

log_with_timestamp("Celery config: Initialization complete! Worker should start now.")

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

