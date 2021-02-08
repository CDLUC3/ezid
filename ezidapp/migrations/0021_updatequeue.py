# -*- coding: utf-8 -*-

import django.db.migrations
import django.db.models
import ezidapp.models.custom_fields
import django.core.validators


class Migration(django.db.migrations.Migration):

    dependencies = [
        ('ezidapp', '0020_storeidentifier'),
    ]

    operations = [
        django.db.migrations.CreateModel(
            name='UpdateQueue',
            fields=[
                ('seq', django.db.models.AutoField(serialize=False, primary_key=True)),
                (
                    'enqueueTime',
                    django.db.models.IntegerField(
                        default=b'',
                        blank=True,
                        validators=[django.core.validators.MinValueValidator(0)],
                    ),
                ),
                ('identifier', django.db.models.CharField(max_length=255)),
                ('object', ezidapp.models.custom_fields.StoreIdentifierObjectField()),
                (
                    'operation',
                    django.db.models.CharField(
                        max_length=1,
                        choices=[
                            (b'C', b'create'),
                            (b'U', b'update'),
                            (b'D', b'delete'),
                        ],
                    ),
                ),
                ('updateExternalServices', django.db.models.BooleanField(default=True)),
            ],
        ),
    ]
