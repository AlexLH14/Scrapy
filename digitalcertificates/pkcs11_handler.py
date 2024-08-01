import crochet
import os
from scrapy.crawler import CrawlerRunner
from scrapy.utils.project import get_project_settings
from scrapy.utils.log import configure_logging
from twisted.internet import reactor
from cirbox_scraper.utils import log_trace
from app_root import ROOT_DIR

crochet.setup()


class PKCS11Handler:
    def __init__(self):
        self.spider_queue = []
        settings = get_project_settings()
        settings.set('DOWNLOAD_TIMEOUT', 180)  # Aumenta el timeout a 120 segundos
        settings.set('CLOSESPIDER_TIMEOUT', 180)  # Aumenta el timeout a 120 segundos
        settings.set('LOG_ENABLED', True)  
        settings.set('LOG_LEVEL', 'DEBUG')  
        settings.set('LOG_FILE', os.path.join(ROOT_DIR, 'static/scrapy.log'))  # Log

        configure_logging({'LOG_FILE': os.path.join(ROOT_DIR, 'static/scrapy.log')})

        self.runner = CrawlerRunner(settings)

    # Función a ejecutar cuando el spider termina sin errores
    def spider_closed(self, result, spider):
        log_trace(self, 'PKCS11Handler', f"Spider {spider.name} cerrado. Nombre de spider alternativo {spider['spider'].__name__}")
        log_trace(self, 'PKCS11Handler', f"Resultado obtenito {result}")
        print(f"El spider {spider.name} ha terminado exitosamente.")

    # Función a ejecutar cuando el spider termina con errores
    def spider_failed(self, failure, spider):
        log_trace(self, 'PKCS11Handler', f"Spider {spider.name} ha fallado. Nombre de spider alternativo {spider['spider'].__name__}")
        log_trace(self, 'PKCS11Handler', f"Error obtenito {failure}")
        print(f"El spider {spider.name} ha terminado con errores: {failure.value}")


    def run_next_spider(self):
        log_trace(self, 'PKCS11Handler', 'Inicio run_next_spider()')
        if len(self.spider_queue) > 0:
            log_trace(self, 'PKCS11Handler', 'Encotramos elementos en la cola de ejecución así que extraigo uno con pop()')
            spider_instance = self.spider_queue.pop(0)

            log_trace(self, 'PKCS11Handler', f"Realizando la llamada al spider {spider_instance['spider'].__name__} ")
            d = self.runner.crawl(spider_instance['spider'], **spider_instance)
            log_trace(self, 'PKCS11Handler', 'Ejecucion del Spider finalizado')

            # Adjuntar los callbacks al objeto Deferred
            d.addCallbacks(self.spider_closed, self.spider_failed, callbackKeywords={'spider': spider_instance}, errbackKeywords={'spider': spider_instance})
            log_trace(self, 'PKCS11Handler', 'Callbacks gestionados')
             
            log_trace(self, 'PKCS11Handler', 'Usamos reactor para lanzar el siguiente spider iterativamente')
            d.addBoth(lambda _: reactor.callLater(0, self.run_next_spider))
