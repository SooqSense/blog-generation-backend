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

# Additional task configuration for batch processing
# Removed custom queue routing to use default 'celery' queue for simplicity
# app.conf.update(
#     task_routes={
#         'tools.ai.schedule_linkedin_post.tasks.schedule_linkedin_post_batch_task': {'queue': 'linkedin_posts'},
#         'tools.ai.schedule_linkedin_post.tasks.schedule_linkedin_post_task': {'queue': 'linkedin_posts'},
#     },
# )

# Celery configuration
# Prioritize environment variables for Docker, fallback to .env values
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

# Override with Docker-friendly URLs if we're in Docker environment
if os.environ.get('DOCKER_ENV') == 'true':
    redis_url = 'redis://redis:6379/0'

broker_url = os.environ.get('CELERY_BROKER_URL', redis_url)
result_backend = os.environ.get('CELERY_RESULT_BACKEND', redis_url)

# Debug logging to see what URLs are being used
print(f"Celery Debug - REDIS_URL: {redis_url}")
print(f"Celery Debug - BROKER_URL: {broker_url}")
print(f"Celery Debug - RESULT_BACKEND: {result_backend}")

app.conf.update(
    broker_url=broker_url,
    result_backend=result_backend,
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