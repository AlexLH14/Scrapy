import re
import base64
import time
import scrapy
from datetime import date

from django.conf import settings
from scrapy.http.response.html import HtmlResponse
from scrapy.http.request import Request
from cirbox_scraper.utils import create_certified_session, set_certificate_doc
from bs4 import BeautifulSoup as BS

from src.apps.certificate_order.enumeration import CertificateOrderType
from src.apps.certificate_order.models.certificate_order_log import CertificateOrderLogModel


class SpiderAgenciaTributaria(scrapy.Spider):
    name = 'agenciatributaria_gob_es_p12'
    allowed_domains = ['agenciatributaria.gob.es']
    start_urls = ['https://www2.agenciatributaria.gob.es/wlpl/BUCV-JDIT/AutenticaDniNieContrasteh?ref=%2'
                  'Fwlpl%2FOVCT%2DCXEW%2FSelectorAcceso%3Fref%3D%252Fwlpl%252FSCEJ%2DMANT%252FSvqueryEDOV%25'
                  '3FMODELO%253D100%2526EJERCICIO%253D%2D1%26aut%3DCPR']

    ''

    custom_settings = {
        "SPIDER_MIDDLEWARES": {
            "scrapy.downloadermiddlewares.cookies.CookiesMiddleware": 450
        }
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36 Edg/97.0.1072.55"
    }

    # ? URLs and Templates
    QUERY_URL = 'https://www1.agenciatributaria.gob.es/wlpl/SCEJ-MANT/SvqueryEDOV'

    # ? Selectors and regex
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

    # Used when trying to implement PKCS11
    # def __init__(self, name=None, request_id=None, username=None, password=None, certificate=None, **kwargs):
    def __init__(self, **kwargs):
        self.order = kwargs.get('order')
        self.modelo = kwargs.get('modelo')
        self.certified_session = None
        self.certificate = kwargs.get('certificate')
        self.password = kwargs.get('password')
        # ? Forms data
        self.renta_query_form_data = {
            "FNIFOBLIGADO": self.order.extra_info['person_id'],
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

        super().__init__(**kwargs)

        CertificateOrderLogModel.objects.create(context='__init__',
                                                event=f'Init completado correctamente',
                                                certificate_order=self.order)

    def start_requests(self):
        try:
            self.certified_session = create_certified_session(
                password=self.password,
                headers=self.headers,
                pkcs12_data=self.certificate
            )
            CertificateOrderLogModel.objects.create(context='start_requests',
                                                    event=f'Sesión lanzada, call a start_urls',
                                                    certificate_order=self.order)
            for url in self.start_urls:
                yield Request(
                    url=url,
                    method='GET',
                    callback=self.main_menu,
                )
            CertificateOrderLogModel.objects.create(context='start_requests',
                                                    event=f'start_requests completado correctamente',
                                                    certificate_order=self.order)
        except Exception as err:
            CertificateOrderLogModel.objects.create(context='start_requests',
                                                    event=f'{self.order.status} > '
                                                          f'{CertificateOrderType.ERROR.value}. Motivo: {repr(err)}',
                                                    certificate_order=self.order)
            self.order.register_error(f'AgenciaTributariaSpider func start_requests. Error: {repr(err)}')

    def main_menu(self, response):
        try:
            CertificateOrderLogModel.objects.create(context='AgenciaTributariaSpider',
                                                    event='Login realizado correctamente',
                                                    certificate_order=self.order)

            login_link = response.xpath(self.XPATH_CERTIFICATE_LOGIN_LINK).get()
            # * Using requests.Session() object with X509Adapter
            login_response = self.certified_session.get(login_link)
            # ? Modify the renta_query_form_data dict according to the exercise
            scrapy_login_response = HtmlResponse(
                url=login_response.url,
                body=login_response.text,
                encoding='utf8'
            )
            formdata = self.renta_query_form_data.copy()
            clasgte = scrapy_login_response.css(self.CSS_CLASGTE).get()
            formdata['CLASGTE'] = clasgte
            year = date.today().year - 1
            formdata['FEJERCICIO'] = str(year)

            # ? Query the exercise for the past year if available
            self.logger.info(f'[!] Querying modelo {self.modelo} document from {year}.')
            results = None
            while not results:
                CertificateOrderLogModel.objects.create(context='AgenciaTributariaSpider',
                                                        event=f'Solicitando modelo {self.modelo} para el año {year}',
                                                        certificate_order=self.order)
                query_response = self.certified_session.post(
                    url=self.QUERY_URL,
                    headers={
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'x-site': 'Sede',
                        'X-XSS-Protection': '1; mode=block'
                    },
                    data=formdata
                )
                query_r_selector = scrapy.Selector(text=query_response.text)
                results = query_r_selector.css(self.CSS_QUERY_RESULTS)
                if not results:
                    CertificateOrderLogModel.objects.create(context='AgenciaTributariaSpider',
                                                            event=f'Modelo del año {year} no encontrada',
                                                            certificate_order=self.order)
                    year -= 1
                    formdata['FEJERCICIO'] = year
                    time.sleep(2)
                if year < 2017:
                    CertificateOrderLogModel.objects.create(context='AgenciaTributariaSpider',
                                                            event=f'Sin resultados encontrados, '
                                                                  f'se termina el proceso de consulta',
                                                            certificate_order=self.order)

                    try:
                        # Si no se devuelve ningún documento se sube uno vacío
                        file_content = open(f'{settings.ROOT_DIR}/assets/modelo_informe_no_disponible.pdf', 'rb').read()
                        pdf_data = base64.b64encode(file_content)
                        set_certificate_doc(order=self.order, doc_data=str(pdf_data)[2:-1])
                        self.order.register_success()
                        CertificateOrderLogModel.objects.create(context='AgenciaTributariaSpider',
                                                                event=f'Subido modelo pdf "documento no encontrado"'
                                                                      f' correctamente',
                                                                certificate_order=self.order)
                    except Exception as err:
                        CertificateOrderLogModel.objects.create(context='AgenciaTributariaSpider func '
                                                                        'set_certificate_doc (2).',
                                                                event=f'Error: {repr(err)}',
                                                                extra_info=f'{self.order.status} > '
                                                                           f'{CertificateOrderType.ERROR.value}.',
                                                                certificate_order=self.order)
                        self.order.register_error(f'AgenciaTributariaSpider func set_certificate_doc (2). '
                                                  f'Error: {repr(err)}')
                    return

            # PDF Se busca la URL que contiene el código "CSV" que es el código de identificador de cada documento
            td = results[0].css(self.CSS_DOWNLOAD_ANCHOR_PDF).get()
            parameters = re.search(self.REGEX_DOWNLOAD_PARAM_PDF, td).group(0)
            download_url = parameters.split(',')[0].split(self.REGEX_DOWNLOAD_URL_PDF)[1]
            csv_attr = download_url.split('CSV=')[1][:-1]

            # Descargamos XML con todos los datos
            url = f'https://www1.agenciatributaria.gob.es/wlpl/inwinvoc/es.aeat.dit.' \
                  f'adu.adht.edecla.DeclaVisor?fDetalle=1&fCsv={csv_attr}&fNif={self.order.extra_info["person_id"]}'
            download_response = self.certified_session.get(
                url=url,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'x-site': 'Sede',
                    'X-XSS-Protection': '1; mode=block'
                }
            )
            if download_response.status_code != 200:
                raise Exception(f'No se ha podido descargar el modelo {self.modelo}')

            CertificateOrderLogModel.objects.create(context='AgenciaTributariaSpider func set_certificate_doc (3)',
                                                    event=f'XML del modelo {self.modelo} descargado correctamente. '
                                                          f'Extrayendo pdf...',
                                                    certificate_order=self.order)

            data = BS(download_response.content, 'lxml')
            content = data.recibo.text
            pdf_base64 = content.split('<![CDATA[')[1][:-3]
            # pdf_data = base64.b64decode(pdf_base64)
            try:
                set_certificate_doc(order=self.order, doc_data=pdf_base64)
                CertificateOrderLogModel.objects.create(context='AgenciaTributariaSpider func set_certificate_doc (4)',
                                                        event=f'PDF enviado a api-cirbox correctamente. '
                                                              f'{self.order.status} > '
                                                              f'{CertificateOrderType.COMPLETADO.value}',
                                                        certificate_order=self.order)
                self.order.register_success()
            except Exception as err:
                CertificateOrderLogModel.objects.create(context='AgenciaTributariaSpider func set_certificate_doc (2).',
                                                        event=f'Error: {repr(err)}',
                                                        extra_info=f'{self.order.status} > '
                                                                   f'{CertificateOrderType.ERROR.value}.',
                                                        certificate_order=self.order)
                self.order.register_error(f'AgenciaTributariaSpider func set_certificate_doc (2). Error: {repr(err)}')

        except Exception as err:
            CertificateOrderLogModel.objects.create(context='AgenciaTributariaSpider func set_certificate_doc 5).',
                                                    event=f'Error: {repr(err)}',
                                                    extra_info=f'{self.order.status} > '
                                                               f'{CertificateOrderType.ERROR.value}.',
                                                    certificate_order=self.order)
            self.order.register_error(f'AgenciaTributariaSpider func set_certificate_doc (5). Error: {repr(err)}')
