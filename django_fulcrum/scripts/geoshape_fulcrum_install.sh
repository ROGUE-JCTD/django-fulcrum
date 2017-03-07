# --!/bin/bash
# exit on any error
set -e

#install django_fulcrum
#add to  /opt/boundless/exchange/settings.py:

EXCHANGE_SETTINGS=/opt/boundless/exchange/bex/settings.py
EXCHANGE_LOCAL_SETTINGS=/opt/boundless/exchange/bex/settings.py
FILE_SERVICE_STORE=/opt/geonode/geoserver_data/file-service-store
FULCRUM_STORE=/opt/geonode/geoserver_data/fulcrum_data
EXCHANGE_URLS=/opt/boundless/exchange/.venv/lib/python2.7/site-packages/exchange/urls.py
EXCHANGE_CELERY_APP=/opt/boundless/exchange/.venv/lib/python2.7/site-packages/exchange/celery_app.py
PIP=/opt/boundless/exchange/.venv/bin/pip
GEONODE_LAYERS_MODELS=/opt/boundless/exchange//.venv/lib/python2.7/site-packages/geonode/layers/models.py


# if django-fulcrum is not mounted from host, clone from github
#yum install git -y
#cd /
#git clone https://github.com/ROGUE-JCTD/django-fulcrum.git

# assuming the /django-fulcrum has been mounted to point to host's folder
source /opt/boundless/exchange/.venv/bin/activate
cd /django-fulcrum
pip install -e .


cd ~
mkdir -p ${FULCRUM_STORE}
chown exchange:geoservice ${FULCRUM_STORE}

yum install memcached -y
service memcached start
chkconfig memcached on

# /var/lib/geonode/bin/pip install django_fulcrum
#${PIP} install fulcrum
#${PIP} install python-memcached
#${PIP} install boto3
#${PIP} install Pillow
grep -qF "INSTALLED_APPS += ('django_fulcrum',)"  ${EXCHANGE_SETTINGS} || echo "INSTALLED_APPS += ('django_fulcrum',)" >>  ${EXCHANGE_SETTINGS}



# change permissions to file_service folder so that django_fulcrum can add data to the folder.
mkdir -p ${FILE_SERVICE_STORE}
chown exchange:geoservice ${FILE_SERVICE_STORE}
chmod 775 ${FILE_SERVICE_STORE}

