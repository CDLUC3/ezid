# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ezidapp', '0009_storeuser'),
    ]

    operations = [
        migrations.AlterField(
            model_name='storeuser',
            name='inheritGroupShoulders',
            field=models.BooleanField(
                default=False,
                help_text=b'If checked, the user has access to all group shoulders; if not checked, the user has access only to the shoulders explicitly selected below.',
                verbose_name=b'inherit group shoulders',
            ),
        ),
    ]
