from django.core.management import BaseCommand

from cirbox_scraper.spiders.agenciatributaria import SpiderAgenciaTributaria
from src.apps.certificate_order.enumeration import CertificateOrderModeEnum
from src.apps.cron.cron_provider import CronProvider
from src.apps.cron.enumeration import CronNames
from cirbox_scraper.utils import log_trace, log_html


class Command(BaseCommand):
    help = "Comando que procesa peticiones Cirbe con PKCS11"

    def add_arguments(self, parser):
        # Define los argumentos que deseas recibir desde la línea de comandos
        parser.add_argument('request', nargs='?', type=str, help='ID de la solicitud a probar')

    def handle(self, *args, **options):
        print('Empezando comando')
        log_trace(self, 'CommandCirbe', 'Iniciando comando')

        # Accede al valor del parámetro pasado desde la línea de comandos
        request_id = options['request']

        # '50107654S'
        from scrapy.utils.project import get_project_settings
        from cirbox_scraper.spiders.cirbe import SpiderCirbe
        from scrapy.crawler import CrawlerRunner
        from twisted.internet import reactor
        import time

        log_trace(self, 'CommandCirbe', 'Iniciando runner')
        runner = CrawlerRunner(get_project_settings())
        log_trace(self, 'CommandCirbe', 'Iniciando crawler SpiderCirbe')
        d = runner.crawl(SpiderCirbe,
                         order={'person_national_id': '50107654S',
                                'person_birth_date': '1977-08-20',
                                'person_email': 'jlbeltran@focusoft.es'},
                         certificate=None,
                         password=None,
                         modelo='100')
        
        log_trace(self, 'CommandCirbe', 'Finalizando crawler')
        d.addBoth(lambda _: reactor.stop())
        if not reactor.running:
            reactor.run()
        time.sleep(160)
        log_trace(self, 'CommandCirbe', 'Comando finalizado')
        print('Flujo terminado')