grep -q '^CELERY_ACCEPT_CONTENT'  ${EXCHANGE_SETTINGS} && sed -i "s/^CELERY_ACCEPT_CONTENT.*/CELERY_ACCEPT_CONTENT=['json']/"  ${EXCHANGE_SETTINGS} || echo "CELERY_ACCEPT_CONTENT=['json']" >>  ${EXCHANGE_SETTINGS}
grep -q '^CELERY_TASK_SERIALIZER'  ${EXCHANGE_SETTINGS} && sed -i "s/^CELERY_TASK_SERIALIZER.*/CELERY_TASK_SERIALIZER='json'/"  ${EXCHANGE_SETTINGS} || echo "CELERY_TASK_SERIALIZER='json'" >>  ${EXCHANGE_SETTINGS}
grep -q '^CELERY_RESULT_SERIALIZER'  ${EXCHANGE_SETTINGS} && sed -i "s/^CELERY_RESULT_SERIALIZER.*/CELERY_RESULT_SERIALIZER='json'/"  ${EXCHANGE_SETTINGS} || echo "CELERY_RESULT_SERIALIZER='json'" >>  ${EXCHANGE_SETTINGS}
grep -q '^CELERY_SEND_EVENTS'  ${EXCHANGE_SETTINGS} && sed -i "s/^CELERY_SEND_EVENTS.*/CELERY_SEND_EVENTS=True/"  ${EXCHANGE_SETTINGS} || echo "CELERY_SEND_EVENTS=True" >>  ${EXCHANGE_SETTINGS}
grep -q '^CELERYBEAT_USER'  ${EXCHANGE_SETTINGS} && sed -i "s/^CELERYBEAT_USER.*/CELERYBEAT_USER='exchange'/"  ${EXCHANGE_SETTINGS} || echo "CELERYBEAT_USER='exchange'" >>  ${EXCHANGE_SETTINGS}
grep -q '^CELERYBEAT_GROUP'  ${EXCHANGE_SETTINGS} && sed -i "s/^CELERYBEAT_GROUP.*/CELERYBEAT_GROUP='geoservice'/"  ${EXCHANGE_SETTINGS} || echo "CELERYBEAT_GROUP='geoservice'" >>  ${EXCHANGE_SETTINGS}
grep -q '^CELERYBEAT_SCHEDULER'  ${EXCHANGE_SETTINGS} && sed -i "s/^CELERYBEAT_SCHEDULER.*/CELERYBEAT_SCHEDULER='djcelery\.schedulers\.DatabaseScheduler'/"  ${EXCHANGE_SETTINGS} || echo "CELERYBEAT_SCHEDULER='djcelery.schedulers.DatabaseScheduler'" >>  ${EXCHANGE_SETTINGS}
grep -q "from datetime import timedelta"  ${EXCHANGE_SETTINGS} || echo "from datetime import timedelta" >>  ${EXCHANGE_SETTINGS}
grep -q "^CELERYBEAT_SCHEDULE ="  ${EXCHANGE_SETTINGS} ||
printf "CELERYBEAT_SCHEDULE = {\n\
    'Update_layers_30_secs': {\n\
        'task': 'django_fulcrum.tasks.task_update_layers',\n\
        'schedule': timedelta(seconds=30),\n\
        'args': None\n\
    },\n\
	'pull_s3_data_120_secs': {\n\
        'task': 'django_fulcrum.tasks.pull_s3_data',\n\
        'schedule': timedelta(seconds=120),\n\
        'args': None\n\
    },\n\
\n}\n" >>  ${EXCHANGE_SETTINGS}
grep -q '^USE_TZ'  ${EXCHANGE_SETTINGS} && sed -i "s/^USE_TZ.*/USE_TZ = True/"  ${EXCHANGE_SETTINGS} || echo "USE_TZ = True" >>  ${EXCHANGE_SETTINGS}
grep -q '^TIME_ZONE'  ${EXCHANGE_SETTINGS} && sed -i "s/^TIME_ZONE.*/TIME_ZONE = 'UTC'/"  ${EXCHANGE_SETTINGS} || echo "TIME_ZONE = 'UTC'" >>  ${EXCHANGE_SETTINGS}
echo 'CELERY_ENABLE_UTC = True' >> ${EXCHANGE_SETTINGS}
grep -q "^CACHES ="  ${EXCHANGE_SETTINGS} ||
printf "CACHES = {\n\
     'default': {\n\
         'BACKEND':\n\
         'django.core.cache.backends.memcached.MemcachedCache',\n\
         'LOCATION': '127.0.0.1:11211',\n\
     }\n\
}\n" >>  ${EXCHANGE_SETTINGS}

grep -q '^SSL_VERIFY'  ${EXCHANGE_SETTINGS} && sed -i "s/^SSL_VERIFY.*/SSL_VERIFY = False/"  ${EXCHANGE_SETTINGS} || echo "SSL_VERIFY = False" >>  ${EXCHANGE_SETTINGS}

#add to ${EXCHANGE_LOCAL_SETTINGS}:

grep -q "^FULCRUM_UPLOAD =" ${EXCHANGE_LOCAL_SETTINGS} ||
echo "FULCRUM_UPLOAD = '"${FULCRUM_STORE}"'" >> ${EXCHANGE_LOCAL_SETTINGS}

grep -q "^DATABASES['fulcrum'] =" ${EXCHANGE_LOCAL_SETTINGS} ||
echo "DATABASES['fulcrum'] = DATABASES['exchange_imports']" >> ${EXCHANGE_LOCAL_SETTINGS}

