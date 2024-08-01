from django.db import transaction
from rest_framework import status as status_framework
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from datetime import datetime

from src.apps.certificate_order.certificate_provider import CertificateProvider
from src.apps.certificate_order.enumeration import CertificateOrderModeEnum
from src.apps.certificate_order.models.certificate_order import CertificateOrderModel
from src.apps.certificate_order.models.log import Log
from src.apps.cron.enumeration import CronNames
from src.utils.permission.permissions_api import IsAuthenticatedAPI


class CertificateOrderView(ViewSet):

    permission_classes = (IsAuthenticatedAPI,)

    def create(self, request):
        try:
            with transaction.atomic():
                data = request.data
                brocode = datetime.today().strftime('%Y%m%d%H%M%f')
                for p in data['products']:
                    certificate_mode = data['certificate_mode']
                    if data['certificate_mode'] in ('pem',):
                        certificate_mode = CertificateOrderModeEnum.P12.value

                    to_create = {
                        'certificate_id': data['certificate_order_id'],
                        'product_type': p['product'],
                        'extra_info': p['extra_info'] if p.get('extra_info') else None,
                        'certificate_mode': certificate_mode,
                        'brocode': brocode
                    }
                    CertificateOrderModel.objects.create(**to_create)

                # # Si es clave pin la lanzamos ya por solo tener margen de 2 minutos
                # if certificate_mode == CertificateOrderModeEnum.CLAVEPIN.value:
                #     try:
                #         CertificateProvider.process_orders(order_status=CronNames.PROCESAR_PENDIENTES.value,
                #                                            mode=CertificateOrderModeEnum.CLAVEPIN.value,
                #                                            brocode=brocode)
                #     except Exception as err:
                #         Log.objects.create(context='cron_crawler', response='funcion_handle_pendientes', error=str(err))

        except Exception as err:
            return Response({"error": f"No se ha podido registrar la petición. Motivo: {err}"},
                            status=status_framework.HTTP_400_BAD_REQUEST)
        return Response(dict(), status=status_framework.HTTP_201_CREATED)

    def list(self, request):
        ...
        # try:
        #     order_id = request.query_params['order_id']
        #     CertificateProvider.process_orders(order_id=order_id)
        # except Exception as err:
        #     return Response({"error": f"No se ha podido procesar la solicitud. Motivo: {err}"},
        #                     status=status_framework.HTTP_400_BAD_REQUEST)
        # return Response(dict(), status=status_framework.HTTP_200_OK)
