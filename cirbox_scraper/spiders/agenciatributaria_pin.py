import base64
import os
import re
import time
from datetime import date
from random import randint
from urllib.parse import urljoin

import scrapy
from django.conf import settings
from django.core.cache import cache
from django.shortcuts import redirect

from cirbox_scraper.utils import set_certificate_doc, set_certificate_status, log_and_save_response, log_trace, log_html
from src.utils.back_client import BackClient


class SpiderAgenciaTributariaPin(scrapy.Spider):
    name = 'agenciatributaria_gob_es_pin'
    allowed_domains = ['agenciatributaria.gob.es']
    custom_settings = {
        "SPIDER_MIDDLEWARES": {
            "scrapy.downloadermiddlewares.cookies.CookiesMiddleware": 450
        }
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36 Edg/97.0.1072.55"
    }

    CSS_CLASGTE = 'input#CLASGTE::attr(value)'
    CSS_QUERY_RESULTS = 'table#GESTOR > tbody > tr[id]'
    CSS_QUERY_RESULT_DOWNLOAD_LINK = 'table#GESTOR > tbody > tr[id] > td:last-child > ' \
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
        self.order = kwargs.get('order')
        self.otp = kwargs.get('otp')
        self.session = None
        self.code = None

        self.filename = f'{self.order["person_national_id"]}.html'
        self.output_dir = os.path.join(settings.STATIC_ROOT, "debug_response", 'agency')
        super().__init__(**kwargs)

        self.renta_query_form_data = {
            "FNIFOBLIGADO": self.order["person_national_id"],
            "FNOMBRE": '',
            "MODELO": '',
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

    def start_requests(self):
        log_trace(self, 'SpiderAgenciaTributariaPin', 'Inicio solicitud')
        try:

            cached_data = cache.get(self.order['id'])

        except Exception as err:
            log_trace(self, 'SpiderAgenciaTributariaPin', f"Error en la ejecución {str(err)} ")
            data = {'isError': True}
            log_trace(self, 'SpiderAgenciaTributariaPin', f"Procesando la gestión de error")
            if self.order and self.order['return_url']:
                log_trace(self, 'SpiderAgenciaTributariaPin', f"El error se gestionará teniendo en cuenta que se definió una return_url ")
                if 'La combinacion Código/PIN introducida es incorrecta' in str(err):
                    log_trace(self, 'SpiderAgenciaTributariaPin', f"Error 'La combinación Codigo/PIN no es correcta' identificado ")
                    data = {'isError': True, 'reason': 'error_pin'}
                elif 'El PIN solicitado ha sido utilizado o ha expirado' in str(err):
                    log_trace(self, 'SpiderAgenciaTributariaPin', f"Error 'Pin utilizado o caducado' identificado ")
                    data = {'isError': True, 'reason': 'error_time_out'}
                else:
                    log_trace(self, 'SpiderAgenciaTributariaPin', f"Error genérico al no identificar uno específico")
                    data = {'isError': True, 'reason': 'error_administraciones_publicas'}

            cache.set(self.order['id'], data, 3600)
            log_trace(self, 'SpiderAgenciaTributariaPin', f"Procedemos a cancelar la solicitud")
            set_certificate_status(self.order, str(err))
            log_trace(self, 'SpiderAgenciaTributariaPin', f"Solicitud cancelada ")

    def get_document(self, modelo, request_type):
        log_trace(self, 'SpiderAgenciaTributariaPin', f"Entrando en la funcion get_document() ")
        year = date.today().year
        formdata = self.renta_query_form_data.copy()
        formdata['FEJERCICIO'] = str(year)
        formdata['MODELO'] = modelo

        log_trace(self, 'SpiderAgenciaTributariaPin', f"Buscando documentos en AEAT para el año {year} para el modelo {modelo} ")
        query_response = self.session.post(
            url=f'https://www6.agenciatributaria.gob.es/wlpl/SCEJ-MANT/CONSUL/index.zul? \ '
                f'MODELO={modelo}&EJERCICIO={year}&NIFOBLIGADO={self.order["person_national_id"]}',
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'x-site': 'Sede',
                'X-XSS-Protection': '1; mode=block'
            },
            data=formdata
        )
        log_trace(self, 'SpiderAgenciaTributariaPin', f"Llamada realizada ")
        log_and_save_response(self, query_response, f'2_Modelo{modelo}', 'Main Content load')

        i = 0

        while True:
            log_trace(self, 'SpiderAgenciaTributariaPin', f"Iniciando vuelta en el bucle de procesado")
            log_trace(self, 'SpiderAgenciaTributariaPin', f"Acceso a AEAT")
            self.session.get('https://sede.agenciatributaria.gob.es/Sede/inicio.html?id=www6')
            time_ms = int(time.time() * 1000)
            log_trace(self, 'SpiderAgenciaTributariaPin', f"Lllamada de mantenimiento de 'activo'")
            url = f'https://www6.agenciatributaria.gob.es/activo?_={time_ms}'
            self.session.get(url, headers={'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'cors',
                                           'Sec-Fetch-Site': 'same-origin', 'X-Requested-With': 'XMLHttpRequest'})

            content = query_response.text.replace("\n", "").replace("\t", "")
            id_matches = re.findall(r"dt:'(.*?)',cu", content)
            log_trace(self, 'SpiderAgenciaTributariaPin', f"Buscando identificadores en la respuesta  ")
            if id_matches:
                log_trace(self, 'SpiderAgenciaTributariaPin', f"ID encontrado")
                dtid = id_matches[0]
                dtid = dtid.encode().decode('unicode_escape')
            else:
                log_trace(self, 'SpiderAgenciaTributariaPin', f"ID no encontrado ")
                if 'La petición de autenticación con Cl@ve Móvil ha caducado' in query_response.text:
                    log_trace(self, 'SpiderAgenciaTributariaPin', f"Error identificado como 'petición de autenticación caducada' ")
                    raise Exception('La petición de autenticación con Cl@ve Móvil ha caducado')
                else:
                    log_trace(self, 'SpiderAgenciaTributariaPin', f"Error no identificado y devolvemos motivo genérico de 'ID no encontrado' ")
                    raise Exception('ID no encontrado en el contenido HTML')

            button_matches = re.search(r"zul\.wgt\.Button','(.*?)',{\$onClick:true,prolog:' ',label:'Buscar'",
                                       content).group(1)
            log_trace(self, 'SpiderAgenciaTributariaPin', f"Buscando boton de accion")
            if button_matches:
                log_trace(self, 'SpiderAgenciaTributariaPin', f"Boton encontrado ")
                words = f"""{button_matches}""".split("','")
                button_id = words[-1].strip()
            else:
                log_trace(self, 'SpiderAgenciaTributariaPin', f"Boton no encontrado, devolviendo error genérico de 'Solicitud no viable en Clave' ")
                raise Exception('Solicitud no viable en CLAVE')

            time_ms += 1

            log_trace(self, 'SpiderAgenciaTributariaPin', f"Llamada para mantener activo")
            url = f'https://www6.agenciatributaria.gob.es/activo?_={time_ms}'
            self.session.get(url, headers={'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'cors',
                                           'Sec-Fetch-Site': 'same-origin', 'X-Requested-With': 'XMLHttpRequest'})
            zk_sid = randint(100, 9999)

            url = 'https://www6.agenciatributaria.gob.es/wlpl/SCEJ-MANT/zkau'
            log_trace(self, 'SpiderAgenciaTributariaPin', f"Llamada a {url} ")
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
                'Connection': 'keep-alive',
                'Origin': 'null',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': "1",
            }

            data = {
                'cmd_0': 'onClick',
                'data_0': '{"pageX":767,"pageY":313,"which":1,"x":33,"y":11}',
                'dtid': dtid,
                'uuid_0': button_id,
            }

            response = self.session.post(url, headers=headers, data=data)
            log_trace(self, 'SpiderAgenciaTributariaPin', f"Llamada ejeuctada ")
            log_and_save_response(self, response, f'3_Modelo{modelo}', f'Zkau response data: {data}')

            content = response.text.replace("\n", "")
            content = content.replace("\t", "")

            if '"redirect",["https:\/\/www6.agenciatributaria.gob.es\/static_files\/common\/internet\/dep\/aplicaciones\/zk65\/pages\/timeout.html",""]]]' in content:
                log_trace(self, 'SpiderAgenciaTributariaPin', f"Redirigido por la AEAT a página con mensaje sobre la caducidad de la autenticación de la solicitud ")
                raise Exception('Tiempo máximo de espera excedido para tramitar la solicitud de Cl@vePin. Deberá '
                                'tramitar una nueva solicitud')

            doc_id = ''
            if request_type == 'modelo_303':
                log_trace(self, 'SpiderAgenciaTributariaPin', f"Procesando 303 y buscando botones para download documentos ")
                # get the document lists
                list_item_matches = re.findall(r"\[\['zul\.sel\.Listitem',\s*(.*?)\s*]]]]]]", content, re.DOTALL)
                if list_item_matches and len(list_item_matches) >= 1:
                    log_trace(self, 'SpiderAgenciaTributariaPin', f"Botones localizados ")
                    last_list_item = list_item_matches[-1]

                    # find the first button for downloading document
                    doc_id_matches = re.search(r"zul\.wgt\.Button','(.*?)',{\$onClick:true,prolog:' ',label:'Ver'",
                                               last_list_item)
                    log_trace(self, 'SpiderAgenciaTributariaPin', f"Localizando el primer boton")
                    if doc_id_matches and len(doc_id_matches.group(1)) >= 1:
                        log_trace(self, 'SpiderAgenciaTributariaPin', f"Boton encontrado ")
                        words = f"""{doc_id_matches.group(1)}""".split("','")
                        doc_id = words[-1].strip()
                    else:
                        log_trace(self, 'SpiderAgenciaTributariaPin', f"Boton no encontrado ")
            else:
                log_trace(self, 'SpiderAgenciaTributariaPin', f"Procesando un modelo diferente al 303 y buscando el botón de descarga ")
                doc_id_matches = re.search(r"zul\.wgt\.Button','(.*?)',{\$onClick:true,prolog:' ',label:'Ver'",
                                           content)
                if doc_id_matches and len(doc_id_matches.group(1)) >= 1:
                    log_trace(self, 'SpiderAgenciaTributariaPin', f"Boton localizado")
                    words = f"""{doc_id_matches.group(1)}""".split("','")
                    doc_id = words[-1].strip()

            if doc_id:
                log_trace(self, 'SpiderAgenciaTributariaPin', f"Datos del documento recopilados (incluyendo doc_id), así que salgo del bucle de búsqueda")

                break
            else:
                log_trace(self, 'SpiderAgenciaTributariaPin', f"no se localizó el botón de descarga así que se busca en un año anterior")
                time_ms += 1
                year -= 1
                url = f'https://www6.agenciatributaria.gob.es/activo?_={time_ms}'
                log_trace(self, 'SpiderAgenciaTributariaPin', f"Llamando para mantener activo {url} ")
                self.session.get(url, headers={'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'cors',
                                               'Sec-Fetch-Site': 'same-origin',
                                               'X-Requested-With': 'XMLHttpRequest'})

                log_trace(self, 'SpiderAgenciaTributariaPin', f"Llamando a {url} ")
                url = 'https://www6.agenciatributaria.gob.es/wlpl/SCEJ-MANT/zkau'
                headers = {
                    'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                    'Sec-Fetch-Dest': 'empty',
                    'Sec-Fetch-Mode': 'no-cors',
                    'Sec-Fetch-Site': 'same-origin'
                }
                data = {
                    'cmd_0': 'rmDesktop',
                    'dtid': dtid,
                    'opt_0': 'i'
                }
                self.session.post(url, headers=headers, data=data)
                log_trace(self, 'SpiderAgenciaTributariaPin', f"Llamanda ejecutada ")

                formdata = self.renta_query_form_data.copy()
                formdata['FEJERCICIO'] = str(year)
                formdata['MODELO'] = modelo

                log_trace(self, 'SpiderAgenciaTributariaPin', f"LRealizando llamada para otra busqueda {str(year)} ")
                query_response = self.session.post(
                    url=f'https://www6.agenciatributaria.gob.es/wlpl/SCEJ-MANT/CONSUL/index.zul? \ '
                        f'MODELO={modelo}&EJERCICIO={year}&NIFOBLIGADO={self.order["person_national_id"]}',
                    headers={
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'x-site': 'Sede',
                        'X-XSS-Protection': '1; mode=block'
                    },
                    data=formdata
                )
                log_trace(self, 'SpiderAgenciaTributariaPin', f"Llamada ejecutada ")
                log_and_save_response(self, query_response, f'4_Modelo{modelo}', f'Query response with {year}')

                i += 1
            if i == 5:
                log_trace(self, 'SpiderAgenciaTributariaPin', f"Se han superado los 5 intentos en 5 años diferentes ")
                try:
                    log_trace(self, 'SpiderAgenciaTributariaPin', f"Subiendo documento por defecto ")
                    # Si no se devuelve ningún documento se sube uno vacío
                    file_content = open(f'{settings.ROOT_DIR}/assets/modelo_informe_no_disponible.pdf', 'rb').read()
                    pdf_data = base64.b64encode(file_content)
                    set_certificate_doc(order=self.order, doc_data=str(pdf_data)[2:-1],
                                        request_type=request_type)
                    log_trace(self, 'SpiderAgenciaTributariaPin', f"docuento por defecto subido")
                except Exception as err:
                    log_trace(self, 'SpiderAgenciaTributariaPin', f"Problema al subir el documento por defecto {str(err)} ")
                    print(err)
                return

        log_trace(self, 'SpiderAgenciaTributariaPin', f"Saliendo de función get_document()")
        return time_ms, zk_sid, dtid, doc_id

    def download_document(self, time_ms, zk_sid, dtid, doc_id, request_type):
        log_trace(self, 'SpiderAgenciaTributariaPin', f"Entrando en función download_document()")

        url = 'https://www6.agenciatributaria.gob.es/wlpl/SCEJ-MANT/zkau/onClick/Ver'
        log_trace(self, 'SpiderAgenciaTributariaPin', f"Preparando llamada {url} ")
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
            'ZK-SID': str(zk_sid + 1),
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        }
        post_data = {
            'cmd_0': 'onClick',
            'data_0': '{"pageX":683,"pageY":582,"which":1,"x":33,"y":7}',
            'dtid': dtid,
            'uuid_0': doc_id
        }
        response = self.session.post(url, headers=headers, data=post_data)
        log_trace(self, 'SpiderAgenciaTributariaPin', f"Llamada realizada")
        log_and_save_response(self, response, f'5', f'Visualizacion del documento')

        content = response.text.replace("\n", "")
        content = content.replace("\t", "")

        matches = re.findall(r'window.open\(\'(.*?)\',', content)
        log_trace(self, 'SpiderAgenciaTributariaPin', f"Buscando doc_id ")
        if matches:
            log_trace(self, 'SpiderAgenciaTributariaPin', f"Encontrado ")
            doc_id = matches[0].split('CSV=')[1]
        else:
            log_trace(self, 'SpiderAgenciaTributariaPin', f"no encontrado. no se pudo cargar el OTP ")
            raise Exception('No se pudo cargar el OTP.')
        time_ms += 1
        url = f'https://www6.agenciatributaria.gob.es/activo?_={time_ms}'
        log_trace(self, 'SpiderAgenciaTributariaPin', f"Llamada para mantener activo ")
        self.session.get(url, headers={'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'cors',
                                       'Sec-Fetch-Site': 'same-origin', 'X-Requested-With': 'XMLHttpRequest'})

        url = 'https://www6.agenciatributaria.gob.es/wlpl/inwinvoc/es.aeat.dit.adu.eeca.catalogo.vis.Visualiza'
        params = {
            'COMPLETA': 'SI',
            'ORIGEN': 'C',
            'CLAVE_CAT': '',
            'NIF': '',
            'ANAGRAMA': '',
            'CSV': doc_id,
            'CLAVE_EE': '',
            'PAGE': '',
            'SEARCH': ''
        }

        response = self.session.get(url, params=params)
        log_trace(self, 'SpiderAgenciaTributariaPin', f"Llamada realizada")
        document = response.content
        log_and_save_response(self, response, f'6_{request_type}_PDF', 'PDF content')
        if b'PDF' not in document:
            log_trace(self, "no se localiza patrón PDF en la respuesta obtenida")
            raise Exception('No se pudo descargar el fichero')
        log_trace(self, 'SpiderAgenciaTributariaPin', f"Codificando  base64 lo obtenido ")
        encoded_document = base64.b64encode(document).decode('utf-8')
        log_trace(self, 'SpiderAgenciaTributariaPin', f"subiendo el documento asociado a la solicitud ")
        set_certificate_doc(order=self.order, doc_data=encoded_document, request_type=request_type)
        log_trace(self, 'SpiderAgenciaTributariaPin', f"Documento subido ")

        url = 'https://www6.agenciatributaria.gob.es/wlpl/inwinvoc/es.aeat.dit.adu.adht.edecla.DeclaVisor'
        log_trace(self, 'SpiderAgenciaTributariaPin', f"Nueva llamada para obtener el XML {url} ")
        params = {
            'fDetalle': '1',
            'fNif': self.order["person_national_id"],
            'fAnagrama': '',
            'fCsv': doc_id,
        }
        response = self.session.get(url, params=params)
        log_trace(self, 'SpiderAgenciaTributariaPin', f"Llamada ejecutada")
        log_and_save_response(self, response, f'7_{request_type}_XML', 'XML Content')
        xml_data = response.content
        if b'<?xml' in xml_data:
            log_trace(self, 'SpiderAgenciaTributariaPin', f"Identificado patrón XML")
            encoded_xml = base64.b64encode(xml_data).decode('utf-8')
            log_trace(self, 'SpiderAgenciaTributariaPin', f"Codificando como base64. Preparando para subirlo")
            set_certificate_doc(order=self.order, doc_data=encoded_xml, request_type=f'{request_type}_xml',
                                content_type='application/octet-stream')
            log_trace(self, 'SpiderAgenciaTributariaPin', f"XML subido a la solicitud ")
        else:
            log_trace(self, 'SpiderAgenciaTributariaPin', f"Patrón XML no encontrado en la respuesta. ")
            data = {
                'comments': "No se encontró ningún XML",
            }
            BackClient.requests(
                method='patch',
                url=f'{BackClient.URLS["requests"]}{self.order["id"]}/',
                data=data
            )
            log_trace(self, 'SpiderAgenciaTributariaPin', f"Agregado comentario con el problema en la solicituden el backend ")

        log_trace(self, 'SpiderAgenciaTributariaPin', f"Saliendo de función download_document()")
