# Generated by Django 3.2.13 on 2022-07-09 11:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('src', '0012_certificateordermodel_updated'),
    ]

    operations = [
        migrations.AlterField(
            model_name='certificateordermodel',
            name='product_type',
            field=models.TextField(choices=[('renta', 'RENTA'), ('vida_laboral', 'VIDA_LABORAL'), ('cirbe', 'CIRBE'), ('iva', 'IVA'), ('pensiones', 'PENSIONES'), ('sociedades', 'SOCIEDADES'), ('base_cotizacion', 'BASE_COTIZACION'), ('modelo_200', 'MODELO_200'), ('modelo_303', 'MODELO_303'), ('modelo_347', 'MODELO_347'), ('modelo_390', 'MODELO_390')]),
        ),
    ]
