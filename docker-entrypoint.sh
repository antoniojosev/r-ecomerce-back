#!/usr/bin/env bash
# Release tasks + server, in one place. collectstatic and migrate run at
# container start (not image build) because both need the real production
# environment — the manifest static storage wants SECRET_KEY and migrate
# needs the database. Migrations are idempotent: on an already-migrated
# database this is a no-op.
set -o errexit

python manage.py collectstatic --no-input
python manage.py migrate --no-input

exec gunicorn backend.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-2}" \
    --timeout "${GUNICORN_TIMEOUT:-60}" \
    --access-logfile - \
    --error-logfile -
