#!/bin/bash
set -e

echo "Starting Django application..."

# Change to the correct directory
cd /app/management_app

# Collect static files (for production)
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Run migrations (one-time at startup)
echo "Running Django migrations..."
python manage.py migrate --noinput

# Create logs directory if it doesn't exist
mkdir -p /app/logs

echo "Starting supervisor..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf 