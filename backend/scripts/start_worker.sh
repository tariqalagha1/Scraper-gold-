#!/usr/bin/env sh
set -eu

cd /app/backend
exec celery -A app.queue.celery_app worker --loglevel=info --concurrency="${CELERY_CONCURRENCY:-4}"
