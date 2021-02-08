# -*- coding: utf-8 -*-


import django.db.migrations
import django.db.models


class Migration(django.db.migrations.Migration):

    dependencies = [
        ('ezidapp', '0017_linkchecker_error'),
    ]

    operations = [
        django.db.migrations.CreateModel(
            name='BinderQueue',
            fields=[
                ('seq', django.db.models.AutoField(serialize=False, primary_key=True)),
                ('enqueueTime', django.db.models.IntegerField()),
                ('identifier', django.db.models.CharField(max_length=255)),
                ('metadata', django.db.models.BinaryField()),
                (
                    'operation',
                    django.db.models.CharField(
                        max_length=1, choices=[(b'O', b'overwrite'), (b'D', b'delete')]
                    ),
                ),
                ('error', django.db.models.TextField(blank=True)),
                ('errorIsPermanent', django.db.models.BooleanField(default=False)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
