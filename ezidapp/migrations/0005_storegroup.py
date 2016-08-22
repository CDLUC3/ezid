# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion
import django.core.validators
import ezidapp.models.validation


class Migration(migrations.Migration):

    dependencies = [
        ('ezidapp', '0004_shoulder_istest'),
    ]

    operations = [
        migrations.CreateModel(
            name='StoreGroup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('pid', models.CharField(unique=True, max_length=255, validators=[ezidapp.models.validation.agentPidOrEmpty])),
                ('groupname', models.CharField(unique=True, max_length=32, validators=[django.core.validators.RegexValidator(b'^[a-z0-9]+([-_.][a-z0-9]+)*$', b'Invalid groupname.', flags=2)])),
                ('organizationName', models.CharField(max_length=255, verbose_name=b'name', validators=[ezidapp.models.validation.nonEmpty])),
                ('organizationAcronym', models.CharField(max_length=255, verbose_name=b'acronym', blank=True)),
                ('organizationUrl', models.URLField(max_length=255, verbose_name=b'URL')),
                ('organizationStreetAddress', models.CharField(max_length=255, verbose_name=b'street address', validators=[ezidapp.models.validation.nonEmpty])),
                ('agreementOnFile', models.BooleanField(default=False, verbose_name=b'agreement on file')),
                ('crossrefEnabled', models.BooleanField(default=False, verbose_name=b'Crossref enabled')),
                ('notes', models.TextField(blank=True)),
                ('realm', models.ForeignKey(to='ezidapp.StoreRealm', on_delete=django.db.models.deletion.PROTECT)),
            ],
            options={
                'verbose_name': 'group',
                'verbose_name_plural': 'groups',
            },
        ),
        migrations.AlterField(
            model_name='newaccountworksheet',
            name='orgUrl',
            field=models.URLField(max_length=255, verbose_name=b'URL', blank=True),
        ),
        migrations.AlterField(
            model_name='newaccountworksheet',
            name='priEmail',
            field=models.EmailField(max_length=255, verbose_name=b'email', blank=True),
        ),
        migrations.AlterField(
            model_name='newaccountworksheet',
            name='reqAccountEmail',
            field=models.EmailField(max_length=255, verbose_name=b'account email', blank=True),
        ),
        migrations.AlterField(
            model_name='newaccountworksheet',
            name='reqCrossrefEmail',
            field=models.EmailField(max_length=255, verbose_name=b'Crossref email', blank=True),
        ),
        migrations.AlterField(
            model_name='newaccountworksheet',
            name='reqEmail',
            field=models.EmailField(max_length=255, verbose_name=b'email', blank=True),
        ),
        migrations.AlterField(
            model_name='newaccountworksheet',
            name='secEmail',
            field=models.EmailField(max_length=255, verbose_name=b'email', blank=True),
        ),
        migrations.AlterField(
            model_name='shoulder',
            name='minter',
            field=models.URLField(max_length=255, blank=True),
        ),
        migrations.AddField(
            model_name='storegroup',
            name='shoulders',
            field=models.ManyToManyField(to='ezidapp.Shoulder', blank=True),
        ),
    ]
