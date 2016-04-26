#!/bin/bash

#run python test cases

sudo -u postgres psql -c "alter user geoshape with superuser;"

/var/lib/geonode/bin/python /var/lib/geonode/rogue_geonode/manage.py test django_fulcrum.tests.test_django_fulcrum django_fulcrum.tests.test_tasks django_fulcrum.tests.test_filters

sudo -u postgres psql -c "alter user geoshape with nosuperuser;"

