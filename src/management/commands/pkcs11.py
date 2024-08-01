from django.core.management import BaseCommand

from cirbox_scraper.spiders.agenciatributaria import SpiderAgenciaTributaria
from cirbox_scraper.spiders.cirbe import SpiderCirbe
from cirbox_scraper.spiders.base_cotizacion_p11 import SpiderBaseCotizacionP11
from src.apps.certificate_order.enumeration import CertificateOrderModeEnum
from src.apps.cron.cron_provider import CronProvider
from src.apps.cron.enumeration import CronNames
from scrapy.utils.project import get_project_settings
from scrapy.crawler import CrawlerRunner
from twisted.internet import reactor
import time


class Command(BaseCommand):
    help = "Cron que procesa manualmente solicitudes para testear"

    def add_arguments(self, parser):
        ...

    def handle(self, *args, **options):
        print('Empezando comando')
        # '50107654S'
        runner = CrawlerRunner(get_project_settings())
        d = runner.crawl(SpiderCirbe,
                         order={
                             'person_national_id': '50107654S',
                             'company_cif': 'B72639453',
                             'person_birth_date': '1977-08-20',
                             'person_email': 'juanjo.nieto@gmail.com',
                             'id': '333'
                        }, #  I20240419002467
                         certificate=None,
                         password=None,
                         reference_number='d',
                         modelo='347')
        d.addBoth(lambda _: reactor.stop())
        if not reactor.running:
            reactor.run()
        time.sleep(160)
        print('Flujo terminado')

