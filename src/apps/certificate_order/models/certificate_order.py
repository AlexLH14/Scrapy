from django.db import models
from datetime import datetime
from src.apps.certificate_order.enumeration import ProductType, CertificateOrderType, CertificateOrderModeEnum


class CertificateOrderModel(models.Model):

    created = models.DateTimeField(auto_now_add=True)
    certificate_id = models.TextField()
    product_type = models.TextField(choices=ProductType.values())
    extra_info = models.JSONField(null=True)
    status = models.TextField(choices=CertificateOrderType.values(), default=CertificateOrderType.PENDIENTE.value)
    error = models.TextField(null=True)
    updated = models.DateTimeField(null=True)
    attempts = models.IntegerField(default=0)
    brocode = models.TextField(null=True)
    certificate_mode = models.TextField(choices=CertificateOrderModeEnum.values(),
                                        default=CertificateOrderModeEnum.P12.value)

    class Meta:
        db_table = 'cirbox_certificateorder'
        app_label = 'src'
        verbose_name = 'CertificateOrder'
        unique_together = ('certificate_id', 'product_type')

    def register_error(self, msg):
        self.updated = datetime.today()
        self.error = msg
        self.status = CertificateOrderType.ERROR.value
        self.attempts += 1
        self.save()

    def register_success(self):
        self.updated = datetime.today()
        self.error = None
        self.status = CertificateOrderType.COMPLETADO.value
        self.attempts = 0
        self.save()

    def set_to_no_programado(self):
        self.updated = datetime.today()
        self.error = f'No hay spider para el producto {self.product_type}'
        self.status = CertificateOrderType.NO_PROGRAMADO.value
        self.attempts = 0
        self.save()

    def reset_to_pendiente(self, error=None):
        self.updated = datetime.today()
        self.error = f'Petición reseteada a {CertificateOrderType.PENDIENTE.value}' if not error else error
        self.status = CertificateOrderType.PENDIENTE.value
        self.attempts += 1
        self.save()

    def still_waiting(self):
        self.reset_to_pendiente(error=f'Peticion todavia no disponible, '
                                      f'se resetea a {CertificateOrderType.PENDIENTE.value}')
