# -*- coding: utf-8 -*-


import django.db.migrations
import django.db.models


class Migration(django.db.migrations.Migration):

    dependencies = [
        ('ezidapp', '0014_linkchecker'),
    ]

    operations = [
        django.db.migrations.AddField(
            model_name='searchidentifier',
            name='linkIsBroken',
            field=django.db.models.BooleanField(default=False, editable=False),
        ),
    ]
