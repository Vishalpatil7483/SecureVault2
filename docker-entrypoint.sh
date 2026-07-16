#!/bin/sh
# Apply any pending database migrations, then start the production WSGI server.
set -e

echo "Applying database migrations..."
flask db upgrade

echo "Starting gunicorn on port ${PORT:-8000}..."
exec gunicorn "run:app" \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-3}" \
    --timeout 120
