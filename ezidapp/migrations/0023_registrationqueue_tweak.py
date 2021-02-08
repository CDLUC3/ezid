# -*- coding: utf-8 -*-


import django.db.models
import django.db.migrations


class Migration(django.db.migrations.Migration):

    dependencies = [
        ('ezidapp', '0022_crossrefqueue_tweak'),
    ]

    operations = [
        django.db.migrations.AlterField(
            model_name='binderqueue',
            name='operation',
            field=django.db.models.CharField(
                max_length=1,
                choices=[(b'C', b'create'), (b'U', b'update'), (b'D', b'delete')],
            ),
        ),
        django.db.migrations.AlterField(
            model_name='datacitequeue',
            name='operation',
            field=django.db.models.CharField(
                max_length=1,
                choices=[(b'C', b'create'), (b'U', b'update'), (b'D', b'delete')],
            ),
        ),
    ]
