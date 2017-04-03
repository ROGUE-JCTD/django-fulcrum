
from datetime import timedelta
import os
import dj_database_url
try:
    from bex.settings import *
except ImportError:
    pass

EXCHANGE_LOCAL_SETTINGS = locals().get('EXCHANGE_LOCAL_SETTINGS', os.getenv('EXCHANGE_LOCAL_SETTINGS', '/opt/boundless/exchange/bex/settings.py'))

INSTALLED_APPS = locals().get('INSTALLED_APPS', tuple())
INSTALLED_APPS += ('django_fulcrum',)

if locals().get('DATABASES'):
    DATABASES['fulcrum'] = dj_database_url.parse(os.getenv('POSTGIS_URL'))
    if not DATABASES['fulcrum']:
        for name, configuration in DATABASES.iteritems():
            if 'postgis' in configuration.get('ENGINE'):
                DATABASES['fulcrum'] = configuration
                break

# DATABASES = {
#         'fulcrum': {
#             'ENGINE': 'django.contrib.gis.db.backends.postgis',
#             'NAME': 'postgis',
#             'USER': 'user',
#             'PASSWORD': 'password',
#             'HOST': 'host',
#             'PORT': 'port'
#         }
#     }

# if not locals().get('DATABASES', {}).get('fulcrum'):
#     raise Exception("A database was not configured for django fulrum. \n"
#                     "A database called 'fulcrum' is expected in DATABASES.")


# OGC_SERVER = {
#     'default': {
#         'BACKEND': 'backend.geoserver',
#         'LOCATION': GEOSERVER_URL,
#         'PUBLIC_LOCATION': GEOSERVER_URL,
#         'USER': 'admin',
#         'PASSWORD': 'xxxxxxx',
#         'DATASTORE': 'exchange_imports',
#     }
# }

FULCRUM_API_KEY= os.getenv("FULCRUM_API_KEY")
FULCRUM_UPLOAD = os.getenv("FULCRUM_UPLOAD")
FULCRUM_LAYER_PREFIX = os.getenv('FULCRUM_LAYER_PREFIX')

S3_CREDENTIALS = [
    # {
    # 's3_bucket': ['my_s3_bucket'],
    # 's3_key': 'XXXXXXXXXXXXXXXXXXXX',
    # 's3_secret': 'XxXxXxXxXxXxXxXxXxXxXxX',
    # 's3_gpg': 'XxXxXxXxXxXxX'
    # }
]

#Define the cache to be used. Memcache is suggested, but other process safe caches can be used too (e.g. file or database)

CACHES = locals().get('CACHES', {})
CACHES['fulcrum'] = {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': os.path.dirname(__file__),
    }

CELERY_ACCEPT_CONTENT = locals().get('CELERY_ACCEPT_CONTENT', ['json'])
CELERY_TASK_SERIALIZER = locals().get('CELERY_TASK_SERIALIZER', 'json')
CELERY_RESULT_SERIALIZER = locals().get('CELERY_RESULT_SERIALIZER', 'json')
CELERY_SEND_EVENTS = locals().get('CELERY_SEND_EVENTS', True)
CELERYBEAT_USER = locals().get('CELERYBEAT_USER', 'exchange')
CELERYBEAT_GROUP = locals().get('CELERYBEAT_GROUP', 'geoservice')
CELERYBEAT_SCHEDULER = locals().get('CELERYBEAT_SCHEDULER', 'djcelery.schedulers.DatabaseScheduler')

CELERYBEAT_SCHEDULE = locals().get('CELERYBEAT_SCHEDULE', {})
CELERYBEAT_SCHEDULE['Update_layers_30_secs'] = {
        'task': 'django_fulcrum.tasks.task_update_layers',
        'schedule': timedelta(seconds=30),
        'args': None
    }

CELERYBEAT_SCHEDULE['Pull_s3_data_120_secs'] = {
        'task': 'django_fulcrum.tasks.pull_s3_data',
        'schedule': timedelta(seconds=120),
        'args': None
    }

USE_TZ = locals().get('USE_TZ', True)
TIME_ZONE = locals().get('TIME_ZONE', 'UTC')
CELERY_ENABLE_UTC = locals().get('CELERY_ENABLE_UTC', True)
SSL_VERIFY = locals().get('SSL_VERIFY', False)
