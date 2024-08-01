from django.db import models


class Log(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    context = models.TextField(null=True)
    error = models.TextField(null=True)
    response = models.TextField(null=True)

    class Meta:
        db_table = 'cirbox_log'
        verbose_name = 'Log'
