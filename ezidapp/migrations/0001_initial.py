# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
import ezidapp.models.validation
import django.db.models.deletion
import ezidapp.models.custom_fields
import django.core.validators
import ezidapp.models.identifier


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CrossrefQueue',
            fields=[
                ('seq', models.AutoField(serialize=False, primary_key=True)),
                ('identifier', models.CharField(max_length=255, db_index=True)),
                ('owner', models.CharField(max_length=255, db_index=True)),
                ('metadata', models.BinaryField()),
                ('operation', models.CharField(max_length=1, choices=[(b'C', b'create'), (b'M', b'modify'), (b'D', b'delete')])),
                ('status', models.CharField(default=b'U', max_length=1, db_index=True, choices=[(b'U', b'awaiting submission'), (b'S', b'submitted'), (b'W', b'registered with warning'), (b'F', b'registration failed')])),
                ('message', models.TextField(blank=True)),
                ('batchId', models.CharField(max_length=36, blank=True)),
                ('submitTime', models.IntegerField(null=True, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='DataciteQueue',
            fields=[
                ('seq', models.AutoField(serialize=False, primary_key=True)),
                ('enqueueTime', models.IntegerField()),
                ('identifier', models.CharField(max_length=255)),
                ('metadata', models.BinaryField()),
                ('operation', models.CharField(max_length=1, choices=[(b'O', b'overwrite'), (b'D', b'delete')])),
                ('error', models.TextField(blank=True)),
                ('errorIsPermanent', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='DownloadQueue',
            fields=[
                ('seq', models.AutoField(serialize=False, primary_key=True)),
                ('requestTime', models.IntegerField()),
                ('rawRequest', models.TextField()),
                ('requestor', models.CharField(max_length=255)),
                ('coOwners', models.TextField(blank=True)),
                ('format', models.CharField(max_length=1, choices=[(b'A', b'ANVL'), (b'C', b'CSV'), (b'X', b'XML')])),
                ('columns', models.TextField(blank=True)),
                ('constraints', models.TextField(blank=True)),
                ('options', models.TextField(blank=True)),
                ('notify', models.TextField(blank=True)),
                ('stage', models.CharField(default=b'C', max_length=1, choices=[(b'C', b'create'), (b'H', b'harvest'), (b'Z', b'compress'), (b'D', b'delete'), (b'M', b'move'), (b'N', b'notify')])),
                ('filename', models.CharField(max_length=10, blank=True)),
                ('currentOwner', models.CharField(max_length=255, blank=True)),
                ('lastId', models.CharField(max_length=255, blank=True)),
                ('fileSize', models.IntegerField(null=True, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='NewAccountWorksheet',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('requestDate', models.DateField(default=datetime.date.today, verbose_name=b'request date')),
                ('orgName', models.CharField(max_length=255, verbose_name=b'name', validators=[ezidapp.models.validation.nonEmpty])),
                ('orgAcronym', models.CharField(max_length=255, verbose_name=b'acronym', blank=True)),
                ('orgUrl', models.URLField(blank=True, max_length=255, verbose_name=b'URL', validators=[ezidapp.models.validation.unicodeBmpOnly])),
                ('orgStreetAddress', models.CharField(max_length=255, verbose_name=b'street address', blank=True)),
                ('reqName', models.CharField(max_length=255, verbose_name=b'name', blank=True)),
                ('reqEmail', models.EmailField(blank=True, max_length=255, verbose_name=b'email', validators=[ezidapp.models.validation.unicodeBmpOnly])),
                ('reqPhone', models.CharField(max_length=255, verbose_name=b'phone', blank=True)),
                ('priUseRequestor', models.BooleanField(default=False, verbose_name=b'use requestor')),
                ('priName', models.CharField(max_length=255, verbose_name=b'name', blank=True)),
                ('priEmail', models.EmailField(blank=True, max_length=255, verbose_name=b'email', validators=[ezidapp.models.validation.unicodeBmpOnly])),
                ('priPhone', models.CharField(max_length=255, verbose_name=b'phone', blank=True)),
                ('secName', models.CharField(max_length=255, verbose_name=b'name', blank=True)),
                ('secEmail', models.EmailField(blank=True, max_length=255, verbose_name=b'email', validators=[ezidapp.models.validation.unicodeBmpOnly])),
                ('secPhone', models.CharField(max_length=255, verbose_name=b'phone', blank=True)),
                ('reqUsername', models.CharField(max_length=255, verbose_name=b'requested username', blank=True)),
                ('reqAccountEmailUsePrimary', models.BooleanField(default=False, verbose_name=b"use primary contact's email")),
                ('reqAccountEmail', models.EmailField(blank=True, max_length=255, verbose_name=b'account email', validators=[ezidapp.models.validation.unicodeBmpOnly])),
                ('reqArks', models.BooleanField(default=False, verbose_name=b'ARKs')),
                ('reqDois', models.BooleanField(default=False, verbose_name=b'DOIs')),
                ('reqShoulders', models.CharField(max_length=255, verbose_name=b'requested shoulders/ branding', blank=True)),
                ('reqCrossref', models.BooleanField(default=False, verbose_name=b'CrossRef')),
                ('reqCrossrefEmailUseAccount', models.BooleanField(default=False, verbose_name=b'use account email')),
                ('reqCrossrefEmail', models.EmailField(blank=True, max_length=255, verbose_name=b'CrossRef email', validators=[ezidapp.models.validation.unicodeBmpOnly])),
                ('reqHasExistingIdentifiers', models.BooleanField(default=False, verbose_name=b'has existing identifiers')),
                ('reqComments', models.TextField(verbose_name=b'requestor comments', blank=True)),
                ('setRealm', models.CharField(max_length=255, verbose_name=b'realm', blank=True)),
                ('setExistingGroup', models.BooleanField(default=False, verbose_name=b'existing group')),
                ('setGroupname', models.CharField(max_length=255, verbose_name=b'groupname', blank=True)),
                ('setUsernameUseRequested', models.BooleanField(default=False, verbose_name=b'use requested')),
                ('setUsername', models.CharField(max_length=255, verbose_name=b'username', blank=True)),
                ('setNeedShoulders', models.BooleanField(default=False, verbose_name=b'new shoulders required')),
                ('setNeedMinters', models.BooleanField(default=False, verbose_name=b'minters required')),
                ('setNotes', models.TextField(verbose_name=b'notes', blank=True)),
                ('staReady', models.BooleanField(default=False, verbose_name=b'request ready')),
                ('staShouldersCreated', models.BooleanField(default=False, verbose_name=b'shoulders created')),
                ('staAccountCreated', models.BooleanField(default=False, verbose_name=b'account created')),
            ],
        ),
        migrations.CreateModel(
            name='SearchDatacenter',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('symbol', models.CharField(unique=True, max_length=17, validators=[ezidapp.models.validation.datacenterSymbol])),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='SearchGroup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('pid', models.CharField(unique=True, max_length=255, validators=[ezidapp.models.validation.agentPid])),
                ('groupname', models.CharField(unique=True, max_length=32, validators=[django.core.validators.RegexValidator(b'^[a-z0-9]+([-_.][a-z0-9]+)*$', b'Invalid groupname.', flags=2)])),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='SearchIdentifier',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('identifier', models.CharField(unique=True, max_length=255, validators=[ezidapp.models.validation.anyIdentifier])),
                ('createTime', models.IntegerField(default=b'', blank=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('updateTime', models.IntegerField(default=b'', blank=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('status', models.CharField(default=b'P', max_length=1, choices=[(b'R', b'reserved'), (b'P', b'public'), (b'U', b'unavailable')])),
                ('unavailableReason', models.TextField(default=b'', blank=True)),
                ('exported', models.BooleanField(default=True)),
                ('crossrefStatus', models.CharField(default=b'', max_length=1, blank=True, choices=[(b'R', b'awaiting status change to public'), (b'B', b'registration in progress'), (b'S', b'successfully registered'), (b'W', b'registered with warning'), (b'F', b'registration failure')])),
                ('crossrefMessage', models.TextField(default=b'', blank=True)),
                ('target', models.URLField(default=b'', max_length=2000, blank=True, validators=[ezidapp.models.validation.unicodeBmpOnly])),
                ('cm', ezidapp.models.custom_fields.CompressedJsonField(default=ezidapp.models.identifier._emptyDict)),
                ('agentRole', models.CharField(default=b'', max_length=1, blank=True, choices=[(b'U', b'user'), (b'G', b'group')])),
                ('isTest', models.BooleanField(editable=False)),
                ('searchableTarget', models.CharField(max_length=255, editable=False)),
                ('resourceCreator', models.TextField(editable=False)),
                ('resourceTitle', models.TextField(editable=False)),
                ('resourcePublisher', models.TextField(editable=False)),
                ('resourcePublicationDate', models.TextField(editable=False)),
                ('searchablePublicationYear', models.IntegerField(null=True, editable=False, blank=True)),
                ('resourceType', models.TextField(editable=False)),
                ('searchableResourceType', models.CharField(max_length=2, editable=False, choices=[(b'A', b'Audiovisual'), (b'C', b'Collection'), (b'D', b'Dataset'), (b'E', b'Event'), (b'Im', b'Image'), (b'In', b'InteractiveResource'), (b'M', b'Model'), (b'Z', b'Other'), (b'P', b'PhysicalObject'), (b'Se', b'Service'), (b'So', b'Software'), (b'Su', b'Sound'), (b'T', b'Text'), (b'W', b'Workflow')])),
                ('keywords', models.TextField(editable=False)),
                ('resourceCreatorPrefix', models.CharField(max_length=50, editable=False)),
                ('resourceTitlePrefix', models.CharField(max_length=50, editable=False)),
                ('resourcePublisherPrefix', models.CharField(max_length=50, editable=False)),
                ('hasMetadata', models.BooleanField(editable=False)),
                ('publicSearchVisible', models.BooleanField(editable=False)),
                ('oaiVisible', models.BooleanField(editable=False)),
                ('hasIssues', models.BooleanField(editable=False)),
                ('datacenter', ezidapp.models.custom_fields.NonValidatingForeignKey(on_delete=django.db.models.deletion.PROTECT, default=None, blank=True, to='ezidapp.SearchDatacenter', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='SearchProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('label', models.CharField(unique=True, max_length=32, validators=[django.core.validators.RegexValidator(b'^[a-z0-9]+([-_.][a-z0-9]+)*$', b'Invalid profile name.', flags=2)])),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='SearchRealm',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=32, validators=[ezidapp.models.validation.nonEmpty])),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='SearchUser',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('pid', models.CharField(unique=True, max_length=255, validators=[ezidapp.models.validation.agentPid])),
                ('username', models.CharField(unique=True, max_length=32, validators=[django.core.validators.RegexValidator(b'^[a-z0-9]+([-_.][a-z0-9]+)*$', b'Invalid username.', flags=2)])),
                ('group', models.ForeignKey(to='ezidapp.SearchGroup', on_delete=django.db.models.deletion.PROTECT)),
                ('realm', models.ForeignKey(to='ezidapp.SearchRealm', on_delete=django.db.models.deletion.PROTECT)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ServerVariables',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('alertMessage', models.CharField(help_text=b'The alert message can be used to communicate urgent announcements.  It is displayed at the top of every UI page.', max_length=255, verbose_name=b'alert message', blank=True)),
                ('secretKey', models.CharField(help_text=b'The secret key identifies the server; changing it invalidates every API session cookie, password reset URL, and OAI-PMH resumption token.  Set it to blank to generate a new random key.', max_length=50, verbose_name=b'secret key', blank=True)),
            ],
            options={
                'verbose_name_plural': 'server variables',
            },
        ),
        migrations.CreateModel(
            name='Shoulder',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('prefix', models.CharField(unique=True, max_length=255, validators=[ezidapp.models.validation.shoulder])),
                ('type', models.CharField(max_length=32, editable=False)),
                ('name', models.CharField(max_length=255, validators=[ezidapp.models.validation.nonEmpty])),
                ('minter', models.URLField(blank=True, max_length=255, validators=[ezidapp.models.validation.unicodeBmpOnly])),
                ('crossrefEnabled', models.BooleanField(default=False, verbose_name=b'CrossRef enabled')),
            ],
        ),
        migrations.CreateModel(
            name='StoreDatacenter',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('symbol', models.CharField(unique=True, max_length=17, validators=[ezidapp.models.validation.datacenterSymbol])),
                ('name', models.CharField(unique=True, max_length=255, validators=[ezidapp.models.validation.nonEmpty])),
            ],
            options={
                'verbose_name': 'datacenter',
                'verbose_name_plural': 'datacenters',
            },
        ),
        migrations.CreateModel(
            name='StoreRealm',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=32, validators=[ezidapp.models.validation.nonEmpty])),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='shoulder',
            name='datacenter',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, default=None, blank=True, to='ezidapp.StoreDatacenter', null=True),
        ),
        migrations.AddField(
            model_name='searchidentifier',
            name='owner',
            field=ezidapp.models.custom_fields.NonValidatingForeignKey(to='ezidapp.SearchUser', on_delete=django.db.models.deletion.PROTECT),
        ),
        migrations.AddField(
            model_name='searchidentifier',
            name='ownergroup',
            field=ezidapp.models.custom_fields.NonValidatingForeignKey(on_delete=django.db.models.deletion.PROTECT, default=None, blank=True, to='ezidapp.SearchGroup', null=True),
        ),
        migrations.AddField(
            model_name='searchidentifier',
            name='profile',
            field=ezidapp.models.custom_fields.NonValidatingForeignKey(on_delete=django.db.models.deletion.PROTECT, default=None, blank=True, to='ezidapp.SearchProfile', null=True),
        ),
        migrations.AddField(
            model_name='searchgroup',
            name='realm',
            field=models.ForeignKey(to='ezidapp.SearchRealm', on_delete=django.db.models.deletion.PROTECT),
        ),
        migrations.AlterUniqueTogether(
            name='shoulder',
            unique_together=set([('name', 'type')]),
        ),
        migrations.AlterIndexTogether(
            name='searchidentifier',
            index_together=set([('publicSearchVisible', 'resourceCreatorPrefix'), ('owner', 'crossrefStatus'), ('owner', 'resourceCreatorPrefix'), ('publicSearchVisible', 'resourcePublisherPrefix'), ('ownergroup', 'hasMetadata'), ('owner', 'hasMetadata'), ('owner', 'hasIssues'), ('owner', 'profile'), ('owner', 'createTime'), ('owner', 'status'), ('publicSearchVisible', 'createTime'), ('searchableTarget',), ('ownergroup', 'searchableResourceType'), ('ownergroup', 'identifier'), ('ownergroup', 'profile'), ('ownergroup', 'exported'), ('owner', 'exported'), ('ownergroup', 'resourceTitlePrefix'), ('publicSearchVisible', 'resourceTitlePrefix'), ('owner', 'resourceTitlePrefix'), ('owner', 'identifier'), ('ownergroup', 'createTime'), ('ownergroup', 'isTest'), ('publicSearchVisible', 'updateTime'), ('publicSearchVisible', 'searchableResourceType'), ('publicSearchVisible', 'identifier'), ('owner', 'searchablePublicationYear'), ('owner', 'updateTime'), ('publicSearchVisible', 'searchablePublicationYear'), ('oaiVisible', 'updateTime'), ('ownergroup', 'resourceCreatorPrefix'), ('ownergroup', 'hasIssues'), ('ownergroup', 'updateTime'), ('owner', 'resourcePublisherPrefix'), ('ownergroup', 'crossrefStatus'), ('ownergroup', 'status'), ('owner', 'isTest'), ('ownergroup', 'resourcePublisherPrefix'), ('owner', 'searchableResourceType'), ('ownergroup', 'searchablePublicationYear')]),
        ),
    ]
