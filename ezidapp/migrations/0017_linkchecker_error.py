# -*- coding: utf-8 -*-


import django.db.migrations
import django.db.models


class Migration(django.db.migrations.Migration):

    dependencies = [
        ('ezidapp', '0016_statistics'),
    ]

    operations = [
        django.db.migrations.AddField(
            model_name='linkchecker',
            name='error',
            field=django.db.models.TextField(blank=True),
        ),
    ]
