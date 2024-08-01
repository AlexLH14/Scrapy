from django.core.management import BaseCommand
from scrapy.crawler import CrawlerProcess, CrawlerRunner
from scrapy.utils.project import get_project_settings

from cirbox_scraper.spiders.sandbox import SpiderSandbox
from cirbox_scraper.spiders.scrapper_pin_eval import EvalClavePin


class Command(BaseCommand):
    help = "Cron que procesa los pedidos"

    def add_arguments(self, parser):
        ...

    def handle(self, *args, **options):
        try:
            nif_data = {
                "nif": '22222222J',
                "fecha_expedicion": '',
                "fecha_vencimiento": '28/05/2028',
                "fecha_nacimiento": '',
                "tipo_nif": "nie",
                "nro_soporte": ''
            }

            # if nif_data['tipo_nif'] == 'nie':
            #     nif_data['nro_soporte'] = request.data.get('extra', None)
            # elif nif_data['tipo_nif'] == 'dni_permanente':
            #     nif_data['fecha_expedicion'] = request.data.get('fecha_expedicion', None)
            # else:
            #     nif_data['fecha_vencimiento'] = request.data.get('fecha_vencimiento', None)
            import crochet
            crochet.setup()
            runner = CrawlerRunner(get_project_settings())
            d = runner.crawl(EvalClavePin, **nif_data)

            a = 3
        except Exception as err:
            a = 3
