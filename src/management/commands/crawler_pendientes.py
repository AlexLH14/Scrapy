from django.core.management import BaseCommand

from src.apps.certificate_order.enumeration import CertificateOrderModeEnum
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
            return  # Este cron ya está deprecated al no tener bbdd propia
            # TODO Quitar tras la demo
            CertificateProvider.process_orders(order_status=CronNames.PROCESAR_PENDIENTES.value,
                                               mode=CertificateOrderModeEnum.CLAVEPIN.value)

            # # Se comprueba si se puede lanzar el cron
            # is_enabled = CronProvider.is_cron_enabled(CronNames.PROCESAR_PENDIENTES.value)
            # if is_enabled:
            #     CertificateProvider.process_orders(order_status=CronNames.PROCESAR_PENDIENTES.value,
            #                                        mode=CertificateOrderModeEnum.CLAVEPIN.value)
            #     CertificateProvider.process_orders(order_status=CronNames.PROCESAR_PENDIENTES.value,
            #                                        mode=CertificateOrderModeEnum.P12.value)
            #     CertificateProvider.process_orders(order_status=CronNames.PROCESAR_PENDIENTES.value,
            #                                        mode=CertificateOrderModeEnum.PKCS11.value)
        except Exception as err:
            Log.objects.create(context='cron_crawler', response='funcion_handle_pendientes', error=str(err))
