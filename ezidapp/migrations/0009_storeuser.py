# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion
import django.core.validators
import ezidapp.models.validation


class Migration(migrations.Migration):

    dependencies = [
        ('ezidapp', '0008_newaccountworksheet'),
    ]

    operations = [
        migrations.CreateModel(
            name='StoreUser',
            fields=[
                (
                    'id',
                    models.AutoField(
                        verbose_name='ID',
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                (
                    'pid',
                    models.CharField(
                        unique=True,
                        max_length=255,
                        validators=[ezidapp.models.validation.agentPid],
                    ),
                ),
                (
                    'username',
                    models.CharField(
                        unique=True,
                        max_length=32,
                        validators=[
                            django.core.validators.RegexValidator(
                                b'^[a-z0-9]+([-_.][a-z0-9]+)*$',
                                b'Invalid username.',
                                flags=2,
                            )
                        ],
                    ),
                ),
                (
                    'displayName',
                    models.CharField(
                        max_length=255,
                        verbose_name=b'display name',
                        validators=[ezidapp.models.validation.nonEmpty],
                    ),
                ),
                (
                    'accountEmail',
                    models.EmailField(
                        help_text=b'The email address to which account-related notifications are sent other than Crossref notifications.',
                        max_length=255,
                        verbose_name=b'account email',
                    ),
                ),
                (
                    'primaryContactName',
                    models.CharField(
                        max_length=255,
                        verbose_name=b'name',
                        validators=[ezidapp.models.validation.nonEmpty],
                    ),
                ),
                (
                    'primaryContactEmail',
                    models.EmailField(max_length=255, verbose_name=b'email'),
                ),
                (
                    'primaryContactPhone',
                    models.CharField(
                        max_length=255,
                        verbose_name=b'phone',
                        validators=[ezidapp.models.validation.nonEmpty],
                    ),
                ),
                (
                    'secondaryContactName',
                    models.CharField(max_length=255, verbose_name=b'name', blank=True),
                ),
                (
                    'secondaryContactEmail',
                    models.EmailField(
                        max_length=255, verbose_name=b'email', blank=True
                    ),
                ),
                (
                    'secondaryContactPhone',
                    models.CharField(max_length=255, verbose_name=b'phone', blank=True),
                ),
                (
                    'inheritGroupShoulders',
                    models.BooleanField(
                        default=True,
                        help_text=b'If checked, the user has access to all group shoulders; if not checked, the user has access only to the shoulders explicitly selected below.',
                        verbose_name=b'inherit group shoulders',
                    ),
                ),
                (
                    'crossrefEnabled',
                    models.BooleanField(
                        default=False, verbose_name=b'Crossref enabled'
                    ),
                ),
                (
                    'crossrefEmail',
                    models.EmailField(
                        max_length=255, verbose_name=b'Crossref email', blank=True
                    ),
                ),
                (
                    'isGroupAdministrator',
                    models.BooleanField(
                        default=False, verbose_name=b'group administrator'
                    ),
                ),
                (
                    'isRealmAdministrator',
                    models.BooleanField(
                        default=False, verbose_name=b'realm administrator'
                    ),
                ),
                (
                    'isSuperuser',
                    models.BooleanField(default=False, verbose_name=b'superuser'),
                ),
                (
                    'loginEnabled',
                    models.BooleanField(default=True, verbose_name=b'login enabled'),
                ),
                (
                    'password',
                    models.CharField(
                        max_length=128, verbose_name=b'set password', blank=True
                    ),
                ),
                ('notes', models.TextField(blank=True)),
                (
                    'group',
                    models.ForeignKey(
                        to='ezidapp.StoreGroup',
                        on_delete=django.db.models.deletion.PROTECT,
                    ),
                ),
                (
                    'proxies',
                    models.ManyToManyField(
                        help_text=b'A proxy is another user that may act on behalf of this user.',
                        to='ezidapp.StoreUser',
                        blank=True,
                    ),
                ),
                (
                    'realm',
                    models.ForeignKey(
                        to='ezidapp.StoreRealm',
                        on_delete=django.db.models.deletion.PROTECT,
                    ),
                ),
                (
                    'shoulders',
                    models.ManyToManyField(to='ezidapp.Shoulder', blank=True),
                ),
            ],
            options={'verbose_name': 'user', 'verbose_name_plural': 'users',},
        ),
    ]
