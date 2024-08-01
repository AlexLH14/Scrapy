from django.db import models

from src.apps.cron.enumeration import CronNames


class CronJobModel(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    job = models.TextField(choices=CronNames.values())
    description = models.TextField(null=True)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = 'cirbox_cron_jobs'
        app_label = 'src'
        verbose_name = 'CronJob'
