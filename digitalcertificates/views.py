import json
import traceback
from datetime import datetime, timedelta
from urllib.parse import urljoin
from types import SimpleNamespace

from django import forms
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render, redirect
from rest_framework import status as status_framework, generics

from cirbox_scraper.spiders.agenciatributaria import SpiderAgenciaTributaria
from cirbox_scraper.spiders.scrapper_pin_eval import EvalClavePin
from cirbox_scraper.spiders.vida_laboral import SpiderVidaLaboral
from cirbox_scraper.spiders.cirbe import SpiderCirbe
from cirbox_scraper.utils import set_certificate_status, log_trace
from digitalcertificates.clave_pin_handler import ClavePinHandler
from digitalcertificates.pkcs11_handler import PKCS11Handler
from src.apps.certificate_order.enumeration import CertificateOrderType, PersonType
from src.apps.certificate_order.models.log import Log
from src.utils.back_client import BackClient
from src.utils.permission.permissions_api import IsAuthenticatedAPI

clave_pin_handler = ClavePinHandler()
pkcs11_handler = PKCS11Handler()

TGSS_TYPE = "tgss"
TGSS_SEDE_TYPE = "sede"
AGENCY_TYPE = "agency"


class ClavePinForm(forms.Form):
    person_national_document_type = forms.ChoiceField(
        choices=[('dni', 'ID'), ('dni_permanente', 'Permanent ID'), ('tja_residencia', 'NIE')])
    person_national_id = forms.CharField(max_length=255)
    person_dni_validation_date = forms.CharField(max_length=255)


class CertificateScrapperPinAPIView(generics.GenericAPIView):
    permission_classes = (IsAuthenticatedAPI,)

    def post(self, request):
        try:
            nif_data = get_nif_data(request.data)
            # Se lanza el spider
            response = ClavePinHandler.run_single_spider(spider=EvalClavePin, params=nif_data)
            return JsonResponse({'status': response}, status=status_framework.HTTP_200_OK)
        except Exception as err:
            traceback.print_exc()
            Log.objects.create(context='eval_pin', response='', error=str(err))
            return JsonResponse({'status': "Error"}, status=status_framework.HTTP_500_INTERNAL_SERVER_ERROR)