grep -q "^S3_CREDENTIALS =" ${EXCHANGE_LOCAL_SETTINGS} ||
printf "# S3_CREDENTIALS = [{'s3_bucket': ['xxxxx'],\n\
        #           's3_key': 'xxxxx',\n\
        #           's3_secret': 'xxxxx',\n\
        #           's3_gpg': 'xxxxx'},\n\
        #           {'s3_bucket': ['xxxxx'],\n\
        #           's3_key': 'xxxxx',\n\
        #           's3_secret': 'xxxxx',\n\
        #           's3_gpg': 'xxxxx'}]\n">> ${EXCHANGE_LOCAL_SETTINGS}

function getFulcrumApiKey() {
	echo "Enter Fulcrum Username:"
	read username
	echo "Enter Fulcrum Password:"
	read -s password

	echo "Getting Fulcrum API Key..."
	## get json, find api token key/value, delete the quotes and then delete the key
	apiToken=`curl -sL --user "$username:$password" https://api.fulcrumapp.com/api/v2/users.json | grep -o '"api_token":"[^"]*"' | sed -e 's/"//g' | sed -e 's/api_token://g'`

        if [ "$apiToken" != "" ]; then
		echo "Success!!!"
        else
                echo "Sorry, your Fulcrum API Key wasn't found. :("
        fi

	## if the token isn't found, it will just print blanks anyway
	echo "FULCRUM_API_KEYS=['"${apiToken}"']" >> ${EXCHANGE_LOCAL_SETTINGS}
}
grep -q '^FULCRUM_API_KEYS' ${EXCHANGE_LOCAL_SETTINGS} || getFulcrumApiKey

#add to ${EXCHANGE_URLS}:
grep -qF 'from django_fulcrum.urls import urlpatterns as django_fulcrum_urls' ${EXCHANGE_URLS} ||
printf "from django_fulcrum.urls import urlpatterns as django_fulcrum_urls\nurlpatterns += django_fulcrum_urls" >> ${EXCHANGE_URLS}

#add to ${EXCHANGE_CELERY_APP}:
grep -qF 'from django.conf import settings' ${EXCHANGE_CELERY_APP} || echo "from django.conf import settings" >> ${EXCHANGE_CELERY_APP}
grep -qF 'app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)' ${EXCHANGE_CELERY_APP} || echo "app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)" >> ${EXCHANGE_CELERY_APP}

#add to /etc/supervisord.conf:
grep -qF 'programs=waitress,celery-worker,celery-beat' /etc/supervisord.conf || sed -i "s/^programs.*/programs=waitress,celery-worker,celery-beat/" /etc/supervisord.conf

grep -qF '[program:celery-beat]' /etc/supervisord.conf ||
printf "[program:celery-beat]\n\
command =   /opt/boundless/exchange/.venv/bin/celery beat\n\
            --app=exchange.celery_app\n\
            --uid exchange\n\
            --loglevel=info\n\
            --workdir=/opt/boundless/exchange/bex\n\
stdout_logfile=/var/log/celery/celery-beat-stdout.log\n\
stderr_logfile=/var/log/celery/celery-beat-stderr.log\n\
autostart=true\n\
autorestart=true\n\
startsecs=10\n\
stopwaitsecs=600\n" >> /etc/supervisord.conf

# WARNING: this is extremly fragile, needs to be checked everytime exchange / geonode is updated
# add to /var/lib/geonode/lib/python2.7/site-packages/geonode/layers/models.py
# needs the line number of "permissions = ("
#     class Meta:
#        # custom permissions,
#        # change and delete are standard in django-guardian
#        permissions = (

sed -i "255i \ \ \ \ \ \ \ \ unique_together = ('store', 'name')" ${GEONODE_LAYERS_MODELS}
sed -i 's|--workdir=/opt/boundless/exchange/bex|--workdir=/opt/boundless/exchange/|' /etc/supervisord.conf

cd /opt/boundless/exchange
python manage.py collectstatic --noinput
python manage.py makemigrations
python manage.py migrate

# django celery migration problem
python manage.py migrate djcelery 0001 --fake
python manage.py migrate djcelery

supervisorctl restart exchange:waitress
