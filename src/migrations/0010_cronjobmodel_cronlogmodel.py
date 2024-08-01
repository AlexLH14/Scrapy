# Generated by Django 3.2.13 on 2022-07-02 20:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('src', '0009_log'),
    ]

    operations = [
        migrations.CreateModel(
            name='CronJobModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('job', models.TextField(choices=[('PROCESAR RENTA', 'PROCESAR_RENTA')])),
                ('description', models.TextField(null=True)),
                ('active', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'CronJob',
                'db_table': 'cirbox_cron_jobs',
            },
        ),
        migrations.CreateModel(
            name='CronLogModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('name', models.TextField(choices=[('PROCESAR RENTA', 'PROCESAR_RENTA')])),
                ('extra_info', models.TextField(null=True)),
                ('start_date', models.DateTimeField()),
                ('end_date', models.DateTimeField(null=True)),
            ],
            options={
                'verbose_name': 'CronLog',
                'db_table': 'cirbox_cron_log',
            },
        ),
    ]