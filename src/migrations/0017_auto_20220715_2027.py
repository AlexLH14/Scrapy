# Generated by Django 3.2.13 on 2022-07-15 18:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('src', '0016_alter_certificateordermodel_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cronjobmodel',
            name='job',
            field=models.TextField(choices=[('PROCESAR_PENDIENTES', 'PROCESAR_PENDIENTES'), ('PROCESAR_ERROR', 'PROCESAR_ERROR'), ('FLAG_SPIDERS', 'FLAG_SPIDERS')]),
        ),
        migrations.AlterField(
            model_name='cronlogmodel',
            name='name',
            field=models.TextField(choices=[('PROCESAR_PENDIENTES', 'PROCESAR_PENDIENTES'), ('PROCESAR_ERROR', 'PROCESAR_ERROR'), ('FLAG_SPIDERS', 'FLAG_SPIDERS')]),
        ),
    ]
