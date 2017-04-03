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

from django.shortcuts import render
from .forms import UploadFulcrumData
from .filters.run_filters import check_filters
from django.http import HttpResponse
from django.conf import settings
import json
import logging

logger = logging.getLogger(__file__)

def index(request):
    return viewer(request)


def geojson(request):
    from .mapping import get_geojson

    geojson_dict = {}
    if request.method == 'GET':
        if 'layer' not in request.GET:
            return HttpResponse("No layer exists, or a layer was not specified.", status=400)
        for layer in request.GET.getlist('layer'):
            if get_geojson(layer=layer):
                geojson_dict[layer] = json.loads(get_geojson(layer=layer))
    if not geojson_dict:
        return HttpResponse("No layer exists, or a layer was not specified.", status=400)
    return HttpResponse(json.dumps(geojson_dict), content_type="application/json")


def upload(request):
    from .django_fulcrum import process_fulcrum_data
    from .mapping import get_geojson

    geojson_dict = {}
    if request.method == 'POST':
        form = UploadFulcrumData(request.POST, request.FILES)
        logger.debug(request.FILES)
        if form.is_valid():
            check_filters()
            available_layers = process_fulcrum_data(request.FILES['file'], request=request)
            for layer in available_layers:
                if get_geojson(layer=layer):
                    geojson_dict[layer] = json.loads(get_geojson(layer=layer))
            return HttpResponse(json.dumps(geojson_dict), content_type="application/json")
        else:
            logger.error("FORM NOT VALID.")
    else:
        form = UploadFulcrumData()
    return render(request, 'django_fulcrum/upload.html', {'form': form})


def viewer(request):
    from .mapping import get_geojson
    if request.method == 'GET':
        basemaps = []
        tuples = settings.LEAFLET_CONFIG['TILES']
        for layer_tuple in tuples:
            name, link, attr = layer_tuple
            basemaps.append([name, link, attr])
        if 'layer' not in request.GET:
            return render(request, 'django_fulcrum/map.html', {'geojson_request_url': '', 'basemaps': basemaps})
        geojson_dict = {}
        available_layers = []
        for layer in request.GET.getlist('layer'):
            if get_geojson(layer=layer):
                available_layers += ['layer=' + layer]
        if geojson_dict:
            return render(request, 'django_fulcrum/map.html',
                          {'geojson_request_url': '/django_fulcrum/geojson?{}' + '&'.join(available_layers),
                           'basemaps': basemaps})
        else:
            return render(request, 'django_fulcrum/map.html', {'geojson_request_url': '', 'basemaps': basemaps})


def layers(request):
    from .mapping import get_layer_names
    return HttpResponse(json.dumps(get_layer_names()), content_type="application/json")
