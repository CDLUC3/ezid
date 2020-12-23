# -*- coding: utf-8 -*-


from django.db import models, migrations
import django.core.validators
import ezidapp.models.validation


class Migration(migrations.Migration):

    dependencies = [
        ('ezidapp', '0015_searchidentifier_linkisbroken'),
    ]

    operations = [
        migrations.CreateModel(
            name='Statistics',
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
                ('month', models.CharField(max_length=7, db_index=True)),
                (
                    'owner',
                    models.CharField(
                        max_length=255, validators=[ezidapp.models.validation.agentPid]
                    ),
                ),
                (
                    'ownergroup',
                    models.CharField(
                        max_length=255, validators=[ezidapp.models.validation.agentPid]
                    ),
                ),
                ('realm', models.CharField(max_length=32)),
                ('type', models.CharField(max_length=32)),
                ('hasMetadata', models.BooleanField()),
                (
                    'count',
                    models.IntegerField(
                        validators=[django.core.validators.MinValueValidator(0)]
                    ),
                ),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='statistics',
            unique_together=set([('month', 'owner', 'type', 'hasMetadata')]),
        ),
    ]
