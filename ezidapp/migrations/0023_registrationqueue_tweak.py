# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ezidapp', '0022_crossrefqueue_tweak'),
    ]

    operations = [
        migrations.AlterField(
            model_name='binderqueue',
            name='operation',
            field=models.CharField(max_length=1, choices=[(b'C', b'create'), (b'U', b'update'), (b'D', b'delete')]),
        ),
        migrations.AlterField(
            model_name='datacitequeue',
            name='operation',
            field=models.CharField(max_length=1, choices=[(b'C', b'create'), (b'U', b'update'), (b'D', b'delete')]),
        ),
    ]
