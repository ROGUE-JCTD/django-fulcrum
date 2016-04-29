# django-fulcrum

This is a django application which allows the user to connect to a Fulcrumapp.com and ingest data, including all media files.

## Requirements

GDAL
GEOS
Python 2.7 with the following packages.
 - celery
 - django-celery
 - fulcrum
 - python-memcached
 - boto3
 - Pillow<=2.9.0
 - django
 - gsconfig
 - requests
 - shapely
 - gdal

The install script for geoshape using the geoshape-vagrant VM will be handled automatically.
Note that GEOS and GDAL are needed with their python bindings, additionally shapely needs to have a compatibly version of GEOS.
Therefore if your platform has a package already created called something similar to, "python-shapely" or "python-gdal" this will probably be
the easiest route to success.

## Setup 

There are two different types of installation instructions.  A set of instructions for using the geoshape-vagrant vm (recommended) or integrating the app into your own project.

### geoshape-vagrant setup

In an elevated session (sudo or "run as administrator),
change directories to the geoshape-vagrant repo, and install the vagrant hosts updater
```
vagrant plugin install vagrant-hostsupdater
```

Copy the vagrant files from django_fulcrum/scripts/geoshape-django_fulcrum-vagrant into a folder.  Also ensure that your geoshape vagrant folder exists on a large disk since by default the scripts will create a disk with a 500 GB capacity (thin provisioned).

Bring up the geoshape vm.
```
vagrant up
```

SSH into the VM and run the following commands
```
cd /tmp
wget https://raw.githubusercontent.com/ROGUE-JCTD/django-fulcrum/master/django_fulcrum/scripts/geoshape_fulcrum_install.sh -O- | tr -d '\r' > /tmp/geoshape_fulcrum_install.sh
sudo bash /tmp/geoshape_fulcrum_install.sh
```

You can modify your fulcrum api key entry in /var/lib/geonode/rogue_geonode/geoshape/local_settings.py file (sudo required).
Additionally in local_settings an S3_CREDENTIALS dict can be added and the app will pull data from an s3 bucket. For examples of these entries, refer to the settings documentation further down the page.
Alternatively you may enter this information in the admin console.  It is more secure in the local_settings file, but the server would need to be restarted, after information is added or removed.

To allow for geoshape tile truncation on addition of new data, make sure there is a default OGC_SERVER value in the  /var/lib/geonode/rogue_genode/geoshape/local_settings.py file.
The setting keys required for tile truncation are USER and PASSWORD. These should correspond to the username/password of your GeoServer. For an example, refer to the settings documentation further down the page.

Add any desired filters to the /var/lib/geonode/lib/Python27/site-packages/django_fulcrum/filters file. (US geospatial and phone number filters are added by default.)
(By default these filters will be turned on, but they can be turned off in the admin console. Please be aware that the filter status changes will not be reflected in already processed data.)
(Any additional filters added must have a primary function `def filter(input)`, where input is a geojson feature collection. The filter function must return `{'passed': passed_features, 'failed': failed_features}`, where passed and failed features are geojson feature collections.)

If you have specific basemaps you would like to use, add them to the `LEAFLET_CONFIG['TILES']` array in /var/lib/geonode/rogue_geonode/geoshape/setting.py. 
Each value in the array should be a tuple where the first element is the basemap name, the second element is the basemap URL, and the third element is the atrribution. All three elements are required. 

Finally run the command:
```
sudo geoshape-config init "geoshape.dev"
```

### custom project

First ensure you install the package:
```
python setup.py install
```

If using an existing Django Project you will need to integrate the urls and the various settings. The default settings should get you minimal functionality.  It is also assumed that you are using celery (which is recommended). If you aren't using celery it can be disabled.

If you don't have a django repo yet a script is provided with default settings that will help get you up and running.

After you installed all of the dependencies. Enter the python interpreter and enter (replacing <> with your own variable):
```
from django_fulcrum.scripts.project import create_mvp
create_mvp(name=<project_name>, dir_path=<project_path>)
quit()
```

Then change directory to <project_path>/<project_name>.
Ensure you edit the <project_name>/settings.py file to the correct settings, and then run:
```
python manage.py makemigrations
python manage.py migrate
python manage.py superuser
<enter user information>
python manage.py runserver
```

## Settings

###-The following settings can be defined in the local_setting.py file for your project

#### DATABASES: (Required)
A database in which the geospatial data can be stored. 
Example: 
```
    DATABASES = {
        'fulcrum': {
            'ENGINE': 'django.contrib.gis.db.backends.postgis',
            'NAME': *database name*,
            'USER': *database user*,
            'PASSWORD': *database password*,
            'HOST': *database host*,
            'PORT': *database port*,
        }
    }
 ```

#### OGC_SERVER: (Optional)
Server to host layers in the database.
Example:
```
    OGC_SERVER = {
        'default': {
            'BACKEND': 'backend.geoserver',
            'LOCATION': GEOSERVER_URL,
            'PUBLIC_LOCATION': GEOSERVER_URL,
            'USER': 'admin',
            'PASSWORD': 'xxxxxxx',
            'DATASTORE': 'geoshape_imports',
        }
    }
```

#### FULCRUM_API_KEYS: (Optional)
The API key which allows the application access to the data in your Fulcrum account.
Example: `FULCRUM_API_KEY= ['xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx']`
            
#### FULCRUM_UPLOAD: (Optional)
A file path where user uploaded files or S3 files will be stored while processing.
Example: `FULCRUM_UPLOAD = '/var/lib/geonode/fulcrum_data'`

#### S3_CREDENTIALS: (Optional)
Configuration to pull data from an S3 bucket.
Example: 
```
    S3_CREDENTIALS = [{
        's3_bucket': ['my_s3_bucket'],
        's3_key': 'XXXXXXXXXXXXXXXXXXXX',
        's3_secret': 'XxXxXxXxXxXxXxXxXxXxXxX',
        's3_gpg': XxXxXxXxXxXxX'
    }]
```

#### --- NOTE: For this app to be functional, you should add at least one of the options: FULCRUM_API_KEYS, FULCRUM_UPLOAD, or S3_CREDENTIALs ---

###-The following settings can be defined in the local_setting.py file for your project

#### INSTALLED_APPS: (Required)
The name of this app must be added to the installed_app variable so it can run as part of the host django project.
Example: `INSTALLED_APPS += ('django_fulcrum',)`

#### CACHES: (Required)
Define the cache to be used. Memcache is suggested, but other process safe caches can be used too.
Example: 
```
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
            'LOCATION': '127.0.0.1:11211',
        }
    }
```

#### CELERY: (Optional)
If you plan to use celery as a task runner there are several celery variables to define.
Examples:
```
CELERY_ACCEPT_CONTENT=['json']
CELERY_TASK_SERIALIZER='json'
CELERY_RESULT_SERIALIZER='json'
CELERY_SEND_EVENTS=True
CELERYBEAT_USER='geoshape'
CELERYBEAT_GROUP='geoservice'
CELERYBEAT_SCHEDULER='djcelery.schedulers.DatabaseScheduler'
CELERYBEAT_SCHEDULE = {
    'Update_layers_30_secs': {
        'task': 'django_fulcrum.tasks.task_update_layers',
        'schedule': timedelta(seconds=30),
        'args': None
    },
    'Pull_s3_data_120_secs': {
        'task': 'django_fulcrum.tasks.pull_s3_data',
        'schedule': timedelta(seconds=120),
        'args': None
    },
}
```

#### LEAFLET_CONFIG: (Optional)
Defines the basemaps to be used in the fulcrum viewer map. If you plan to use the fulcrum viewer, you will need to define your selected basemaps here.
Example: 
```
    LEAFLET_CONFIG = {
        'TILES': [
            ('BasemapName',
             'url-to-basemap-server-here',
             'Attribution for the basemap'),
        ]
    }
```

## Usage
Once up and running you need to configure filters and import data from FulrumApp.

To configure the filters, navigate to the django admin console and navigate to django_fulcrum - filters.
Then click on each filter and either make it not active or change the settings.  By default for testing, there are filters active which excludes data in the US.  Optionally, you can switch to show ONLY data in the US, or deactivate the filter.
Filters are available to reduce the amount of undesired redundant data on your remote system.  This is to allow only subsets to exist on the current system. Note that the filters are destructive. If you filter points, the system marks the time that they were "filtered" and won't evaluate them again, so old data won't show up if it was "filtered" previously.  Likewise if you run a new filter on old points, "filtered" points (or media) will be deleted.

To import data you can (all of which will be run through existing filters):
 - upload a geojson zip archive from Fulcrum through the fulcrum_viewer.
 - Enter S3 Credentials to automatically download zip archives from an S3 bucket(s).
 - Enter FulcrumApp API key to download the data directly from Fulcrum.  (Recommended)
 Note that zip files are extracted and imported.  Extracted files are deleted but zip files are left in the FULCRUM_UPLOAD folder.
 The advantage of using the API key is that all of your data will be downloaded and updated automatically. Furthermore it includes videos and audio files that historically have not been included in Fulcrum exports.

## Known Issues
- Tiles are completely dumped when a layer is updated.  This is because the GWC bounding box tools was unsuccessful during various attempts even using their built in web tool.  This solution while inefficient is probably ok for static datasets and rarely updated data, as opposed to just not caching tiles at all.

## Bugs

Todo

LICENSE

The code for this project is provided under the Apache 2 license. Any contributions to this repository constitutes agreement with your contribtions being provided under this license. 
