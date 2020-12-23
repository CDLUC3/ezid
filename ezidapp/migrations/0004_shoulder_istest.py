# -*- coding: utf-8 -*-


from django.db import models, migrations
import ezidapp.models.validation


class Migration(migrations.Migration):

    dependencies = [
        ('ezidapp', '0003_newaccountworksheet'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='storerealm',
            options={'verbose_name': 'realm', 'verbose_name_plural': 'realms'},
        ),
        migrations.AddField(
            model_name='shoulder',
            name='isTest',
            field=models.BooleanField(default=False, editable=False),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='searchgroup',
            name='pid',
            field=models.CharField(
                unique=True,
                max_length=255,
                validators=[ezidapp.models.validation.agentPidOrEmpty],
            ),
        ),
    ]
