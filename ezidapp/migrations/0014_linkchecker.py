# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ezidapp', '0013_linkchecker'),
    ]

    operations = [
        migrations.AddField(
            model_name='linkchecker',
            name='isBad',
            field=models.BooleanField(default=False, editable=False),
        ),
        migrations.AlterIndexTogether(
            name='linkchecker',
            index_together=set([('owner_id', 'isBad', 'lastCheckTime')]),
        ),
    ]
