from __future__ import absolute_import

import os
from importlib import import_module
from django.core.exceptions import ImproperlyConfigured
from django.db import OperationalError
import logging

logger = logging.getLogger(__file__)

def filter_features(features, filter_name=None, run_once=False):
    """

    Args:
        features: A geojson Feature Collection
        filter_name: The name of a filter to use if None all active filters are used (default:None)
        run_once: Run the filter one time without being active.
    Returns:
         Geojson Feature Collection that passed any filters in the in filter package
         If no features passed None is returned
    """

    from ..models import Filter
    from ..django_fulcrum import delete_feature

    workspace = os.path.dirname(os.path.abspath(__file__))
    files = os.listdir(workspace)

    if features.get('features'):
        filtered_feature_count = len(features.get('features'))
        filtered_results = None
        if filter_name:
            filter_models = Filter.objects.filter(filter_name__iexact=filter_name)
        else:
            filter_models = Filter.objects.all()
        if filter_models:
            un_needed = []
            for filter_model in filter_models:
                if filter_model.filter_name in files:
                    if filter_model.filter_active or run_once:
                        if not features:
                            break
                        try:
                            module_name = 'django_fulcrum.filters.' + str(filter_model.filter_name.rstrip('.py'))
                            mod = import_module(module_name)
                            filtered_results = mod.filter_features(features)
                        except ImportError:
                            logging.error("Could not filter features - ImportError")
                        except TypeError as te:
                            logging.error(te)
                            logging.error("Could not filter features - TypeError")
                        except Exception as e:
                            logging.error("Unknown error occurred, could not filter features")
                            logging.error(repr(e))
                        if filtered_results:
                            if filtered_results.get('failed').get('features'):
                                for feature in filtered_results.get('failed').get('features'):
                                    if run_once:
                                        delete_feature(feature.get('properties').get('fulcrum_id'))
                                logging.warn("{} features failed the filter".format(
                                        len(filtered_results.get('failed').get('features'))))
                            if filtered_results.get('passed').get('features'):
                                logging.info("{} features passed the filter".format(
                                        len(filtered_results.get('passed').get('features'))))
                                features = filtered_results.get('passed')
                                filtered_feature_count = len(filtered_results.get('passed').get('features'))
                            else:
                                features = None
                                filtered_feature_count = 0
                        else:
                            logging.error("Failure to get filtered results")
                else:
                    un_needed.append(filter_model)
            if un_needed:
                for filter_model in un_needed:
                    logging.error("The filter {} was found in the database but the module is "
                          "missing.".format(filter_model.filter_name))
                    logging.error("It will be disabled.  If the module is installed later, reenable the filter "
                          "in the admin console.")
                    filter_model.filter_active = False
    else:
        features = None
        filtered_feature_count = 0
    logger.debug("returning {0} features".format(filtered_feature_count))
    return features, filtered_feature_count


def check_filters():
    """
    Returns: True if checking the filters was successful.

    Finds '.py' files used for filtering and adds to db model for use in admin console.
    Sets cache value so function will not running fully every time it is called by tasks.py
    """
    from ..models import Filter
    from ..tasks import get_lock, set_lock, get_lock_id
    from django.db import IntegrityError
    from importlib import import_module
    workspace = os.path.dirname(os.path.abspath(__file__))
    files = os.listdir(workspace)
    if files:
        lock_id = get_lock_id('list-filters-success')
        if get_lock(lock_id):
            return True
        if not check_init():
            return False
        for filter_file in files:
            if filter_file.endswith('.py'):
                if filter_file == 'run_filters.py' or filter_file == '__init__.py':
                    continue
                try:
                    filter_names = Filter.objects.filter(filter_name__iexact=filter_file)
                    if not filter_names.exists():
                        filter_model = Filter.objects.create(filter_name=filter_file)
                        logging.info("Created filter {}".format(filter_model.filter_name))
                except IntegrityError:
                    return False
                try:
                    mod = import_module('django_fulcrum.filters.' + str(filter_file.rstrip('.py')))
                    if 'setup_filter_model' in dir(mod):
                        if mod.setup_filter_model() is False:
                            return False
                except ImportError:
                    return False
        set_lock(lock_id, True, 20)
    return True


def check_init():
    """

    Returns: True if the super admin was created.

    """
    try:
        from django.core.exceptions import AppRegistryNotReady
        try:
            from .tasks import task_update_layers, pull_s3_data
        except AppRegistryNotReady:
            django.setup()
            from .tasks import task_update_layers, pull_s3_data
    except ImportError:
        pass
    try:
        try:
            # from django.contrib.auth.models import User
            from django.contrib.auth import get_user_model
            user = get_user_model()
            if user.objects.filter(id='-1').exists() or user.objects.filter(id='1').exists():
                return True
        except ImproperlyConfigured:
            return False
    except OperationalError:
        return False