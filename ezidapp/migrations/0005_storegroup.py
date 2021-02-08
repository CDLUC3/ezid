# -*- coding: utf-8 -*-


import django.db.models
import django.core.validators
import ezidapp.models.validation
import django.db.migrations


class Migration(django.db.migrations.Migration):

    dependencies = [
        ('ezidapp', '0004_shoulder_istest'),
    ]

    operations = [
        django.db.migrations.CreateModel(
            name='StoreGroup',
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
                    'pid',
                    django.db.models.CharField(
                        unique=True,
                        max_length=255,
                        validators=[ezidapp.models.validation.agentPidOrEmpty],
                    ),
                ),
                (
                    'groupname',
                    django.db.models.CharField(
                        unique=True,
                        max_length=32,
                        validators=[
                            django.core.validators.RegexValidator(
                                '^[a-z0-9]+([-_.][a-z0-9]+)*$',
                                'Invalid groupname.',
                                flags=2,
                            )
                        ],
                    ),
                ),
                (
                    'organizationName',
                    django.db.models.CharField(
                        max_length=255,
                        verbose_name=b'name',
                        validators=[ezidapp.models.validation.nonEmpty],
                    ),
                ),
                (
                    'organizationAcronym',
                    django.db.models.CharField(
                        max_length=255, verbose_name=b'acronym', blank=True
                    ),
                ),
                (
                    'organizationUrl',
                    django.db.models.URLField(max_length=255, verbose_name=b'URL'),
                ),
                (
                    'organizationStreetAddress',
                    django.db.models.CharField(
                        max_length=255,
                        verbose_name=b'street address',
                        validators=[ezidapp.models.validation.nonEmpty],
                    ),
                ),
                (
                    'agreementOnFile',
                    django.db.models.BooleanField(
                        default=False, verbose_name=b'agreement on file'
                    ),
                ),
                (
                    'crossrefEnabled',
                    django.db.models.BooleanField(
                        default=False, verbose_name=b'Crossref enabled'
                    ),
                ),
                ('notes', django.db.models.TextField(blank=True)),
                (
                    'realm',
                    django.db.models.ForeignKey(
                        to='ezidapp.StoreRealm',
                        on_delete=django.db.models.deletion.PROTECT,
                    ),
                ),
            ],
            options={
                'verbose_name': 'group',
                'verbose_name_plural': 'groups',
            },
        ),
        django.db.migrations.AlterField(
            model_name='newaccountworksheet',
            name='orgUrl',
            field=django.db.models.URLField(
                max_length=255, verbose_name=b'URL', blank=True
            ),
        ),
        django.db.migrations.AlterField(
            model_name='newaccountworksheet',
            name='priEmail',
            field=django.db.models.EmailField(
                max_length=255, verbose_name=b'email', blank=True
            ),
        ),
        django.db.migrations.AlterField(
            model_name='newaccountworksheet',
            name='reqAccountEmail',
            field=django.db.models.EmailField(
                max_length=255, verbose_name=b'account email', blank=True
            ),
        ),
        django.db.migrations.AlterField(
            model_name='newaccountworksheet',
            name='reqCrossrefEmail',
            field=django.db.models.EmailField(
                max_length=255, verbose_name=b'Crossref email', blank=True
            ),
        ),
        django.db.migrations.AlterField(
            model_name='newaccountworksheet',
            name='reqEmail',
            field=django.db.models.EmailField(
                max_length=255, verbose_name=b'email', blank=True
            ),
        ),
        django.db.migrations.AlterField(
            model_name='newaccountworksheet',
            name='secEmail',
            field=django.db.models.EmailField(
                max_length=255, verbose_name=b'email', blank=True
            ),
        ),
        django.db.migrations.AlterField(
            model_name='shoulder',
            name='minter',
            field=django.db.models.URLField(max_length=255, blank=True),
        ),
        django.db.migrations.AddField(
            model_name='storegroup',
            name='shoulders',
            field=django.db.models.ManyToManyField(to='ezidapp.Shoulder', blank=True),
        ),
    ]
