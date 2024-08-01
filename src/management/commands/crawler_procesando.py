from django.core.management import BaseCommand

from src.apps.cron.cron_provider import CronProvider
from src.apps.cron.enumeration import CronNames


class Command(BaseCommand):
    help = "Cron que procesa los pedidos"

    def add_arguments(self, parser):
        ...

    def handle(self, *args, **options):
        from src.apps.certificate_order.certificate_provider import CertificateProvider
        from src.apps.certificate_order.models.log import Log

        try:
            # Se comprueba si se puede lanzar el cron
            is_enabled = CronProvider.is_cron_enabled(CronNames.PROCESAR_PROCESANDO.value)
            if is_enabled:
                CertificateProvider.process_procesando()
        except Exception as err:
            Log.objects.create(context='cron_crawler', response='funcion_handle_procesando', error=str(err))
