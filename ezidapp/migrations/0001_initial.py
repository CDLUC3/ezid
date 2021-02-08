# -*- coding: utf-8 -*-
import django.db.migrations
import django.db.models
import datetime
import ezidapp.models.validation

# import django.db.models.deletion
import ezidapp.models.custom_fields
import django.core.validators
import ezidapp.models.identifier


class Migration(django.db.migrations.Migration):

    dependencies = []

    operations = [
        django.db.migrations.CreateModel(
            name='CrossrefQueue',
            fields=[
                ('seq', django.db.models.AutoField(serialize=False, primary_key=True)),
                (
                    'identifier',
                    django.db.models.CharField(max_length=255, db_index=True),
                ),
                ('owner', django.db.models.CharField(max_length=255, db_index=True)),
                ('metadata', django.db.models.BinaryField()),
                (
                    'operation',
                    django.db.models.CharField(
                        max_length=1,
                        choices=[
                            (b'C', b'create'),
                            (b'M', b'modify'),
                            (b'D', b'delete'),
                        ],
                    ),
                ),
                (
                    'status',
                    django.db.models.CharField(
                        default=b'U',
                        max_length=1,
                        db_index=True,
                        choices=[
                            (b'U', b'awaiting submission'),
                            (b'S', b'submitted'),
                            (b'W', b'registered with warning'),
                            (b'F', b'registration failed'),
                        ],
                    ),
                ),
                ('message', django.db.models.TextField(blank=True)),
                ('batchId', django.db.models.CharField(max_length=36, blank=True)),
                ('submitTime', django.db.models.IntegerField(null=True, blank=True)),
            ],
        ),
        django.db.migrations.CreateModel(
            name='DataciteQueue',
            fields=[
                ('seq', django.db.models.AutoField(serialize=False, primary_key=True)),
                ('enqueueTime', django.db.models.IntegerField()),
                ('identifier', django.db.models.CharField(max_length=255)),
                ('metadata', django.db.models.BinaryField()),
                (
                    'operation',
                    django.db.models.CharField(
                        max_length=1, choices=[(b'O', b'overwrite'), (b'D', b'delete')]
                    ),
                ),
                ('error', django.db.models.TextField(blank=True)),
                ('errorIsPermanent', django.db.models.BooleanField(default=False)),
            ],
        ),
        django.db.migrations.CreateModel(
            name='DownloadQueue',
            fields=[
                ('seq', django.db.models.AutoField(serialize=False, primary_key=True)),
                ('requestTime', django.db.models.IntegerField()),
                ('rawRequest', django.db.models.TextField()),
                ('requestor', django.db.models.CharField(max_length=255)),
                ('coOwners', django.db.models.TextField(blank=True)),
                (
                    'format',
                    django.db.models.CharField(
                        max_length=1,
                        choices=[(b'A', b'ANVL'), (b'C', b'CSV'), (b'X', b'XML')],
                    ),
                ),
                ('columns', django.db.models.TextField(blank=True)),
                ('constraints', django.db.models.TextField(blank=True)),
                ('options', django.db.models.TextField(blank=True)),
                ('notify', django.db.models.TextField(blank=True)),
                (
                    'stage',
                    django.db.models.CharField(
                        default=b'C',
                        max_length=1,
                        choices=[
                            (b'C', b'create'),
                            (b'H', b'harvest'),
                            (b'Z', b'compress'),
                            (b'D', b'delete'),
                            (b'M', b'move'),
                            (b'N', b'notify'),
                        ],
                    ),
                ),
                ('filename', django.db.models.CharField(max_length=10, blank=True)),
                (
                    'currentOwner',
                    django.db.models.CharField(max_length=255, blank=True),
                ),
                ('lastId', django.db.models.CharField(max_length=255, blank=True)),
                ('fileSize', django.db.models.IntegerField(null=True, blank=True)),
            ],
        ),
        django.db.migrations.CreateModel(
            name='NewAccountWorksheet',
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
                    'requestDate',
                    django.db.models.DateField(
                        default=datetime.date.today, verbose_name=b'request date'
                    ),
                ),
                (
                    'orgName',
                    django.db.models.CharField(
                        max_length=255,
                        verbose_name=b'name',
                        validators=[ezidapp.models.validation.nonEmpty],
                    ),
                ),
                (
                    'orgAcronym',
                    django.db.models.CharField(
                        max_length=255, verbose_name=b'acronym', blank=True
                    ),
                ),
                (
                    'orgUrl',
                    django.db.models.URLField(
                        blank=True,
                        max_length=255,
                        verbose_name=b'URL',
                        validators=[ezidapp.models.validation.unicodeBmpOnly],
                    ),
                ),
                (
                    'orgStreetAddress',
                    django.db.models.CharField(
                        max_length=255, verbose_name=b'street address', blank=True
                    ),
                ),
                (
                    'reqName',
                    django.db.models.CharField(
                        max_length=255, verbose_name=b'name', blank=True
                    ),
                ),
                (
                    'reqEmail',
                    django.db.models.EmailField(
                        blank=True,
                        max_length=255,
                        verbose_name=b'email',
                        validators=[ezidapp.models.validation.unicodeBmpOnly],
                    ),
                ),
                (
                    'reqPhone',
                    django.db.models.CharField(
                        max_length=255, verbose_name=b'phone', blank=True
                    ),
                ),
                (
                    'priUseRequestor',
                    django.db.models.BooleanField(
                        default=False, verbose_name=b'use requestor'
                    ),
                ),
                (
                    'priName',
                    django.db.models.CharField(
                        max_length=255, verbose_name=b'name', blank=True
                    ),
                ),
                (
                    'priEmail',
                    django.db.models.EmailField(
                        blank=True,
                        max_length=255,
                        verbose_name=b'email',
                        validators=[ezidapp.models.validation.unicodeBmpOnly],
                    ),
                ),
                (
                    'priPhone',
                    django.db.models.CharField(
                        max_length=255, verbose_name=b'phone', blank=True
                    ),
                ),
                (
                    'secName',
                    django.db.models.CharField(
                        max_length=255, verbose_name=b'name', blank=True
                    ),
                ),
                (
                    'secEmail',
                    django.db.models.EmailField(
                        blank=True,
                        max_length=255,
                        verbose_name=b'email',
                        validators=[ezidapp.models.validation.unicodeBmpOnly],
                    ),
                ),
                (
                    'secPhone',
                    django.db.models.CharField(
                        max_length=255, verbose_name=b'phone', blank=True
                    ),
                ),
                (
                    'reqUsername',
                    django.db.models.CharField(
                        max_length=255, verbose_name=b'requested username', blank=True
                    ),
                ),
                (
                    'reqAccountEmailUsePrimary',
                    django.db.models.BooleanField(
                        default=False, verbose_name=b"use primary contact's email"
                    ),
                ),
                (
                    'reqAccountEmail',
                    django.db.models.EmailField(
                        blank=True,
                        max_length=255,
                        verbose_name=b'account email',
                        validators=[ezidapp.models.validation.unicodeBmpOnly],
                    ),
                ),
                (
                    'reqArks',
                    django.db.models.BooleanField(default=False, verbose_name=b'ARKs'),
                ),
                (
                    'reqDois',
                    django.db.models.BooleanField(default=False, verbose_name=b'DOIs'),
                ),
                (
                    'reqShoulders',
                    django.db.models.CharField(
                        max_length=255,
                        verbose_name=b'requested shoulders/ branding',
                        blank=True,
                    ),
                ),
                (
                    'reqCrossref',
                    django.db.models.BooleanField(
                        default=False, verbose_name=b'Crossref'
                    ),
                ),
                (
                    'reqCrossrefEmailUseAccount',
                    django.db.models.BooleanField(
                        default=False, verbose_name=b'use account email'
                    ),
                ),
                (
                    'reqCrossrefEmail',
                    django.db.models.EmailField(
                        blank=True,
                        max_length=255,
                        verbose_name=b'Crossref email',
                        validators=[ezidapp.models.validation.unicodeBmpOnly],
                    ),
                ),
                (
                    'reqHasExistingIdentifiers',
                    django.db.models.BooleanField(
                        default=False, verbose_name=b'has existing identifiers'
                    ),
                ),
                (
                    'reqComments',
                    django.db.models.TextField(
                        verbose_name=b'requestor comments', blank=True
                    ),
                ),
                (
                    'setRealm',
                    django.db.models.CharField(
                        max_length=255, verbose_name=b'realm', blank=True
                    ),
                ),
                (
                    'setExistingGroup',
                    django.db.models.BooleanField(
                        default=False, verbose_name=b'existing group'
                    ),
                ),
                (
                    'setGroupname',
                    django.db.models.CharField(
                        max_length=255, verbose_name=b'groupname', blank=True
                    ),
                ),
                (
                    'setUsernameUseRequested',
                    django.db.models.BooleanField(
                        default=False, verbose_name=b'use requested'
                    ),
                ),
                (
                    'setUsername',
                    django.db.models.CharField(
                        max_length=255, verbose_name=b'username', blank=True
                    ),
                ),
                (
                    'setNeedShoulders',
                    django.db.models.BooleanField(
                        default=False, verbose_name=b'new shoulders required'
                    ),
                ),
                (
                    'setNeedMinters',
                    django.db.models.BooleanField(
                        default=False, verbose_name=b'minters required'
                    ),
                ),
                (
                    'setNotes',
                    django.db.models.TextField(verbose_name=b'notes', blank=True),
                ),
                (
                    'staReady',
                    django.db.models.BooleanField(
                        default=False, verbose_name=b'request ready'
                    ),
                ),
                (
                    'staShouldersCreated',
                    django.db.models.BooleanField(
                        default=False, verbose_name=b'shoulders created'
                    ),
                ),
                (
                    'staAccountCreated',
                    django.db.models.BooleanField(
                        default=False, verbose_name=b'account created'
                    ),
                ),
            ],
        ),
        django.db.migrations.CreateModel(
            name='SearchDatacenter',
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
                    'symbol',
                    django.db.models.CharField(
                        unique=True,
                        max_length=17,
                        validators=[ezidapp.models.validation.datacenterSymbol],
                    ),
                ),
            ],
            options={
                'abstract': False,
            },
        ),
        django.db.migrations.CreateModel(
            name='SearchGroup',
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
            ],
            options={
                'abstract': False,
            },
        ),
        django.db.migrations.CreateModel(
            name='SearchIdentifier',
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
                    'searchableTarget',
                    django.db.models.CharField(max_length=255, editable=False),
                ),
                ('resourceCreator', django.db.models.TextField(editable=False)),
                ('resourceTitle', django.db.models.TextField(editable=False)),
                ('resourcePublisher', django.db.models.TextField(editable=False)),
                ('resourcePublicationDate', django.db.models.TextField(editable=False)),
                (
                    'searchablePublicationYear',
                    django.db.models.IntegerField(
                        null=True, editable=False, blank=True
                    ),
                ),
                ('resourceType', django.db.models.TextField(editable=False)),
                (
                    'searchableResourceType',
                    django.db.models.CharField(
                        max_length=2,
                        editable=False,
                        choices=[
                            (b'A', b'Audiovisual'),
                            (b'C', b'Collection'),
                            (b'D', b'Dataset'),
                            (b'E', b'Event'),
                            (b'Im', b'Image'),
                            (b'In', b'InteractiveResource'),
                            (b'M', b'Model'),
                            (b'Z', b'Other'),
                            (b'P', b'PhysicalObject'),
                            (b'Se', b'Service'),
                            (b'So', b'Software'),
                            (b'Su', b'Sound'),
                            (b'T', b'Text'),
                            (b'W', b'Workflow'),
                        ],
                    ),
                ),
                ('keywords', django.db.models.TextField(editable=False)),
                (
                    'resourceCreatorPrefix',
                    django.db.models.CharField(max_length=50, editable=False),
                ),
                (
                    'resourceTitlePrefix',
                    django.db.models.CharField(max_length=50, editable=False),
                ),
                (
                    'resourcePublisherPrefix',
                    django.db.models.CharField(max_length=50, editable=False),
                ),
                ('hasMetadata', django.db.models.BooleanField(editable=False)),
                ('publicSearchVisible', django.db.models.BooleanField(editable=False)),
                ('oaiVisible', django.db.models.BooleanField(editable=False)),
                ('hasIssues', django.db.models.BooleanField(editable=False)),
                (
                    'datacenter',
                    ezidapp.models.custom_fields.NonValidatingForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        default=None,
                        blank=True,
                        to='ezidapp.SearchDatacenter',
                        null=True,
                    ),
                ),
            ],
            options={
                'abstract': False,
            },
        ),
        django.db.migrations.CreateModel(
            name='SearchProfile',
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
                    'label',
                    django.db.models.CharField(
                        unique=True,
                        max_length=32,
                        validators=[
                            django.core.validators.RegexValidator(
                                '^[a-z0-9]+([-_.][a-z0-9]+)*$',
                                'Invalid profile name.',
                                flags=2,
                            )
                        ],
                    ),
                ),
            ],
            options={
                'abstract': False,
            },
        ),
        django.db.migrations.CreateModel(
            name='SearchRealm',
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
                    'name',
                    django.db.models.CharField(
                        unique=True,
                        max_length=32,
                        validators=[ezidapp.models.validation.nonEmpty],
                    ),
                ),
            ],
            options={
                'abstract': False,
            },
        ),
        django.db.migrations.CreateModel(
            name='SearchUser',
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
                    'group',
                    django.db.models.ForeignKey(
                        to='ezidapp.SearchGroup',
                        on_delete=django.db.models.deletion.PROTECT,
                    ),
                ),
                (
                    'realm',
                    django.db.models.ForeignKey(
                        to='ezidapp.SearchRealm',
                        on_delete=django.db.models.deletion.PROTECT,
                    ),
                ),
            ],
            options={
                'abstract': False,
            },
        ),
        django.db.migrations.CreateModel(
            name='ServerVariables',
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
                    'alertMessage',
                    django.db.models.CharField(
                        help_text=b'The alert message can be used to communicate urgent announcements.  It is displayed at the top of every UI page.',
                        max_length=255,
                        verbose_name=b'alert message',
                        blank=True,
                    ),
                ),
                (
                    'secretKey',
                    django.db.models.CharField(
                        help_text=b'The secret key identifies the server; changing it invalidates every API session cookie, password reset URL, and OAI-PMH resumption token.  Set it to blank to generate a new random key.',
                        max_length=50,
                        verbose_name=b'secret key',
                        blank=True,
                    ),
                ),
            ],
            options={
                'verbose_name_plural': 'server variables',
            },
        ),
        django.db.migrations.CreateModel(
            name='Shoulder',
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
                    'prefix',
                    django.db.models.CharField(
                        unique=True,
                        max_length=255,
                        validators=[ezidapp.models.validation.shoulder],
                    ),
                ),
                ('type', django.db.models.CharField(max_length=32, editable=False)),
                (
                    'name',
                    django.db.models.CharField(
                        max_length=255, validators=[ezidapp.models.validation.nonEmpty]
                    ),
                ),
                (
                    'minter',
                    django.db.models.URLField(
                        blank=True,
                        max_length=255,
                        validators=[ezidapp.models.validation.unicodeBmpOnly],
                    ),
                ),
                (
                    'crossrefEnabled',
                    django.db.models.BooleanField(
                        default=False, verbose_name=b'Crossref enabled'
                    ),
                ),
            ],
        ),
        django.db.migrations.CreateModel(
            name='StoreDatacenter',
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
                    'symbol',
                    django.db.models.CharField(
                        unique=True,
                        max_length=17,
                        validators=[ezidapp.models.validation.datacenterSymbol],
                    ),
                ),
                (
                    'name',
                    django.db.models.CharField(
                        unique=True,
                        max_length=255,
                        validators=[ezidapp.models.validation.nonEmpty],
                    ),
                ),
            ],
            options={
                'verbose_name': 'datacenter',
                'verbose_name_plural': 'datacenters',
            },
        ),
        django.db.migrations.CreateModel(
            name='StoreRealm',
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
                    'name',
                    django.db.models.CharField(
                        unique=True,
                        max_length=32,
                        validators=[ezidapp.models.validation.nonEmpty],
                    ),
                ),
            ],
            options={
                'abstract': False,
            },
        ),
        django.db.migrations.AddField(
            model_name='shoulder',
            name='datacenter',
            field=django.db.models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                default=None,
                blank=True,
                to='ezidapp.StoreDatacenter',
                null=True,
            ),
        ),
        django.db.migrations.AddField(
            model_name='searchidentifier',
            name='owner',
            field=ezidapp.models.custom_fields.NonValidatingForeignKey(
                to='ezidapp.SearchUser', on_delete=django.db.models.deletion.PROTECT
            ),
        ),
        django.db.migrations.AddField(
            model_name='searchidentifier',
            name='ownergroup',
            field=ezidapp.models.custom_fields.NonValidatingForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                default=None,
                blank=True,
                to='ezidapp.SearchGroup',
                null=True,
            ),
        ),
        django.db.migrations.AddField(
            model_name='searchidentifier',
            name='profile',
            field=ezidapp.models.custom_fields.NonValidatingForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                default=None,
                blank=True,
                to='ezidapp.SearchProfile',
                null=True,
            ),
        ),
        django.db.migrations.AddField(
            model_name='searchgroup',
            name='realm',
            field=django.db.models.ForeignKey(
                to='ezidapp.SearchRealm', on_delete=django.db.models.deletion.PROTECT
            ),
        ),
        django.db.migrations.AlterUniqueTogether(
            name='shoulder',
            unique_together={('name', 'type')},
        ),
        django.db.migrations.AlterIndexTogether(
            name='searchidentifier',
            index_together={
                ('publicSearchVisible', 'resourceCreatorPrefix'),
                ('owner', 'crossrefStatus'),
                ('owner', 'resourceCreatorPrefix'),
                ('publicSearchVisible', 'resourcePublisherPrefix'),
                ('ownergroup', 'hasMetadata'),
                ('owner', 'hasMetadata'),
                ('owner', 'hasIssues'),
                ('owner', 'profile'),
                ('owner', 'createTime'),
                ('owner', 'status'),
                ('publicSearchVisible', 'createTime'),
                ('searchableTarget',),
                ('ownergroup', 'searchableResourceType'),
                ('ownergroup', 'identifier'),
                ('ownergroup', 'profile'),
                ('ownergroup', 'exported'),
                ('owner', 'exported'),
                ('ownergroup', 'resourceTitlePrefix'),
                ('publicSearchVisible', 'resourceTitlePrefix'),
                ('owner', 'resourceTitlePrefix'),
                ('owner', 'identifier'),
                ('ownergroup', 'createTime'),
                ('ownergroup', 'isTest'),
                ('publicSearchVisible', 'updateTime'),
                ('publicSearchVisible', 'searchableResourceType'),
                ('publicSearchVisible', 'identifier'),
                ('owner', 'searchablePublicationYear'),
                ('owner', 'updateTime'),
                ('publicSearchVisible', 'searchablePublicationYear'),
                ('oaiVisible', 'updateTime'),
                ('ownergroup', 'resourceCreatorPrefix'),
                ('ownergroup', 'hasIssues'),
                ('ownergroup', 'updateTime'),
                ('owner', 'resourcePublisherPrefix'),
                ('ownergroup', 'crossrefStatus'),
                ('ownergroup', 'status'),
                ('owner', 'isTest'),
                ('ownergroup', 'resourcePublisherPrefix'),
                ('owner', 'searchableResourceType'),
                ('ownergroup', 'searchablePublicationYear'),
            },
        ),
    ]
