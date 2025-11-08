"""
Dynamic settings loader for Django project.
Selects environment settings based on DJANGO_ENV variable.
"""
import os

DJANGO_ENV = os.getenv("env", "local").lower()

if DJANGO_ENV == "prod" or DJANGO_ENV == "production":
    from .prod import *
elif DJANGO_ENV == "local" or DJANGO_ENV == "dev" or DJANGO_ENV == "development":
    from .local import *
else:
    raise RuntimeError(f"Unknown DJANGO_ENV: {DJANGO_ENV}. Use 'local' or 'prod'.")