def pkcs11_landing1_view(request, order):
    try:
        name, context = get_name_and_context(order)
        contexto = {}
        contexto.update({
            'order': dict(order)
        })

        self = SimpleNamespace(order=dict(order))

        log_trace(self, 'pkcs11_landing1_view', f"Iniciando funcion pkcs11_landing1_view()")
        log_trace(self, 'pkcs11_landing1_view', f"context: {self}")

        if request.method == 'POST':

            log_trace(self, 'pkcs11_landing1_view', f"Identificado metodo POST")
            try:
                log_trace(self, 'pkcs11_landing1_view', f"Preprando cambio de estado a STARTED")
                data = {
                    'status': CertificateOrderType.STATUS_STARTED.value
                },
                BackClient.requests(
                    method='post',
                    url=f'{BackClient.URLS["requests"]}{order["id"]}/status/',
                    data=data
                )
                log_trace(self, 'pkcs11_landing1_view', f"Estado cambiado")

                # Para cada petición lanzamos su spider
                log_trace(self, 'pkcs11_landing1_view', f"Iniciando bucle que recorre los request_types: {order['request_type']}")
                hay_cirbe = False

                for r in order['request_type']:
                    obj = {'order': order}
                    if r == 'vida_laboral':
                        log_trace(self, 'pkcs11_landing1_view', f"Identificada Vida Laboral. Agregando spider")
                        obj.update({
                            'spider': SpiderVidaLaboral
                        })
                    elif r == 'renta':
                        log_trace(self, 'pkcs11_landing1_view', f"Identificada Renta. Agregando spider")
                        obj.update({
                            'spider': SpiderAgenciaTributaria,
                            'modelo': '100'
                        })
                    elif r == 'modelo_390':
                        log_trace(self, 'pkcs11_landing1_view', f"Identificada Modelo 390. Agregando spider")
                        obj.update({
                            'spider': SpiderAgenciaTributaria,
                            'modelo': '390'
                        })
                    elif r == 'modelo_303':
                        log_trace(self, 'pkcs11_landing1_view', f"Identificada Modelo 303. Agregando spider")
                        obj.update({
                            'spider': SpiderAgenciaTributaria,
                            'modelo': '303'
                        })
                    elif r == 'modelo_347':
                        log_trace(self, 'pkcs11_landing1_view', f"Identificada Modelo 347. Agregando spider")
                        obj.update({
                            'spider': SpiderAgenciaTributaria,
                            'modelo': '347'
                        })
                    elif r == 'modelo_200':
                        log_trace(self, 'pkcs11_landing1_view', f"Identificada Modelo 200. Agregando spider")
                        obj.update({
                            'spider': SpiderAgenciaTributaria,
                            'modelo': '200'
                        })
                    elif r == 'cirbe':
                        log_trace(self, 'pkcs11_landing1_view', f"Identificada Cirbe. Agregando spider")
                        hay_cirbe = True
                        obj.update({
                            'spider': SpiderCirbe,
                            'certificate': None,
                            'password': None,
                            'modelo': '100'
                        })
                    else:
                        log_trace(self, 'pkcs11_landing1_view', f"Identificando tipo no controlado: {r}")
                        continue
                    
                    log_trace(self, 'pkcs11_landing1_view', f"Agregando los spiders a la cola de ejecucion")
                    pkcs11_handler.spider_queue.append(obj)

                if pkcs11_handler.spider_queue:
                    log_trace(self, 'pkcs11_landing1_view', f"Preparando llamada a run_next_spider")
                    pkcs11_handler.run_next_spider()
                    log_trace(self, 'pkcs11_landing1_view', f"Finalizando llamada recursiva a run_next_spider")

                    log_trace(self, 'pkcs11_landing1_view', f"Marcando como completada la solicitud: {order['id']}")
                    if hay_cirbe == False:
                        contexto = set_order_status_completed(context, order["id"])

                    log_trace(self, 'pkcs11_landing1_view', f"Solicitud marcada como completada")


                log_trace(self, 'pkcs11_landing1_view', f"Cambiando contexto a finished")
                context.update({'finished': 'Solicitud procesada correctamente'})

                log_trace(self, 'pkcs11_landing1_view', f"Redireccionando a pkcs11_landing1.html")
                return render(request, 'pkcs11_landing1.html', context)

            except Exception as err:
                log_trace(self, 'pkcs11_landing1_view', f"Error de ejecucion: {str(err)}")
                traceback.print_exc()
                log_trace(self, 'pkcs11_landing1_view', f"Cambiando estado de solicitud a CANCELADA con el motivo de error")
                set_certificate_status(order, str(err), False)
                log_trace(self, 'pkcs11_landing1_view', f"Marcando el contexto como solicitud erronea")
                set_context_error(context, f'Motivo: {str(err)}')
                log_trace(self, 'pkcs11_landing1_view', f"Redireccionando a pkcs11_landing1.html")
                return render(request, 'pkcs11_landing1.html', context)

        # Se evita avanzar a landing2 si ha dado error, está completada o cancelada
        if order['status'] == CertificateOrderType.STATUS_CANCELLED.value:
            log_trace(self, 'pkcs11_landing1_view', f"Solicitd identificada como CANCELADA")
            log_trace(self, 'pkcs11_landing1_view', f"Ajustado el contexto de la solicitud con el error")
            set_context_error(context, f'Motivo: {order["cancellation_reason"]}')
            log_trace(self, 'pkcs11_landing1_view', f"Redireccion a pkcs11_landing1.html con {context}")
            return render(request, 'pkcs11_landing1.html', context)

        if order['status'] != CertificateOrderType.STATUS_APPROVED.value:
            log_trace(self, 'pkcs11_landing1_view', f"Solicitud identificada como APROBADA")
            log_trace(self, 'pkcs11_landing1_view', f"Ajustado el contexto de la solicitud como success")
            set_context_success(context)
            log_trace(self, 'pkcs11_landing1_view', f"Redireccion a pkcs11_landing1.html con {context}")
            return render(request, 'pkcs11_landing1.html', context)

        try:
            log_trace(self, 'pkcs11_landing1_view', f"Recuperando la lista de productos")
            res = BackClient.requests(method='get', url=BackClient.URLS['products'])
            products = json.loads(res.content)

            log_trace(self, 'pkcs11_landing1_view', f"Bucle de verificación de productos")
            for serial in order['request_type']:
                product = next((p for p in products['products_general'] if p['serial'] == serial), None)
                if product is not None:
                    log_trace(self, 'pkcs11_landing1_view', f"Agregando producto matcheado al contexto {product['name']}")
                    context['products'].append(product['name'])

        except Exception as err:
            log_trace(self, 'pkcs11_landing1_view', f"Error de ejecucion: {str(err)}")
            Log.objects.create(context='products', response='', error=str(err))

        log_trace(self, 'pkcs11_landing1_view', f"Redireccion a pkcs11_landing1.html con {context}")
        return render(request, 'pkcs11_landing1.html', context)

    except Exception as err:
        log_trace(self, 'pkcs11_landing1_view', f"Error de ejecucion: {str(err)}")
        Log.objects.create(context='pkcs11_landing1_view', response='', error=str(err))

    log_trace(self, 'pkcs11_landing1_view', f"Redireccion a pkcs11_landing1.html con context vacio")
    return render(request, 'pkcs11_landing1.html', context={})


