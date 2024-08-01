import os
from urllib.parse import urljoin

import requests
import scrapy
from django.conf import settings
from django.core.cache import cache
from django.shortcuts import redirect

from cirbox_scraper.utils import set_certificate_status, log_and_save_response, log_trace


class GetClavePinSede(scrapy.Spider):
    name = 'get_clave_pin_sede'
    allowed_domains = ['portal.seg-social.gob.es', 'ipce.seg-social.es', 'sp.seg-social.es']
    handle_httpstatus_list = [301, 302, 303, 403]
    start_urls = 'https://sede.seg-social.gob.es/wps/portal/sede/Seguridad/PortalRedirectorN1P?idApp=1036&idContenido=5d2c9ebd-7f5c-41d0-aa03-d508ed0225fc&idPagina=com.ss.sede.Ciudadanos&N1&P'
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
        self.dni = kwargs.get('dni')
        self.order = kwargs.get('order')
        self.expiration_date = kwargs.get('expiration_date')
        self.soporte = kwargs.get('soporte')
        self.session = requests.sessions.Session()

        self.filename = f'{self.dni}.html'
        self.output_dir = os.path.join(settings.STATIC_ROOT, "debug_response", 'tgss_sede_auth')
        super().__init__(**kwargs)

    def start_requests(self):
        log_trace(self, 'GetClavePinSede', 'Inicio solicitud')
        try:
            log_trace(self, 'GetClavePinSede', f"Llamando a {self.start_urls}")

        except Exception as err:
            log_trace(self, 'GetClavePinSede', f"Error en la ejecución: {str(err)}")
            data = {'isError': True, 'reason': 'error_no_clavepin'}
            cache.set(self.order['id'], data, 3600)
            log_trace(self, 'GetClavePinSede', 'Agregando comentario en el estado de la solicitud')
            set_certificate_status(self.order, str(err))
            log_trace(self, 'GetClavePinSede', 'Comentario agregado')
