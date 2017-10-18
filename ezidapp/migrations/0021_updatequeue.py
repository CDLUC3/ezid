# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import ezidapp.models.custom_fields
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('ezidapp', '0020_storeidentifier'),
    ]

    operations = [
        migrations.CreateModel(
            name='UpdateQueue',
            fields=[
                ('seq', models.AutoField(serialize=False, primary_key=True)),
                ('enqueueTime', models.IntegerField(default=b'', blank=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('identifier', models.CharField(max_length=255)),
                ('object', ezidapp.models.custom_fields.StoreIdentifierObjectField()),
                ('operation', models.CharField(max_length=1, choices=[(b'C', b'create'), (b'U', b'update'), (b'D', b'delete')])),
                ('updateExternalServices', models.BooleanField(default=True)),
            ],
        ),
    ]
