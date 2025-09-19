FROM python:3.12.8-slim AS base

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
CMD ["sh", "-c", "python management_app/manage.py migrate && python management_app/manage.py runserver 0.0.0.0:8000"]

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
WORKDIR /app/management_app

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 1 --threads 2 --timeout 300"]

# Streamlit stage for Cloud Run deployment
FROM base AS streamlit
ENV DEBUG=False
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV STREAMLIT_SERVER_ENABLE_CORS=false
ENV STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false

COPY . .

# Create non-root user with home directory
RUN groupadd -r streamlit && useradd -r -g streamlit -m -d /home/streamlit streamlit

# Create necessary directories
RUN mkdir -p /app/logs /app/.streamlit

# Create minimal Streamlit config (port will be set via command line)
RUN echo '[server]\naddress = "0.0.0.0"\nheadless = true\n[browser]\ngatherUsageStats = false\n[client]\ntoolbarMode = "minimal"\n' > /app/.streamlit/config.toml

# Create a startup script to debug and handle PORT properly
RUN echo '#!/bin/bash\n\
echo "=== Container Startup Debug ==="\n\
echo "PORT environment variable: ${PORT}"\n\
echo "All environment variables:"\n\
env | grep -E "(PORT|STREAMLIT)" || true\n\
echo "=============================="\n\
\n\
# Use PORT from environment, fallback to 8080 (Cloud Run default)\n\
ACTUAL_PORT=${PORT:-8080}\n\
echo "Starting Streamlit on port: $ACTUAL_PORT"\n\
\n\
exec streamlit run app.py \\\n\
    --server.port=$ACTUAL_PORT \\\n\
    --server.address=0.0.0.0 \\\n\
    --server.headless=true \\\n\
    --browser.gatherUsageStats=false\n' > /app/start-streamlit.sh

# Make script executable and set permissions
RUN chmod +x /app/start-streamlit.sh && chown streamlit:streamlit /app/start-streamlit.sh

# Set up directory permissions
RUN chown -R streamlit:streamlit /app /home/streamlit

# Switch to non-root user
USER streamlit

# Set working directory for Streamlit app
WORKDIR /app/frontend

# Health check for Streamlit (use PORT env var with Cloud Run default fallback)
HEALTHCHECK --interval=30s --timeout=30s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/_stcore/health || exit 1

# Use the startup script
CMD ["/app/start-streamlit.sh"]

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
WORKDIR /app/management_app

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 1 --threads 2 --timeout 300"] 