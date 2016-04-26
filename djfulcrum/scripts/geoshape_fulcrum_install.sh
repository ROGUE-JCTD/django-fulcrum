#!/bin/bash

#install djfulcrum
#add to /var/lib/geonode/rogue_geonode/geoshape/settings.py: 
cd ~
yum install unzip -y
wget https://github.com/venicegeo/fm-mvp/archive/master.zip
# wget https://github.com/venicegeo/fm-mvp/archive/master.zip
unzip master.zip
mv -f fm-mvp-master/mvp/djfulcrum /var/lib/geonode/lib/python2.7/site-packages/
chown geoshape:geoservice -R /var/lib/geonode/lib/python2.7/site-packages/djfulcrum
rm master.zip
rm -rf master

mkdir /var/lib/geonode/fulcrum_data
chown geoshape:geoservice /var/lib/geonode/fulcrum_data
yum install memcached -y
service memcached start
chkconfig memcached on

/var/lib/geonode/bin/pip install djfulcrum
/var/lib/geonode/bin/pip install fulcrum
/var/lib/geonode/bin/pip install python-memcached
/var/lib/geonode/bin/pip install boto3
/var/lib/geonode/bin/pip install Pillow
grep -qF "INSTALLED_APPS += ('djfulcrum',)" /var/lib/geonode/rogue_geonode/geoshape/settings.py || echo "INSTALLED_APPS += ('djfulcrum',)" >> /var/lib/geonode/rogue_geonode/geoshape/settings.py

# change permissions to file_service folder so that djfulcrum can add data to the folder.
chown tomcat:geoservice /var/lib/geoserver_data/file-service-store
chmod 775 /var/lib/geoserver_data/file-service-store

grep -q '^CELERY_ACCEPT_CONTENT' /var/lib/geonode/rogue_geonode/geoshape/settings.py && sed -i "s/^CELERY_ACCEPT_CONTENT.*/CELERY_ACCEPT_CONTENT=['json']/" /var/lib/geonode/rogue_geonode/geoshape/settings.py || echo "CELERY_ACCEPT_CONTENT=['json']" >> /var/lib/geonode/rogue_geonode/geoshape/settings.py
grep -q '^CELERY_TASK_SERIALIZER' /var/lib/geonode/rogue_geonode/geoshape/settings.py && sed -i "s/^CELERY_TASK_SERIALIZER.*/CELERY_TASK_SERIALIZER='json'/" /var/lib/geonode/rogue_geonode/geoshape/settings.py || echo "CELERY_TASK_SERIALIZER='json'" >> /var/lib/geonode/rogue_geonode/geoshape/settings.py
grep -q '^CELERY_RESULT_SERIALIZER' /var/lib/geonode/rogue_geonode/geoshape/settings.py && sed -i "s/^CELERY_RESULT_SERIALIZER.*/CELERY_RESULT_SERIALIZER='json'/" /var/lib/geonode/rogue_geonode/geoshape/settings.py || echo "CELERY_RESULT_SERIALIZER='json'" >> /var/lib/geonode/rogue_geonode/geoshape/settings.py
grep -q '^CELERY_SEND_EVENTS' /var/lib/geonode/rogue_geonode/geoshape/settings.py && sed -i "s/^CELERY_SEND_EVENTS.*/CELERY_SEND_EVENTS=True/" /var/lib/geonode/rogue_geonode/geoshape/settings.py || echo "CELERY_SEND_EVENTS=True" >> /var/lib/geonode/rogue_geonode/geoshape/settings.py
grep -q '^CELERYBEAT_USER' /var/lib/geonode/rogue_geonode/geoshape/settings.py && sed -i "s/^CELERYBEAT_USER.*/CELERYBEAT_USER='geoshape'/" /var/lib/geonode/rogue_geonode/geoshape/settings.py || echo "CELERYBEAT_USER='geoshape'" >> /var/lib/geonode/rogue_geonode/geoshape/settings.py
grep -q '^CELERYBEAT_GROUP' /var/lib/geonode/rogue_geonode/geoshape/settings.py && sed -i "s/^CELERYBEAT_GROUP.*/CELERYBEAT_GROUP='geoservice'/" /var/lib/geonode/rogue_geonode/geoshape/settings.py || echo "CELERYBEAT_GROUP='geoservice'" >> /var/lib/geonode/rogue_geonode/geoshape/settings.py
grep -q '^CELERYBEAT_SCHEDULER' /var/lib/geonode/rogue_geonode/geoshape/settings.py && sed -i "s/^CELERYBEAT_SCHEDULER.*/CELERYBEAT_SCHEDULER='djcelery\.schedulers\.DatabaseScheduler'/" /var/lib/geonode/rogue_geonode/geoshape/settings.py || echo "CELERYBEAT_SCHEDULER='djcelery.schedulers.DatabaseScheduler'" >> /var/lib/geonode/rogue_geonode/geoshape/settings.py
grep -q "from datetime import timedelta" /var/lib/geonode/rogue_geonode/geoshape/settings.py || echo "from datetime import timedelta" >> /var/lib/geonode/rogue_geonode/geoshape/settings.py
grep -q "^CELERYBEAT_SCHEDULE =" /var/lib/geonode/rogue_geonode/geoshape/settings.py ||
printf "CELERYBEAT_SCHEDULE = {\n\
    'Update_layers_30_secs': {\n\
        'task': 'djfulcrum.tasks.task_update_layers',\n\
        'schedule': timedelta(seconds=30),\n\
        'args': None\n\
    },\n\
	'pull_s3_data_120_secs': {\n\
        'task': 'djfulcrum.tasks.pull_s3_data',\n\
        'schedule': timedelta(seconds=120),\n\
        'args': None\n\
    },\n\
\n}\n" >> /var/lib/geonode/rogue_geonode/geoshape/settings.py
grep -q '^USE_TZ' /var/lib/geonode/rogue_geonode/geoshape/settings.py && sed -i "s/^USE_TZ.*/USE_TZ = False/" /var/lib/geonode/rogue_geonode/geoshape/settings.py || echo "USE_TZ = False" >> /var/lib/geonode/rogue_geonode/geoshape/settings.py
grep -q '^TIME_ZONE' /var/lib/geonode/rogue_geonode/geoshape/settings.py && sed -i "s/^TIME_ZONE.*/TIME_ZONE = None/" /var/lib/geonode/rogue_geonode/geoshape/settings.py || echo "TIME_ZONE = None" >> /var/lib/geonode/rogue_geonode/geoshape/settings.py
grep -q "^CACHES =" /var/lib/geonode/rogue_geonode/geoshape/settings.py ||
printf "CACHES = {\n\
     'default': {\n\
         'BACKEND':\n\
         'django.core.cache.backends.memcached.MemcachedCache',\n\
         'LOCATION': '127.0.0.1:11211',\n\
     }\n\
}\n" >> /var/lib/geonode/rogue_geonode/geoshape/settings.py

