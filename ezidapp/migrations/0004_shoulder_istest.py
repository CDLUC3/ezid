# -*- coding: utf-8 -*-


import django.db.models
import ezidapp.models.validation
import django.db.migrations


class Migration(django.db.migrations.Migration):

    dependencies = [
        ('ezidapp', '0003_newaccountworksheet'),
    ]

    operations = [
        django.db.migrations.AlterModelOptions(
            name='storerealm',
            options={'verbose_name': 'realm', 'verbose_name_plural': 'realms'},
        ),
        django.db.migrations.AddField(
            model_name='shoulder',
            name='isTest',
            field=django.db.models.BooleanField(default=False, editable=False),
            preserve_default=False,
        ),
        django.db.migrations.AlterField(
            model_name='searchgroup',
            name='pid',
            field=django.db.models.CharField(
                unique=True,
                max_length=255,
                validators=[ezidapp.models.validation.agentPidOrEmpty],
            ),
        ),
    ]
