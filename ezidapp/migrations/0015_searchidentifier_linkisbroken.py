# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ezidapp', '0014_linkchecker'),
    ]

    operations = [
        migrations.AddField(
            model_name='searchidentifier',
            name='linkIsBroken',
            field=models.BooleanField(default=False, editable=False),
        ),
    ]
