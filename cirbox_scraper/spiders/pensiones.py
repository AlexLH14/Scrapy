import scrapy
import base64
from scrapy.http.request import Request
from cirbox_scraper.utils import create_certified_session, set_certificate_doc, log_and_save_response, log_trace
from src.apps.certificate_order.enumeration import CertificateOrderType
from src.apps.certificate_order.models.certificate_order_log import CertificateOrderLogModel


class SpiderPensiones(scrapy.Spider):

    name = 'spider_pensiones'
    allowed_domains = ['portal.seg-social.gob.es', 'ipce.seg-social.es', 'sp.seg-social.es']
    handle_httpstatus_list = [301, 302, 303, 403]
    start_urls = ["https://example.com"]

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
    CSS_BASE_URL = 'base::attr(href)'
    CSS_RELAY_STATE = 'input#RelayState::attr(value)'
    CSS_SAML_REQUEST = 'input[name=SAMLRequest]::attr(value)'
    CSS_SAML_RESPONSE = 'input[name=SAMLResponse]::attr(value)'

    def __init__(self, **kwargs):
        self.order = kwargs.get('order')
        self.certified_session = None
        self.session = None
        self.certificate = kwargs.get('certificate')
        self.password = kwargs.get('password')
        super().__init__(**kwargs)
        CertificateOrderLogModel.objects.create(context='__init__',
                                                event=f'Init completado correctamente',
                                                certificate_order=self.order)

    def start_requests(self):
        log_trace(self, 'SpiderPensiones', 'Inicio solicitud')
        try:
            for url in self.start_urls:
                yield Request(
                    url=url,
                    method="GET",
                    callback=self.download_pdf,
                )
        except Exception as err:
            CertificateOrderLogModel.objects.create(context='start_requests',
                                                    event=f'{self.order.status} > '
                                                          f'{CertificateOrderType.ERROR.value}. Motivo: {repr(err)}',
                                                    certificate_order=self.order)
            self.order.register_error(f'SpiderPensiones func start_requests. Error: {repr(err)}')

    def download_pdf(self, response):
        try:
            self.certified_session = create_certified_session(
                password=self.password,
                headers=self.headers,
                pkcs12_data=self.certificate
            )


        except Exception as err:
            CertificateOrderLogModel.objects.create(context='start_requests',
                                                    event=f'{self.order.status} > '
                                                          f'{CertificateOrderType.ERROR.value}. Motivo: {repr(err)}',
                                                    certificate_order=self.order)
            self.order.register_error(f'PensionesSpider func start_requests. Error: {repr(err)}')

    def make_requests(self, method, url, counter, data=None, allow_redirects=None):
        self.logger.info(f'\n\n\n Paso {counter} \n\n\n')
        params = {
            'url': url,
            'headers': self.headers,
            'data': data
        }
        if allow_redirects:
            params.update({'allow_redirects': allow_redirects})
        response = self.session[method](**params)
        CertificateOrderLogModel.objects.create(context='make_requests', event=f'Paso {counter}',
                                                certificate_order=self.order)
        return response
