#!/usr/bin/env bash

if [ "$EUID" -ne 0 ]
  then echo "Please run as the root user."
  exit
fi

read -p "Are you want to remove django-fulcrum and all of the associated data? " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then

FULCRUM_STORE=/opt/geonode/geoserver_data/fulcrum_data
EXCHANGE_SETTINGS=/etc/profile.d/exchange-settings.sh
EXCHANGE_DIR=/opt/boundless/exchange/
BEX_SETTINGS=$EXCHANGE_DIR/bex/settings.py
EXCHANGE_URLS=$EXCHANGE_DIR/.venv/lib/python2.7/site-packages/exchange/urls.py
PIP=$EXCHANGE_DIR/.venv/bin/pip
PYTHON=$EXCHANGE_DIR/.venv/bin/python
MANAGE=$EXCHANGE_DIR/manage.py
CELERY_BEAT_SCRIPT=$EXCHANGE_DIR/celery-beat.sh

grep FULCRUM_UPLOAD $EXCHANGE_SETTINGS && \
sed -i -e "s|export FULCRUM_UPLOAD=.*$||" $EXCHANGE_SETTINGS

cd $EXCHANGE_DIR
$PYTHON - <<END
import django
import os
from string import Template

os.environ['DJANGO_SETTINGS_MODULE'] = 'bex.settings'
django.setup()

from django.db import connection
from django.db.utils import ProgrammingError


from djcelery.models import PeriodicTask
try:
    PeriodicTask.objects.get(name='django_fulcrum.tasks.task_update_layers').delete()
    print("Successfully removed PeriodicTask: django_fulcrum.tasks.task_update_layers")
except PeriodicTask.DoesNotExist as e:
    print("Unable to remove PeriodicTask: django_fulcrum.tasks.task_update_layers")
    print(e)

try:
    PeriodicTask.objects.get(name='django_fulcrum.tasks.pull_s3_data').delete()
    print("Successfully removed PeriodicTask: django_fulcrum.tasks.pull_s3_data")
except PeriodicTask.DoesNotExist as e:
    print("Unable to remove PeriodicTask: django_fulcrum.tasks.pull_s3_data")
    print(e)

from geonode.base.models import TopicCategory
try:
    TopicCategory.objects.get(gn_description='Fulcrum').delete()
    print("Successfully removed TopicCategory: Fulcrum")
except TopicCategory.DoesNotExist as e:
    print("Unable to remove TopicCategory: Fulcrum")
    print(e)

django_fulcrum_tables = ['django_fulcrum_asset',
                        'django_fulcrum_feature',
                        'django_fulcrum_filter',
                        'django_fulcrum_filterarea',
                        'django_fulcrum_filtergeneric',
                        'django_fulcrum_fulcrumapikey',
                        'django_fulcrum_layer',
                        'django_fulcrum_s3bucket',
                        'django_fulcrum_s3credential',
                        'django_fulcrum_s3sync',
                        'django_fulcrum_textfilter']

command_template = Template("DROP TABLE \$tables CASCADE;")
with connection.cursor() as cursor:
    try:
        command = command_template.safe_substitute({'tables': ','.join(django_fulcrum_tables)})
        cursor.execute(command)
        print("Removed the django_fulcrum tables.")
    except ProgrammingError as error:
        print(error)
END
cd -

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
sed -i -e "s|from django_fulcrum.settings import.*$||" ${BEX_SETTINGS}

# django celery migration problem
service exchange restart

fi