from django.db import models

from src.apps.certificate_order.models.certificate_order import CertificateOrderModel


class CertificateOrderLogModel(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    context = models.TextField(null=True)
    event = models.TextField(null=True)
    extra_info = models.TextField(null=True)
    certificate_order = models.ForeignKey(CertificateOrderModel, on_delete=models.PROTECT)

    class Meta:
        db_table = 'cirbox_certificateorder_log'
        verbose_name = 'CertificateOrderLog'
