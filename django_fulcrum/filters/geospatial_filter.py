import os
from shapely.geometry import Point, shape
from types import DictType
import json
import copy


def filter_features(input_features, **kwargs):
    """
    Args:
         input_features: A Geojson feature collection

    Returns:
        A json of two geojson feature collections: passed and failed
    """
    if type(input_features) is DictType:
        if input_features.get("features"):
            return iterate_geojson(input_features, **kwargs)
    else:
        print "The function filter_features is returning none due " \
              "to an invalid input_features type: {}.".format(type(input_features))
        return None


def iterate_geojson(input_features, filter_inclusion=None, **kwargs):
    """
    Args:
         input_features: A Geojson feature collection
         filter_inclusion: Optionally override the model, for include/exclude for use in testing.

    Returns:
        A json of two geojson feature collections: passed and failed
    """

    passed = []
    failed = []
    features = input_features.get("features")
    linked_filter, filter_list = create_filter_list(**kwargs)
    if not linked_filter:
        if filter_inclusion is None:
            print('The filter has not been linked to a filter_name.')
            return
    else:
        filter_inclusion = linked_filter.filter_inclusion
    for feature in features:
        feature_passed = None
        if not feature or not feature.get('geometry'):
            continue
        coords = feature.get('geometry').get('coordinates')
        if coords:
            for filter_shape in filter_list:
                if check_geometry(coords, filter_shape) and filter_inclusion:
                    feature_passed = True  # To pass inclusion the feature needs to be in only one shape.
                    break
                elif not check_geometry(coords, filter_shape) and not filter_inclusion:
                    continue  # To pass exclusion the feature needs to not exist in any shape.
                else:
                    feature_passed = False
            if feature_passed is None:
                feature_passed = True
            if feature_passed:
                passed.append(feature)
            else:
                failed.append(feature)
        else:
            passed.append(feature)
    passed_features = copy.deepcopy(input_features)
    passed_features['features'] = passed
    failed_features = input_features
    failed_features['features'] = failed
    return {'passed': passed_features, 'failed': failed_features}


def create_filter_list(boundary_features=None):
    from ..models import FilterArea
    filter_list = []
    if boundary_features:
        filter_list += boundary_features
        return None, filter_list
    else:
        for filter_area in FilterArea.objects.all():
            boundaries = get_boundary_features(geojson=filter_area.filter_area_data,
                                               buffer_dist=filter_area.filter_area_buffer)
            if filter_area.filter_area_enabled:
                filter_list += [boundaries]
        geospatial_filters = FilterArea.objects.all()
        try:
            linked_filter = geospatial_filters[0].filter
        except IndexError:
            linked_filter = None
        except ValueError:
            linked_filter = None
        return linked_filter, filter_list


def check_geometry(coords, boundary_features):
    """
    Args:
        coords: Array of coordinates
        boundary_features: An array of shapely Polygons/MultiPolygons used to filter features

    Returns:
         True if coordinates lie within any boundary_features
         False if coordinate do not lie within any boundary_features
    """
    point = Point(coords[0], coords[1])
    if boundary_features:
        for index, boundary in enumerate(boundary_features):
            if boundary_features[index].contains(point):
                return True
    return False


def setup_filter_model():
    from ..models import FilterArea, Filter
    from django.core.exceptions import ObjectDoesNotExist
    from django.db import IntegrityError, transaction

    try:
        geospatial_filter = Filter.objects.get(filter_name__iexact='geospatial_filter.py')
    except ObjectDoesNotExist:
        print("Geospatial Filter hasn't been saved to the database yet.")
        return False
    boundary_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'boundary_polygons')
    for boundary_file in os.listdir(boundary_file_path):
        if boundary_file.endswith('.geojson'):
            try:
                filter_area_names = FilterArea.objects.filter(filter_area_name__iexact=boundary_file)
                if not filter_area_names.exists():
                    FilterArea.objects.create(filter_area_name=boundary_file, filter=geospatial_filter)
                else:
                    with transaction.atomic():
                        filter_area = filter_area_names[0]
                        with open(os.path.join(boundary_file_path, boundary_file)) as file_data:
                            filter_area.filter_area_data = file_data.read()
                            filter_area.save()
            except IntegrityError:
                continue
    return True


def get_boundary_features(geojson, buffer_dist):
    """
    Args:
        geojson: A geojson string.
        buffer_dist: A float representing a distance to surround the boundaries.

    Returns:
         An array of shapely Polygons or MultiPolygons from the boundary_polygon file which should contain geojson files
    """
    boundaries = []
    geometries = []
    try:
        data = json.loads(geojson)
        if data.get("features"):
            for feature in data.get("features"):
                geometries += [feature.get('geometry')]
        else:
            geometries = [data.get("geometry")]
        if geometries:
            for data in geometries:
                geometry = shape(data).buffer(buffer_dist)
                if geometry.geom_type is 'MultiPolygon' or geometry.geom_type is 'Polygon':
                    boundaries += [geometry]
    except ValueError:
        print "Error getting polygon data"
    return boundaries
