# -*- coding: utf-8 -*-


import django.db.migrations
import django.db.models


class Migration(django.db.migrations.Migration):

    dependencies = [
        ('ezidapp', '0013_linkchecker'),
    ]

    operations = [
        django.db.migrations.AddField(
            model_name='linkchecker',
            name='isBad',
            field=django.db.models.BooleanField(default=False, editable=False),
        ),
        django.db.migrations.AlterIndexTogether(
            name='linkchecker',
            index_together={('owner_id', 'isBad', 'lastCheckTime')},
        ),
    ]
