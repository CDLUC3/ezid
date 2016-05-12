# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ezidapp', '0011_downloadqueue_part1'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='downloadqueue',
            name='coOwners',
        ),
        migrations.RemoveField(
            model_name='downloadqueue',
            name='currentOwner',
        ),
    ]
