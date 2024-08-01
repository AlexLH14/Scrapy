import os

import requests
import scrapy
from django.conf import settings
from django.core.cache import cache

from cirbox_scraper.utils import set_certificate_status, log_and_save_response, log_trace


class GetClavePinAgenci(scrapy.Spider):
    name = 'get_clave_pin_agenci'
    allowed_domains = ['agenciatributaria.gob.es']
    handle_httpstatus_list = [301, 302, 303, 403]
    custom_settings = {
        "SPIDER_MIDDLEWARES": {
            "scrapy.downloadermiddlewares.cookies.CookiesMiddleware": 450
        }
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36 Edg/97.0.1072.55"
    }

    def __init__(self, **kwargs):
        self.dni = kwargs.get('dni')
        self.order = kwargs.get('order')
        self.expiration_date = kwargs.get('expiration_date')
        self.soporte = kwargs.get('soporte')
        self.modelo = kwargs.get('modelo')
        self.session = requests.sessions.Session()

        self.filename = f'{self.dni}.html'
        self.output_dir = os.path.join(settings.STATIC_ROOT, "debug_response", 'agency_auth')

        super().__init__(**kwargs)

    def start_requests(self):
        log_trace(self, 'GetClavePinAgenci', 'Inicio solicitud')
        try:
            user_data = dict()

        except Exception as err:
            log_trace(self, 'GetClavePinAgenci', f"Se ha producido un error: {str(err)}. Se actualizará el mensaje de estado de la solicitud")

            data = {'isError': True, 'reason': 'error_no_clavepin'}
            cache.set(self.order['id'], data, 3600)

            set_certificate_status(self.order, str(err))
            log_trace(self, 'GetClavePinAgenci', 'Solicitud modificada indicando el motivo de error')
