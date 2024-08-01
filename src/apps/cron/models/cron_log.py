from django.db import models

from src.apps.cron.enumeration import CronNames


class CronLogModel(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    name = models.TextField(choices=CronNames.values())
    extra_info = models.TextField(null=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True)

    class Meta:
        db_table = 'cirbox_cron_log'
        app_label = 'src'
        verbose_name = 'CronLog'
