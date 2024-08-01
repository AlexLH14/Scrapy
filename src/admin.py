from django.contrib import admin

from .apps.certificate_order.models.certificate_order import CertificateOrderModel
from .apps.certificate_order.models.certificate_order_log import CertificateOrderLogModel
from .apps.cron.models.cron_job import CronJobModel
from .apps.cron.models.cron_log import CronLogModel
from .models import AccessPermission, Log


@admin.register(AccessPermission)
class CoockieAdmin(admin.ModelAdmin):
    list_display = ("created", "key", "value")


@admin.register(CertificateOrderModel)
class CertificateOrder(admin.ModelAdmin):
    list_display = ("created", "updated", "certificate_id", "product_type", "extra_info", "status",
                    "error", "updated", "attempts", "brocode", "certificate_mode")


@admin.register(CertificateOrderLogModel)
class CertificateOrderLog(admin.ModelAdmin):
    list_display = ("created", "context", "event", "extra_info", "certificate_order")


@admin.register(Log)
class LogAdmin(admin.ModelAdmin):
    list_display = ("created", "context", "error", "response")


@admin.register(CronJobModel)
class CronJobModelAdmin(admin.ModelAdmin):
    list_display = ("created", "job", "description", "active")


@admin.register(CronLogModel)
class CronLogModelAdmin(admin.ModelAdmin):
    list_display = ("created", "name", "extra_info", "start_date", "end_date")
