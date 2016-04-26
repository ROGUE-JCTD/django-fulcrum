"""alerts URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from . import views
from .signals import handlers  # Signals appear to be unused but they are actually registered with django.

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    url(r'^fulcrum_geojson$', views.geojson),
    url(r'^fulcrum_map$', views.viewer),
    url(r'^fulcrum_viewer$', views.viewer),
    url(r'^fulcrum_upload$', views.upload),
    url(r'^fulcrum_layers$', views.layers),
    url(r'^fulcrum_pzworkflow$', views.pzworkflow)
]

