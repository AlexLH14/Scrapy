import json
import requests
import scrapy
import urllib.parse as prs
from pathlib import Path
from requests_pkcs12 import Pkcs12Adapter
from requests_toolbelt.adapters.x509 import X509Adapter
from scrapy.http import FormRequest
from scrapy.http.request import Request
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
from cirbox_scraper.utils import create_certified_session


class SpiderVidaLaboral(scrapy.Spider):
    name = 'seg_social_gob_es'
    allowed_domains = ['portal.seg-social.gob.es']
    handle_httpstatus_list = [301, 302, 303, 403]
    start_urls = [
        'https://portal.seg-social.gob.es/wps/portal/importass/!ut/p/z0/'
        '04_Sj9CPykssy0xPLMnMz0vMAfIj8nKt8jNTrMoLivV88tMz8_QLsh0VAZSk7Xs!/'
    ]
    custom_settings = {
        'SPIDER_MIDDLEWARES': {'scrapy.downloadermiddlewares.cookies.CookiesMiddleware': 450}
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36 Edg/97.0.1072.55'
    }

    start_login_body = {'loginFormSubmit': 'ACCESO_CERTIFICADO'}
    login_body = {'SAMLRequest': '', 'RelayState': ''}

    login_headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,'\
            'image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '\
            '(KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36 Edg/97.0.1072.55'
    }

    # URLs and templates
    LOGIN_URL = 'https://portal.seg-social.gob.es/wps/portal/importass/!ut/p/z1/04_Sj9CPykssy0xPLMnMz0vMAfIjo8ziDVCAo4FTkJGTsYGBu7OJfjgWBchK9aMI6Y_Cq8TCAKsCFCuCU_P0C3IjDLJMHBUB8IMRIQ!!/p0/IZ7_J0M2HA42PG6M80QLMJ7L3S3000=CZ6_00000000000000A0BR2B300GC4=LA0=/?loginFormSubmit=LOGIN'
    LOGIN_URL = 'https://w2.seg-social.es/IPCE/Login'

    CSS_BASE_URL = 'base::attr(href)'
    CSS_CERTIFICATE_ACCESS_FORM = 'form#P017_login2::attr(action)'
    CSS_RELAY_STATE = 'input#RelayState::attr(value)'
    CSS_SAML_REQUEST = 'input[name=SAMLRequest]::attr(value)'

    def start_requests(self):
        self.custom_settings['REQUEST_ID'] = self.settings.attributes['REQUEST_ID']
        for url in self.start_urls:
            yield Request(
                url=url,
                method='GET',
                callback=self.send_certificate,
            )

    def send_certificate(self, response):
        # ? Extract or define needed data for following requests
        base_url = response.css(self.CSS_BASE_URL).get()
        form_action = response.css(self.CSS_CERTIFICATE_ACCESS_FORM).get()
        # yield FormRequest(
        #     url=base_url + form_action,
        #     formdata=self.start_login_body,
        #     callback=self.make_login,
        # )
        cert = (
            'cirbox_scraper/certificates/50107654s/50107654s.cert',
            'cirbox_scraper/certificates/50107654s/50107654s.key'
        )

        # * Using http.client to make connection and openssl context
        # ? First load certificate data
        # certificate_file = f'cirbox_scraper/certificates/'\
        #     f'{self.custom_settings["REQUEST_ID"].value}/key_cert.pem'
        # certificate_pass = '50107654s'
        # host = prs.urlparse(response.url).hostname
        # url = prs.urlparse(base_url+form_action).path
        # context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        # context.load_cert_chain(certfile=certificate_file, password=certificate_pass)

        # connection = http.client.HTTPSConnection(host, port=443, context=context)
        # connection.request(method='POST', url=url, body=json.dumps(self.extract_relay_state_body))
        # response = connection.getresponse()
        # print(response.status, response.reason)
        # print(response.headers['Location'])
        # response_text = response.read()
        # print()

        # * Using requests.Session() object with X509Adapter
        certified_session = create_certified_session(
            self.custom_settings['REQUEST_ID'].value,
            password=self.custom_settings['REQUEST_ID'].value,
            headers=response.headers.to_unicode_dict()
        )
        fr_response = certified_session.post(
            url=base_url + form_action,
            headers=self.login_headers,
            data=self.start_login_body,
            # cert=cert
            # verify='cirbox_scraper/certificates/50107654s/50107654s_publickey.pem'
        )
        # print(fr_response.headers)

        # ? Handle request to base_url + form_action
        selector = scrapy.Selector(response=fr_response)
        saml_request = selector.css(self.CSS_SAML_REQUEST).get()
        relay_state = selector.css(self.CSS_RELAY_STATE).get()
        # self.logger.info(f'[!] SAMLRequest: {saml_request}')
        # self.logger.info(f'[!] RelayState: {relay_state}')
        self.login_body['SAMLRequest'] = saml_request
        self.login_body['RelayState'] = relay_state

        # ? Make login POST request using Session object
        # ? with saml_request and relay_state variables on body
        # self.logger.info(f'[!] Login body: {self.login_body}')
        # self.login_headers['Authorization'] = fr_response.headers['Set-Cookie']
        login_response = certified_session.post(
            self.LOGIN_URL,
            headers=self.login_headers,
            data=self.login_body,
            # verify='cirbox_scraper/certificates/verification.pem',
            # cert=cert
        )
        # print(login_response.headers)
        print(login_response.text)
        # ? Make login POST request using Scrapy FormRequest
        # yield FormRequest(
        #     url=self.LOGIN_URL,
        #     callback=self.logged,
        #     formdata=self.login_body,
        #     dont_filter=True
        # )

        # print(login_response.history)
        # yield Request(
        #     url = self.LOGIN_URL,
        #     method='POST',
        #     callback=self.logged,
        #     body=json.dumps(self.login_body),
        #     dont_filter=True
        # )

    def make_login(self, response):
        # ? Handle request to base_url + form_action
        selector = scrapy.Selector(response=response)
        saml_request = selector.css(self.CSS_SAML_REQUEST).get()
        relay_state = selector.css(self.CSS_RELAY_STATE).get()
        self.logger.info(f'[!] SAMLRequest: {saml_request}')
        self.logger.info(f'[!] RelayState: {relay_state}')
        self.login_body['SAMLRequest'] = saml_request
        self.login_body['RelayState'] = relay_state
        yield FormRequest.from_response(
            response=response,
            url=self.LOGIN_URL,
            callback=self.logged,
            body=json.dumps(self.login_body),
            dont_filter=True
        )

    def logged(self, response):
        if response.status == 200:
            print('logged')
        else:
            print(response.text)
