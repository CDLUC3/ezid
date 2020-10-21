# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ezidapp', '0002_downloadqueue_compression'),
    ]

    operations = [
        migrations.AddField(
            model_name='newaccountworksheet',
            name='reqAccountDisplayName',
            field=models.CharField(
                max_length=255, verbose_name=b'account display name', blank=True
            ),
        ),
        migrations.AddField(
            model_name='newaccountworksheet',
            name='reqAccountDisplayNameUseOrganization',
            field=models.BooleanField(
                default=False, verbose_name=b'use organization name'
            ),
        ),
        migrations.AddField(
            model_name='newaccountworksheet',
            name='reqShoulderName',
            field=models.CharField(
                max_length=255, verbose_name=b'shoulder name', blank=True
            ),
        ),
        migrations.AddField(
            model_name='newaccountworksheet',
            name='reqShoulderNameUseOrganization',
            field=models.BooleanField(
                default=False, verbose_name=b'use organization name'
            ),
        ),
        migrations.AddField(
            model_name='newaccountworksheet',
            name='setDatacenter',
            field=models.CharField(
                max_length=255, verbose_name=b'datacenter', blank=True
            ),
        ),
        migrations.AddField(
            model_name='newaccountworksheet',
            name='setExistingDatacenter',
            field=models.BooleanField(
                default=False, verbose_name=b'existing datacenter'
            ),
        ),
        migrations.AlterField(
            model_name='newaccountworksheet',
            name='reqShoulders',
            field=models.CharField(
                max_length=255, verbose_name=b'requested shoulder branding', blank=True
            ),
        ),
    ]
