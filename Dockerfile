FROM python:3.12.8-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=management_app.config.settings

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    netcat-traditional \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Development stage
FROM base AS development

ENV DEBUG=True

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]

# Staging stage
FROM base AS staging

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
WORKDIR /app

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && daphne management_app.config.asgi:application --port 8000 --bind 0.0.0.0"]

# Production stage
FROM base AS production

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
WORKDIR /app/

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && daphne management_app.config.asgi:application --port 8000 --bind 0.0.0.0"]
