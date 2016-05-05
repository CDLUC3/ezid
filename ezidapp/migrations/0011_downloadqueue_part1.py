# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ezidapp', '0010_storeuser_inheritgroupshoulders'),
    ]

    operations = [
        migrations.AddField(
            model_name='downloadqueue',
            name='currentIndex',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='downloadqueue',
            name='toHarvest',
            field=models.TextField(default=''),
            preserve_default=False,
        ),
    ]
