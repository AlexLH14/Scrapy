import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

from .base import *

DATABASE_NAME = env('DATABASE_NAME', default='')
DATABASE_USER = env('DATABASE_USER', default='')
DATABASE_PASSWORD = env('DATABASE_PASSWORD', default='')
DATABASE_HOST = env('DATABASE_HOST', default='')
DATABASE_PORT = env('DATABASE_PORT', default='')
DATABASE_OPTIONS = env('DATABASE_OPTIONS', default='')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.getenv('DATABASE_NAME'),
        'USER': os.getenv('DATABASE_USER'),
        'PASSWORD': os.getenv('DATABASE_PASSWORD'),
        'HOST': os.getenv('DATABASE_HOST'),
        'PORT': os.getenv('DATABASE_PORT'),
        'OPTIONS': environ.Env.parse_value(os.getenv('DATABASE_OPTIONS'), dict),
    }
}

SENTRY_URL = env('SENTRY_URL', default='')
BACK_DNS = "https://api.pinpass.es"
PHP_SCRAPPER = "http://172.30.0.99/"   # Mismo que para PROD
CRAWLER_PHP_IP = '18.200.229.88'

SECRET_KEY = env('SECRET_KEY', default='')

sentry_sdk.init(
    dsn=SENTRY_URL,
    integrations=[DjangoIntegration()],
    # If you wish to associate users to errors (assuming you are using
    # django.contrib.auth) you may enable sending PII data.
    send_default_pii=True
)
