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

from django.conf import settings
from django.core.cache import caches
from celery import shared_task
from hashlib import md5
from .s3_downloader import pull_all_s3_data
from .models import FulcrumApiKey
from .filters.run_filters import check_filters
from fulcrum.exceptions import UnauthorizedException
import time
import logging

logger = logging.getLogger(__file__)


@shared_task(name="django_fulcrum.tasks.update_geonode_layers")
def update_geonode_layers(**kwargs):
    """
    Runs update layers.
    """
    from geonode.geoserver.helpers import gs_slurp
    from geonode.people.models import Profile

    owner = kwargs.get('owner')

    if owner and not isinstance(owner, Profile):
        kwargs['owner'] = Profile.objects.get(username=owner)

    return gs_slurp(**kwargs)

@shared_task(name="django_fulcrum.tasks.task_update_layers")
def task_update_layers():

    from .django_fulcrum import DjangoFulcrum

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
        logging.error("Cannot update layers from fulcrum without an API key added to the admin page, "
              "or FULCRUM_API_KEYS = ['some_key'] defined in settings.")

    # http://docs.celeryproject.org/en/latest/tutorials/task-cookbook.html#ensuring-a-task-is-only-executed-one-at-a-time
    lock_id = get_lock_id("django_fulcrum.tasks.task_update_layers")

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
                    django_fulcrum = DjangoFulcrum(fulcrum_api_key=fulcrum_api_key)
                    django_fulcrum.update_all_layers()
                except UnauthorizedException:
                    logging.error("The API key ending in: {}, is unauthorized.".format(fulcrum_api_key[-4:]))
                    continue
        finally:
            release_lock(lock_id)


@shared_task(name="django_fulcrum.tasks.pull_s3_data")
def pull_s3_data():
    if not check_filters():
        return False
    pull_all_s3_data()


@shared_task(name="django_fulcrum.tasks.task_update_tiles")
def update_tiles(filtered_features, layer_name=''):
    from .django_fulcrum import truncate_tiles

    truncate_tiles(layer_name=layer_name.lower(), srs=4326)
    truncate_tiles(layer_name=layer_name.lower(), srs=900913)


@shared_task(name="django_fulcrum.tasks.task_filter_features")
def task_filter_features(filter_name, features, run_once=False, run_time=None):
    from .models import Filter, Layer
    from .filters.run_filters import filter_features

    if not check_filters():
        return False

    task_name = "django_fulcrum.tasks.task_filter_features"
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


@shared_task(name="django_fulcrum.tasks.task_filter_assets")
def task_filter_assets(filter_name, after_time_added, run_once=False, run_time=None):
    from .models import Filter, Asset
    from dateutil.parser import parse
    from .django_fulcrum import is_valid_photo

    task_name = "django_fulcrum.tasks.task_filter_assets"
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
                        logging.info("Attempting to delete {}".format(asset.asset_data.path))
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
        if get_lock(get_lock_id(task_name)):
            return True


def is_filter_task_locked(filter_name):
    """
    Args:
        filter_name: The name of the filter task to look for.

    Returns True if one of the tasks which filters is currently running."""
    from .models import Filter

    for task_name in list_task_names():
        if get_lock(Filter.get_lock_id(task_name, filter_name)):
            return True


def get_lock_id(name):
    lock_id = '{0}-lock-{1}'.format(name, md5(name).hexdigest())
    logger.debug("lock id: {0}".format(lock_id))
    return lock_id


def list_task_names():
    names = []
    global_items = globals()
    for global_item, val in global_items.iteritems():
        try:
            names += [val.name]
        except AttributeError:
            continue
    return names

def get_lock(lock_id):
    lock = caches['fulcrum'].get(lock_id)
    if lock:
        logger.debug("lock {0} exists".format(lock_id))
    else:
        logger.debug("lock {0} does NOT exist".format(lock_id))
    return lock


def set_lock(lock_id, *args):
    logger.debug("Setting lock {0}".format(lock_id))
    caches['fulcrum'].set(lock_id, args)


def acquire_lock(lock_id, expire):
    lock = caches['fulcrum'].add(lock_id, True, expire)
    if lock:
        logger.debug("Successfully obtained lock {0}".format(lock_id))
    else:
        logger.debug("Failed to obtain lock {0}".format(lock_id))
    return lock


def release_lock(lock_id):
    logger.debug("Releasing lock {0}".format(lock_id))
    return caches['fulcrum'].delete(lock_id)
