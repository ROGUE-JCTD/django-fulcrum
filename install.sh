#!/usr/bin/env bash
# exit on any error
set -e

if [ "$EUID" -ne 0 ]
  then echo "Please run as the root user."
  exit
fi

FILE_SERVICE_STORE=/opt/boundless/exchange/.storage/media/fileservice
FULCRUM_STORE=/opt/geonode/geoserver_data/fulcrum_data
EXCHANGE_SETTINGS=/etc/profile.d/exchange-settings.sh
EXCHANGE_DIR=/opt/boundless/exchange/
BEX_SETTINGS=/opt/boundless/exchange/bex/settings.py
EXCHANGE_URLS=/opt/boundless/exchange/.venv/lib/python2.7/site-packages/exchange/urls.py
EXCHANGE_CELERY_APP=/opt/boundless/exchange/.venv/lib/python2.7/site-packages/exchange/celery_app.py
PIP=/opt/boundless/exchange/.venv/bin/pip
PYTHON=/opt/boundless/exchange/.venv/bin/python
GEONODE_LAYERS_MODELS=/opt/boundless/exchange/.venv/lib/python2.7/site-packages/geonode/layers/models.py
MANAGE=/opt/boundless/exchange/manage.py
CELERY_BEAT_SCRIPT=/opt/boundless/exchange/celery-beat.sh

source $EXCHANGE_SETTINGS

grep FULCRUM_UPLOAD $EXCHANGE_SETTINGS && \
sed -i -e "s|export FULCRUM_UPLOAD=.*$|export FULCRUM_UPLOAD=\$\{FULCRUM_STORE\:\-'$FULCRUM_STORE'\}|" $EXCHANGE_SETTINGS || \
sed -i -e "s|set +e|export FULCRUM_UPLOAD=\$\{FULCRUM_UPLOAD\:\-'$FULCRUM_STORE'\}\nset +e|" $EXCHANGE_SETTINGS

grep FILE_SERVICE_STORE $EXCHANGE_SETTINGS && \
sed -i -e "s|export FILE_SERVICE_STORE=.*$|export FILE_SERVICE_STORE=\$\{FILE_SERVICE_STORE\:\-'$FILE_SERVICE_STORE'\}|" $EXCHANGE_SETTINGS || \
sed -i -e "s|set +e|export FILE_SERVICE_STORE=\$\{FILE_SERVICE_STORE\:\-'$FILE_SERVICE_STORE'\}\nset +e|" $EXCHANGE_SETTINGS

$PIP uninstall -y django_fulcrum
$PIP install  -e ./

mkdir -p $FULCRUM_STORE
chown exchange:geoservice $FULCRUM_STORE
chmod 775 $FULCRUM_STORE

# change permissions to file_service folder so that django_fulcrum can add data to the folder.
mkdir -p $FILE_SERVICE_STORE
chown exchange:geoservice $FILE_SERVICE_STORE
chmod 775 $FILE_SERVICE_STORE

#add to ${EXCHANGE_URLS}:
grep -qF 'from django_fulcrum.urls import urlpatterns as django_fulcrum_urls' $EXCHANGE_URLS ||
printf "\nfrom django_fulcrum.urls import urlpatterns as django_fulcrum_urls\nurlpatterns += django_fulcrum_urls\n" >> $EXCHANGE_URLS

#add to ${EXCHANGE_CELERY_APP}:
grep -qF 'from django.conf import settings' $EXCHANGE_CELERY_APP || echo "from django.conf import settings" >> $EXCHANGE_CELERY_APP
grep -qF 'app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)' ${EXCHANGE_CELERY_APP} || echo "app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)" >> ${EXCHANGE_CELERY_APP}

#add django_fulrum to bex.settings
grep -qF 'from django_fulcrum.settings import *' ${BEX_SETTINGS} ||
printf "\nfrom django_fulcrum.settings import *" >> ${BEX_SETTINGS}

if [ ! -f $CELERY_BEAT_SCRIPT ]; then

cat << END > $CELERY_BEAT_SCRIPT
#!/bin/bash

source /etc/profile.d/exchange-settings.sh
source /etc/profile.d/vendor-libs.sh
cd /opt/boundless/exchange
source .venv/bin/activate

/opt/boundless/exchange/.venv/bin/celery beat --app=exchange.celery_app --uid=exchange --loglevel=info --workdir=/opt/boundless/exchange
END

chown exchange:geoservice $CELERY_BEAT_SCRIPT
chmod 775 $CELERY_BEAT_SCRIPT

fi

#add to /etc/supervisord.conf and fix duplicate layer bug in geonode
cd $EXCHANGE_DIR
$PYTHON -  << END
import ConfigParser
import os
import django
import os
from string import Template

os.environ['DJANGO_SETTINGS_MODULE'] = 'bex.settings'
django.setup()

from django.db import connection
from django.db.utils import ProgrammingError


config_file = '/etc/supervisord.conf'
config = ConfigParser.SafeConfigParser()
config.read(config_file)
program = 'celery-beat'
program_configuration = {"command": "/opt/boundless/exchange/celery-beat.sh",
                        "stdout_logfile": "/var/log/celery/celery-beat-stdout.log",
                        "stderr_logfile": "/var/log/celery/celery-beat-stderr.log",
                        "autostart": "true",
                        "autorestart": "true",
                        "startsecs": "10",
                        "stopwaitsecs": "600"}
if program not in config.get('group:exchange', 'programs'):
    config.set('group:exchange', 'programs', '{0},{1}'.format(config.get('group:exchange', 'programs'), program))
program_section = 'program:{0}'.format(program)
if not config.has_section(program_section):
    config.add_section(program_section)
for key,value in program_configuration.iteritems():
    config.set(program_section, key, value)
with open(config_file, 'wb') as configfile:
    config.write(configfile)

geonode_layers_table = 'layers_layer'
command_template = Template("ALTER TABLE $table_name ADD CONSTRAINT store_name_key UNIQUE (store, name);")
with connection.cursor() as cursor:
    try:
        command = command_template.safe_substitute({'table_name': geonode_layers_table})
        cursor.execute(command)
    except ProgrammingError:
        pass

from geonode.base.models import TopicCategory
topic = TopicCategory.objects.get_or_create(gn_description='Fulcrum',
                                            description='Data loaded features pictures, videos, and audio.',
                                            is_choice=True,
                                            fa_class='fa-user-circle-o',
                                            identifier='fulcrum')
END
cd -

source $EXCHANGE_SETTINGS

$PYTHON $MANAGE collectstatic --noinput
$PYTHON $MANAGE loaddata django_fulcrum/fixtures/topic.json
$PYTHON $MANAGE migrate

## django celery migration problem
#$PYTHON $MANAGE migrate djcelery 0001 --fake
#$PYTHON $MANAGE migrate djcelery

service exchange restart

set +e
