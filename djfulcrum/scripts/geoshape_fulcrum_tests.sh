#!/bin/bash

#run python test cases

sudo -u postgres psql -c "alter user geoshape with superuser;"

/var/lib/geonode/bin/python /var/lib/geonode/rogue_geonode/manage.py test djfulcrum.tests.test_djfulcrum djfulcrum.tests.test_tasks djfulcrum.tests.test_filters

sudo -u postgres psql -c "alter user geoshape with nosuperuser;"

