import scrapy
import requests
import base64
import os
import urllib.parse as prs
from datetime import datetime
from scrapy.http import FormRequest
from scrapy.http.request import Request
from cirbox_scraper.spiders.pkcs11_helper import request_by_pkcs11
from cirbox_scraper.utils import create_certified_session, set_certificate_doc, set_certificate_status, log_and_save_response, log_trace, log_html
from rest_framework import status
from src.apps.certificate_order.enumeration import CertificateOrderType
from src.apps.certificate_order.models.certificate_order_log import CertificateOrderLogModel
from app_root import ROOT_DIR
from src.utils.back_client import BackClient


class SpiderCirbe(scrapy.Spider):

    """ApsBdeEsSpider extracts CIRBE report from aps.bde.es website
    """
    name = "aps_bde_es_cirbe"
    allowed_domains = ["aps.bde.es"]
    start_urls = ["https://example.com"]
    cirbe_start_urls = [
        "https://aps.bde.es/iaet/Initializer",
        "https://aps.bde.es/cir_www",
    ]
    custom_settings = {
        "SPIDER_MIDDLEWARES": {
            "scrapy.downloadermiddlewares.cookies.CookiesMiddleware": 450
        }
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36 Edg/97.0.1072.55"
    }
    certified_session = None
    cirbe_request_form_data = {
        "RejillaConPaginacionEnServidor_select": "0",
        "form:CajaParaFechaNacimiento": "",
        "form:CajaDeTextoCorreoElectronico": "",
        "form:CajaDeTextoNIE": "",
        "form:CheckBoxSimpleCondicionesPrivacidad": "true",
        "form:BotonAceptar": "Aceptar",
        "token": "",
        "form_SUBMIT": "1",
        "javax.faces.ViewState": "",
    }
    cirbe_consult_form_data = {
        "RejillaPeticiones_select": "0",
        "form:BotonDescargar": "Descargar",
        "token": "",
        "form_SUBMIT": "1",
        "javax.faces.ViewState": ""
    }
    cirbe_download_form_data = {
        "RejillaConPaginacionEnServidor_select": "0",
        "form:BotonDescargar": "Descargar",
        "token": "",
        "form_SUBMIT": "1",
        "javax.faces.ViewState": ""
    }

    BASE_URL = "https://aps.bde.es"

    CSS_REQUEST_TOKEN = "input#token::attr(value)"
    CSS_REQUEST_VIEWSTATE = 'input[name="javax.faces.ViewState"]::attr(value)'
    CSS_REQUEST_REFERENCE_NUMBER = "span#form\:Etiqueta_Label::text"
    CSS_REQUEST_DOWNLOAD_LINK = 'a#form\:Enlace_Link::attr(href)'
    XPATH_CIRBE_REQUEST_URL = '//a[contains(text(), "Petición de informe")]/@href'
    XPATH_CIRBE_CONSULT_URL = '//a[contains(text(), "Consulta de estado")]/@href'

    def __init__(self, name=None, request_id=None, **kwargs):
        self.order = kwargs.get('order')
        self.birthdate = self.order['person_birth_date']
        self.email = self.order['person_email']
        self.cirbe_txt_file = kwargs.get('cirbe_txt_file')
        self.reference_number = kwargs.get('reference_number', None)
        super().__init__(name, **kwargs)

    def start_requests(self):
        log_trace(self, 'SpiderCirbe', 'Inicio solicitud')
        # print('start requests')
        try:
            log_trace(self, 'SpiderCirbe', 'Definiendo fecha de nacimiento')
            self.birthdate = datetime.strptime(self.birthdate, '%Y-%m-%d').strftime('%d/%m/%Y')
            log_trace(self, 'SpiderCirbe', f"Definida: {self.birthdate}")
        except:
            # print('except')
            log_trace(self, 'SpiderCirbe', f"Error recuperando y convirtiendo fecha: {self.birthdate}")
            raise Exception('Cirbe: No se ha definido una fecha de nacimiento')

        try:
            self.certified_session = requests.Session()

            # ? Generate login response for CIRBE
            log_trace(self, 'SpiderCirbe', f"Preparando llamada de login al Cirbe: {self.cirbe_start_urls[0]}")
            request_by_pkcs11(url=self.cirbe_start_urls[0],
                              dni=self.order['person_national_id'],
                              method='GET',
                              body=None,
                              authorization=None,
                              simplec='cirbe',
                              decode=False,
                              nif=self.order['company_cif'])

            log_trace(self, 'SpiderCirbe', f"Haciendo segunda llamada: {self.cirbe_start_urls[1]}")
            login_response = request_by_pkcs11(url=self.cirbe_start_urls[1],
                                               dni=self.order['person_national_id'],
                                               method='GET',
                                               body=None,
                                               authorization=None,
                                               simplec='cirbe',
                                               decode=False,
                                               nif=self.order['company_cif'])
            log_html(self, login_response, '1', 'SpiderCirbe', self.cirbe_start_urls[1])
            selector = scrapy.Selector(text=login_response)

            # Si entra en el IF estamos en fase 1
            log_trace(self, 'SpiderCirbe', f"Verificamos en que fase estamos de la obtención")
            if not self.reference_number:
                log_trace(self, 'SpiderCirbe', f"Fase 1: Solicitud. No se detecta referencia")
                # print('No hay referencia')
                cirbe_request_url = prs.urljoin(
                    self.BASE_URL, selector.xpath(self.XPATH_CIRBE_REQUEST_URL).get()
                )
                # print(cirbe_request_url)
                log_trace(self, 'SpiderCirbe', f"Llamando a url {cirbe_request_url}")
                login_response = request_by_pkcs11(url=cirbe_request_url,
                                                   dni=self.order['person_national_id'],
                                                   method='GET',
                                                   body=None,
                                                   authorization=None,
                                                   simplec='cirbe',
                                                   decode=False,
                                                   nif=self.order['company_cif'])
                log_html(self, login_response, '2', 'SpiderCirbe', cirbe_request_url)
                response = scrapy.Selector(text=login_response)

                # Generando solicitud a CIRBE
                request_token = response.css(self.CSS_REQUEST_TOKEN).get()
                view_state = response.css(self.CSS_REQUEST_VIEWSTATE).get()

                self.cirbe_request_form_data["token"] = request_token
                self.cirbe_request_form_data["javax.faces.ViewState"] = view_state
                self.cirbe_request_form_data["form:CajaParaFechaNacimiento"] = self.birthdate
                self.cirbe_request_form_data["form:CajaDeTextoCorreoElectronico"] = self.email
                # print(self.cirbe_request_form_data)
                form = response.xpath('//form[@id="form"]')
                # Extrae la URL del formulario del atributo 'action'
                form_action = form.xpath('@action').get()
                # print(form_action)
                cirbe_request_url = prs.urljoin(self.BASE_URL, form_action)
                # print(cirbe_request_url)
                log_trace(self, 'SpiderCirbe', f"Generando llamada de solicitud con url : {cirbe_request_url}")
                login_response = request_by_pkcs11(url=cirbe_request_url,
                                                   dni=self.order['person_national_id'],
                                                   method='POST',
                                                   body=self.cirbe_request_form_data,
                                                   authorization=None,
                                                   simplec='cirbe',
                                                   decode=False,
                                                   nif=self.order['company_cif'])
                log_html(self, login_response, '3', 'SpiderCirbe', cirbe_request_url)
                # print(login_response)
                response = scrapy.Selector(text=login_response)

                #TODO Si en la respuesta obtenida aparece la imagen Atencion.gif .. es que están pintando una alerta en la creación de la solicitud 
                # y, por tanto, no se ha creado y lo que obtengamos probablemente no sea el numero de referencia  (ejemplo static/traces/202404/25/5078a6ce-65dd-4b62-ae8f-93f6ab236b2e.log ) 
                # Habría que meter un control (en el ejemplo facilitado era un problema con el email facilitado)

                self.reference_number = response.css(self.CSS_REQUEST_REFERENCE_NUMBER).get()
                log_trace(self, 'SpiderCirbe', f"Obtenido el numero de referencia: {self.reference_number}")

                # Una vez obtenido el código lo almacenamos
                directory = os.path.join(ROOT_DIR, 'static/flags/cirbe')
                log_trace(self, 'SpiderCirbe', f"Creando fichero testigo: {directory}/{self.reference_number}.txt")
                with open(f'{directory}/{self.reference_number}.txt', 'w') as f:
                    log_trace(self, 'SpiderCirbe', f"Fichero abierto")
                    file_content = f"{datetime.now().strftime('%Y-%m-%d %H:%M')},{self.order['id']},{self.order['person_national_id']},{self.order['person_email']},{self.order['person_birth_date']}"
                    f.write(file_content)
                    log_trace(self, 'SpiderCirbe', f"Fichero escrito")
                    f.close()
                    log_trace(self, 'SpiderCirbe', f"Fichero cerrado")


            else:
                # print('<---- En segunda fase, probamos a descargarlo ------>')
                log_trace(self, 'SpiderCirbe', f"Fase 2: Obtención del documento")
                # Aquí printamos le contenido de la tabla
                cirbe_consult_url = prs.urljoin(self.BASE_URL, selector.xpath(self.XPATH_CIRBE_CONSULT_URL).get())
                # print(cirbe_consult_url)
                log_trace(self, 'SpiderCirbe', f"Llamada para obtener listado de documentos disponibles")
                login_response = request_by_pkcs11(url=cirbe_consult_url,
                                                   dni=self.order['person_national_id'],
                                                   method='GET',
                                                   body=None,
                                                   authorization=None,
                                                   simplec='cirbe',
                                                   decode=False,
                                                   nif=self.order['company_cif'])
                log_html(self, login_response, '4', 'SpiderCirbe', cirbe_consult_url)
                response = scrapy.Selector(text=login_response)

                # Seleccionamos el primer registro de la tabla
                log_trace(self, 'SpiderCirbe', f"Fase 2: Seleccionamos el primer registro de la tabla")
                request_token = response.css(self.CSS_REQUEST_TOKEN).get()
                view_state = response.css(self.CSS_REQUEST_VIEWSTATE).get()
                self.cirbe_consult_form_data['token'] = request_token
                self.cirbe_consult_form_data['javax.faces.ViewState'] = view_state

                log_trace(self, 'SpiderCirbe', f"Seleccionamos primer registro y damos a Descargar")
                login_response = request_by_pkcs11(
                    url=prs.urljoin(self.BASE_URL, response.css('form#form::attr(action)').get()),
                    dni=self.order['person_national_id'],
                    method='POST',
                    body=self.cirbe_consult_form_data,
                    authorization=None,
                    simplec='cirbe',
                    decode=False,
                    nif=self.order['company_cif'])
                # print(login_response)
                log_html(self, login_response, '5', 'SpiderCirbe', 'Pulsado dobre botón Descargar')
                response = scrapy.Selector(text=login_response)

                # Pulsamos a descargar
                log_trace(self, 'SpiderCirbe', f"Fase 2: Pulsamos a descargar")
                request_token = response.css(self.CSS_REQUEST_TOKEN).get()
                view_state = response.css(self.CSS_REQUEST_VIEWSTATE).get()
                self.cirbe_download_form_data['token'] = request_token
                self.cirbe_download_form_data['javax.faces.ViewState'] = view_state
                log_trace(self, 'SpiderCirbe', f"Si el estado es el correcto, pulsamos en descargar")
                login_response = request_by_pkcs11(
                    url=prs.urljoin(self.BASE_URL, response.css('form#form::attr(action)').get()),
                    dni=self.order['person_national_id'],
                    method='POST',
                    body=self.cirbe_download_form_data,
                    authorization=None,
                    simplec='cirbe',
                    decode=False,
                    nif=self.order['company_cif'])
                log_trace(self, 'SpiderCirbe', f"Llamada de descarga realizada")
                log_html(self, login_response, '6', 'SpiderCirbe', 'Descarga de documento Cirbe')
                # print(login_response)
                response = scrapy.Selector(text=login_response)

                # Si el enlace no está disponible, terminamos sin eliminar el txt para que se intente más tarde
                if not response.css(self.CSS_REQUEST_DOWNLOAD_LINK).get():
                    # print('todavía no está disponible')
                    log_trace(self, 'SpiderCirbe', f"Fichero aún no disponible")
                    return

                # Si llega aquí está el fichero y nos lo descargamos
                download_url = prs.urljoin(self.BASE_URL, response.css(self.CSS_REQUEST_DOWNLOAD_LINK).get())
                log_trace(self, 'SpiderCirbe', f"Llamada para descargar fichero preparada")
                login_response = request_by_pkcs11(url=download_url,
                                                   dni=self.order['person_national_id'],
                                                   method='POST',
                                                   body=self.cirbe_download_form_data,
                                                   authorization=None,
                                                   simplec='cirbe',
                                                   decode=False,
                                                   nif=self.order['company_cif'])
                # print(login_response)
                log_trace(self, 'SpiderCirbe', f"Llamada para descargar fichero realizada")
                pdf_data = base64.b64encode(login_response).decode('utf-8')
                log_trace(self, 'SpiderCirbe', f"Preparando subida de fichero")
                set_certificate_doc(order=self.order, doc_data=pdf_data, request_type='cirbe')
                log_trace(self, 'SpiderCirbe', f"Fichero subido")

                # Eliminamos el TXT
                try:
                    log_trace(self, 'SpiderCirbe', f"Iremos a borrar la traza {self.cirbe_txt_file}")
                    os.remove(os.path.join(ROOT_DIR, 'static/flags/cirbe', self.cirbe_txt_file))
                    log_trace(self, 'SpiderCirbe', f"Eliminamos traza txt")

                    log_trace(self, 'SpiderCirbe', f"Marcando como completada la solicitud: {self.order['id']}")
                    data = {
                        'status': CertificateOrderType.STATUS_COMPLETED.value
                    },
                    BackClient.requests(
                        method='post',
                        url=f'{BackClient.URLS["requests"]}{self.order["id"]}/status/',
                        data=data
                    )
                    log_trace(self, 'SpiderCirbe', f"Solicitud marcada como completada")
                except FileNotFoundError:
                    log_trace(self, 'SpiderCirbe', f"Problema eliminando la traza txt. no se encontró el fichero")
                    pass

        except Exception as err:
            #print('1', str(err))
            log_trace(self, 'SpiderCirbe', f"Error en la ejecución: {str(err)}")
            
            #log_trace(self, 'SpiderCirbe', f"Marcando solicitud como cancelada")
            respuesta = set_certificate_status(self.order, str(err), False)
            #log_trace(self, 'SpiderCirbe', f"Cancelación realizada: {respuesta}")

            raise Exception('Error en la obtención del Cirbe')

    # def download_cirbe(self, response):
    #     download_url = prs.urljoin(self.BASE_URL, response.css(self.CSS_REQUEST_DOWNLOAD_LINK).get())
    #     yield Request(url=download_url, method='POST', callback=self.downloaded)
    #
    # def downloaded(self, response):
    #             file_content = response.body
    #             pdf_data = base64.b64encode(file_content)
    #             set_certificate_doc(order=self.order, doc_data=str(pdf_data)[2:-1])

