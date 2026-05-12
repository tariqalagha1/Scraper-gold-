#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"

RUN_BACKEND=1
RUN_FRONTEND=1
INSTALL_DEPS=1

usage() {
    cat <<'EOF'
Usage: ./quality_check.sh [options]

Options:
    --backend-only   Run only backend checks
    --frontend-only  Run only frontend checks
    --no-install     Skip dependency installation (pip install/npm ci)
    -h, --help       Show this help message
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --backend-only)
            RUN_BACKEND=1
            RUN_FRONTEND=0
            ;;
        --frontend-only)
            RUN_BACKEND=0
            RUN_FRONTEND=1
            ;;
        --no-install)
            INSTALL_DEPS=0
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
    shift
done

need_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Missing required command: $1"
        exit 1
    fi
}

echo "=== Smart Scraper Quality Check ==="
echo "Project root: $ROOT_DIR"

if [[ "$RUN_BACKEND" -eq 1 ]]; then
    echo
    echo "--- Backend quality check ---"
    need_cmd python
    need_cmd pip

    if [[ "$INSTALL_DEPS" -eq 1 ]]; then
        python -m pip install --upgrade pip
        pip install -r "$ROOT_DIR/backend/requirements.txt"
    fi

    (
        cd "$ROOT_DIR"
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
        print('Python syntax check failed')
        for err in errors:
                print(err)
        sys.exit(1)

print('Python syntax check passed')
PY
    )

    mkdir -p "$ROOT_DIR/backend/pytest-tmp" "$ROOT_DIR/backend/pytest-cache"
    (
        cd "$ROOT_DIR/backend"
        pytest tests -q --basetemp ../backend/pytest-tmp -o cache_dir=../backend/pytest-cache
    )
fi

if [[ "$RUN_FRONTEND" -eq 1 ]]; then
    echo
    echo "--- Frontend quality check ---"
    need_cmd npm

    if [[ "$INSTALL_DEPS" -eq 1 ]]; then
        (cd "$ROOT_DIR/frontend" && npm ci)
    fi

    (cd "$ROOT_DIR/frontend" && npm run test:ci)
    (cd "$ROOT_DIR/frontend" && npm run build:ci)
fi

echo
echo "=== Quality check completed successfully ==="
