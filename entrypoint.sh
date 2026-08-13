#!/bin/bash
set -e

# Fix permissions on named volumes (bind mounts may fail — that's ok)
chown -R app:app /app/data 2>/dev/null || true
chown app:app /app/staticfiles 2>/dev/null || true
chown app:app /app/media 2>/dev/null || true

gosu app python manage.py makemigrations --noinput
gosu app python manage.py migrate --noinput
gosu app python manage.py collectstatic --noinput --clear

exec gosu app gunicorn project.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 1 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
