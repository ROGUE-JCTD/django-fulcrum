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

# ogr2ogr.py is Copyright (c) 2010-2013, Even Rouault <even dot rouault at mines-paris dot org>
# Copyright (c) 1999, Frank Warmerdam


from __future__ import absolute_import

from .djfulcrum import DjangoFulcrum, truncate_tiles
from django.conf import settings
from django.core.cache import cache
from celery import shared_task
from hashlib import md5
from .s3_downloader import pull_all_s3_data
from .models import FulcrumApiKey
from .filters.run_filters import check_filters
from fulcrum.exceptions import UnauthorizedException
import time


@shared_task(name="djfulcrum.tasks.task_update_layers")
def task_update_layers():

    fulcrum_api_keys = []
    try:
        fulcrum_api_keys = settings.FULCRUM_API_KEYS
    except AttributeError:
        pass

    if type(fulcrum_api_keys) != list:
        fulcrum_api_keys = [fulcrum_api_keys]

    for api_key in FulcrumApiKey.objects.all():
        fulcrum_api_keys += [api_key.fulcrum_api_key]

    if not fulcrum_api_keys:
        print("Cannot update layers from fulcrum without an API key added to the admin page, "
              "or FULCRUM_API_KEYS = ['some_key'] defined in settings.")

    # http://docs.celeryproject.org/en/latest/tutorials/task-cookbook.html#ensuring-a-task-is-only-executed-one-at-a-time
    lock_id = get_lock_id("djfulcrum.tasks.task_update_layers")

    lock_expire = 60 * 60
    if acquire_lock(lock_id, lock_expire):
        if not check_filters():
            release_lock(lock_id)
            return False
        try:
            for fulcrum_api_key in fulcrum_api_keys:
                if not fulcrum_api_key:
                    continue
                try:
                    djfulcrum = DjangoFulcrum(fulcrum_api_key=fulcrum_api_key)
                    djfulcrum.update_all_layers()
                except UnauthorizedException:
                    print("The API key ending in: {}, is unauthorized.".format(fulcrum_api_key[-4:]))
                    continue
        finally:
            release_lock(lock_id)


@shared_task(name="djfulcrum.tasks.pull_s3_data")
def pull_s3_data():
    if not check_filters():
        return False
    pull_all_s3_data()


@shared_task(name="djfulcrum.tasks.task_update_tiles")
def update_tiles(filtered_features, layer_name=''):
    truncate_tiles(layer_name=layer_name.lower(), srs=4326)
    truncate_tiles(layer_name=layer_name.lower(), srs=900913)


@shared_task(name="djfulcrum.tasks.task_filter_features")
def task_filter_features(filter_name, features, run_once=False, run_time=None):
    from .models import Filter, Layer
    from .filters.run_filters import filter_features

    check_filters()

    task_name = "djfulcrum.tasks.task_filter_features"
    filter_lock_expire = 60 * 60
    filter_model = Filter.objects.get(filter_name=filter_name)
    if acquire_lock(Filter.get_lock_id(task_name, filter_model.filter_name), filter_lock_expire):
        filter_model.save()
        while is_feature_task_locked():
            time.sleep(1)
        try:
            filtered_features = filter_features(features, filter_name=filter_name, run_once=run_once)
            for layer in Layer.objects.all():
                update_tiles(filtered_features=filtered_features, layer_name=layer.layer_name)
            filter_model.filter_previous_time = run_time
        finally:
            release_lock(Filter.get_lock_id(task_name, filter_model.filter_name))
            filter_model.save()


@shared_task(name="djfulcrum.tasks.task_filter_assets")
def task_filter_assets(filter_name, after_time_added, run_once=False, run_time=None):
    from .models import Filter, Asset
    from dateutil.parser import parse
    from .djfulcrum import is_valid_photo

    task_name = "djfulcrum.tasks.task_filter_assets"
    filter_lock_expire = 60 * 60
    filter_model = Filter.objects.get(filter_name=filter_name)
    if acquire_lock(Filter.get_lock_id(task_name, filter_model.filter_name), filter_lock_expire):
        assets = Asset.objects.exclude(asset_added_time__lt=parse(after_time_added))
        filter_model.save()
        while is_feature_task_locked():
            time.sleep(1)
        try:
            delete_list = []
            for asset in assets:
                if asset.asset_type == 'photos':
                    if not is_valid_photo(asset.asset_data.path, filter_name=filter_name, run_once=run_once):
                        print("Attempting to delete {}".format(asset.asset_data.path))
                        delete_list += [asset.asset_uid]
            for asset_uid in delete_list:
                Asset.objects.filter(asset_uid__iexact=asset_uid).delete()
            filter_model.filter_previous_time = run_time
        finally:
            release_lock(Filter.get_lock_id(task_name, filter_model.filter_name))
            filter_model.save()


def is_feature_task_locked():
    """Returns True if one of the tasks which add features is currently running."""
    for task_name in list_task_names():
        if cache.get(get_lock_id(task_name)):
            return True


def is_filter_task_locked(filter_name):
    """
    Args:
        filter_name: The name of the filter task to look for.

    Returns True if one of the tasks which filters is currently running."""
    from .models import Filter

    for task_name in list_task_names():
        if cache.get(Filter.get_lock_id(task_name, filter_name)):
            return True


def get_lock_id(name):
    return '{0}-lock-{1}'.format(name, md5(name).hexdigest())


def list_task_names():
    names = []
    global_items = globals()
    for global_item, val in global_items.iteritems():
        try:
            names += [val.name]
        except AttributeError:
            continue
    return names


def acquire_lock(lock_id, expire):
    return cache.add(lock_id, True, expire)


def release_lock(lock_id):
    return cache.delete(lock_id)
