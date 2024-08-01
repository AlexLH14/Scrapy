import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def handler(event, context):

    MY_SCOPE = os.environ.get('MY_ENV_SCOPE', default=None)
    if not MY_SCOPE:
        raise Exception('No se ha especificado un entorno')
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", MY_SCOPE)

    try:
        import django
        django.setup()

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

    user = 'ec0311beca9d89'
    password = '2266d4798c54c9'
    smtp = 'smtp.mailtrap.io'
    email = MIMEMultipart()
    email['From'] = f"development <jlbeltran@focusoft.es>"
    email['To'] = ','.join(['proyectos@focusoft.es'])
    email['Cc'] = ','.join([])
    email['Cco'] = ','.join([])
    email['Subject'] = 'asunto del correo'
    email.attach(MIMEText('cuerpo del correo', 'html'))
    email = email.as_string()
    server = smtplib.SMTP(smtp, 587)
    server.starttls()
    server.login(user, password)
    server.sendmail('jlbeltran@focusoft.es', 'proyectos@focusoft.es', email)
