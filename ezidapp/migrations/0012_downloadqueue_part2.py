# -*- coding: utf-8 -*-


import django.db.migrations
import django.db.models


class Migration(django.db.migrations.Migration):

    dependencies = [
        ('ezidapp', '0011_downloadqueue_part1'),
    ]

    operations = [
        django.db.migrations.RemoveField(
            model_name='downloadqueue',
            name='coOwners',
        ),
        django.db.migrations.RemoveField(
            model_name='downloadqueue',
            name='currentOwner',
        ),
    ]
