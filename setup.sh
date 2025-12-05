#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f ".env" ]; then
  cp .env.example .env
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput

if [[ -n "${DJANGO_SUPERUSER_EMAIL:-}" && -n "${DJANGO_SUPERUSER_PASSWORD:-}" && -n "${DJANGO_SUPERUSER_FIRST_NAME:-}" && -n "${DJANGO_SUPERUSER_LAST_NAME:-}" && -n "${DJANGO_SUPERUSER_MOBILE:-}" ]]; then
  python manage.py createsuperuser \
    --email "$DJANGO_SUPERUSER_EMAIL" \
    --first_name "$DJANGO_SUPERUSER_FIRST_NAME" \
    --last_name "$DJANGO_SUPERUSER_LAST_NAME" \
    --mobile "$DJANGO_SUPERUSER_MOBILE" \
    --noinput || true
fi

echo "Setup complete. Activate the virtualenv with: source .venv/bin/activate"

