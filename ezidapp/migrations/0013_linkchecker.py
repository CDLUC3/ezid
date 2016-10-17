# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('ezidapp', '0012_downloadqueue_part2'),
    ]

    operations = [
        migrations.CreateModel(
            name='LinkChecker',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('identifier', models.CharField(unique=True, max_length=255)),
                ('owner_id', models.IntegerField(db_index=True)),
                ('target', models.URLField(max_length=2000)),
                ('lastCheckTime', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ('numFailures', models.IntegerField(default=0, db_index=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('returnCode', models.IntegerField(null=True, blank=True)),
                ('mimeType', models.CharField(max_length=255, blank=True)),
                ('size', models.IntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('hash', models.CharField(max_length=32, blank=True)),
            ],
        ),
    ]
