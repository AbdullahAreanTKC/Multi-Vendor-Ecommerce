#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

python manage.py migrate --noinput
python manage.py collectstatic --noinput

export PORT="${PORT:-8001}"
export WEB_CONCURRENCY="${WEB_CONCURRENCY:-4}"
export GUNICORN_THREADS="${GUNICORN_THREADS:-2}"

exec gunicorn ecommerce.wsgi:application \
  --bind "0.0.0.0:${PORT}" \
  --workers "${WEB_CONCURRENCY}" \
  --threads "${GUNICORN_THREADS}" \
  --timeout 120

