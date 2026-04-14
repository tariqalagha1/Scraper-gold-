#!/usr/bin/env bash
set -euo pipefail

echo "=== Smart Scraper Quality Check ==="

# Backend quality checks
echo "\n--- Backend quality check ---"
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
python - <<'PY'
import pathlib
import py_compile
import sys

roots = [pathlib.Path('backend/app'), pathlib.Path('backend/tests')]
errors = []

for root in roots:
    if not root.exists():
        continue
    for path in root.rglob('*.py'):
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            errors.append(f"{path}: {exc.msg}")

if errors:
    print('Backend lint failed')
    for err in errors:
        print(err)
    sys.exit(1)
PY
mkdir -p backend/pytest-tmp backend/pytest-cache || true
(cd backend && pytest tests -q --basetemp ../pytest-tmp -o cache_dir=../pytest-cache)

# Frontend quality checks
echo "\n--- Frontend quality check ---"
(cd frontend && npm ci)
(cd frontend && npm run test:ci)
(cd frontend && npm run build:ci)

echo "\n=== Quality check completed successfully ==="
