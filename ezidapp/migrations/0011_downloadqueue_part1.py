# -*- coding: utf-8 -*-


import django.db.migrations
import django.db.models


class Migration(django.db.migrations.Migration):

    dependencies = [
        ('ezidapp', '0010_storeuser_inheritgroupshoulders'),
    ]

    operations = [
        django.db.migrations.AddField(
            model_name='downloadqueue',
            name='currentIndex',
            field=django.db.models.IntegerField(default=0),
        ),
        django.db.migrations.AddField(
            model_name='downloadqueue',
            name='toHarvest',
            field=django.db.models.TextField(default=''),
            preserve_default=False,
        ),
    ]
