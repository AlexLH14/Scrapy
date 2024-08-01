"""
ASGI config for cirbox project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

MY_SCOPE = os.environ.get('MY_ENV_SCOPE', default=None)
if not MY_SCOPE:
    raise Exception('No se ha especificado un entorno')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', MY_SCOPE)

application = get_asgi_application()
