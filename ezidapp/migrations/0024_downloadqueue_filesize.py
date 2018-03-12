# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ezidapp', '0023_registrationqueue_tweak'),
    ]

    operations = [
        migrations.AlterField(
            model_name='downloadqueue',
            name='fileSize',
            field=models.BigIntegerField(null=True, blank=True),
        ),
    ]
