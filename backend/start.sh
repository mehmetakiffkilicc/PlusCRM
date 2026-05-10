#!/bin/bash
set -e

# Port configuration
export PORT=${PORT:-8000}

echo "=== MarketFlow Backend Startup Script ==="
echo "=== Environment: ${ENVIRONMENT:-production} ==="
echo "=== Port: $PORT ==="
echo "=== Python: $(python --version) ==="

# Pre-flight: Django import kontrolü (import hataları net görülsün)
echo "Pre-flight: Django import kontrolü..."
python -c "
import django, sys, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
print('Django import: OK')
" 2>&1 || {
    echo "HATA: Django import başarısız! Detaylar yukarıda."
    exit 1
}

# Memory management for fragmentation
export MALLOC_MMAP_THRESHOLD_=131072
export MALLOC_ARENA_MAX=2

# Workers configuration
export WEB_CONCURRENCY=${WEB_CONCURRENCY:-2}

echo "Starting Gunicorn with $WEB_CONCURRENCY workers..."

# Run migrations in background — don't block gunicorn startup
# Railway healthcheck will pass once gunicorn is listening, regardless of migration status
(
    echo "Background: Running migrations..."
    python manage.py migrate --noinput 2>&1 && echo "Background: Migrations OK" || echo "Background: Migration failed (non-critical)"
    
    echo "Background: Creating cache table (if needed)..."
    python manage.py createcachetable 2>&1 || true
) &

# Start gunicorn immediately — healthcheck will pass once port is bound
exec gunicorn core.wsgi:application \
  --bind 0.0.0.0:$PORT \
  --workers $WEB_CONCURRENCY \
  --worker-class gthread \
  --threads 2 \
  --timeout 300 \
  --keep-alive 5 \
  --max-requests 1000 \
  --max-requests-jitter 50 \
  --access-logfile - \
  --error-logfile - \
  --capture-output \
  --log-level info

