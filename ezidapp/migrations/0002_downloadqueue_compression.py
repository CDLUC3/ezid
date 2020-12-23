# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ezidapp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='downloadqueue',
            name='compression',
            field=models.CharField(
                default='G', max_length=1, choices=[(b'G', b'GZIP'), (b'Z', b'ZIP')]
            ),
            preserve_default=False,
        ),
    ]
