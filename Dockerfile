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
EXPOSE 8000
RUN pip install gunicorn
CMD ["sh", "-c", "python management_app/manage.py migrate && gunicorn --bind 0.0.0.0:${PORT} --workers 2 --timeout 300 --threads 1 config.wsgi:application --chdir management_app"]

# Production stage
FROM base as production
ENV DEBUG=False
COPY . .
EXPOSE 8000
RUN pip install gunicorn
CMD ["sh", "-c", "python management_app/manage.py migrate && gunicorn --bind 0.0.0.0:8000 --workers 4 --threads 2 --timeout 300 config.wsgi:application --chdir management_app"] 