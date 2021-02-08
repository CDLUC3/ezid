# -*- coding: utf-8 -*-


import django.db.migrations
import django.db.models
import ezidapp.models.identifier
import ezidapp.models.custom_fields
import django.core.validators
import ezidapp.models.validation


class Migration(django.db.migrations.Migration):

    dependencies = [
        ('ezidapp', '0019_storeprofile'),
    ]

    operations = [
        django.db.migrations.CreateModel(
            name='StoreIdentifier',
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
                    'identifier',
                    django.db.models.CharField(
                        unique=True,
                        max_length=255,
                        validators=[ezidapp.models.validation.anyIdentifier],
                    ),
                ),
                (
                    'createTime',
                    django.db.models.IntegerField(
                        default=b'',
                        blank=True,
                        validators=[django.core.validators.MinValueValidator(0)],
                    ),
                ),
                (
                    'updateTime',
                    django.db.models.IntegerField(
                        default=b'',
                        blank=True,
                        validators=[django.core.validators.MinValueValidator(0)],
                    ),
                ),
                (
                    'status',
                    django.db.models.CharField(
                        default=b'P',
                        max_length=1,
                        choices=[
                            (b'R', b'reserved'),
                            (b'P', b'public'),
                            (b'U', b'unavailable'),
                        ],
                    ),
                ),
                (
                    'unavailableReason',
                    django.db.models.TextField(default=b'', blank=True),
                ),
                ('exported', django.db.models.BooleanField(default=True)),
                (
                    'crossrefStatus',
                    django.db.models.CharField(
                        default=b'',
                        max_length=1,
                        blank=True,
                        choices=[
                            (b'R', b'awaiting status change to public'),
                            (b'B', b'registration in progress'),
                            (b'S', b'successfully registered'),
                            (b'W', b'registered with warning'),
                            (b'F', b'registration failure'),
                        ],
                    ),
                ),
                (
                    'crossrefMessage',
                    django.db.models.TextField(default=b'', blank=True),
                ),
                (
                    'target',
                    django.db.models.URLField(
                        default=b'',
                        max_length=2000,
                        blank=True,
                        validators=[ezidapp.models.validation.unicodeBmpOnly],
                    ),
                ),
                (
                    'cm',
                    ezidapp.models.custom_fields.CompressedJsonField(
                        default=ezidapp.models.identifier.emptyDict
                    ),
                ),
                (
                    'agentRole',
                    django.db.models.CharField(
                        default=b'',
                        max_length=1,
                        blank=True,
                        choices=[(b'U', b'user'), (b'G', b'group')],
                    ),
                ),
                ('isTest', django.db.models.BooleanField(editable=False)),
                (
                    'datacenter',
                    ezidapp.models.custom_fields.NonValidatingForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        default=None,
                        blank=True,
                        to='ezidapp.StoreDatacenter',
                        null=True,
                    ),
                ),
                (
                    'owner',
                    ezidapp.models.custom_fields.NonValidatingForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        blank=True,
                        to='ezidapp.StoreUser',
                        null=True,
                    ),
                ),
                (
                    'ownergroup',
                    ezidapp.models.custom_fields.NonValidatingForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        default=None,
                        blank=True,
                        to='ezidapp.StoreGroup',
                        null=True,
                    ),
                ),
                (
                    'profile',
                    ezidapp.models.custom_fields.NonValidatingForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        default=None,
                        blank=True,
                        to='ezidapp.StoreProfile',
                        null=True,
                    ),
                ),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
