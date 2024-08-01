import base64
import os
from urllib.parse import urljoin

import scrapy
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.cache import cache
from django.shortcuts import redirect

from cirbox_scraper.utils import set_certificate_doc, set_certificate_status, log_and_save_response, log_trace


class SpiderPensionesPin(scrapy.Spider):
    name = 'spider_pensiones_pin'
    allowed_domains = ['portal.seg-social.gob.es', 'ipce.seg-social.es', 'sp.seg-social.es']
    handle_httpstatus_list = [301, 302, 303, 403]
    custom_settings = {
        'SPIDER_MIDDLEWARES': {'scrapy.downloadermiddlewares.cookies.CookiesMiddleware': 450}
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36 Edg/97.0.1072.55'
    }
    login_headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,'
                  'image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36 Edg/97.0.1072.55'
    }
    BASE_URL = 'https://sede-tu.seg-social.gob.es/'
    CSS_BASE_URL = 'base::attr(href)'
    CSS_RELAY_STATE = 'input#RelayState::attr(value)'
    CSS_SAML_REQUEST = 'input[name=SAMLRequest]::attr(value)'
    CSS_SAML_RESPONSE = 'input[name=SAMLResponse]::attr(value)'

    def __init__(self, **kwargs):
        self.order = kwargs.get('order')
        self.otp = kwargs.get('otp')
        self.session = None
        self.code = None

        self.filename = f'{self.order["person_national_id"]}.html'
        self.output_dir = os.path.join(settings.STATIC_ROOT, "debug_response", 'sede')
        super().__init__(**kwargs)

    def start_requests(self):
        log_trace(self, 'SpiderPensionesPin', 'Inicio solicitud')
        try:
            cached_data = cache.get(self.order['id'])
            log_trace(self, 'SpiderPensionesPin', 'Fichero subido')

        except Exception as err:
            log_trace(self, 'SpiderPensionesPin', f"Error producido: {str(err)}")
            data = {'isError': True}
            if self.order and self.order['return_url']:
                log_trace(self, 'SpiderPensionesPin', 'Gestiono la respuesta al tener definida un return_url')
                if 'La combinacion Código/PIN introducida es incorrecta' in str(err):
                    data = {'isError': True, 'reason': 'error_pin'}
                elif 'El PIN solicitado ha sido utilizado o ha expirado' in str(err):
                    data = {'isError': True, 'reason': 'error_time_out'}
                else:
                    data = {'isError': True, 'reason': 'error_administraciones_publicas'}

            log_trace(self, 'SpiderPensionesPin', f"Grabando datos en cache: {data}")
            cache.set(self.order['id'], data, 3600)
            log_trace(self, 'SpiderPensionesPin', f"Ajustando comentario de error en solicitud")
            set_certificate_status(self.order, str(err))
            log_trace(self, 'SpiderPensionesPin', f"Comentario actualizado")
