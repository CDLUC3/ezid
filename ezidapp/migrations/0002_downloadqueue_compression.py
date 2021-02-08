# -*- coding: utf-8 -*-


import django.db.migrations
import django.db.models


class Migration(django.db.migrations.Migration):

    dependencies = [
        ('ezidapp', '0001_initial'),
    ]

    operations = [
        django.db.migrations.AddField(
            model_name='downloadqueue',
            name='compression',
            field=django.db.models.CharField(
                default='G', max_length=1, choices=[(b'G', b'GZIP'), (b'Z', b'ZIP')]
            ),
            preserve_default=False,
        ),
    ]
