#!/usr/bin/env bash

read -p "Are you want to remove django-fulcrum and all of the associated data? " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then

FILE_SERVICE_STORE=/opt/geonode/geoserver_data/file-service-store
FULCRUM_STORE=/opt/geonode/geoserver_data/fulcrum_data
EXCHANGE_SETTINGS=/etc/profile.d/exchange-settings.sh
BEX_SETTINGS=/opt/boundless/exchange/bex/settings.py
EXCHANGE_URLS=/opt/boundless/exchange/.venv/lib/python2.7/site-packages/exchange/urls.py
PIP=/opt/boundless/exchange/.venv/bin/pip
PYTHON=/opt/boundless/exchange/.venv/bin/python
MANAGE=/opt/boundless/exchange/manage.py

grep FULCRUM_UPLOAD $EXCHANGE_SETTINGS && \
sed -i -e "s|export FULCRUM_UPLOAD=.*$||" $EXCHANGE_SETTINGS

# if django-fulcrum is not mounted from host, clone from github
yum install git -y
$PYTHON $MANAGE sqlclear django_fulcrum
$PIP uninstall -y django_fulcrum

rm -rf $FULCRUM_STORE

# Other content may exist in the file-service-store, so it doesn't make sense to remove it,
# unless only being used for django-fulcrum
# rm -rf $FILE_SERVICE_STORE

#add to ${EXCHANGE_URLS}:
grep -qF 'from django_fulcrum.urls import urlpatterns as django_fulcrum_urls' $EXCHANGE_URLS && \
sed -i -e "s|from django_fulcrum.urls import urlpatterns as django_fulcrum_urls||"  $EXCHANGE_URLS && \
sed -i -e "s|urlpatterns += django_fulcrum_urls||"  $EXCHANGE_URLS


#add django_fulrum to bex.settings
grep -qF 'from django_fulcrum.settings import *' ${BEX_SETTINGS} && \
sed -i -e "s|\nfrom django_fulcrum.settings import.*$||" ${BEX_SETTINGS}

# django celery migration problem
service exchange restart

fi