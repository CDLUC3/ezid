# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ezidapp', '0006_storegroup_accounttype'),
    ]

    operations = [
        migrations.AlterField(
            model_name='storegroup',
            name='accountType',
            field=models.CharField(blank=True, max_length=1, verbose_name=b'account type', choices=[(b'B', b'Associate/bachelors-granting'), (b'C', b'Corporate'), (b'G', b'Group'), (b'I', b'Institution'), (b'M', b'Masters-granting'), (b'N', b'Non-paying'), (b'S', b'Service')]),
        ),
    ]
