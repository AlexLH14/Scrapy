import base64
import requests
from django.db import transaction
from datetime import datetime, timezone
# from scrapy.crawler import CrawlerRunner
# from twisted.internet import reactor
# from multiprocessing import Process, Queue
from cirbox_scraper.spiders.base_cotizacion import SpiderBaseCotizacion
from cirbox_scraper.spiders.cirbe import SpiderCirbe
from cirbox_scraper.spiders.get_clave_pin import GetClavePin
from cirbox_scraper.spiders.pensiones import SpiderPensiones
from cirbox_scraper.spiders.vida_laboral import SpiderVidaLaboral
from cirbox_scraper.utils import set_certificate_doc, set_certificate_status
from src.apps.certificate_order.enumeration import CertificateOrderType, CertificateOrderModeEnum
from src.apps.certificate_order.models.certificate_order import CertificateOrderModel
from src.apps.certificate_order.models.certificate_order_log import CertificateOrderLogModel
from src.apps.cron.enumeration import CronNames
from src.utils.back_client import BackClient
from scrapy.utils.project import get_project_settings
from cirbox_scraper.spiders.agenciatributaria import SpiderAgenciaTributaria
from src.utils.php_client import PHPClient


class CertificateProvider:

    @staticmethod
    def manage_certificate(response):
        response = response.json()
        req = requests.get(url=response['certificate_document'])
        req.raise_for_status()
        return {
            'certificate': base64.b64decode(req.content),
            'password': response['password']
        }

        # with open('/home/jlbeltran/Development/cirbox/api-crawler/certificados/jose.p12', 'rb') as pkcs12_file:
        # # with open('/home/jlbeltran/Development/cirbox/api-crawler/certificados/energetica.p12', 'rb') as pkcs12_file:
        #     pkcs12_data = pkcs12_file.read()
        # return {'certificate': pkcs12_data, 'password': 'qw12qwerty'}

    @staticmethod
    def process_orders(order_status, mode, brocode=None):

        # Obtener los 'order' a procesar
        if order_status == CronNames.PROCESAR_PENDIENTES.value:
            filter = {'status': CertificateOrderType.PENDIENTE.value, 'certificate_mode': mode}
            if brocode:
                filter.update({'brocode': brocode})
            orders = CertificateOrderModel.objects.filter(**filter)
            orders = orders.order_by('created')
        else:
            # Si están en error se selecciona el que menos intentos tiene
            filter = {'status': CertificateOrderType.ERROR.value, 'certificate_mode': mode, 'attempts__lte': 1680}
            if brocode:
                filter.update({'brocode': brocode})
            orders = CertificateOrderModel.objects.filter(**filter)   # 1680 son 3,5 días
            orders = orders.order_by('attempts', 'created')

        for order in orders:
            with transaction.atomic():
                CertificateOrderLogModel.objects.create(context='process_orders',
                                                        event='Petición encolada para gestionar',
                                                        extra_info=f'{order.status} > '
                                                                   f'{CertificateOrderType.PROCESANDO.value}. '
                                                                   f'Attempts: {order.attempts}',
                                                        certificate_order=order)
                order.status = CertificateOrderType.PROCESANDO.value
                order.updated = datetime.today()
                order.save()

        if orders:
            if mode == CertificateOrderModeEnum.P12.value:
                CertificateProvider.run_orders_with_p12(orders=orders)
            elif mode == CertificateOrderModeEnum.CLAVEPIN.value:
                CertificateProvider.run_orders_with_clave_pin(orders=orders)
            else:
                CertificateProvider.run_orders_with_pkcs11(orders=orders)

    @staticmethod
    def run_orders_with_clave_pin(orders):
        brocodes = list(set([obj.brocode for obj in orders]))
        for brocode in brocodes:
            _orders = CertificateOrderModel.objects.filter(brocode=brocode)
            peticiones = list()
            try:
                for order in _orders:
                    if order.attempts > 2520:  # 2520 porque las PENDIENTE se ejecutan cada 2 minutos
                        order.register_error('Se ha llegado al máximo de reintentos (3,5 días)')
                        raise Exception('Saltar a siguiente brocode')
                    peticiones.append(order.product_type)
            except:
                continue

            first = _orders.first().extra_info
            fecha_nacimiento = None
            if 'fecha_nacimiento' in first and first['fecha_nacimiento'] is not None:
                fecha_nacimiento = first['fecha_nacimiento'].replace('/', '-')
            data = {
                "scratchard": first['nif'],
                "nif": first['nif'],
                "tipo_nif": first['dni_type'],
                "fecha_expedicion": first['fecha_expedicion'].replace('/', '-'),
                "fecha_vencimiento": first['fecha_vencimiento'].replace('/', '-'),
                "peticiones": peticiones,
                "cola_id": _orders.first().certificate_id,
                "fecha_nacimiento": fecha_nacimiento
            }
            try:
                response = PHPClient.requests(method='post', url=PHPClient.URLS['clavepin'], data=data)
            except Exception as err:
                for order in _orders:
                    order.register_error(str(err))
                return

            if response.status_code != 201:
                for order in _orders:
                    order.register_error(str(response.content))
            else:
                try:
                    response = response.json()
                    for order in response['peticiones']:
                        obj_order = _orders.filter(product_type=order['tipo']).first()
                        if order['status'] == 'ERROR':
                            msg = str(order['data'])
                            set_certificate_status(order=obj_order, data=msg)
                            obj_order.register_error(msg)
                        elif order['status'] == 'OK':
                            set_certificate_doc(order=obj_order, doc_data=str(order['data']))
                            obj_order.register_success()
                        else:
                            obj_order.register_error(f'status PHP desconocido: {order["status"]}')
                except Exception as err:
                    CertificateOrderLogModel.objects.create(context=str(err),
                                                            event='status_error',
                                                            certificate_order=_orders.first())

    @staticmethod
    def run_orders_with_pkcs11(orders):
        brocodes = list(set([obj.brocode for obj in orders]))
        for brocode in brocodes:
            _orders = CertificateOrderModel.objects.filter(brocode=brocode)
            peticiones = list()
            try:
                for order in _orders:
                    if order.attempts > 2520:  # 2520 porque las PENDIENTE se ejecutan cada 2 minutos
                        order.register_error('Se ha llegado al máximo de reintentos (3,5 días)')
                        raise Exception('Saltar a siguiente brocode')
                    peticiones.append(order.product_type)
            except:
                continue

            first = _orders.first().extra_info
            data = {
                "scratchard": first['username'],
                "password": first['password'],
                "pin": first['pin'],
                "peticiones": peticiones
            }
            response = PHPClient.requests(method='post', url=PHPClient.URLS['pkcs11'], data=data)
            response = response.json()

            # example_response = {
            #     "scratchard": "543534",
            #     "peticiones": [{
            #         "tipo": "vida_laboral",
            #         "data": "BASE64|MOTIVO_ERROR",
            #         "status": "OK|ERROR"
            #     }]
            # }
            for order in response['peticiones']:
                obj_order = _orders.filter(product_type=order['tipo']).first()
                if order['status'] == 'ERROR':
                    obj_order.register_error(str(order['data']))
                elif order['status'] == 'OK':
                    set_certificate_doc(order=obj_order, doc_data=str(order['data']))
                    obj_order.register_success()
                else:
                    obj_order.register_error(f'status PHP desconocido: {order["status"]}')

    @staticmethod
    def run_orders_with_p12(orders):

        func = {
            'renta': CertificateProvider.process_renta,
            'cirbe': CertificateProvider.process_cirbe,
            'vida_laboral': CertificateProvider.process_vida_laboral,
            'pensiones': CertificateProvider.process_pensiones,
            'modelo_347': CertificateProvider.process_modelo347,
            'modelo_390': CertificateProvider.process_modelo390,
            'base_cotizacion': CertificateProvider.base_cotizacion
        }

        # Se procesa cada order
        for order in orders:
            try:
                # Las peticiones PENDIENTES con más de 3,5 días se pasan a error. Aquí no llegarán las de ERROR con
                # más de 3,5 días ya que se descartan en la query de antes
                if order.attempts > 2520:   # 2520 porque las PENDIENTE se ejecutan cada 2 minutos
                    order.register_error('Se ha llegado al máximo de reintentos (3,5 días)')
                    continue

                # Primero se obtiene el certificado digital al vuelo para hacer la petición
                try:
                    response = BackClient.requests(
                        method='get',
                        url=BackClient.URLS['get_certificate'],
                        params={'id': order.certificate_id}
                    )
                    CertificateOrderLogModel.objects.create(context='get_certificate',
                                                            event='URL a certificado obtenida correctamente',
                                                            certificate_order=order)
                except Exception as err:
                    CertificateOrderLogModel.objects.create(context='get_certificate',
                                                            event=f'Error obteniendo certificado. Motivo: {repr(err)}',
                                                            extra_info=f'{order.status} > '
                                                                       f'{CertificateOrderType.ERROR.value}.',
                                                            certificate_order=order)
                    order.register_error(f'Error obteniendo certificado (get_certificate). Motivo: {repr(err)}')
                    continue

                # Generar objeto de certificado + password
                try:
                    response = CertificateProvider.manage_certificate(response)
                    CertificateOrderLogModel.objects.create(context='manage_certificate',
                                                            event='Certificado descargado y extraído correctamente',
                                                            certificate_order=order)
                except Exception as err:
                    CertificateOrderLogModel.objects.create(context='manage_certificate',
                                                            event=f'Error extrayendo certificado. Motivo: {repr(err)}',
                                                            extra_info=f'{order.status} > '
                                                                       f'{CertificateOrderType.ERROR.value}.',
                                                            certificate_order=order)
                    order.register_error(f'Error extrayendo certificado (manage_certificate). Motivo: {repr(err)}')
                    continue

                f = func.get(order.product_type, None)
                if not func.get(order.product_type):
                    # Si no existe Spider para ese producto se marca como NO PROGRAMADO
                    order.set_to_no_programado()
                    CertificateOrderLogModel.objects.create(context='process_orders (3)',
                                                            event=f'No hay spider para el producto {order.product_type}',
                                                            extra_info=f'{order.status} > '
                                                                       f'{CertificateOrderType.NO_PROGRAMADO.value}.',
                                                            certificate_order=order)
                    continue

                f(order=order, response=response)

            except Exception as err:
                if err:
                    CertificateOrderLogModel.objects.create(context='process_orders, except',
                                                            event=f'Error al procesar la solicitud. Motivo: {repr(err)}',
                                                            extra_info=f'{order.status} > '
                                                                       f'{CertificateOrderType.ERROR.value}.',
                                                            certificate_order=order)
                    order.register_error(f'process_orders. Err: {repr(err)}')

                    # Se reinicia el proceso por el tema del ReactorNotRestartable
                    import os
                    import sys
                    os.execl(sys.executable, sys.executable, *sys.argv)

                else:
                    CertificateOrderLogModel.objects.create(context='process_orders, except',
                                                            event=f'Hilo interrumpido',
                                                            extra_info=f'{order.status} > '
                                                                       f'{CertificateOrderType.PENDIENTE.value}.',
                                                            certificate_order=order)
                    order.status = CertificateOrderType.PENDIENTE.value
                    order.attempts = 0
                    order.save()

    @staticmethod
    def run_spider(spider, order, response, modelo=None):
        # def f(q):
        #     try:
        #         runner = CrawlerRunner(get_project_settings())
        #         password = response.get('password')
        #         deferred = runner.crawl(spider, order=order, certificate=response.get('certificate'),
        #                                 password=password, modelo=modelo)
        #         deferred.addBoth(lambda _: reactor.stop())
        #         reactor.run()
        #         q.put(None)
        #     except Exception as e:
        #         q.put(e)
        #
        # q = Queue()
        # p = Process(target=f, args=(q,))
        # p.start()
        # result = q.get()
        # p.join()
        #
        # if result is not None:
        #     raise result

        # process = CrawlerProcess(get_project_settings())
        # password = response.get('password')
        # CertificateOrderLogModel.objects.create(context='run_spider', event='Instanciando crawler',
        #                                         certificate_order=order)
        # process.crawl(spider, order=order, certificate=response.get('certificate'),
        #               password=password, modelo=modelo)
        # CertificateOrderLogModel.objects.create(context='run_spider', event='Lanzando start()',
        #                                         certificate_order=order)
        # process.start()
        # time.sleep(1)
        # os.execl(sys.executable, sys.executable, *sys.argv)
        from scrapy.crawler import CrawlerRunner
        from twisted.internet import reactor
        password = response.get('password')
        runner = CrawlerRunner(get_project_settings())
        d = runner.crawl(spider, order=order, certificate=response.get('certificate'), password=password, modelo=modelo)
        d.addBoth(lambda _: reactor.stop())
        reactor.run()
        # the script will block here until the crawling is finished
        # time.sleep(1)
        # os.execl(sys.executable, sys.executable, *sys.argv)

    @staticmethod
    def process_renta(order, response):
        CertificateProvider.run_spider(spider=SpiderAgenciaTributaria, order=order, response=response, modelo='100')

    @staticmethod
    def process_cirbe(order, response):
        # Se verifica que esté la fecha de nacimiento informada al ser un dato obligatorio
        if order.extra_info['birthdate'] is None:
            raise Exception('La fecha de nacimiento no está informada')
        CertificateProvider.run_spider(spider=SpiderCirbe, order=order, response=response)

    @staticmethod
    def process_vida_laboral(order, response):
        CertificateProvider.run_spider(spider=SpiderVidaLaboral, order=order, response=response)

    @staticmethod
    def process_pensiones(order, response):
        CertificateProvider.run_spider(spider=SpiderPensiones, order=order, response=response)

    @staticmethod
    def process_get_clave_pin(order, response):
        CertificateProvider.run_spider(spider=GetClavePin, order=order, response=response)

    @staticmethod
    def process_modelo347(order, response):
        CertificateProvider.run_spider(spider=SpiderAgenciaTributaria, order=order, response=response, modelo='347')

    @staticmethod
    def process_modelo390(order, response):
        CertificateProvider.run_spider(spider=SpiderAgenciaTributaria, order=order, response=response, modelo='390')

    @staticmethod
    def base_cotizacion(order, response):
        CertificateProvider.run_spider(spider=SpiderBaseCotizacion, order=order, response=response)

    @staticmethod
    def process_procesando():
        orders = CertificateOrderModel.objects.filter(status=CertificateOrderType.PROCESANDO.value)
        for order in orders:
            try:
                if int((datetime.now(timezone.utc) - order.updated).seconds / 60) > 3:
                    order.reset_to_pendiente()
                    CertificateOrderLogModel.objects.create(context='process_procesando',
                                                            event=f'Petición reseteada a '
                                                                  f'{CertificateOrderType.PENDIENTE.value}',
                                                            certificate_order=order)
            except Exception as err:
                CertificateOrderLogModel.objects.create(context='process_procesando',
                                                        event=f'Error: {repr(err)}',
                                                        extra_info=f'{order.status}',
                                                        certificate_order=order)
