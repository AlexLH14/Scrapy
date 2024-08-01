import scrapy
import base64

from django.conf import settings
from scrapy.http.request import Request
from cirbox_scraper.utils import create_certified_session, set_certificate_doc, log_and_save_response, log_trace
from src.apps.certificate_order.enumeration import CertificateOrderType
from src.apps.certificate_order.models.certificate_order_log import CertificateOrderLogModel


class SpiderSandbox(scrapy.Spider):
    name = 'sandbox'
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
        CertificateOrderLogModel.objects.create(context='__init__',
                                                event=f'Init completado correctamente',
                                                certificate_order=self.order)

    def start_requests(self):
        log_trace(self, 'SpiderSandbox', 'Inicio solicitud')
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
                    callback=self.do_things,
                )
            CertificateOrderLogModel.objects.create(context='start_requests',
                                                    event=f'start_requests completado correctamente',
                                                    certificate_order=self.order)
        except Exception as err:
            CertificateOrderLogModel.objects.create(context='start_requests',
                                                    event=f'{self.order.status} > '
                                                          f'{CertificateOrderType.ERROR.value}. Motivo: {repr(err)}',
                                                    certificate_order=self.order)
            self.order.register_error(f'VidaLaboralSpider func start_requests. Error: {repr(err)}')

    def do_things(self, response):

        try:

            CertificateOrderLogModel.objects.create(context='do_things',
                                                    event=f'Fase de login 1/6',
                                                    certificate_order=self.order)

            # Obtener del html de respuesta la info del form para enviar formulario con petición de login
            base_url = response.css(self.CSS_BASE_URL).get()
            form_action = response.css('form#P017_login::attr(action)').get()

            fr_response = self.certified_session.post(
                url=base_url + form_action,
                headers=self.login_headers,
                data={'loginFormSubmit': 'ACCESO'},
            )

            CertificateOrderLogModel.objects.create(context='do_things',
                                                    event=f'Fase de login 2/6',
                                                    certificate_order=self.order)

            # Procesando respuesta a solicitud de login, ahora nos manda a la pasarela externa de autenticación
            selector = scrapy.Selector(response=fr_response)
            saml_request = selector.css(self.CSS_SAML_REQUEST).get()
            relay_state = selector.css(self.CSS_RELAY_STATE).get()
            self.login_body['SAMLRequest'] = saml_request
            self.login_body['RelayState'] = relay_state
            self.login_headers['Authorization'] = fr_response.headers['Set-Cookie']
            self.certified_session.post(
                'https://sp.seg-social.es/PGIS/Login',
                headers=self.login_headers,
                data=self.login_body,
            )

            CertificateOrderLogModel.objects.create(context='do_things',
                                                    event=f'Fase de login 3/6',
                                                    certificate_order=self.order)

            # Una vez obtenemos el html de la pasarela de autenticación, invocamos proceso de login con certificado
            login_response = self.certified_session.post(
                'https://sp.seg-social.es/PGIS/Login?seleccion=IPCE',
                headers=self.login_headers,
                data=self.login_body,
            )
            selector = scrapy.Selector(response=login_response)
            saml_request = selector.css(self.CSS_SAML_REQUEST).get()
            relay_state = selector.css(self.CSS_RELAY_STATE).get()
            self.login_body['SAMLRequest'] = saml_request
            self.login_body['RelayState'] = relay_state
            self.login_body.update({'allowLegalPerson': 'true'})

            CertificateOrderLogModel.objects.create(context='do_things',
                                                    event=f'Fase de login 4/6',
                                                    certificate_order=self.order)

            # Invocamos endpoint para login, este ya es el paso final para terminar proceso de autenticación
            login_response = self.certified_session.post(
                'https://ipce.seg-social.es/IPCE/Login',
                headers=self.login_headers,
                data=self.login_body,
                allow_redirects=True
            )

            # Redirección postlogin
            selector = scrapy.Selector(response=login_response)
            login_body = dict()
            login_body['SAMLResponse'] = selector.css('input[name=SAMLResponse]::attr(value)').get()
            login_body['RelayState'] = selector.css(self.CSS_RELAY_STATE).get()
            form_action = selector.css('form#redirectForm::attr(action)').get()

            CertificateOrderLogModel.objects.create(context='do_things',
                                                    event=f'Fase de login 5/6',
                                                    certificate_order=self.order)

            login_response = self.certified_session.post(
                form_action,
                headers=self.login_headers,
                data=login_body,
                allow_redirects=True
            )

            # Redirección postlogin (sí, es otra redirección, tiene que ser el mismo código otra vez)
            selector = scrapy.Selector(response=login_response)
            login_body = dict()
            login_body['SAMLResponse'] = selector.css('input[name=SAMLResponse]::attr(value)').get()
            login_body['RelayState'] = selector.css(self.CSS_RELAY_STATE).get()
            form_action = selector.css('form#redirectForm::attr(action)').get()

            CertificateOrderLogModel.objects.create(context='do_things',
                                                    event=f'Fase de login 6/6',
                                                    certificate_order=self.order)

            self.certified_session.post(
                form_action,
                headers=self.login_headers,
                data=login_body,
                allow_redirects=True
            )

            CertificateOrderLogModel.objects.create(context='do_things',
                                                    event=f'Login completando, accediendo a la ficha de vida laboral',
                                                    certificate_order=self.order)

            # En este punto ya hemos hecho login
            login_response = self.certified_session.get(
                'https://portal.seg-social.gob.es/wps/myportal/importass/importass/tramites/datosvidalaboral',
                headers=self.login_headers,
            )

            # Se obtiene el enlace completo al PDF
            selector = scrapy.Selector(response=login_response)
            base_url = selector.css(self.CSS_BASE_URL).get()
            relative_pdf_url = selector.css('button[value=AC_DESC_VIDA_LABORAL]::attr(onclick)').get()
            try:
                relative_pdf_url = relative_pdf_url.split('"')[1]
            except Exception as err:
                # Si no se devuelve ningún documento se sube uno vacío
                file_content = open(f'{settings.ROOT_DIR}/assets/modelo_informe_no_disponible.pdf', 'rb').read()
                pdf_data = base64.b64encode(file_content)
                set_certificate_doc(order=self.order, doc_data=str(pdf_data)[2:-1])
                self.order.register_success()
                CertificateOrderLogModel.objects.create(context='spider VidaLaboral',
                                                        event=f'Subido modelo pdf "documento no encontrado"'
                                                              f' correctamente',
                                                        certificate_order=self.order)
                return

            CertificateOrderLogModel.objects.create(context='do_things',
                                                    event=f'Descargando PDF...',
                                                    certificate_order=self.order)

            login_response = self.certified_session.get(
                base_url + relative_pdf_url,
                headers=self.login_headers,
            )

            pdf_data = base64.b64encode(login_response.content)
            set_certificate_doc(order=self.order, doc_data=str(pdf_data)[2:-1])

            CertificateOrderLogModel.objects.create(context='do_things',
                                                    event=f'PDF enviado a api-cirbox correctamente. '
                                                          f'{self.order.status} > '
                                                          f'{CertificateOrderType.COMPLETADO.value}',
                                                    certificate_order=self.order)
            self.order.register_success()

        except Exception as err:
            CertificateOrderLogModel.objects.create(context='do_things',
                                                    event=f'Error: {repr(err)}',
                                                    extra_info=f'{self.order.status} > '
                                                               f'{CertificateOrderType.ERROR.value}.',
                                                    certificate_order=self.order)
            self.order.register_error(f'VidaLaboralSpider func do_things. Error: {repr(err)}')


