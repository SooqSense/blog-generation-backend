FROM python:3.12.8-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=config.settings

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    netcat-traditional \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Development stage
FROM base as development
ENV DEBUG=True
EXPOSE 8000
CMD ["sh", "-c", "python management_app/manage.py migrate && python management_app/manage.py runserver 0.0.0.0:8000"]

# Staging stage
FROM base as staging
ENV DEBUG=False
ENV PORT=8000

COPY . .

# Create non-root user with home directory
RUN groupadd -r django && useradd -r -g django -m -d /home/django django

# Create necessary directories
RUN mkdir -p /app/logs

# Set up directory permissions
RUN chown -R django:django /app /home/django

# Switch to non-root user
USER django

# Set working directory for Django app
WORKDIR /app/management_app

EXPOSE 8000
CMD sh -c "python manage.py migrate --noinput && celery -A config worker --loglevel=info --concurrency=1 & celery -A config beat --loglevel=info --scheduler=django_celery_beat.schedulers:DatabaseScheduler & gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 1 --threads 2 --timeout 300"

# Production stage
FROM base as production
ENV DEBUG=False
ENV PORT=8000

COPY . .

# Create non-root user with home directory
RUN groupadd -r django && useradd -r -g django -m -d /home/django django

# Create necessary directories
RUN mkdir -p /app/logs

# Set up directory permissions
RUN chown -R django:django /app /home/django

# Switch to non-root user
USER django

# Set working directory for Django app
WORKDIR /app/management_app

EXPOSE 8000
CMD sh -c "python manage.py migrate --noinput && celery -A config worker --loglevel=info --concurrency=1 & celery -A config beat --loglevel=info --scheduler=django_celery_beat.schedulers:DatabaseScheduler & gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 1 --threads 2 --timeout 300" 