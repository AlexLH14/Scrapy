import scrapy
import base64

from scrapy.http.request import Request
from cirbox_scraper.utils import create_certified_session, set_certificate_doc, log_and_save_response, log_trace
from src.apps.certificate_order.enumeration import CertificateOrderType
from src.apps.certificate_order.models.certificate_order_log import CertificateOrderLogModel


class SpiderBaseCotizacion(scrapy.Spider):
    name = 'base_cotizacion_seg_social_gob_es'
    allowed_domains = ['portal.seg-social.gob.es', 'ipce.seg-social.es', 'sp.seg-social.es']
    handle_httpstatus_list = [301, 302, 303, 403]
    start_urls = ['https://portal.seg-social.gob.es/wps/portal/importass/!ut/p/z0/04_Sj9CPykssy0'
                  'xPLMnMz0vMAfIj8nKt8jNTrMoLivV88tMz8_QLsh0VAZSk7Xs!/']
    custom_settings = {
        'SPIDER_MIDDLEWARES': {'scrapy.downloadermiddlewares.cookies.CookiesMiddleware': 450}
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36 Edg/97.0.1072.55'
    }

    login_body = {'SAMLRequest': '', 'RelayState': ''}

    login_headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,'
                  'image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36 Edg/97.0.1072.55'
    }

    CSS_BASE_URL = 'base::attr(href)'
    CSS_RELAY_STATE = 'input#RelayState::attr(value)'
    CSS_SAML_REQUEST = 'input[name=SAMLRequest]::attr(value)'

    def __init__(self, **kwargs):
        self.order = kwargs.get('order')
        self.certified_session = None
        self.certificate = kwargs.get('certificate')
        self.password = kwargs.get('password')
        super().__init__(**kwargs)
        # CertificateOrderLogModel.objects.create(context='__init__',
        #                                         event=f'Init completado correctamente',
        #                                         certificate_order=self.order)

    def start_requests(self):
        log_trace(self, 'SpiderBaseCotizacion', 'Inicio solicitud')
        try:
            log_trace(self, 'SpiderBaseCotizacion', 'Creando la sesion')
            self.certified_session = create_certified_session(
                password=self.password,
                headers=self.headers,
                pkcs12_data=self.certificate
            )
            # CertificateOrderLogModel.objects.create(context='start_requests',
            #                                         event=f'Sesión lanzada, call a start_urls',
            #                                         certificate_order=self.order)

            log_trace(self, 'SpiderBaseCotizacion', 'Procesando las urls disponibles')
            for url in self.start_urls:
                log_trace(self, 'SpiderBaseCotizacion', f"Gestionando y procesando la respuesta de la url {url} con do_things()")
                yield Request(
                    url=url,
                    method='GET',
                    callback=self.do_things,
                )
            # CertificateOrderLogModel.objects.create(context='start_requests',
            #                                         event=f'start_requests completado correctamente',
            #                                         certificate_order=self.order)
        except Exception as err:
            # CertificateOrderLogModel.objects.create(context='start_requests',
            #                                         event=f'{self.order.status} > '
            #                                               f'{CertificateOrderType.ERROR.value}. Motivo: {repr(err)}',
            #                                         certificate_order=self.order)
            log_trace(self, 'SpiderBaseCotizacion', f"Error registrado: {repr(err)}")
            self.order.register_error(f'BaseCotizacionSpider func start_requests. Error: {repr(err)}')

    def do_things(self, response):
        log_trace(self, 'SpiderBaseCotizacion', 'Iniciando función do_things()')

        try:
            # CertificateOrderLogModel.objects.create(context='do_things',
            #                                         event=f'Fase de login 1/6',
            #                                         certificate_order=self.order)

            # Obtener del html de respuesta la info del form para enviar formulario con petición de login
            log_trace(self, 'SpiderBaseCotizacion', 'Obteniendo URL para enviar peticion de login')


        except Exception as err:
            # CertificateOrderLogModel.objects.create(context='do_things',
            #                                         event=f'Error: {repr(err)}',
            #                                         extra_info=f'{self.order.status} > '
            #                                                    f'{CertificateOrderType.ERROR.value}.',
            #                                         certificate_order=self.order)
            log_trace(self, 'SpiderBaseCotizacion', f"Error registrado en el proceso {str(err)}")
            self.order.register_error(f'BaseCotizacionSpider func do_things. Error: {repr(err)}')



