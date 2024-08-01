# Generated by Django 3.2.13 on 2022-07-15 18:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('src', '0015_certificateorderlogmodel'),
    ]

    operations = [
        migrations.AlterField(
            model_name='certificateordermodel',
            name='status',
            field=models.TextField(choices=[('COMPLETADO', 'COMPLETADO'), ('ERROR', 'ERROR'), ('PENDIENTE', 'PENDIENTE'), ('PROCESANDO', 'PROCESANDO'), ('NO_PROGRAMADO', 'NO_PROGRAMADO')], default='PENDIENTE'),
        ),
    ]