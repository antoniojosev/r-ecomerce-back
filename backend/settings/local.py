"""
Local development settings.
"""
from .base import *

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Local database (sqlite3)
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }
DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.postgresql'),
        'NAME': os.getenv('DB_NAME', ''),
        'USER': os.getenv('DB_USER', ''),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', ''),
        'PORT': os.getenv('DB_PORT', ''),
    }
}


# Add development-only apps
INSTALLED_APPS += [
    "django_extensions",
]

# Local media storage (default FileSystemStorage)
# STORAGES = {
#     "default": {
#         "BACKEND": "django.core.files.storage.FileSystemStorage",
#     },
#     "staticfiles": {
#         "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
#     },
# }
# --- Cloudflare R2 Storage Integration ---
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
AWS_S3_ENDPOINT_URL = os.getenv('AWS_S3_ENDPOINT_URL')
AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', '')
AWS_S3_ADDRESSING_STYLE = os.getenv('AWS_S3_ADDRESSING_STYLE', 'virtual')
AWS_S3_SIGNATURE_VERSION = os.getenv('AWS_S3_SIGNATURE_VERSION', 's3v4')
AWS_QUERYSTRING_AUTH = os.getenv('AWS_QUERYSTRING_AUTH', 'False') == 'True'
AWS_DEFAULT_ACL = None
AWS_S3_FILE_OVERWRITE = False
R2_PUBLIC_DOMAIN = os.getenv("R2_PUBLIC_DOMAIN")

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {
            "location": "media",
            **({"custom_domain": R2_PUBLIC_DOMAIN} if R2_PUBLIC_DOMAIN else {}),
        },
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
# Local email backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
