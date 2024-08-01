from django.core.management import BaseCommand
import crochet
from scrapy.crawler import CrawlerRunner
from scrapy.utils.project import get_project_settings
from cirbox_scraper.utils import log_and_save_response, set_certificate_status, log_trace, log_html

from cirbox_scraper.spiders.cirbe import SpiderCirbe
from app_root import ROOT_DIR

crochet.setup()
runner = CrawlerRunner(get_project_settings())


class Command(BaseCommand):
    help = "Cron que comprueba si hay respuesta de CIRBE a procesar"

    def add_arguments(self, parser):
        ...

    def handle(self, *args, **options):
        from twisted.internet import reactor
        log_trace(self, 'CommandCirbeCheck', 'Inicio solicitud')

        spider_queue = []

        log_trace(self, 'CommandCirbeCheck', 'Crear función run_next_spider')
        def run_next_spider():
            log_trace(self, 'CommandCirbeCheck', 'Lanzo run_next_spider()')
            try:
                if len(spider_queue) > 0:
                    log_trace(self, 'CommandCirbeCheck', 'Identifico spider en la cola')
                    spider_instance = spider_queue.pop(0)
                    log_trace(self, 'CommandCirbeCheck', f"Recupero spider a ejecutar {spider_instance}")
                    log_trace(self, 'CommandCirbeCheck', 'Lanzo ejecucion')
                    d = runner.crawl(spider_instance[0], **spider_instance[1])
                    log_trace(self, 'CommandCirbeCheck', 'Spider ejecutado')
                    d.addBoth(lambda _: reactor.callLater(0, run_next_spider))
            except Exception as err:
                log_trace(self, 'SpiderCirbe', f"Error recogido: {str(err)}")
                print(str(err))


        import os
        directory = os.path.join(ROOT_DIR, 'static/flags/cirbe')
        log_trace(self, 'SpiderCirbe', f"Vamos a buscar flags en : {directory}")
        for filename in os.listdir(directory):
            if filename.endswith(".txt"):
                log_trace(self, 'SpiderCirbe', f"Ficheo encontrado : {filename}")
                filepath = os.path.join(directory, filename)
                with open(filepath, 'r') as file:
                    log_trace(self, 'SpiderCirbe', f"Fichero abierto")
                    content = file.readline().strip().split(',')
                    if len(content) == 5:
                        log_trace(self, 'SpiderCirbe', f"Identificamos que tiene dos elementos el fichero")
                        filename_with_extension = os.path.basename(filepath)
                        creation_date = content[0]
                        order_id = content[1]
                        person_national_id = content[2]
                        log_trace(self, 'SpiderCirbe', f"Vamos a buscar con order_id : {order_id} del DNI: {person_national_id} con el numero de referencia {filename_with_extension.split('.')[0]}")
                        spider_queue.append([SpiderCirbe, {
                            'order': {
                                'person_national_id': person_national_id,
                                'id': order_id,
                                'person_email': content[3],
                                'person_birth_date': content[4],
                            },
                            'reference_number': filename_with_extension.split('.')[0],
                            'cirbe_txt_file': filename_with_extension
                        }])

        if spider_queue:
            log_trace(self, 'SpiderCirbe', f"Hay más elementos en cola así que llamo al spider nuevamente")
            log_trace(self, 'SpiderCirbe', f"Cola: {spider_queue}")
            run_next_spider()
