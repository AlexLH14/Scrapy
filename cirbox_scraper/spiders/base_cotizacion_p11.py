import scrapy
import base64
import requests
from django.conf import settings
from scrapy.http.request import Request

from cirbox_scraper.spiders.pkcs11_helper import request_by_pkcs11
from cirbox_scraper.utils import set_certificate_doc, log_and_save_response, log_trace, log_html
from src.apps.certificate_order.enumeration import CertificateOrderType
from src.utils.back_client import BackClient


class SpiderBaseCotizacionP11(scrapy.Spider):
    name = 'seg_social_gob_es_p11'
    allowed_domains = ['portal.seg-social.gob.es', 'ipce.seg-social.es', 'sp.seg-social.es']
    handle_httpstatus_list = [301, 302, 303, 403]
    start_urls = ['https://portal.seg-social.gob.es/wps/portal/importass/!ut/p/z0/04_Sj9CPykssy0'
                  'xPLMnMz0vMAfIj8nKt8jNTrMoLivV88tMz8_QLsh0VAZSk7Xs!/']
    custom_settings = {
        'LOG_LEVEL': 'DEBUG',
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
        super().__init__(**kwargs)

    def start_requests(self):
        log_trace(self, 'SpiderBaseCotizacionP11', 'Inicio solicitud')
        try:
            log_trace(self, 'SpiderBaseCotizacionP11', 'Iniciando sesion')
            self.certified_session = requests.Session()
            for url in self.start_urls:
                yield Request(
                    url=url,
                    method='GET',
                    callback=self.do_things,
                )
        except Exception as err:
            log_trace(self, 'SpiderBaseCotizacionP11', f"Error en la exploración de las URLs: {str(err)}")
            print('1', str(err))

    def do_things(self, response):
        log_html(self, response, '1', 'SpiderBaseCotizacionP11', 'not defined')

        try:
            log_trace(self, 'SpiderBaseCotizacionP11', 'Iniciando el procesado de la respuesta')

            log_trace(self, 'SpiderBaseCotizacionP11', 'Documento subido')

        except Exception as err:
            log_trace(self, 'SpiderBaseCotizacionP11', f"Error en el proceso: {str(err)}")
            raise err
