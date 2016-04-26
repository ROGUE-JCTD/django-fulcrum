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


def get_geojson(layer=None):
    """

    Args:
        layer: Converts the feature data for a layer to geojson.

    Returns:

    """
    from django.core.exceptions import ObjectDoesNotExist
    from .models import Layer, Feature
    import json
    import time
    from dateutil import parser

    json_features = []
    try:
        if layer:
            layer = Layer.objects.get(layer_name=layer)
            features = Feature.objects.filter(layer=layer)
        else:
            features = Feature.objects.all()
    except ObjectDoesNotExist:
        return None
    for feature in features:
        json_feature = json.loads(feature.feature_data)
        if json_feature.get('properties').get('system_updated_at'):
            date = parser.parse(json_feature.get('properties').get('system_updated_at'))
        elif json_feature.get('properties').get('updated_at'):
            date = parser.parse(json_feature.get('properties').get('updated_at'))
        elif json_feature.get('properties').get('created_at'):
            date = parser.parse(json_feature.get('properties').get('created_at'))
        else:
            date = None
        if date:
            json_feature["properties"]["time"] = time.mktime(date.timetuple())
        json_features += [json_feature]

    feature_collection = {"type": "FeatureCollection", "features": json_features}
    return json.dumps(feature_collection)


def get_layer_names():
    """

    Returns: The layers as a dict.

    """
    from .models import Layer

    layers = {}
    for layer in Layer.objects.all():
        layers[layer.layer_name] = None
    return layers
