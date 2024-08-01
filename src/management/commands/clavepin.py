import traceback

from django.core.management import BaseCommand
from django.core.cache import cache

from cirbox_scraper.spiders.agenciatributaria import SpiderAgenciaTributaria
from cirbox_scraper.spiders.vida_laboral import SpiderVidaLaboral

from src.apps.certificate_order.enumeration import CertificateOrderModeEnum
from src.apps.certificate_order.models.certificate_order import CertificateOrderModel
from src.apps.cron.cron_provider import CronProvider
from src.apps.cron.enumeration import CronNames
from digitalcertificates.pkcs11_handler import PKCS11Handler
from digitalcertificates.clave_pin_handler import ClavePinHandler
from src.apps.certificate_order.enumeration import CertificateOrderType
from cirbox_scraper.spiders.scrapper_pin_eval import EvalClavePin

from cirbox_scraper.utils import set_certificate_status, log_trace


pkcs11_handler = PKCS11Handler()
clave_pin_handler = ClavePinHandler()

TGSS_TYPE = "tgss"
TGSS_SEDE_TYPE = "sede"
AGENCY_TYPE = "agency"

class Command(BaseCommand):
    help = "Cron que procesa los pedidos"

    def add_arguments(self, parser):
        ...

    def handle(self, *args, **options):
        log_trace(self, 'ClavePinCommand', 'Inicio el comando')
        from scrapy.utils.project import get_project_settings
        from scrapy.crawler import CrawlerRunner
        from twisted.internet import reactor

        print('Iniciando comando ClavePin')
        try:
            log_trace(self, 'ClavePinCommand', 'Inicializando CrawlerRunner')
            runner = CrawlerRunner(get_project_settings())
            # d = runner.crawl(SpiderVidaLaboral, order=None, certificate=None, password=None, modelo=None)
            order = {
                "id": "efe0aeb5-bda8-4790-bf58-6aa903d9a97d",
                "person_national_id": "50107654S",
                "person_national_document_type": "dni",
                "status": CertificateOrderType.STATUS_APPROVED.value,
                "request_type": "{vida_laboral,renta}",
                "key_document_value": "2030-08-13",
                "person_birth_date": "1977-08-20",
                "auth_type": "clavepin",
                "return_url": ""
                #"return_url": "https://www.google.es"
                #"person_national_id": "44157543G"
            }
            print(order)
            self.order = order

            obj = {'order': order}
            obj.update({
                'spider': EvalClavePin,
                'modelo': '100'
            })
            log_trace(self, 'ClavePinCommand', f"Creando objeto para el crawler: {str(obj)}")
            clave_pin_handler.spider_queue.append(obj)
            log_trace(self, 'ClavePinCommand', "Agrego spider a la cola")
            if clave_pin_handler.spider_queue:                        
                clave_pin_handler.run_next_spider()
            
            request_type = AGENCY_TYPE

            log_trace(self, 'ClavePinCommand', "Voy a llamar a get_pin_code()")
            clave_pin_handler.get_pin_code(order, request_type)
            log_trace(self, 'ClavePinCommand', "Llamada a get_pin_code() realizada")
            cached_data = cache.get(order['id'])
            if cached_data is not None and cached_data.get('reason') is not None:
                log_trace(self, 'ClavePinCommand', f"Error detectado: {str(cached_data.get('reason'))}")

        except Exception as err:
            log_trace(self, 'ClavePinCommand', f"Error en la ejecucion: {str(err)}")
            traceback.print_exc()

        # Ejecución de Vida Laboral
        #d = runner.crawl(SpiderVidaLaboral, order=order, certificate=None, password=None, modelo=None)

        # Ejecución de Renta
        #d = runner.crawl(SpiderAgenciaTributaria, order=order, modelo='100')

        #d.addBoth(lambda _: reactor.stop())
        if not reactor.running:
            reactor.run()

        log_trace(self, 'ClavePinCommand', "Fin del comando")
        print('Fin del proceso')
