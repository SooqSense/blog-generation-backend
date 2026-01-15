"""
Celery configuration for Blog Generation Backend.

This module initializes the Celery application with Django integration
and configures task discovery for modular task organization.
"""

import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'management_app.config.settings')

# Initialize Django before creating Celery app (with comprehensive safety check)
import django
from django.conf import settings
import sys

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
    if is_celery_safe_to_setup():
        if not settings.configured:
            print("Celery: Setting up Django...")
            django.setup()
        elif not hasattr(django, 'apps') or not django.apps.apps.ready:
            if not django.apps.apps.loading:  # Extra check to avoid loading conflicts
                print("Celery: Completing Django setup...")
                django.setup()
            else:
                print("Celery: Django apps loading, skipping setup")
    else:
        print("Celery: Not safe to setup Django or already configured")
except RuntimeError as e:
    # Django might already be set up in the main process
    if "populate() isn't reentrant" in str(e):
        print("Celery: Django already initialized, using existing setup")
    else:
        print(f"Celery: Runtime error during Django setup: {e}")
        raise e
except Exception as e:
    print(f"Celery: Unexpected error during Django setup: {e}")
    # Don't raise - let Celery continue with existing Django state

# Create Celery application
app = Celery('blog_generation_backend')

# Load configuration from Django settings
# Using namespace='CELERY' means all celery-related settings 
# in settings.py should have a 'CELERY_' prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Manually include modular task packages
app.conf.include = [
    'management_app.config.celery.tasks.blog_generator_tasks.blog_generation_task',
]

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
