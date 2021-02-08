# -*- coding: utf-8 -*-


import django.db.migrations
import django.db.models
import django.core.validators
import ezidapp.models.validation


class Migration(django.db.migrations.Migration):

    dependencies = [
        ('ezidapp', '0015_searchidentifier_linkisbroken'),
    ]

    operations = [
        django.db.migrations.CreateModel(
            name='Statistics',
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
                ('month', django.db.models.CharField(max_length=7, db_index=True)),
                (
                    'owner',
                    django.db.models.CharField(
                        max_length=255, validators=[ezidapp.models.validation.agentPid]
                    ),
                ),
                (
                    'ownergroup',
                    django.db.models.CharField(
                        max_length=255, validators=[ezidapp.models.validation.agentPid]
                    ),
                ),
                ('realm', django.db.models.CharField(max_length=32)),
                ('type', django.db.models.CharField(max_length=32)),
                ('hasMetadata', django.db.models.BooleanField()),
                (
                    'count',
                    django.db.models.IntegerField(
                        validators=[django.core.validators.MinValueValidator(0)]
                    ),
                ),
            ],
        ),
        django.db.migrations.AlterUniqueTogether(
            name='statistics',
            unique_together={('month', 'owner', 'type', 'hasMetadata')},
        ),
    ]
