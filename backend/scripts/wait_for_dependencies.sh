#!/usr/bin/env sh
set -eu

echo "[backend] [INFO] waiting for postgres:5432"
until nc -z postgres 5432; do
  sleep 1
done

echo "[backend] [INFO] waiting for redis:6379"
until nc -z redis 6379; do
  sleep 1
done

echo "[backend] [INFO] dependencies ready"
exec "$@"
