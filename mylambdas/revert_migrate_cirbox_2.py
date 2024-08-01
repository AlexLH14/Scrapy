import os
import sys

def handler(event, context):
    """
    Este lambda ejecuta las migraciones en la DB, actualizando su estado.
    """
    BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if os.path.exists(os.path.join(BASE_PATH, '.envdev')):
        # reading .env file
        # Get enviroment variables and permit their access
        MY_SCOPE = os.environ.get('MY_ENV_SCOPE', default='cirbox.settings.development')
    else:
        # No puede haber un archivo .envdev en producción.
        MY_SCOPE = os.environ.get('MY_ENV_SCOPE', default='')

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", MY_SCOPE)
    try:
        from django.core.management import execute_from_command_line
    except ImportError:
        # The above import may fail for some other reason. Ensure that the
        # issue is really that Django is missing to avoid masking other
        # exceptions on Python 2.
        try:
            import django
        except ImportError:
            raise ImportError(
                "Couldn't import Django. Are you sure it's installed and "
                "available on your PYTHONPATH environment variable? Did you "
                "forget to activate a virtual environment?"
            )
        raise
    execute_from_command_line(['manage.py', 'migrate', 'digitalcertificates', 'zero'])
