import os

from datetime import datetime
import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
from requests_toolbelt.adapters.x509 import X509Adapter
from app_root import ROOT_DIR

from src.utils.back_client import BackClient


def create_certified_session(password, headers, pkcs12_data):
    pkcs12_password_bytes = password.encode('utf8')
    key_cert = load_key_and_certificates(pkcs12_data, pkcs12_password_bytes, default_backend())
    cert_bytes = key_cert[1].public_bytes(Encoding.PEM)
    pk_bytes = key_cert[0].private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())

    # ? Create the adapter
    x509_adapter = X509Adapter(
        max_retries=3,
        cert_bytes=cert_bytes,
        pk_bytes=pk_bytes,
        encoding=Encoding.PEM
    )
    session = requests.Session()
    session.mount('https://', x509_adapter)
    session.headers.update(headers)
    return session


def set_certificate_doc(order, doc_data, request_type, content_type='application/pdf'):
    """
    Envía a api-back el documento obtenido con el spider
    """
    data = {
        'id': order['id'],
        'request_type': request_type,
        'content_type': content_type,
        'document': doc_data
    }
    BackClient.requests(
        method='post',
        url=BackClient.URLS['send_document'],
        data=data,
    )


def set_certificate_status(order, data, sent_mail=True):
    """
    Envía a api-back el status del order
    """
    data = {
        'id': order['id'],
        'status_msg': data,
        'sent_mail': sent_mail,
    }
    BackClient.requests(
        method='post',
        url=BackClient.URLS['send_status'],
        data=data
    )


def log_and_save_response(self, response, step, desc, first_load=False):
    ruta_absoluta = os.path.join(ROOT_DIR, 'static/html')

    # Creo carpeta si no existe
    if not os.path.exists(ruta_absoluta):
        os.makedirs(ruta_absoluta)

    subcarpeta = datetime.now().strftime("%Y%m")

    # Construye la ruta intermedia con año y mes
    ruta_mes = os.path.join(ROOT_DIR, f"static/html/{subcarpeta}")

    # Creo carpeta si no existe
    if not os.path.exists(ruta_mes):
        os.makedirs(ruta_mes)


    # Construye la ruta final con subcarpeta por dias
    dia = datetime.now().strftime("%d")

    ruta_final = os.path.join(ruta_mes, dia)

    # Creo carpeta si no existe
    if not os.path.exists(ruta_final):
        os.makedirs(ruta_final)

    if not getattr(self, 'order', None) or self.order == '' or not self.order.get('id', ''):
        return

    # Obtiene la fecha y hora actuales
    fecha_hora = datetime.now().strftime("%Y%m%d%H%M%S")

    filename = os.path.join(ruta_final, f"{self.order['id']}_{fecha_hora}_step_{step}.html")

    additional_info = f'\n<!--\nInformación de la traza\n' + f'Url:: {response.url}\n' + f'Step: {step} \n' + f'Descripción: {desc} \n' + f'Ejecucion: {fecha_hora} \n' + f'-->\n'

    # Formatea el mensaje a escribir
    mensaje = f"{additional_info} \n {response.text}"
    
    # Abre el fichero para escribir (creándolo si no existe) y agrega el mensaje al final
    with open(filename, 'a') as fichero:
        fichero.write(mensaje)


def log_html(self, response, step, desc, url="Not defined"):
    # Construye la ruta absoluta
    ruta_absoluta = os.path.join(ROOT_DIR, 'static/html')

    # Creo carpeta si no existe
    if not os.path.exists(ruta_absoluta):
        os.makedirs(ruta_absoluta)

    subcarpeta = datetime.now().strftime("%Y%m")

    # Construye la ruta intermedia con año y mes
    ruta_mes = os.path.join(ROOT_DIR, f"static/html/{subcarpeta}")

    # Creo carpeta si no existe
    if not os.path.exists(ruta_mes):
        os.makedirs(ruta_mes)

    # Construye la ruta final con subcarpeta por dias
    dia = datetime.now().strftime("%d")

    ruta_final = os.path.join(ruta_mes, dia)

    # Creo carpeta si no existe
    if not os.path.exists(ruta_final):
        os.makedirs(ruta_final)

    if not getattr(self, 'order', None) or self.order == '' or not self.order.get('id', ''):
        return

    # Obtiene la fecha y hora actuales
    fecha_hora = datetime.now().strftime("%Y%m%d%H%M%S")

    filename = os.path.join(ruta_final, f"{self.order['id']}_{fecha_hora}_step_{step}.html")

    additional_info = f'\n<!--\nInformación de la traza\n' + f'Url:: {url}\n' + f'Step: {step} \n' + f'Descripción: {desc} \n' + f'Ejecucion: {fecha_hora} \n' + f'-->\n'

    # Formatea el mensaje a escribir
    mensaje = f"{additional_info} \n {response}"
    
    # Abre el fichero para escribir (creándolo si no existe) y agrega el mensaje al final
    with open(filename, 'a') as fichero:
        fichero.write(mensaje)


def log_trace(data, context, content):
    # Construye la ruta absoluta
    ruta_absoluta = os.path.join(ROOT_DIR, 'static/traces')

    # Creo carpeta si no existe
    if not os.path.exists(ruta_absoluta):
        os.makedirs(ruta_absoluta)

    subcarpeta = datetime.now().strftime("%Y%m")

    # Construye la ruta intermedia con año y mes
    ruta_mes = os.path.join(ROOT_DIR, f"static/traces/{subcarpeta}")

    # Creo carpeta si no existe
    if not os.path.exists(ruta_mes):
        os.makedirs(ruta_mes)

    # Construye la ruta final con subcarpeta por dias
    dia = datetime.now().strftime("%d")

    ruta_absoluta = os.path.join(ruta_mes, dia)

    # Creo carpeta si no existe
    if not os.path.exists(ruta_absoluta):
        os.makedirs(ruta_absoluta)

    datos = None
    if  getattr(data, 'order', None) :
        datos = data.order

    if not getattr(data, 'order', None) or data.order == '' or not data.order['id']:
        filename = os.path.join(ruta_absoluta, f"_unknown.log")
    else: 
        filename = os.path.join(ruta_absoluta, f"{data.order['id']}.log")



    # Obtiene la fecha y hora actuales
    fecha_hora = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")

    # Formatea el mensaje a escribir
    mensaje = f"{fecha_hora} {context} - {content} - {datos}\n"
    
    # Abre el fichero para escribir (creándolo si no existe) y agrega el mensaje al final
    with open(filename, 'a') as fichero:
        fichero.write(mensaje)
