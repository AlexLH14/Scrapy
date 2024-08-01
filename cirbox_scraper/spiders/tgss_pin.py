import base64
import os
import traceback
from urllib.parse import urljoin

import scrapy
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.cache import cache
from django.shortcuts import redirect

from cirbox_scraper.utils import set_certificate_doc, set_certificate_status, log_and_save_response, log_trace


class SpiderTGSSPin(scrapy.Spider):
    name = 'seg_social_gob_es_pin'
    allowed_domains = ['portal.seg-social.gob.es', 'ipce.seg-social.es', 'sp.seg-social.es']
    handle_httpstatus_list = [301, 302, 303, 403]
    custom_settings = {
        'SPIDER_MIDDLEWARES': {'scrapy.downloadermiddlewares.cookies.CookiesMiddleware': 450}
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
        self.otp = kwargs.get('otp')
        self.session = None
        self.code = None

        self.filename = f'{self.order["person_national_id"]}.html'
        self.output_dir = os.path.join(settings.STATIC_ROOT, "debug_response", "tgss")
        super().__init__(**kwargs)

    def start_requests(self):
        log_trace(self, 'SpiderTGSSPin', 'Iniciando procesado TGSS Pin')
        try:
            log_trace(self, 'SpiderTGSSPin', 'Obteniendo información de cache')
            cached_data = cache.get(self.order['id'])

            log_trace(self, 'SpiderTGSSPin', f"Documento subido")  

        except Exception as err:
            log_trace(self, 'SpiderTGSSPin', f"Se ha producido un error en el procesado de la solicitud: {str(err)}")  
            data = {'isError': True}
            if self.order and self.order['return_url']:
                if 'La combinacion Código/PIN introducida es incorrecta' in str(err):
                    data = {'isError': True, 'reason': 'error_pin'}
                elif 'El PIN solicitado ha sido utilizado o ha expirado' in str(err):
                    data = {'isError': True, 'reason': 'error_time_out'}
                else:
                    data = {'isError': True, 'reason': 'error_administraciones_publicas'}

            log_trace(self, 'SpiderTGSSPin', f"Almacenando en caché mensajes de error")  
            cache.set(self.order['id'], data, 3600)
            log_trace(self, 'SpiderTGSSPin', 'Almacenando mensaje de error en la solicitud')  
            set_certificate_status(self.order, str(err))
            log_trace(self, 'SpiderTGSSPin', 'Mensaje de error almacenado en la solicitud')  

    def get_default_pdf(self, request_type):
        log_trace(self, 'SpiderTGSSPin', 'Iniciando función de grabación de documento por defecto')
        file_content = open(f'{settings.ROOT_DIR}/assets/modelo_informe_no_disponible.pdf', 'rb').read()
        log_trace(self, 'SpiderTGSSPin', 'Leyendo fichero')
        pdf_data = base64.b64encode(file_content)
        log_trace(self, 'SpiderTGSSPin', 'Codificando base64')
        set_certificate_doc(order=self.order, doc_data=str(pdf_data)[2:-1], request_type=request_type)
        log_trace(self, 'SpiderTGSSPin', 'Subiendo el fichero asociado a la solicitud')

    def review_authenticate(self, response):
        log_trace(self, 'SpiderTGSSPin', 'Verificando si seguimos autenticados')
        # Buscar todos los scripts en la página
        soup = BeautifulSoup(response.text, 'html.parser')
        scripts = soup.find_all('script')

        # Iterar sobre los scripts para buscar el que contiene la variable dataLayer
        for script_tag in scripts:
            # Obtener el contenido del script
            script_content = script_tag.string
            
            # Verificar si la cadena 'dataLayer' está contenida en el contenido del script
            if script_content and 'dataLayer' in script_content:
                # Verificar si la cadena 'authenticated":"true"' está contenida en el contenido del script
                if 'authenticated":"true"' in script_content:
                    log_trace(self, 'SpiderTGSSPin', 'Usuario Identificado')
                    return True
                else:
                    log_trace(self, 'SpiderTGSSPin', 'Aparente problema de autenticación (1) al no encontrar el authenticated:true')
                    return False
                # Si encuentras la variable dataLayer, puedes detener el bucle, ya que ya has encontrado lo que buscabas
                break
        else:
            log_trace(self, 'SpiderTGSSPin', 'Aparente problema de autenticación (2) al no encontrar el authenticated:true')
        
        return False
