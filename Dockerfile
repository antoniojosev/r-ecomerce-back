FROM python:3.12-slim

# Settings are selected by backend/settings/__init__.py from the `env`
# variable (same mechanism the Render deploy used) — NOT by
# DJANGO_SETTINGS_MODULE, whose package __init__ would still run the
# loader and pull local settings in.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    env=prod

WORKDIR /app

COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/prod.txt

COPY . .

RUN adduser --disabled-password --uid 1000 django \
    && mkdir -p staticfiles && chown -R django:django /app
USER django

EXPOSE 8000
ENTRYPOINT ["./docker-entrypoint.sh"]
