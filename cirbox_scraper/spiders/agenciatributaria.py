import os
import re
import time
import base64
import scrapy
from django.conf import settings
from random import randint
from datetime import date
from cirbox_scraper.spiders.pkcs11_helper import request_by_pkcs11
from cirbox_scraper.utils import set_certificate_doc, log_trace, log_html
from app_root import ROOT_DIR


class SpiderAgenciaTributaria(scrapy.Spider):

    name = 'agenciatributaria_gob_es'
    allowed_domains = ['agenciatributaria.gob.es']
    start_urls = ['https://www2.agenciatributaria.gob.es/wlpl/BUCV-JDIT/AutenticaDniNieContrasteh?ref=%2'
                  'Fwlpl%2FOVCT%2DCXEW%2FSelectorAcceso%3Fref%3D%252Fwlpl%252FSCEJ%2DMANT%252FSvqueryEDOV%25'
                  '3FMODELO%253D100%2526EJERCICIO%253D%2D1%26aut%3DCPR']
    custom_settings = {
        "SPIDER_MIDDLEWARES": {
            "scrapy.downloadermiddlewares.cookies.CookiesMiddleware": 450
        }
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36 Edg/97.0.1072.55"
    }
    QUERY_URL = 'https://www1.agenciatributaria.gob.es/wlpl/SCEJ-MANT/SvqueryEDOV'
    CSS_CLASGTE = 'input#CLASGTE::attr(value)'
    CSS_QUERY_RESULTS = 'table#GESTOR > tbody > tr[id]'
    CSS_QUERY_RESULT_DOWNLOAD_LINK = 'table#GESTOR > tbody > tr[id] > td:last-child > '\
        'span > a::attr(onclick)'
    CSS_DOWNLOAD_ANCHOR_XML = 'td:last-child > span > a::attr(onclick)'
    CSS_DOWNLOAD_ANCHOR_PDF = 'td:nth-child(4) > span > input::attr(onclick)'
    XPATH_CERTIFICATE_LOGIN_LINK = '//a[contains(text(), "certificado o DNI")]/@href'
    REGEX_DOWNLOAD_PARAM_XML = r'javascript\:enlaceConPost\((.*)\);'
    REGEX_DOWNLOAD_PARAM_PDF = r'window.open\((.*)\)'
    REGEX_DOWNLOAD_URL_XML = r'"(https:\/\/.+)", {'
    REGEX_DOWNLOAD_URL_PDF = ".open('"
    REGEX_DOWNLOAD_BODY = r'({.+})'

    def __init__(self, **kwargs):
        print("en el __init__")
        self.order = kwargs.get('order')
        self.modelo = kwargs.get('modelo')

        document_types = {
            '100': 'renta',
            '347': 'modelo_347',
            '390': 'modelo_390',
            '303': 'modelo_303',
            '200': 'modelo_200'
        }
        self.request_type = document_types[self.modelo]

        self.renta_query_form_data = {
            "FNIFOBLIGADO": self.order['person_national_id'],
            "FNOMBRE": '',
            "MODELO": self.modelo,
            "FEJERCICIO": "",  # ? FECHA DEL EJERCICIO A SOLICITAR
            "FPERIODO": "",
            "FFECHADESDE": "",
            "FFECHAHASTA": "",
            "HORADESDE": "00",
            "MINDESDE": "00",
            "SEGDESDE": "00",
            "HORAHASTA": "00",
            "MINHASTA": "00",
            "SEGHASTA": "00",
            "CLASGTE": "20/1/20220322223839457033",
            "QUE_MODO": "NORMAL",
            "ESTADO_COLS": "1",
            "NUM_RESULTADOS_RS": "1",
            "VEZ": "BUSCAR1",
            "NOM_QUERY": "es.aeat.scej.mant.web.query.SvqueryEDOV",
            "COLUMNA_ORDEN": "",
            "MODO_ORDEN": "",
            "hiddenCKBcolumna_n1": "1",
            "hiddenCKBcolumna_n2": "1",
            "hiddenCKBcolumna_n3": "1",
            "hiddenCKBcolumna_n4": "1",
            "hiddenCKBcolumna_n5": "1",
            "CKBcolumna_n1": "on",
            "CKBcolumna_n2": "on",
            "CKBcolumna_n3": "on",
            "CKBcolumna_n4": "on",
            "CKBcolumna_n5": "on",
        }
        if self.order['company_cif']:
            self.renta_query_form_data['FNIFOBLIGADO'] = self.order['company_cif']

        super().__init__(**kwargs)

    def start_requests(self):
        log_trace(self, 'SpiderAgenciaTributaria', 'Inicio solicitud')
        try:
            self.main_menu()
        except Exception as err:
            log_trace(self, 'SpiderAgenciaTributaria', f"Error de ejecucion: {str(err)}")
            print('1', str(err))

    def main_menu(self):
        log_trace(self, 'SpiderAgenciaTributaria', 'Inicio main_menu()')
        log_trace(self, 'SpiderAgenciaTributaria', f"Request type: {self.request_type}")
        log_trace(self, 'SpiderAgenciaTributaria', f"Modelo: {self.modelo}")
        log_trace(self, 'SpiderAgenciaTributaria', f"self.order: {self.order}")

        ruta_fichero = f'/app/renta_{self.order["person_national_id"]}.txt'


        if os.path.exists(ruta_fichero):
            os.remove(ruta_fichero)
