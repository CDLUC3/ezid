# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ezidapp', '0017_linkchecker_error'),
    ]

    operations = [
        migrations.CreateModel(
            name='BinderQueue',
            fields=[
                ('seq', models.AutoField(serialize=False, primary_key=True)),
                ('enqueueTime', models.IntegerField()),
                ('identifier', models.CharField(max_length=255)),
                ('metadata', models.BinaryField()),
                (
                    'operation',
                    models.CharField(
                        max_length=1, choices=[(b'O', b'overwrite'), (b'D', b'delete')]
                    ),
                ),
                ('error', models.TextField(blank=True)),
                ('errorIsPermanent', models.BooleanField(default=False)),
            ],
            options={'abstract': False,},
        ),
    ]
