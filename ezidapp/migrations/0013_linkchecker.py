# -*- coding: utf-8 -*-


import django.db.migrations
import django.db.models
import django.core.validators


class Migration(django.db.migrations.Migration):

    dependencies = [
        ('ezidapp', '0012_downloadqueue_part2'),
    ]

    operations = [
        django.db.migrations.CreateModel(
            name='LinkChecker',
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
                ('identifier', django.db.models.CharField(unique=True, max_length=255)),
                ('owner_id', django.db.models.IntegerField(db_index=True)),
                ('target', django.db.models.URLField(max_length=2000)),
                (
                    'lastCheckTime',
                    django.db.models.IntegerField(
                        default=0,
                        validators=[django.core.validators.MinValueValidator(0)],
                    ),
                ),
                (
                    'numFailures',
                    django.db.models.IntegerField(
                        default=0,
                        db_index=True,
                        validators=[django.core.validators.MinValueValidator(0)],
                    ),
                ),
                ('returnCode', django.db.models.IntegerField(null=True, blank=True)),
                ('mimeType', django.db.models.CharField(max_length=255, blank=True)),
                (
                    'size',
                    django.db.models.IntegerField(
                        blank=True,
                        null=True,
                        validators=[django.core.validators.MinValueValidator(0)],
                    ),
                ),
                ('hash', django.db.models.CharField(max_length=32, blank=True)),
            ],
        ),
    ]
