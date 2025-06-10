import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Initialize Django before creating Celery app
import django
django.setup()

app = Celery('blog_generation_backend')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Manually include tasks from tools directory
app.conf.include = [
    'tools.ai.schedule_linkedin_post.tasks',
]

# Celery configuration
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
app.conf.update(
    broker_url=os.environ.get('CELERY_BROKER_URL'),
    result_backend=os.environ.get('CELERY_RESULT_BACKEND'),
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}') 