# -*- coding: utf-8 -*-


import django.db.migrations
import django.db.models


class Migration(django.db.migrations.Migration):

    dependencies = [
        ('ezidapp', '0021_updatequeue'),
    ]

    operations = [
        django.db.migrations.AlterField(
            model_name='crossrefqueue',
            name='operation',
            field=django.db.models.CharField(
                max_length=1,
                choices=[(b'C', b'create'), (b'U', b'update'), (b'D', b'delete')],
            ),
        ),
    ]
