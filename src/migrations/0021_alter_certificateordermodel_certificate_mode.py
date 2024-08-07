# Generated by Django 3.2.13 on 2022-11-28 20:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('src', '0020_alter_certificateordermodel_brocode'),
    ]

    operations = [
        migrations.AlterField(
            model_name='certificateordermodel',
            name='certificate_mode',
            field=models.TextField(choices=[('P12', 'P12'), ('PKCS11', 'PKCS11'), ('CLAVEPIN', 'CLAVEPIN')], default='P12'),
        ),
    ]
