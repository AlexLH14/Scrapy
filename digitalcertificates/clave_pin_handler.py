from datetime import datetime

import crochet
from django.core.cache import cache
from scrapy.crawler import CrawlerRunner
from scrapy.utils.project import get_project_settings
from twisted.internet import reactor

from cirbox_scraper.spiders.agenciatributaria_pin import SpiderAgenciaTributariaPin
from cirbox_scraper.spiders.get_clave_pin import GetClavePin
from cirbox_scraper.spiders.get_clave_pin_agenci import GetClavePinAgenci
from cirbox_scraper.spiders.get_clave_pin_sede import GetClavePinSede
from cirbox_scraper.spiders.pensiones_pin import SpiderPensionesPin
from cirbox_scraper.spiders.tgss_pin import SpiderTGSSPin
from src.apps.certificate_order.models.log import Log
from cirbox_scraper.utils import set_certificate_status, log_trace


crochet.setup()
runner = CrawlerRunner(get_project_settings())


class ClavePinHandler:
    def __init__(self):
        self.spider_queue = []

    @staticmethod
    def run_single_spider(spider, params):
        log = Log.objects.create(context=f'Verificando si hay clave pin para {params["nif"]}')
        params.update({'spider_log': log})
        runner.crawl(spider, **params)
        log.refresh_from_db()
        return log.response

    def run_next_spider(self):
        log_trace(self, 'ClavePinHandler', 'Inicio run_next_spider()')
        try:
            if len(self.spider_queue) > 0:
                log_trace(self, 'ClavePinHandler', 'Quedan elementos en cola')
                spider_instance = self.spider_queue.pop(0)
                if self.order_has_error(spider_instance["order"]):
                    log_trace(self, 'ClavePinHandler', f"No encontrado la request que se intentaba procesar: {spider_instance['order']}")
                    return

                log_trace(self, 'ClavePinHandler', 'Lanzando crawler')
                d = runner.crawl(spider_instance['spider'], **spider_instance)
                log_trace(self, 'ClavePinHandler', 'Crawler ejecutado')
                log_trace(self, 'ClavePinHandler', 'Marcando para ejecutar el proximo spider')
                d.addBoth(lambda _: reactor.callLater(0, self.run_next_spider))
        except Exception as err:
            log_trace(self, 'ClavePinHandler', f"Error ejecutando run_next_spider: {str(err)}")

    def get_pin_code(self, order, request_type):
        if self.order_has_error(order):
            return

        formatted_date = ''
        soporte = ''
        try:
            date_obj = datetime.strptime(order['key_document_value'], '%Y-%m-%d')
            formatted_date = date_obj.strftime('%d-%m-%Y')
        except ValueError:
            soporte = order['key_document_value']
            pass

        res = {
            'dni': order['person_national_id'],  # 50107654s
            'expiration_date': formatted_date,  # '13-08-2030'
            'soporte': soporte
        }

        if request_type == 'agency':
            self.spider_queue.append({
                'spider': GetClavePinAgenci,
                'order': order,
                'dni': res.get('dni'),
                'expiration_date': res.get('expiration_date'),
                'soporte': res.get('soporte'),
                'modelo': '100'})
        else:
            self.spider_queue.append({
                'spider': GetClavePin if request_type == 'tgss' else GetClavePinSede,
                'order': order,
                'dni': res.get('dni'),
                'expiration_date': res.get('expiration_date'),
                'soporte': res.get('soporte'),
            })

        if self.spider_queue:
            self.run_next_spider()

    @staticmethod
    def order_has_error(order):
        cached_data = cache.get(order['id'])
        if cached_data is not None and cached_data.get('isError') is not None:
            return True
        return False

    @staticmethod
    def process_agency(order, res):
        return run_spider(SpiderAgenciaTributariaPin, order=order, response=res)

    @staticmethod
    def process_tgss(order, res):
        return run_spider(SpiderTGSSPin, order=order, response=res)

    @staticmethod
    def process_sede(order, res):
        return run_spider(SpiderPensionesPin, order=order, response=res)


def run_spider(spider, order, response):
    otp = response.get('otp')
    return {
        'spider': spider,
        'order': order,
        'otp': otp
    }
