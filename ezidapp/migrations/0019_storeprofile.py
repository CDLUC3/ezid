# -*- coding: utf-8 -*-


from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('ezidapp', '0018_binderqueue'),
    ]

    operations = [
        migrations.CreateModel(
            name='StoreProfile',
            fields=[
                (
                    'id',
                    models.AutoField(
                        verbose_name='ID',
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                (
                    'label',
                    models.CharField(
                        unique=True,
                        max_length=32,
                        validators=[
                            django.core.validators.RegexValidator(
                                b'^[a-z0-9]+([-_.][a-z0-9]+)*$',
                                b'Invalid profile name.',
                                flags=2,
                            )
                        ],
                    ),
                ),
            ],
            options={'abstract': False,},
        ),
    ]