def clave_pin_landing1_view(request, certificate_order_id):
    try:
        order = get_order(certificate_order_id)
        contexto = {}
        contexto.update({
            'order': dict(order)
        })

        self = SimpleNamespace(order=dict(order))

        log_trace(self, 'clave_pin_landing1_view', f"Iniciando carga de vista landing1 con {contexto}")

        # Check pkcs11 flow
        if order['auth_type'] == 'pkcs11':
            log_trace(self, 'clave_pin_landing1_view', f"Identificada solicitud PKCS11")
            return pkcs11_landing1_view(request=request, order=order)

        filtered_tgss_requests, filtered_agency_requests, filtered_tgss_sede_requests = filter_requests(order)
        name, context = get_name_and_context(order)
        log_trace(self, 'clave_pin_landing1_view', f"Recuperando información de solicitud: {context}")

        if request.method == 'POST':
            log_trace(self, 'clave_pin_landing1_view', f"Petición de tipo POST")
            try:
                log_trace(self, 'clave_pin_landing1_view', f"Marcando solicitud como STARTED")
                data = {
                    'status': CertificateOrderType.STATUS_STARTED.value
                },
                BackClient.requests(
                    method='post',
                    url=f'{BackClient.URLS["requests"]}{certificate_order_id}/status/',
                    data=data
                )
                log_trace(self, 'clave_pin_landing1_view', f"Solicitud actualizada")

                # handle the external requests if order has return url
                if order['return_url']:
                    log_trace(self, 'clave_pin_landing1_view', f"La solicitud contiene definido el parámetro return_url: {order['return_url']}")
                    log_trace(self, 'clave_pin_landing1_view', f"Cargando formulario")
                    form = ClavePinForm(request.POST)
                    if form.is_valid():
                        log_trace(self, 'clave_pin_landing1_view', f"Formulario validado")
                        form_data = {
                            'person_national_document_type': form.cleaned_data['person_national_document_type'],
                            'person_national_id': form.cleaned_data['person_national_id'].upper(),
                            'key_document_value': form.cleaned_data['person_dni_validation_date'].upper(),
                        }

                        log_trace(self, 'clave_pin_landing1_view', f"Preparando llamada para actualizar solicitud con información del formulario {form_data}")
                        response = BackClient.requests(
                            method='patch',
                            url=f'{BackClient.URLS["requests"]}{certificate_order_id}/',
                            data=form_data
                        )
                        log_trace(self, 'clave_pin_landing1_view', f"Solicitud actualizada")

                        order = json.loads(response.content.decode('utf-8'))
                        temp_nif_data = organize_nif_data_for_external_request(order)
                        nif_data = get_nif_data(temp_nif_data)

                        log_trace(self, 'clave_pin_landing1_view', f"Preparando llamada a EvalClaePin")
                        clave_pin_handler.spider_queue.append({
                            'spider': EvalClavePin,
                            'order': order,
                            **nif_data
                        })
                        log_trace(self, 'clave_pin_landing1_view', f"Agregado a la cola y llamando a run_next_spider")
                        clave_pin_handler.run_next_spider()
                        log_trace(self, 'clave_pin_landing1_view', f"run_next_spider ejecutado")

                log_trace(self, 'clave_pin_landing1_view', f"Comprobando documentos solicitado y definiendo request_type")
                if filtered_agency_requests:
                    request_type = AGENCY_TYPE
                elif filtered_tgss_requests:
                    request_type = TGSS_TYPE
                else:
                    request_type = TGSS_SEDE_TYPE
                log_trace(self, 'clave_pin_landing1_view', f"request_type definido: {request_type}")

                log_trace(self, 'clave_pin_landing1_view', f"Llamando a función get_pin_code")
                clave_pin_handler.get_pin_code(order, request_type)
                log_trace(self, 'clave_pin_landing1_view', f"Llamada realizada")
                reason = get_error_status(order)
                if reason:
                    log_trace(self, 'clave_pin_landing1_view', f"Error capturado: {reason}")
                    log_trace(self, 'clave_pin_landing1_view', f"Redirigiendo al return_url con el motivo de error")
                    return redirect(urljoin(f'{order["return_url"].rstrip("/")}/{order["id"]}', f'?status={reason}'))
            except Exception as err:
                log_trace(self, 'clave_pin_landing1_view', f"Error en la ejecución: {str(err)}")
                traceback.print_exc()
                log_trace(self, 'clave_pin_landing1_view', f"Atualización de estado de la solicitud")
                set_certificate_status(order, str(err), False)
                log_trace(self, 'clave_pin_landing1_view', f"Almacenando error en variable contexto")
                set_context_error(context, f'Motivo: {str(err)}')
                log_trace(self, 'clave_pin_landing1_view', f"Redirigiendo a clave_pin_landing1.html con {context}")
                return render(request, 'clave_pin_landing1.html', context)

            log_trace(self, 'clave_pin_landing1_view', f"Ejecución correcta y redirigiendo a clavepin2")
            return redirect("digitalcertificates:clavepin2", certificate_order_id, request_type)

        # Se evita avanzar a landing2 si ha dado error, está completada o cancelada
        if order['status'] == CertificateOrderType.STATUS_CANCELLED.value:
            log_trace(self, 'clave_pin_landing1_view', f"Solicitud en estado CANCELLED, asi que vamos a actualizar el contexto con el mensaje de cancelacion: {order['cancellation_reason']}")
            set_context_error(context, f'Motivo: {order["cancellation_reason"]}')
            log_trace(self, 'clave_pin_landing1_view', f"Redirección a clave_pin_landing1.html con {context}")
            return render(request, 'clave_pin_landing1.html', context)

        if order['status'] != CertificateOrderType.STATUS_APPROVED.value:
            log_trace(self, 'clave_pin_landing1_view', f"Solicitud en estado APPROVED así que marcaremos el contexto como success")
            set_context_success(context)
            log_trace(self, 'clave_pin_landing1_view', f"Redirección a clave_pin_landing1.html con {context}")
            return render(request, 'clave_pin_landing1.html', context)

        try:
            log_trace(self, 'clave_pin_landing1_view', f"Recuperando lista de productos para verificar request_type: {order['request_type']}")
            res = BackClient.requests(method='get', url=BackClient.URLS['products'])
            products = json.loads(res.content)

            for serial in order['request_type']:
                log_trace(self, 'clave_pin_landing1_view', f"Verificando {serial}")
                product = next((p for p in products['products_general'] if p['serial'] == serial), None)
                if product is not None:
                    log_trace(self, 'clave_pin_landing1_view', f"Encontrada coincidencia en {product}")
                    context['products'].append(product['name'])

        except Exception as err:
            log_trace(self, 'clave_pin_landing1_view', f"Error en ejecucion: {str(err)}")
            Log.objects.create(context='products', response='', error=str(err))
        
        log_trace(self, 'clave_pin_landing1_view', f"Redirección a clave_pin_landing1.html con {context}")
        return render(request, 'clave_pin_landing1.html', context)

    except Exception as err:
        log_trace(self, 'clave_pin_landing1_view', f"Error en ejecucion: {str(err)}")
        Log.objects.create(context='clave_pin_landing1_view', response='', error=str(err))

    log_trace(self, 'clave_pin_landing1_view', f"Redirección a clave_pin_landing1.html con context vacío")
    return render(request, 'clave_pin_landing1.html', context={})


