#!/bin/bash
set -e

echo "=== Starting Celery Worker Service ==="
echo "Time: $(date)"
echo "Python version: $(python3 --version)"
echo "Working directory: $(pwd)"

# Verify critical environment variables
echo ""
echo "=== Checking Environment Variables ==="
for VAR in REDIS_URL CELERY_BROKER_URL CELERY_RESULT_BACKEND OPENAI_API_KEY PINECONE_API_KEY; do
    VALUE="${!VAR}"
    if [ -z "$VALUE" ]; then
        echo "⚠️  WARNING: $VAR is NOT SET"
    else
        echo "✅ $VAR is set"
    fi
done
echo ""

# Start HTTP health check server in background
echo "Starting HTTP health check server on port 8000..."
python3 -m http.server 8000 &
HTTP_PID=$!
echo "HTTP server started with PID: $HTTP_PID"

# Give HTTP server time to start
sleep 2

# Test Redis connection
echo "Testing Redis connection..."
python3 -c "
import os
import redis
url = os.environ.get('REDIS_URL', 'not set')
print(f'REDIS_URL: {url[:50]}... (truncated)')
try:
    r = redis.from_url(url)
    print(f'Redis ping: {r.ping()}')
    print('✅ Redis connection successful!')
except Exception as e:
    print(f'❌ Redis connection failed: {e}')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ Redis connection test failed. Exiting."
    kill $HTTP_PID
    exit 1
fi

# Start Celery worker
echo "Starting Celery worker..."
echo "Celery command: celery -A management_app.config.celery worker --loglevel=info --concurrency=2 --pool=threads"

exec celery -A management_app.config.celery worker \
    --loglevel=info \
    --concurrency=2 \
    --pool=threads \
    --without-heartbeat \
    --without-gossip \
    --without-mingle
