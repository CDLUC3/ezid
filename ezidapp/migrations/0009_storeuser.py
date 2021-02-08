# -*- coding: utf-8 -*-


import django.db.migrations
import django.db.models
import django.core.validators
import ezidapp.models.validation


class Migration(django.db.migrations.Migration):

    dependencies = [
        ('ezidapp', '0008_newaccountworksheet'),
    ]

    operations = [
        django.db.migrations.CreateModel(
            name='StoreUser',
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
                        validators=[ezidapp.models.validation.agentPid],
                    ),
                ),
                (
                    'username',
                    django.db.models.CharField(
                        unique=True,
                        max_length=32,
                        validators=[
                            django.core.validators.RegexValidator(
                                '^[a-z0-9]+([-_.][a-z0-9]+)*$',
                                'Invalid username.',
                                flags=2,
                            )
                        ],
                    ),
                ),
                (
                    'displayName',
                    django.db.models.CharField(
                        max_length=255,
                        verbose_name=b'display name',
                        validators=[ezidapp.models.validation.nonEmpty],
                    ),
                ),
                (
                    'accountEmail',
                    django.db.models.EmailField(
                        help_text=b'The email address to which account-related notifications are sent other than Crossref notifications.',
                        max_length=255,
                        verbose_name=b'account email',
                    ),
                ),
                (
                    'primaryContactName',
                    django.db.models.CharField(
                        max_length=255,
                        verbose_name=b'name',
                        validators=[ezidapp.models.validation.nonEmpty],
                    ),
                ),
                (
                    'primaryContactEmail',
                    django.db.models.EmailField(max_length=255, verbose_name=b'email'),
                ),
                (
                    'primaryContactPhone',
                    django.db.models.CharField(
                        max_length=255,
                        verbose_name=b'phone',
                        validators=[ezidapp.models.validation.nonEmpty],
                    ),
                ),
                (
                    'secondaryContactName',
                    django.db.models.CharField(
                        max_length=255, verbose_name=b'name', blank=True
                    ),
                ),
                (
                    'secondaryContactEmail',
                    django.db.models.EmailField(
                        max_length=255, verbose_name=b'email', blank=True
                    ),
                ),
                (
                    'secondaryContactPhone',
                    django.db.models.CharField(
                        max_length=255, verbose_name=b'phone', blank=True
                    ),
                ),
                (
                    'inheritGroupShoulders',
                    django.db.models.BooleanField(
                        default=True,
                        help_text=b'If checked, the user has access to all group shoulders; if not checked, the user has access only to the shoulders explicitly selected below.',
                        verbose_name=b'inherit group shoulders',
                    ),
                ),
                (
                    'crossrefEnabled',
                    django.db.models.BooleanField(
                        default=False, verbose_name=b'Crossref enabled'
                    ),
                ),
                (
                    'crossrefEmail',
                    django.db.models.EmailField(
                        max_length=255, verbose_name=b'Crossref email', blank=True
                    ),
                ),
                (
                    'isGroupAdministrator',
                    django.db.models.BooleanField(
                        default=False, verbose_name=b'group administrator'
                    ),
                ),
                (
                    'isRealmAdministrator',
                    django.db.models.BooleanField(
                        default=False, verbose_name=b'realm administrator'
                    ),
                ),
                (
                    'isSuperuser',
                    django.db.models.BooleanField(
                        default=False, verbose_name=b'superuser'
                    ),
                ),
                (
                    'loginEnabled',
                    django.db.models.BooleanField(
                        default=True, verbose_name=b'login enabled'
                    ),
                ),
                (
                    'password',
                    django.db.models.CharField(
                        max_length=128, verbose_name=b'set password', blank=True
                    ),
                ),
                ('notes', django.db.models.TextField(blank=True)),
                (
                    'group',
                    django.db.models.ForeignKey(
                        to='ezidapp.StoreGroup',
                        on_delete=django.db.models.deletion.PROTECT,
                    ),
                ),
                (
                    'proxies',
                    django.db.models.ManyToManyField(
                        help_text=b'A proxy is another user that may act on behalf of this user.',
                        to='ezidapp.StoreUser',
                        blank=True,
                    ),
                ),
                (
                    'realm',
                    django.db.models.ForeignKey(
                        to='ezidapp.StoreRealm',
                        on_delete=django.db.models.deletion.PROTECT,
                    ),
                ),
                (
                    'shoulders',
                    django.db.models.ManyToManyField(to='ezidapp.Shoulder', blank=True),
                ),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
            },
        ),
    ]