grep -q '^SSL_VERIFY' /var/lib/geonode/rogue_geonode/geoshape/settings.py && sed -i "s/^SSL_VERIFY.*/SSL_VERIFY = False/" /var/lib/geonode/rogue_geonode/geoshape/settings.py || echo "SSL_VERIFY = False" >> /var/lib/geonode/rogue_geonode/geoshape/settings.py

#add to /var/lib/geonode/rogue_geonode/geoshape/local_settings.py:

grep -q "^FULCRUM_UPLOAD =" /var/lib/geonode/rogue_geonode/geoshape/local_settings.py ||
echo "FULCRUM_UPLOAD = '/var/lib/geonode/fulcrum_data'" >> /var/lib/geonode/rogue_geonode/geoshape/local_settings.py

grep -q "^DATABASES['fulcrum'] =" /var/lib/geonode/rogue_geonode/geoshape/local_settings.py ||
echo "DATABASES['fulcrum'] = DATABASES['geoshape_imports']" >> /var/lib/geonode/rogue_geonode/geoshape/local_settings.py

grep -q "^S3_CREDENTIALS =" /var/lib/geonode/rogue_geonode/geoshape/local_settings.py ||
printf "# S3_CREDENTIALS = [{'s3_bucket': ['xxxxx'],\n\
        #           's3_key': 'xxxxx',\n\
        #           's3_secret': 'xxxxx',\n\
        #           's3_gpg': 'xxxxx'},\n\
        #           {'s3_bucket': ['xxxxx'],\n\
        #           's3_key': 'xxxxx',\n\
        #           's3_secret': 'xxxxx',\n\
        #           's3_gpg': 'xxxxx'}]\n">> /var/lib/geonode/rogue_geonode/geoshape/local_settings.py

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
	echo "FULCRUM_API_KEYS=['$apiToken']" >> /var/lib/geonode/rogue_geonode/geoshape/local_settings.py
}
grep -q '^FULCRUM_API_KEYS' /var/lib/geonode/rogue_geonode/geoshape/local_settings.py || getFulcrumApiKey

#add to /var/lib/geonode/rogue_geonode/geoshape/urls.py:
grep -qF 'from djfulcrum.urls import urlpatterns as djfulcrum_urls' /var/lib/geonode/rogue_geonode/geoshape/urls.py ||
printf "from djfulcrum.urls import urlpatterns as djfulcrum_urls\nurlpatterns += djfulcrum_urls" >> /var/lib/geonode/rogue_geonode/geoshape/urls.py

#add to /var/lib/geonode/rogue_geonode/geoshape/celery_app.py:
grep -qF 'from django.conf import settings' /var/lib/geonode/rogue_geonode/geoshape/celery_app.py || echo "from django.conf import settings" >> /var/lib/geonode/rogue_geonode/geoshape/celery_app.py
grep -qF 'app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)' /var/lib/geonode/rogue_geonode/geoshape/celery_app.py || echo "app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)" >> /var/lib/geonode/rogue_geonode/geoshape/celery_app.py

#add to /etc/supervisord.conf:
grep -qF 'programs=uwsgi,celery-worker1,celery-worker2,celery-worker3,celery-worker4,celery-worker5,celery-beat' /etc/supervisord.conf || sed -i "s/^programs.*/programs=uwsgi,celery-worker1,celery-worker2,celery-worker3,celery-worker4,celery-worker5,celery-beat/" /etc/supervisord.conf

grep -qF '[program:celery-beat]' /etc/supervisord.conf ||
printf "[program:celery-beat]\n\
command =   /var/lib/geonode/bin/celery beat\n\
            --app=geoshape.celery_app\n\
            --uid geoshape\n\
            --loglevel=info\n\
            --workdir=/var/lib/geonode/rogue_geonode\n\
stdout_logfile=/var/log/celery/celery-beat-stdout.log\n\
stderr_logfile=/var/log/celery/celery-beat-stderr.log\n\
autostart=true\n\
autorestart=true\n\
startsecs=10\n\
stopwaitsecs=600\n" >> /etc/supervisord.conf

# add to /var/lib/geonode/lib/python2.7/site-packages/geonode/layers/models.py
sed -i "224i \ \ \ \ \ \ \ \ unique_together = ('store', 'name')" /var/lib/geonode/lib/python2.7/site-packages/geonode/layers/models.py
