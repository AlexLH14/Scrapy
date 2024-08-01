import os
from urllib.parse import urljoin

import requests
import scrapy
from django.conf import settings
from django.core.cache import cache
from django.shortcuts import redirect

from cirbox_scraper.utils import set_certificate_status, log_and_save_response, log_trace


class EvalClavePin(scrapy.Spider):
    name = 'eval_clave_pin'
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
        self.order = kwargs.get('order')
        self.nif = kwargs.get('nif')
        self.fecha_expedicion = kwargs.get('fecha_expedicion')
        self.fecha_vencimiento = kwargs.get('fecha_vencimiento')
        self.fecha_nacimiento = kwargs.get('fecha_nacimiento')
        self.nro_soporte = kwargs.get('nro_soporte')
        self.tipo_nif = kwargs.get('tipo_nif')
        self.filename = f'{self.nif}.html'
        self.output_dir = os.path.join(settings.STATIC_ROOT, "debug_response", 'eval_pin')
        self.session = requests.sessions.Session()
        self.spider_log = kwargs.get('spider_log')
        super().__init__(**kwargs)

    def start_requests(self):
        log_trace(self, 'EvalClavePin', 'Inicio de procesado')
        try:
            user_data = dict()
            user_data['AZUL'] = '',


        except Exception as err:
            log_trace(self, 'EvalClavePin', f"Se ha producido un error en la ejecucion: {str(err)}")
            data = {'isError': True, 'reason': 'error_no_clavepin'}
            cache.set(self.order['id'], data, 3600)
            log_trace(self, 'EvalClavePin', 'Actualizando el mensaje de la solicitud')
            set_certificate_status(self.order, str(err))
            log_trace(self, 'EvalClavePin', 'Solicitud actualizada con el mensaje de error ')

            if self.spider_log is not None:
                log_trace(self, 'EvalClavePin', 'Grabando el error en spider_log')
                self.spider_log.response = str(err)

        if self.spider_log is not None:
            log_trace(self, 'EvalClavePin', 'Grabando spider_log (funcion save())')
            self.spider_log.save()
