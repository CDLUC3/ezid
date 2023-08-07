# Generated by Django 3.2.17 on 2023-08-07 10:23

import django.core.serializers.json
import django.core.validators
from django.db import migrations, models
import ezidapp.models.validation


class Migration(migrations.Migration):

    dependencies = [
        ('ezidapp', '0002_auto_20221026_1139'),
    ]

    operations = [
        migrations.CreateModel(
            name='Minter',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('prefix', models.CharField(max_length=255, unique=True, validators=[ezidapp.models.validation.shoulder])),
                ('minterState', models.JSONField(default=dict, encoder=django.core.serializers.json.DjangoJSONEncoder)),
                ('createTime', models.IntegerField(db_index=True, default=1691428998, validators=[django.core.validators.MinValueValidator(0)])),
                ('updateTime', models.IntegerField(db_index=True, default=1691428998, validators=[django.core.validators.MinValueValidator(0)])),
            ],
        ),
        migrations.AlterField(
            model_name='binderqueue',
            name='status',
            field=models.CharField(choices=[('U', 'Awaiting submission'), ('C', 'Submitted, unchecked'), ('S', 'Submitted'), ('W', 'Registered with warning'), ('F', 'Registration failed'), ('T', 'Registration attempt unsuccessful'), ('I', 'Ignored (operation not applicable)'), ('O', 'Completed successfully')], db_index=True, default='U', max_length=1),
        ),
        migrations.AlterField(
            model_name='crossrefqueue',
            name='status',
            field=models.CharField(choices=[('U', 'Awaiting submission'), ('C', 'Submitted, unchecked'), ('S', 'Submitted'), ('W', 'Registered with warning'), ('F', 'Registration failed'), ('T', 'Registration attempt unsuccessful'), ('I', 'Ignored (operation not applicable)'), ('O', 'Completed successfully')], db_index=True, default='U', max_length=1),
        ),
        migrations.AlterField(
            model_name='datacitequeue',
            name='status',
            field=models.CharField(choices=[('U', 'Awaiting submission'), ('C', 'Submitted, unchecked'), ('S', 'Submitted'), ('W', 'Registered with warning'), ('F', 'Registration failed'), ('T', 'Registration attempt unsuccessful'), ('I', 'Ignored (operation not applicable)'), ('O', 'Completed successfully')], db_index=True, default='U', max_length=1),
        ),
        migrations.AlterField(
            model_name='searchindexerqueue',
            name='status',
            field=models.CharField(choices=[('U', 'Awaiting submission'), ('C', 'Submitted, unchecked'), ('S', 'Submitted'), ('W', 'Registered with warning'), ('F', 'Registration failed'), ('T', 'Registration attempt unsuccessful'), ('I', 'Ignored (operation not applicable)'), ('O', 'Completed successfully')], db_index=True, default='U', max_length=1),
        ),
    ]
