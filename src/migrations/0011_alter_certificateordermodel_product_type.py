# Generated by Django 3.2.13 on 2022-07-07 14:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('src', '0010_cronjobmodel_cronlogmodel'),
    ]

    operations = [
        migrations.AlterField(
            model_name='certificateordermodel',
            name='product_type',
            field=models.TextField(choices=[('renta', 'RENTA'), ('vida_laboral', 'VIDA_LABORAL'), ('cirbe', 'CIRBE'), ('iva', 'IVA'), ('pensiones', 'PENSIONES')]),
        ),
    ]