def clave_pin_landing2_view(request, certificate_order_id, request_type):
    try:
        order = get_order(certificate_order_id)
        contexto = {}
        contexto.update({
            'order': dict(order)
        })

        self = SimpleNamespace(order=dict(order))
        log_trace(self, 'clave_pin_landing2_view', f"Iniciando carga de vista landing2 con {contexto}")
        context = {
            'logo': order['logo_url'].replace(settings.BACK_DNS, ""),
            'landing_text': getLandingText(request_type)
        }

        filtered_tgss_requests, filtered_agency_requests, filtered_tgss_sede_requests = filter_requests(order)
        if request.method == 'POST':
            try:
                log_trace(self, 'clave_pin_landing2_view', f"Procesando llamada POST")
                log_trace(self, 'clave_pin_landing2_view', f"Llamada a start_spider_document_process")
                start_spider_document_process(request, order, request_type)
                log_trace(self, 'clave_pin_landing2_view', f"Finalizada llamada a start_spider_document_process")

                if request_type == AGENCY_TYPE:
                    log_trace(self, 'clave_pin_landing2_view', f"Identificado Agencia Tributaria")
                    if filtered_tgss_requests:
                        request_type = TGSS_TYPE
                        log_trace(self, 'clave_pin_landing2_view', f"Preparando llamada a get_pin_code()")
                        clave_pin_handler.get_pin_code(order, request_type)
                        log_trace(self, 'clave_pin_landing2_view', f"Redireccion a digitalcertificates:clavepin3")
                        return redirect("digitalcertificates:clavepin3", certificate_order_id, request_type)
                    elif filtered_tgss_sede_requests:
                        request_type = TGSS_SEDE_TYPE
                        log_trace(self, 'clave_pin_landing2_view', f"Preparando llamada a get_pin_code()")
                        clave_pin_handler.get_pin_code(order, request_type)
                        log_trace(self, 'clave_pin_landing2_view', f"Redireccion a digitalcertificates:clavepin3")
                        return redirect("digitalcertificates:clavepin3", certificate_order_id, request_type)

                if request_type == TGSS_TYPE and filtered_tgss_sede_requests:
                    log_trace(self, 'clave_pin_landing2_view', f"Identificado TGSS")
                    request_type = TGSS_SEDE_TYPE
                    log_trace(self, 'clave_pin_landing2_view', f"Preparando llamada a get_pin_code()")
                    clave_pin_handler.get_pin_code(order, request_type)
                    log_trace(self, 'clave_pin_landing2_view', f"Redireccion a digitalcertificates:clavepin3")
                    return redirect("digitalcertificates:clavepin3", certificate_order_id, request_type)

                log_trace(self, 'clave_pin_landing2_view', f"Llamando a set_order_status_completed()")
                context = set_order_status_completed(context, certificate_order_id)
                reason = get_error_status(order)
                if reason:
                    log_trace(self, 'clave_pin_landing2_view', f"Identificado error ({reason}) y vamos a redirigir")
                    return redirect(urljoin(f'{order["return_url"].rstrip("/")}/{order["id"]}', f'?status={reason}'))

                log_trace(self, 'clave_pin_landing2_view', f"Redirigimos a clave_pin_landing2.html")
                return render(request, 'clave_pin_landing2.html', context)

            except Exception as err:
                log_trace(self, 'clave_pin_landing2_view', f"Error identificado: {str(err)}")
                set_certificate_status(order, str(err), False)
                set_context_error(context, f'Motivo: {str(err)}')
                log_trace(self, 'clave_pin_landing2_view', f"Redirigimos a clave_pin_landing2.html")
                return render(request, 'clave_pin_landing2.html', context)

        if order['status'] == CertificateOrderType.STATUS_APPROVED.value:
            log_trace(self, 'clave_pin_landing2_view', f"Solicitud APPROVED. Redirigiendo a digitalcertificates:clavepin1")
            return redirect("digitalcertificates:clavepin1", certificate_order_id)

        if order['status'] == CertificateOrderType.STATUS_CANCELLED.value:
            log_trace(self, 'clave_pin_landing2_view', f"Solicitud CANCELLED. Redirigiendo a clave_pin_landing2.html")
            set_context_error(context, f'Motivo: {order["cancellation_reason"]}')
            return render(request, 'clave_pin_landing2.html', context)

        empty_array_count = sum(
            1 for arr in [filtered_agency_requests, filtered_tgss_requests, filtered_tgss_sede_requests] if
            len(arr) == 0)
        
        log_trace(self, 'clave_pin_landing2_view', f"Cantidad en empty_array_count: {str(empty_array_count)}")
        if empty_array_count >= 2:
            log_trace(self, 'clave_pin_landing2_view', f"Cantidad >=2")
            return render(request, 'clave_pin_landing4.html', context)
        else:
            log_trace(self, 'clave_pin_landing2_view', f"Cantidad <2")
            return render(request, 'clave_pin_landing2.html', context)

    except Exception as err:
        log_trace(self, 'clave_pin_landing2_view', f"Error recogido: {str(err)}")
        Log.objects.create(context='clave_pin_landing2_view', response='', error=str(err))

    log_trace(self, 'clave_pin_landing2_view', f"Redireccion a clave_pin_landing2.html")
    return render(request, 'clave_pin_landing2.html', context={})


