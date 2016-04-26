# Copyright 2016, RadiantBlue Technologies, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals

from django.db import models
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.utils import timezone
import os
import json
from datetime import datetime, timedelta

if getattr(settings, 'SITENAME', '').lower() == 'geoshape':
    fulcrum_media_dir = getattr(settings, 'FILESERVICE_CONFIG', {}).get('store_dir')
else:
    fulcrum_media_dir = getattr(settings, 'MEDIA_ROOT', None)
if not fulcrum_media_dir:
    if not os.path.exists(os.path.join(os.getcwd(), 'media')):
        os.mkdir(os.path.join(os.getcwd(), 'media'))
    fulcrum_media_dir = os.path.join(os.getcwd(), 'media')

fulcrum_data_dir = getattr(settings, 'FULCRUM_UPLOAD', None)
if not fulcrum_data_dir:
    fulcrum_data_dir = getattr(settings, 'MEDIA_ROOT', None)
if not fulcrum_data_dir:
    if not os.path.exists(os.path.join(os.getcwd(), 'data')):
        os.mkdir(os.path.join(os.getcwd(), 'data'))
    fulcrum_data_dir = os.path.join(os.getcwd(), 'data')


def get_media_dir():
    return fulcrum_media_dir


def get_data_dir():
    return fulcrum_data_dir


def default_datetime():
    return datetime(1, 1, 1, 0, 0, 0)


def get_asset_name(instance, *args):
    """

    Args:
        instance: The model instance.

    Returns:
        a string representing the file with an extension.

    """
    return './{}.{}'.format(instance.asset_uid, get_type_extension(instance.asset_type))


def get_type_extension(file_type):
    """

    Args:
        file_type: A generic for the file (e.g. photos, videos, audio).

    Returns:
        The mapped extension (e.g. jpg, mp4, m4a).
    """
    asset_types = {'photos': 'jpg', 'videos': 'mp4', 'audio': 'm4a'}
    if asset_types.get(file_type):
        return asset_types.get(file_type)
    else:
        return None


def get_all_features(after_time_added=None):
    """

    Args:
        after_time_added: get all features that were added to the db after this date.

    Returns:

    """
    features = []
    if after_time_added:
        for feature in Feature.objects.exclude(feature_added_time__lt=after_time_added):
            features += [json.loads(feature.feature_data)]
    else:
        for feature in Feature.objects.all():
            features += [json.loads(feature.feature_data)]
    return {"features": features}


class CustomStorage(FileSystemStorage):

    def get_available_name(self, name):
        return name

    def _save(self, name, content):
        if self.exists(name):
            return name
        return super(CustomStorage, self)._save(name, content)


class Asset(models.Model):
    """Structure to hold file locations."""
    asset_uid = models.CharField(max_length=100, primary_key=True)
    asset_type = models.CharField(max_length=100)
    asset_data = models.FileField(storage=CustomStorage(location=get_media_dir()), upload_to=get_asset_name)
    asset_added_time = models.DateTimeField(default=timezone.now())

    def delete(self, *args, **kwargs):
        super(Asset, self).delete(*args, **kwargs)
        self.asset_data.delete()


class Layer(models.Model):
    """Structure to hold information about layers."""
    layer_name = models.CharField(max_length=100, primary_key=True)
    layer_uid = models.CharField(max_length=100)
    layer_date = models.IntegerField(default=0)
    layer_media_keys = models.CharField(max_length=2000, default="{}")

    class Meta:
        unique_together = (("layer_name", "layer_uid"),)


class Feature(models.Model):
    """Structure to hold information about and actual feature data."""
    feature_uid = models.CharField(max_length=100)
    feature_version = models.IntegerField(default=0)
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE, default="")
    feature_data = models.TextField()
    feature_added_time = models.DateTimeField(default=timezone.now())

    class Meta:
        unique_together = (("feature_uid", "feature_version"),)


class S3Sync(models.Model):
    """Structure to persist knowledge of a file download."""
    s3_filename = models.CharField(max_length=500, primary_key=True)


class S3Credential(models.Model):
    s3_description = models.TextField(help_text="A name to use for these credentials.")
    s3_key = models.CharField(max_length=100, help_text="The access key.")
    s3_secret = models.CharField(max_length=255, help_text="The secret key.")
    s3_gpg = models.CharField(max_length=255, help_text="An arbitrary key for GPG.")

    class Meta:
        unique_together = (("s3_key", "s3_secret"),)

    def __unicode__(self):
        return "{}({})".format(self.s3_description, self.s3_key)


class S3Bucket(models.Model):
    s3_bucket = models.CharField(max_length=511)
    s3_credential = models.ForeignKey(S3Credential, on_delete=models.CASCADE, default="")

    def __unicode__(self):
        return self.s3_bucket


class FulcrumApiKey(models.Model):
    fulcrum_api_description = models.CharField(max_length=100)
    fulcrum_api_key = models.CharField(max_length=255, default="", primary_key=True)

    def __unicode__(self):
        return self.fulcrum_api_description


