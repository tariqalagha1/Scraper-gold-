#!/usr/bin/env sh
set -eu

cd /app/backend
alembic upgrade head
