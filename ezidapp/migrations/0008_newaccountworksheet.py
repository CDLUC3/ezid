# -*- coding: utf-8 -*-


import django.db.models
import ezidapp.models.validation
import django.db.migrations


class Migration(django.db.migrations.Migration):

    dependencies = [
        ('ezidapp', '0007_storegroup_accounttype'),
    ]

    operations = [
        django.db.migrations.RemoveField(
            model_name='newaccountworksheet',
            name='priUseRequestor',
        ),
        django.db.migrations.RemoveField(
            model_name='newaccountworksheet',
            name='reqAccountDisplayName',
        ),
        django.db.migrations.RemoveField(
            model_name='newaccountworksheet',
            name='reqAccountDisplayNameUseOrganization',
        ),
        django.db.migrations.RemoveField(
            model_name='newaccountworksheet',
            name='reqAccountEmail',
        ),
        django.db.migrations.RemoveField(
            model_name='newaccountworksheet',
            name='reqAccountEmailUsePrimary',
        ),
        django.db.migrations.RemoveField(
            model_name='newaccountworksheet',
            name='reqCrossrefEmailUseAccount',
        ),
        django.db.migrations.RemoveField(
            model_name='newaccountworksheet',
            name='reqHasExistingIdentifiers',
        ),
        django.db.migrations.RemoveField(
            model_name='newaccountworksheet',
            name='reqShoulderName',
        ),
        django.db.migrations.RemoveField(
            model_name='newaccountworksheet',
            name='reqShoulderNameUseOrganization',
        ),
        django.db.migrations.RemoveField(
            model_name='newaccountworksheet',
            name='reqShoulders',
        ),
        django.db.migrations.RemoveField(
            model_name='newaccountworksheet',
            name='reqUsername',
        ),
        django.db.migrations.RemoveField(
            model_name='newaccountworksheet',
            name='setDatacenter',
        ),
        django.db.migrations.RemoveField(
            model_name='newaccountworksheet',
            name='setExistingDatacenter',
        ),
        django.db.migrations.RemoveField(
            model_name='newaccountworksheet',
            name='setExistingGroup',
        ),
        django.db.migrations.RemoveField(
            model_name='newaccountworksheet',
            name='setNeedMinters',
        ),
        django.db.migrations.RemoveField(
            model_name='newaccountworksheet',
            name='setNeedShoulders',
        ),
        django.db.migrations.RemoveField(
            model_name='newaccountworksheet',
            name='setUsernameUseRequested',
        ),
        django.db.migrations.AddField(
            model_name='newaccountworksheet',
            name='accountEmail',
            field=django.db.models.EmailField(
                help_text=b"Defaults to the primary contact's email.",
                max_length=255,
                verbose_name=b'account email',
                blank=True,
            ),
        ),
        django.db.migrations.AddField(
            model_name='newaccountworksheet',
            name='setNonDefaultSetup',
            field=django.db.models.BooleanField(
                default=False, verbose_name=b'non-default setup'
            ),
        ),
        django.db.migrations.AddField(
            model_name='newaccountworksheet',
            name='setShoulderDisplayName',
            field=django.db.models.CharField(
                help_text=b'Defaults to the organization name.',
                max_length=255,
                verbose_name=b'shoulder display name',
                blank=True,
            ),
        ),
        django.db.migrations.AddField(
            model_name='newaccountworksheet',
            name='setUserDisplayName',
            field=django.db.models.CharField(
                help_text=b'Defaults to the organization name.',
                max_length=255,
                verbose_name=b'user display name',
                blank=True,
            ),
        ),
        django.db.migrations.AlterField(
            model_name='newaccountworksheet',
            name='orgAcronym',
            field=django.db.models.CharField(
                help_text=b'Ex: tDAR',
                max_length=255,
                verbose_name=b'acronym',
                blank=True,
            ),
        ),
        django.db.migrations.AlterField(
            model_name='newaccountworksheet',
            name='orgName',
            field=django.db.models.CharField(
                help_text=b'Ex: The Digital Archaeological Record',
                max_length=255,
                verbose_name=b'name',
                validators=[ezidapp.models.validation.nonEmpty],
            ),
        ),
    ]