def clave_pin_landing3_view(request, certificate_order_id, request_type):
    try:
        order = get_order(certificate_order_id)
        context = {
            'logo': order['logo_url'].replace(settings.BACK_DNS, ""),
            'landing_text': getLandingText(request_type)
        }

        self = SimpleNamespace(order=dict(order))
        log_trace(self, 'clave_pin_landing3_view', f"Iniciando carga de vista landing3 para {certificate_order_id}")

        filtered_tgss_requests, filtered_agency_requests, filtered_tgss_sede_requests = filter_requests(order)

        if request.method == 'POST':
            try:
                log_trace(self, 'clave_pin_landing3_view', f"Procesando llamada POST")
                log_trace(self, 'clave_pin_landing3_view', f"Llamando a start_spider_document_process()")
                start_spider_document_process(request, order, request_type)

                if request_type == TGSS_TYPE and filtered_tgss_sede_requests:
                    request_type = TGSS_SEDE_TYPE
                    log_trace(self, 'clave_pin_landing3_view', f"Llamando a get_pin_code con {request_type}")
                    clave_pin_handler.get_pin_code(order, request_type)
                    log_trace(self, 'clave_pin_landing3_view', f"Redireccion a digitalcertificates:clavepin4")
                    return redirect("digitalcertificates:clavepin4", certificate_order_id, request_type)

                log_trace(self, 'clave_pin_landing3_view', f"Llamando a set_order_status_completed()")
                context = set_order_status_completed(context, certificate_order_id)
                reason = get_error_status(order)
                if reason:
                    log_trace(self, 'clave_pin_landing3_view', f"Redireccionando con error {reason} ")
                    return redirect(urljoin(f'{order["return_url"].rstrip("/")}/{order["id"]}', f'?status={reason}'))

                log_trace(self, 'clave_pin_landing3_view', f"Devolviendo clave_pin_landing3.html")
                return render(request, 'clave_pin_landing3.html', context)
            except Exception as err:
                log_trace(self, 'clave_pin_landing3_view', f"Error producido: {str(err)}")
                traceback.print_exc()
                log_trace(self, 'clave_pin_landing3_view', f"Cambio estado de request")
                set_certificate_status(order, str(err), False)
                set_context_error(context, f'Motivo: {str(err)}')
                log_trace(self, 'clave_pin_landing3_view', f"Devolviendo clave_pin_landing3.html")
                return render(request, 'clave_pin_landing3.html', context)

        if order['status'] == CertificateOrderType.STATUS_APPROVED.value:
            log_trace(self, 'clave_pin_landing3_view', f"Solicitud APPROVED y redireccionando a digitalcertificates:clavepin1")
            return redirect("digitalcertificates:clavepin1", certificate_order_id)

        if order['status'] == CertificateOrderType.STATUS_CANCELLED.value:
            log_trace(self, 'clave_pin_landing3_view', f"Solicitud CANCELLED y redireccionando a clave_pin_landing3.html")
            set_context_error(context, f'Motivo: {order["cancellation_reason"]}')
            return render(request, 'clave_pin_landing3.html', context)

        if len(filtered_tgss_requests) == 0 or len(filtered_tgss_sede_requests) == 0:
            log_trace(self, 'clave_pin_landing3_view', f"filtered_tgss_requests o filtered_tgss_sede_requests es CERO y redireccionando a clave_pin_landing4.html")
            return render(request, 'clave_pin_landing4.html', context)
        else:
            log_trace(self, 'clave_pin_landing3_view', f"filtered_tgss_requests o filtered_tgss_sede_requests diferente de CERO y redireccionando a clave_pin_landing3.html")
            return render(request, 'clave_pin_landing3.html', context)

    except Exception as err:
        log_trace(self, 'clave_pin_landing3_view', f"Error producido: {str(err)}")
        Log.objects.create(context='clave_pin_landing3_view', response='', error=str(err))

    log_trace(self, 'clave_pin_landing3_view', f"Redireccion a clave_pin_landing3.html ")
    return render(request, 'clave_pin_landing3.html', context={})


