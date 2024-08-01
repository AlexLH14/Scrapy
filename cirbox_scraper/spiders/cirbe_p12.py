import scrapy
import base64
import urllib.parse as prs
from scrapy.http import FormRequest
from scrapy.http.request import Request
from cirbox_scraper.utils import create_certified_session, set_certificate_doc
from rest_framework import status
from src.apps.certificate_order.enumeration import CertificateOrderType
from src.apps.certificate_order.models.certificate_order_log import CertificateOrderLogModel


class SpiderCirbe(scrapy.Spider):

    """ApsBdeEsSpider extracts CIRBE report from aps.bde.es website
    """
    name = "aps_bde_es_cirbe_p12"
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

    def __init__(
        self,
        name=None,
        request_id=None,
        **kwargs
    ):
        self.request_id = request_id
        self.order = kwargs.get('order')
        self.certificate = kwargs.get('certificate')
        self.password = kwargs.get('password')
        self.birthdate = self.order.extra_info['birthdate']
        self.email = self.order.extra_info['email']
        self.reference_number = self.order.extra_info.get('reference_number')
        super().__init__(name, **kwargs)

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
                    method="GET",
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
            self.order.register_error(f'CirbeSpider func start_requests. Error: {repr(err)}')

    def main_menu(self, response):
        try:
            CertificateOrderLogModel.objects.create(context='spider CIRBE',
                                                    event='Login realizado correctamente',
                                                    certificate_order=self.order)
            # ? Generate login response for CIRBE
            login_response = self.certified_session.get(
                self.cirbe_start_urls[0], allow_redirects=True
            )
            login_response = self.certified_session.get(
                self.cirbe_start_urls[-1], allow_redirects=True
            )
            selector = scrapy.Selector(text=login_response.text)
            # ? Determine if the document has been requested
            if not self.reference_number:
                CertificateOrderLogModel.objects.create(context='spider CIRBE',
                                                        event=f'No tiene número de referencia, se inicia fase 1',
                                                        certificate_order=self.order)
                cirbe_request_url = prs.urljoin(
                    self.BASE_URL, selector.xpath(self.XPATH_CIRBE_REQUEST_URL).get()
                )
                yield Request(
                    url=cirbe_request_url,
                    callback=self.generate_cirbe_request,
                    cookies={k: v for k, v in self.certified_session.cookies.items()},
                    dont_filter=True,
                )
            else:
                CertificateOrderLogModel.objects.create(context='spider CIRBE',
                                                        event=f'Tiene número de referencia, se inicia fase 2',
                                                        certificate_order=self.order)
                # ? Once the document is requested we can try to donwload it
                cirbe_consult_url = prs.urljoin(
                    self.BASE_URL, selector.xpath(self.XPATH_CIRBE_CONSULT_URL).get()
                )
                yield Request(
                    url=cirbe_consult_url,
                    callback=self.consult_cirbe_request,
                    cookies={k: v for k, v in self.certified_session.cookies.items()},
                    dont_filter=True,
                )
        except Exception as err:
            CertificateOrderLogModel.objects.create(context='CirbeSpider func set_certificate_doc (5).',
                                                    event=f'Error: {repr(err)}',
                                                    extra_info=f'{self.order.status} > '
                                                               f'{CertificateOrderType.ERROR.value}.',
                                                    certificate_order=self.order)
            self.order.register_error(f'CirbeSpider func set_certificate_doc (5). Error: {repr(err)}')

    def generate_cirbe_request(self, response):
        CertificateOrderLogModel.objects.create(context='CirbeSpider func generate_cirbe_request.',
                                                event=f'Generando solicitud a cirbe',
                                                certificate_order=self.order)
        request_token = response.css(self.CSS_REQUEST_TOKEN).get()
        view_state = response.css(self.CSS_REQUEST_VIEWSTATE).get()
        # ? Fill data for the request form
        self.cirbe_request_form_data["token"] = request_token
        self.cirbe_request_form_data["javax.faces.ViewState"] = view_state
        # ? Birth date should be in the initial data of the request
        self.cirbe_request_form_data["form:CajaParaFechaNacimiento"] = self.birthdate
        self.cirbe_request_form_data[
            "form:CajaDeTextoCorreoElectronico"
        ] = self.email
        yield FormRequest.from_response(
            response=response,
            callback=self.request_generated,
            formdata=self.cirbe_request_form_data,
        )

    def consult_cirbe_request(self, response):
        download_page = response.meta.get('download_page', False)
        # form_action = 'form#form::attr(action)'
        if download_page:
            CertificateOrderLogModel.objects.create(context='CirbeSpider func consult_cirbe_request',
                                                    event=f'Seleccionando detalle del informe',
                                                    certificate_order=self.order)
            self.logger.info(f'[!] Selecting detailed report...')
            request_token = response.css(self.CSS_REQUEST_TOKEN).get()
            view_state = response.css(self.CSS_REQUEST_VIEWSTATE).get()
            self.cirbe_download_form_data['token'] = request_token
            self.cirbe_download_form_data['javax.faces.ViewState'] = view_state
            form_action = response.css('form#form::attr(action)').get()
            yield FormRequest(
                url=prs.urljoin(self.BASE_URL, form_action),
                callback=self.download_cirbe,
                formdata=self.cirbe_download_form_data
            )
        else:
            CertificateOrderLogModel.objects.create(context='CirbeSpider func consult_cirbe_request',
                                                    event=f'Solicitando descarga de PDF',
                                                    certificate_order=self.order)
            self.logger.info(f'[!] Listing requests...')
            request_token = response.css(self.CSS_REQUEST_TOKEN).get()
            view_state = response.css(self.CSS_REQUEST_VIEWSTATE).get()
            self.cirbe_consult_form_data['token'] = request_token
            self.cirbe_consult_form_data['javax.faces.ViewState'] = view_state
            yield FormRequest(
                url=prs.urljoin(self.BASE_URL, response.css('form#form::attr(action)').get()),
                callback=self.consult_cirbe_request,
                formdata=self.cirbe_consult_form_data,
                meta={'download_page': True}
            )

    def request_generated(self, response):
        # * We need to save reference number for when the document is ready we can download it
        CertificateOrderLogModel.objects.create(context='CirbeSpider func request_generated',
                                                event=f'Almacenando en la solicitud el reference_number',
                                                certificate_order=self.order)
        reference_number = response.css(self.CSS_REQUEST_REFERENCE_NUMBER).get()
        self.order.extra_info.update({'reference_number': reference_number})
        self.order.status = CertificateOrderType.PENDIENTE.value
        self.order.save()
        CertificateOrderLogModel.objects.create(context='CirbeSpider func request_generated',
                                                event=f'Fase 1 completada correctamente, se finaliza el proceso',
                                                certificate_order=self.order)
        return None

    def download_cirbe(self, response):
        CertificateOrderLogModel.objects.create(context='CirbeSpider func download_cirbe',
                                                event=f'Descargando cirbe',
                                                certificate_order=self.order)
        if not response.css(self.CSS_REQUEST_DOWNLOAD_LINK).get():
            self.order.still_waiting()
            return
        download_url = prs.urljoin(self.BASE_URL, response.css(self.CSS_REQUEST_DOWNLOAD_LINK).get())
        yield Request(url=download_url, method='POST', callback=self.downloaded)
        CertificateOrderLogModel.objects.create(context='CirbeSpider func download_cirbe',
                                                event=f'Cirbe descargado',
                                                certificate_order=self.order)

    def downloaded(self, response):
        CertificateOrderLogModel.objects.create(context='CirbeSpider func downloaded',
                                                event=f'Dentro de la función downloaded',
                                                certificate_order=self.order)
        if response.status != status.HTTP_200_OK:
            CertificateOrderLogModel.objects.create(context='CirbeSpider func downloaded',
                                                    event=f'CIRBE no disponible, se marca la petición como '
                                                          f'{CertificateOrderType.PENDIENTE.value}',
                                                    certificate_order=self.order)
            self.order.status = CertificateOrderType.PENDIENTE.value
            self.order.save()
        else:
            try:
                CertificateOrderLogModel.objects.create(context='CirbeSpider func downloaded',
                                                        event=f'CIRBE PDF descargado, enviando al back',
                                                        certificate_order=self.order)
                file_content = response.body
                pdf_data = base64.b64encode(file_content)
                set_certificate_doc(order=self.order, doc_data=str(pdf_data)[2:-1])
                CertificateOrderLogModel.objects.create(context='CirbeSpider func downloaded',
                                                        event=f'CIRBE PDF enviado al back',
                                                        extra_info=f'{self.order.status} > '
                                                                   f'{CertificateOrderType.COMPLETADO.value}',
                                                        certificate_order=self.order)
                self.order.register_success()
            except Exception as err:
                CertificateOrderLogModel.objects.create(context='CirbeSpider func downloaded',
                                                        event=f'Err: {repr(err)}',
                                                        extra_info=f'{self.order.status} > '
                                                                   f'{CertificateOrderType.ERROR.value}',
                                                        certificate_order=self.order)
                self.order.register_error(f'CirbeSpider func downloaded. '
                                          f'Error: {repr(err)}')
