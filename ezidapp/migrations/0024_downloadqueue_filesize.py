# -*- coding: utf-8 -*-


import django.db.models
import django.db.migrations


class Migration(django.db.migrations.Migration):

    dependencies = [
        ('ezidapp', '0023_registrationqueue_tweak'),
    ]

    operations = [
        django.db.migrations.AlterField(
            model_name='downloadqueue',
            name='fileSize',
            field=django.db.models.BigIntegerField(null=True, blank=True),
        ),
    ]