def clave_pin_landing4_view(request, certificate_order_id, request_type):
    try:
        order = get_order(certificate_order_id)
        context = {
            'logo': order['logo_url'].replace(settings.BACK_DNS, ""),
            'landing_text': getLandingText(request_type)
        }

        self = SimpleNamespace(order=dict(order))
        log_trace(self, 'clave_pin_landing4_view', f"Iniciando carga de vista landing2 para {certificate_order_id}")

        if request.method == 'POST':
            try:
                start_spider_document_process(request, order, request_type)
                context = set_order_status_completed(context, certificate_order_id)
                reason = get_error_status(order)
                if reason:
                    return redirect(urljoin(f'{order["return_url"].rstrip("/")}/{order["id"]}', f'?status={reason}'))
            except Exception as err:
                traceback.print_exc()
                set_certificate_status(order, str(err), False)
                set_context_error(context, f'Motivo: {str(err)}')
                return render(request, 'clave_pin_landing4.html', context)

        if order['status'] == CertificateOrderType.STATUS_APPROVED.value:
            return redirect("digitalcertificates:clavepin1", certificate_order_id)

        if order['status'] == CertificateOrderType.STATUS_CANCELLED.value:
            set_context_error(context, f'Motivo: {order["cancellation_reason"]}')
            return render(request, 'clave_pin_landing4.html', context)

        return render(request, 'clave_pin_landing4.html', context)

    except Exception as err:
        Log.objects.create(context='clave_pin_landing4_view', response='', error=str(err))

    return render(request, 'clave_pin_landing4.html', context={})


