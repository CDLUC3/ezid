# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ezidapp', '0016_statistics'),
    ]

    operations = [
        migrations.AddField(
            model_name='linkchecker', name='error', field=models.TextField(blank=True),
        ),
    ]