def get_init_time():
    return datetime(1, 1, 1)


class Filter(models.Model):
    """Structure to hold knowledge of filters in the filter package."""
    INCLUSION = (
        (False, "Exclude"),
        (True, "Include")
    )
    filter_name = models.TextField(primary_key=True)
    filter_active = models.BooleanField(default=True)
    filter_inclusion = models.BooleanField(default=False,
                                           choices=INCLUSION,
                                           help_text="Exclude: Do not show data that matches this filter.\n"
                                                     "Include: Only show data that matches this filter.")
    filter_previous = models.BooleanField(verbose_name="Filter previous points",
                                          default=False,
                                          help_text="Selecting this will permenantly remove all points based on the current"
                                                    " filter settings.")
    filter_previous_status = models.TextField(verbose_name="Filter previous last run", default="")
    filter_previous_time = models.DateTimeField(default=get_init_time())

    __filter_inclusion = None

    def __init__(self, *args, **kwargs):
        super(Filter, self).__init__(*args, **kwargs)
        self.__filter_inclusion = self.filter_inclusion

    @staticmethod
    def get_lock_id(task_name, filter_name):
        """

        Args:
            task_name: The name of the task using the lock
            filter_name: The name of the filter as a string.

        Returns: A name to use to store the lock.

        """
        return '{0}-lock-{1}'.format(task_name, filter_name)

    def save(self, *args, **kwargs):

        if self.filter_inclusion != self.__filter_inclusion:
            self.filter_previous_time = get_init_time()
        self.__filter_inclusion = self.filter_inclusion

        if not self.is_filter_running():
            super(Filter, self).save(*args, **kwargs)
        else:
            if self.filter_previous_status:
                self.filter_previous_status = "Filtering is in progress..."
                super(Filter, self).save(update_fields=["filter_previous_status"])
            return
        if self.filter_previous and not self.is_filter_running():
            # add a time buffer to account for subtle time differences.
            run_time = (timezone.now() - timedelta(minutes=1)).isoformat()
            from .tasks import task_filter_features, task_filter_assets
            if getattr(settings, 'DJANGO_FULCRUM_USE_CELERY', True):
                task_filter_features.apply_async(kwargs={'filter_name': self.filter_name,
                                                         'features': get_all_features(
                                                                 after_time_added=self.filter_previous_time),
                                                         'run_once': True,
                                                         'run_time': run_time})
                task_filter_assets.apply_async(kwargs={'filter_name': self.filter_name,
                                                       'after_time_added': self.filter_previous_time.isoformat(),
                                                       'run_once': True,
                                                       'run_time': run_time})
            else:
                task_filter_features(filter_name=self.filter_name,
                                     features=self.filter_previous_time,
                                     run_once=True,
                                     run_time=run_time)
                task_filter_assets(filter_name=self.filter_name,
                                   after_time_added=self.filter_previous_time.isoformat(),
                                   run_once=True,
                                   run_time=run_time)
            self.filter_previous = False
        if self.is_filter_running():
            self.filter_previous_status = "Filtering is in progress..."
        else:
            self.filter_previous_status = "Filter previous last ran at {}.".format(self.filter_previous_time)
        super(Filter, self).save(*args, **kwargs)

    def is_filter_running(self):
        """

        Returns: True if a lock exists for the current filter.

        """
        from .tasks import is_filter_task_locked
        if is_filter_task_locked(self.filter_name):
            return True
        return False

    def __unicode__(self):
        if self.filter_active:
            status = "  (Active)"
        else:
            status = "  (Inactive)"
        if self.is_filter_running():
            status = "{} - Filtering old features...)".format(status[:-1])
        return self.filter_name + status


class FilterGeneric(models.Model):
    filter = models.ForeignKey(Filter)


class TextFilter(FilterGeneric):
    pass


class FilterArea(FilterGeneric):
    filter_area_enabled = models.BooleanField(default=True)
    filter_area_name = models.CharField(max_length=100)
    filter_area_buffer = models.FloatField(default=0.1,
                                           help_text="Distance to increase or decrease around the geometries.")
    filter_area_data = models.TextField(help_text="A geojson geometry or features containing geometries.")

    __filter_area_buffer = None
    __filter_area_data = None

    def __init__(self, *args, **kwargs):
        super(FilterArea, self).__init__(*args, **kwargs)
        self.__filter_area_buffer = self.filter_area_buffer
        self.__filter_area_data = self.filter_area_data

    def save(self, force_insert=False, force_update=False, *args, **kwargs):
        if (self.filter_area_buffer != self.__filter_area_buffer or
                self.filter_area_data != self.__filter_area_data or
                not self.pk):
            self.filter.filter_previous_time = get_init_time()
            self.filter.save()
        super(FilterArea, self).save(force_insert, force_update, *args, **kwargs)
        self.__filter_area_buffer = self.filter_area_buffer
        self.__filter_area_data = self.filter_area_data
