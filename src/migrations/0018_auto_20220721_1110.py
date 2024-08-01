# Generated by Django 3.2.13 on 2022-07-21 09:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('src', '0017_auto_20220715_2027'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cronjobmodel',
            name='job',
            field=models.TextField(choices=[('PROCESAR_PENDIENTES', 'PROCESAR_PENDIENTES'), ('PROCESAR_ERROR', 'PROCESAR_ERROR'), ('PROCESAR_PROCESANDO', 'PROCESAR_PROCESANDO'), ('FLAG_SPIDERS', 'FLAG_SPIDERS')]),
        ),
        migrations.AlterField(
            model_name='cronlogmodel',
            name='name',
            field=models.TextField(choices=[('PROCESAR_PENDIENTES', 'PROCESAR_PENDIENTES'), ('PROCESAR_ERROR', 'PROCESAR_ERROR'), ('PROCESAR_PROCESANDO', 'PROCESAR_PROCESANDO'), ('FLAG_SPIDERS', 'FLAG_SPIDERS')]),
        ),
    ]
