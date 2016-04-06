# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import ezidapp.models.validation


class Migration(migrations.Migration):

    dependencies = [
        ('ezidapp', '0007_storegroup_accounttype'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='newaccountworksheet',
            name='priUseRequestor',
        ),
        migrations.RemoveField(
            model_name='newaccountworksheet',
            name='reqAccountDisplayName',
        ),
        migrations.RemoveField(
            model_name='newaccountworksheet',
            name='reqAccountDisplayNameUseOrganization',
        ),
        migrations.RemoveField(
            model_name='newaccountworksheet',
            name='reqAccountEmail',
        ),
        migrations.RemoveField(
            model_name='newaccountworksheet',
            name='reqAccountEmailUsePrimary',
        ),
        migrations.RemoveField(
            model_name='newaccountworksheet',
            name='reqCrossrefEmailUseAccount',
        ),
        migrations.RemoveField(
            model_name='newaccountworksheet',
            name='reqHasExistingIdentifiers',
        ),
        migrations.RemoveField(
            model_name='newaccountworksheet',
            name='reqShoulderName',
        ),
        migrations.RemoveField(
            model_name='newaccountworksheet',
            name='reqShoulderNameUseOrganization',
        ),
        migrations.RemoveField(
            model_name='newaccountworksheet',
            name='reqShoulders',
        ),
        migrations.RemoveField(
            model_name='newaccountworksheet',
            name='reqUsername',
        ),
        migrations.RemoveField(
            model_name='newaccountworksheet',
            name='setDatacenter',
        ),
        migrations.RemoveField(
            model_name='newaccountworksheet',
            name='setExistingDatacenter',
        ),
        migrations.RemoveField(
            model_name='newaccountworksheet',
            name='setExistingGroup',
        ),
        migrations.RemoveField(
            model_name='newaccountworksheet',
            name='setNeedMinters',
        ),
        migrations.RemoveField(
            model_name='newaccountworksheet',
            name='setNeedShoulders',
        ),
        migrations.RemoveField(
            model_name='newaccountworksheet',
            name='setUsernameUseRequested',
        ),
        migrations.AddField(
            model_name='newaccountworksheet',
            name='accountEmail',
            field=models.EmailField(help_text=b"Defaults to the primary contact's email.", max_length=255, verbose_name=b'account email', blank=True),
        ),
        migrations.AddField(
            model_name='newaccountworksheet',
            name='setNonDefaultSetup',
            field=models.BooleanField(default=False, verbose_name=b'non-default setup'),
        ),
        migrations.AddField(
            model_name='newaccountworksheet',
            name='setShoulderDisplayName',
            field=models.CharField(help_text=b'Defaults to the organization name.', max_length=255, verbose_name=b'shoulder display name', blank=True),
        ),
        migrations.AddField(
            model_name='newaccountworksheet',
            name='setUserDisplayName',
            field=models.CharField(help_text=b'Defaults to the organization name.', max_length=255, verbose_name=b'user display name', blank=True),
        ),
        migrations.AlterField(
            model_name='newaccountworksheet',
            name='orgAcronym',
            field=models.CharField(help_text=b'Ex: tDAR', max_length=255, verbose_name=b'acronym', blank=True),
        ),
        migrations.AlterField(
            model_name='newaccountworksheet',
            name='orgName',
            field=models.CharField(help_text=b'Ex: The Digital Archaeological Record', max_length=255, verbose_name=b'name', validators=[ezidapp.models.validation.nonEmpty]),
        ),
    ]
