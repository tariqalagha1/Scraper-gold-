#!/usr/bin/env bash
set -euo pipefail

PORTS=(43101 43102 45432 46379 3000 3001 8000 8001 5432 6379)

echo "Checking common local ports..."
echo

for port in "${PORTS[@]}"; do
  if lsof -nP -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "PORT ${port}: IN USE"
    lsof -nP -iTCP:"${port}" -sTCP:LISTEN | tail -n +2
  else
    echo "PORT ${port}: free"
  fi
  echo
done
