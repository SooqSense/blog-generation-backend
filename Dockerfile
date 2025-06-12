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
    supervisor \
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
RUN mkdir -p /app/logs /var/log/supervisor /var/run/supervisor

# Copy supervisor configuration and entrypoint script
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY entrypoint.sh /app/entrypoint.sh

# Make entrypoint script executable
RUN chmod +x /app/entrypoint.sh

# Set up directory permissions
RUN chown -R django:django /app /var/log/supervisor /var/run/supervisor /home/django

# Switch to non-root user
USER django

EXPOSE 8000
EXPOSE ${PORT}
CMD ["/app/entrypoint.sh"]

# Production stage
FROM base as production
ENV DEBUG=False
ENV PORT=8000

COPY . .

# Create non-root user with home directory
RUN groupadd -r django && useradd -r -g django -m -d /home/django django

# Create necessary directories
RUN mkdir -p /app/logs /var/log/supervisor /var/run/supervisor

# Copy supervisor configuration and entrypoint script
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY entrypoint.sh /app/entrypoint.sh

# Make entrypoint script executable
RUN chmod +x /app/entrypoint.sh

# Set up directory permissions
RUN chown -R django:django /app /var/log/supervisor /var/run/supervisor /home/django

# Switch to non-root user
USER django

EXPOSE 8000
CMD ["/app/entrypoint.sh"] 