from django.db import models


class AccessPermission(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    key = models.TextField(unique=True)
    value = models.TextField()

    class Meta:
        db_table = 'cirbox_access_permission'
        app_label = 'src'
        verbose_name = 'AccessPermission'
