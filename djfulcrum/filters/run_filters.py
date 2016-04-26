from __future__ import absolute_import

import os
from importlib import import_module


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
    from ..djfulcrum import delete_feature

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
                            module_name = 'djfulcrum.filters.' + str(filter_model.filter_name.rstrip('.py'))
                            mod = import_module(module_name)
                            print "Running: {}".format(filter_model.filter_name)
                            filtered_results = mod.filter_features(features)
                        except ImportError:
                            print "Could not filter features - ImportError"
                        except TypeError as te:
                            print te
                            print "Could not filter features - TypeError"
                        except Exception as e:
                            "Unknown error occurred, could not filter features"
                            print repr(e)
                        if filtered_results:
                            if filtered_results.get('failed').get('features'):
                                for feature in filtered_results.get('failed').get('features'):
                                    if run_once:
                                        delete_feature(feature.get('properties').get('fulcrum_id'))
                                print "{} features failed the filter".format(
                                        len(filtered_results.get('failed').get('features')))
                            if filtered_results.get('passed').get('features'):
                                print "{} features passed the filter".format(
                                        len(filtered_results.get('passed').get('features')))
                                features = filtered_results.get('passed')
                                filtered_feature_count = len(filtered_results.get('passed').get('features'))
                            else:
                                features = None
                                filtered_feature_count = 0
                        else:
                            print "Failure to get filtered results"
                else:
                    un_needed.append(filter_model)
            if un_needed:
                for filter_model in un_needed:
                    print("The filter {} was found in the database but the module is "
                          "missing.".format(filter_model.filter_name))
                    print("It will be disabled.  If the module is installed later, reenable the filter "
                          "in the admin console.")
                    filter_model.filter_active = False
    else:
        features = None
        filtered_feature_count = 0
    return features, filtered_feature_count


def check_filters():
    """
    Returns: True if checking the filters was successful.

    Finds '.py' files used for filtering and adds to db model for use in admin console.
    Sets cache value so function will not running fully every time it is called by tasks.py
    """
    from ..models import Filter
    from ..tasks import get_lock_id
    from django.db import IntegrityError
    from importlib import import_module
    from django.core.cache import cache
    workspace = os.path.dirname(os.path.abspath(__file__))
    files = os.listdir(workspace)
    if files:
        lock_id = get_lock_id('list-filters-success')
        if cache.get(lock_id):
            return True
        for filter_file in files:
            if filter_file.endswith('.py'):
                if filter_file == 'run_filters.py' or filter_file == '__init__.py':
                    continue
                try:
                    filter_names = Filter.objects.filter(filter_name__iexact=filter_file)
                    if not filter_names.exists():
                        filter_model = Filter.objects.create(filter_name=filter_file)
                        print ("Created filter {}".format(filter_model.filter_name))
                except IntegrityError:
                    return False
                try:
                    mod = import_module('djfulcrum.filters.' + str(filter_file.rstrip('.py')))
                    if 'setup_filter_model' in dir(mod):
                        mod.setup_filter_model()
                except ImportError:
                    return False
        cache.set(lock_id, True, 20)
        return True
