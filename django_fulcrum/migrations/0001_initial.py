# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime
from django.utils.timezone import utc
import django_fulcrum.models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Asset',
            fields=[
                ('asset_uid', models.CharField(max_length=100, serialize=False, primary_key=True)),
                ('asset_type', models.CharField(max_length=100)),
                ('asset_data', models.FileField(storage=django_fulcrum.models.CustomStorage(base_url='/api/fileservice/view/', location=b'/opt/boundless/exchange/.storage/media/fileservice'), upload_to=django_fulcrum.models.get_asset_name)),
                ('asset_added_time', models.DateTimeField(default=datetime.datetime(1, 1, 1, 0, 0, tzinfo=utc))),
            ],
        ),
        migrations.CreateModel(
            name='Feature',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('feature_uid', models.CharField(max_length=100)),
                ('feature_version', models.IntegerField(default=0)),
                ('feature_data', models.TextField()),
                ('feature_added_time', models.DateTimeField(default=datetime.datetime(1, 1, 1, 0, 0, tzinfo=utc))),
            ],
        ),
        migrations.CreateModel(
            name='Filter',
            fields=[
                ('filter_name', models.TextField(serialize=False, primary_key=True)),
                ('filter_active', models.BooleanField(default=True)),
                ('filter_inclusion', models.BooleanField(default=False, help_text='Exclude: Do not show data that matches this filter.\nInclude: Only show data that matches this filter.', choices=[(False, 'Exclude'), (True, 'Include')])),
                ('filter_previous', models.BooleanField(default=False, help_text='Selecting this will permenantly remove all points based on the current filter settings.', verbose_name='Filter previous points')),
                ('filter_previous_status', models.TextField(default='', verbose_name='Filter previous last run')),
                ('filter_previous_time', models.DateTimeField(default=datetime.datetime(1, 1, 1, 0, 0, tzinfo=utc))),
            ],
        ),
        migrations.CreateModel(
            name='FilterGeneric',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
        ),
        migrations.CreateModel(
            name='FulcrumApiKey',
            fields=[
                ('fulcrum_api_description', models.CharField(max_length=100)),
                ('fulcrum_api_key', models.CharField(default='', max_length=255, serialize=False, primary_key=True)),
            ],
        ),
        migrations.CreateModel(
            name='Layer',
            fields=[
                ('layer_name', models.CharField(max_length=100, serialize=False, primary_key=True)),
                ('layer_uid', models.CharField(max_length=100)),
                ('layer_date', models.IntegerField(default=0)),
                ('layer_media_keys', models.CharField(default='{}', max_length=2000)),
            ],
        ),
        migrations.CreateModel(
            name='S3Bucket',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('s3_bucket', models.CharField(max_length=511)),
            ],
        ),
        migrations.CreateModel(
            name='S3Credential',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('s3_description', models.TextField(help_text='A name to use for these credentials.')),
                ('s3_key', models.CharField(help_text='The access key.', max_length=100)),
                ('s3_secret', models.CharField(help_text='The secret key.', max_length=255)),
                ('s3_gpg', models.CharField(help_text='An arbitrary key for GPG.', max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='S3Sync',
            fields=[
                ('s3_filename', models.CharField(max_length=500, serialize=False, primary_key=True)),
            ],
        ),
        migrations.CreateModel(
            name='FilterArea',
            fields=[
                ('filtergeneric_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='django_fulcrum.FilterGeneric')),
                ('filter_area_enabled', models.BooleanField(default=True)),
                ('filter_area_name', models.CharField(max_length=100)),
                ('filter_area_buffer', models.FloatField(default=0.1, help_text='Distance to increase or decrease around the geometries.')),
                ('filter_area_data', models.TextField(help_text='A geojson geometry or features containing geometries.')),
            ],
            bases=('django_fulcrum.filtergeneric',),
        ),
        migrations.CreateModel(
            name='TextFilter',
            fields=[
                ('filtergeneric_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='django_fulcrum.FilterGeneric')),
            ],
            bases=('django_fulcrum.filtergeneric',),
        ),
        migrations.AlterUniqueTogether(
            name='s3credential',
            unique_together=set([('s3_key', 's3_secret')]),
        ),
        migrations.AddField(
            model_name='s3bucket',
            name='s3_credential',
            field=models.ForeignKey(default='', to='django_fulcrum.S3Credential'),
        ),
        migrations.AlterUniqueTogether(
            name='layer',
            unique_together=set([('layer_name', 'layer_uid')]),
        ),
        migrations.AddField(
            model_name='filtergeneric',
            name='filter',
            field=models.ForeignKey(to='django_fulcrum.Filter'),
        ),
        migrations.AddField(
            model_name='feature',
            name='layer',
            field=models.ForeignKey(default='', to='django_fulcrum.Layer'),
        ),
        migrations.AlterUniqueTogether(
            name='feature',
            unique_together=set([('feature_uid', 'feature_version')]),
        ),
    ]
