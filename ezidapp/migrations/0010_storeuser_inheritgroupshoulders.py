# -*- coding: utf-8 -*-


import django.db.migrations
import django.db.models


class Migration(django.db.migrations.Migration):

    dependencies = [
        ('ezidapp', '0009_storeuser'),
    ]

    operations = [
        django.db.migrations.AlterField(
            model_name='storeuser',
            name='inheritGroupShoulders',
            field=django.db.models.BooleanField(
                default=False,
                help_text=b'If checked, the user has access to all group shoulders; if not checked, the user has access only to the shoulders explicitly selected below.',
                verbose_name=b'inherit group shoulders',
            ),
        ),
    ]
