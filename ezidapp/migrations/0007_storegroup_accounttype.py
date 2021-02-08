# -*- coding: utf-8 -*-


import django.db.migrations
import django.db.models


class Migration(django.db.migrations.Migration):

    dependencies = [
        ('ezidapp', '0006_storegroup_accounttype'),
    ]

    operations = [
        django.db.migrations.AlterField(
            model_name='storegroup',
            name='accountType',
            field=django.db.models.CharField(
                blank=True,
                max_length=1,
                verbose_name=b'account type',
                choices=[
                    (b'B', b'Associate/bachelors-granting'),
                    (b'C', b'Corporate'),
                    (b'G', b'Group'),
                    (b'I', b'Institution'),
                    (b'M', b'Masters-granting'),
                    (b'N', b'Non-paying'),
                    (b'S', b'Service'),
                ],
            ),
        ),
    ]