def start_spider_document_process(request, order, request_type):
    otp = request.POST['otp'].upper()
    res = {
        'otp': otp,
    }

    self = SimpleNamespace(order=dict(order))
    log_trace(self, 'start_spider_document_process', f"Iniciando proceso")
    func = {
        AGENCY_TYPE: clave_pin_handler.process_agency,
        TGSS_TYPE: clave_pin_handler.process_tgss,
        TGSS_SEDE_TYPE: clave_pin_handler.process_sede,
    }[request_type]

    clave_pin_handler.spider_queue.append(func(order, res))

    if clave_pin_handler.spider_queue:
        clave_pin_handler.run_next_spider()


def set_order_status_completed(context, certificate_order_id):
    order = get_order(certificate_order_id)

    self = SimpleNamespace(order=dict(order))
    log_trace(self, 'set_order_status_completed', f"Iniciando proceso")

    if order['status'] != CertificateOrderType.STATUS_CANCELLED.value:
        set_context_success(context)
        data = {
            'status': CertificateOrderType.STATUS_COMPLETED.value
        },
        BackClient.requests(
            method='post',
            url=f'{BackClient.URLS["requests"]}{certificate_order_id}/status/',
            data=data
        )
        data = {'isError': True, 'reason': 'success'}
        cache.set(order['id'], data, 3600)
    else:
        set_context_error(context, f'Motivo: {order["cancellation_reason"]}')
    
    return context


