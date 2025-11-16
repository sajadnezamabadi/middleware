#!/usr/bin/env bash
set -e

# Load .env if present
if [ -f "/app/ACL/.env" ]; then
  set -a
  . /app/ACL/.env
  set +a
fi

python manage.py migrate --noinput

exec gunicorn ACL.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 60


