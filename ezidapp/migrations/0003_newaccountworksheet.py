# -*- coding: utf-8 -*-


import django.db.migrations
import django.db.models


class Migration(django.db.migrations.Migration):

    dependencies = [
        ('ezidapp', '0002_downloadqueue_compression'),
    ]

    operations = [
        django.db.migrations.AddField(
            model_name='newaccountworksheet',
            name='reqAccountDisplayName',
            field=django.db.models.CharField(
                max_length=255, verbose_name=b'account display name', blank=True
            ),
        ),
        django.db.migrations.AddField(
            model_name='newaccountworksheet',
            name='reqAccountDisplayNameUseOrganization',
            field=django.db.models.BooleanField(
                default=False, verbose_name=b'use organization name'
            ),
        ),
        django.db.migrations.AddField(
            model_name='newaccountworksheet',
            name='reqShoulderName',
            field=django.db.models.CharField(
                max_length=255, verbose_name=b'shoulder name', blank=True
            ),
        ),
        django.db.migrations.AddField(
            model_name='newaccountworksheet',
            name='reqShoulderNameUseOrganization',
            field=django.db.models.BooleanField(
                default=False, verbose_name=b'use organization name'
            ),
        ),
        django.db.migrations.AddField(
            model_name='newaccountworksheet',
            name='setDatacenter',
            field=django.db.models.CharField(
                max_length=255, verbose_name=b'datacenter', blank=True
            ),
        ),
        django.db.migrations.AddField(
            model_name='newaccountworksheet',
            name='setExistingDatacenter',
            field=django.db.models.BooleanField(
                default=False, verbose_name=b'existing datacenter'
            ),
        ),
        django.db.migrations.AlterField(
            model_name='newaccountworksheet',
            name='reqShoulders',
            field=django.db.models.CharField(
                max_length=255, verbose_name=b'requested shoulder branding', blank=True
            ),
        ),
    ]