def get_error_status(order):
    cached_data = cache.get(order['id'])
    if order['return_url'] and cached_data is not None and cached_data.get('reason') is not None:
        return cached_data.get("reason")


def get_order(certificate_order_id):
    try:
        response = BackClient.requests(
            method='get',
            url=f'{BackClient.URLS["requests"]}{certificate_order_id}',
        )
        return json.loads(response.content)
    except Exception as err:
        Log.objects.create(context='get_order', response='', error=str(err))
        return None


def filter_requests(order):
    TGSS_REQUESTS = ['vida_laboral', 'base_cotizacion']
    TGSS_SEDE_REQUESTS = ['pensiones']
    AGENCY_REQUESTS = ['renta', 'modelo_347', 'modelo_390', 'modelo_303']

    requests_types = order['request_type']
    filtered_tgss_requests = [item for item in requests_types if item in TGSS_REQUESTS]
    filtered_tgss_sede_requests = [item for item in requests_types if item in TGSS_SEDE_REQUESTS]
    filtered_agency_requests = [item for item in requests_types if item in AGENCY_REQUESTS]

    return filtered_tgss_requests, filtered_agency_requests, filtered_tgss_sede_requests


def get_name_and_context(order):
    name = order['person_first_name']

    context = {
        'return_url': order['return_url'],
        'order': order,
        'name': name,
        'logo': order['logo_url'].replace(settings.BACK_DNS, ""),
        'nif': order['person_national_id'],
        'products': []
    }
    return name, context


def set_context_error(context, error_msg):
    context.update({'error': error_msg})


def set_context_success(context):
    context.update({'success': True})


def get_nif_data(data):
    nif_data = {
        'scratchard': data.get('scratchard', None),
        'nif': data.get('nif', None),
        'fecha_expedicion': '',
        'fecha_vencimiento': '',
        'fecha_nacimiento': '',
        'nro_soporte': '',
        'tipo_nif': data.get('tipo_nif', None)
    }

    if nif_data['tipo_nif'] == 'nie':
        nif_data['nro_soporte'] = data.get('extra', None)
    elif nif_data['tipo_nif'] == 'dni_permanente':
        nif_data['fecha_expedicion'] = data.get('fecha_expedicion', None)
    else:
        nif_data['fecha_vencimiento'] = data.get('fecha_vencimiento', None)

    return nif_data


def organize_nif_data_for_external_request(order):
    key_document_value = None
    birth_date = None
    if order['person_birth_date']:
        birth_date = order['person_birth_date'].strftime('%d-%m-%Y')
    try:
        if order['key_document_value']:
            tmp_date = datetime.strptime(order['key_document_value'], '%Y-%m-%d')
            key_document_value = tmp_date.strftime('%d-%m-%Y')
    except:
        pass
    nif = order['person_national_id']
    if nif:
        nif = nif.upper()
    data = {
        "nif": nif,
        "fecha_expedicion": key_document_value,
        "fecha_vencimiento": key_document_value,
        "fecha_nacimiento": birth_date,
        "tipo_nif": order['person_national_document_type']
    }
    if data.get("tipo_nif") == "tja_residencia":
        data['tipo_nif'] = 'nie'
        data['extra'] = order['key_document_value']
        data['fecha_expedicion'] = '01-01-1900'
        data['fecha_vencimiento'] = '01-01-1900'

    return data


def getLandingText(request_type):
    if request_type == AGENCY_TYPE:
        return "<strong>¡Estamos conectando con Hacienda para avanzar rápidamente con tu solicitud!<br>En pocos segundos recibirás un SMS del sistema Cl@ve. Solo necesitarás introducir el PIN recibido.</strong>"
    else:
        return "<strong>¡Conectando con la Seguridad Social!<br>En unos segundos recibirás un SMS con el PIN de Cl@ve.</strong>"