# -*- coding: utf-8 -*-


import django.db.migrations
import django.db.models
import django.core.validators


class Migration(django.db.migrations.Migration):

    dependencies = [
        ('ezidapp', '0018_binderqueue'),
    ]

    operations = [
        django.db.migrations.CreateModel(
            name='StoreProfile',
            fields=[
                (
                    'id',
                    django.db.models.AutoField(
                        verbose_name='ID',
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                (
                    'label',
                    django.db.models.CharField(
                        unique=True,
                        max_length=32,
                        validators=[
                            django.core.validators.RegexValidator(
                                '^[a-z0-9]+([-_.][a-z0-9]+)*$',
                                'Invalid profile name.',
                                flags=2,
                            )
                        ],
                    ),
                ),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
