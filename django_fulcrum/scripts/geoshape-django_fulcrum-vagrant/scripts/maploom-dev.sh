#!/usr/bin/env bash

# exit if anything returns failure
set -e

## TODO: move this script to geoshape-config maploom-dev

echo '
   This script will modify geonode in the guest machine to point to the a build of maploom
   on the host machine to speedup the edit-build-test cycle of maploom. Make sure the
   /Maploom folder is sym-linked to the clone of the MapLoom git repository on the host machine.'

while true; do
    read -p "=> Are you sure you want to continue? " yn
    case $yn in
        [Yy]* ) break;;
        [Nn]* ) echo "    Aborted script.";exit;;
        * ) echo "    Please answer yes or no.";;
    esac
done

[ ! -d /MapLoom ] && echo 'Directory /Maploom not found. have you linked it to Maploom repo on host?'
[ ! -f /MapLoom/build/maploom.html ] && echo '/MapLoom/build/maploom.html not found. have you built maploom? e.g. \"grunt watch\" '

rm -rf /var/lib/geonode/lib/python2.7/site-packages/maploom/static/maploom/*
ln -s /MapLoom/build/* /var/lib/geonode/lib/python2.7/site-packages/maploom/static/maploom/
rm /var/lib/geonode/lib/python2.7/site-packages/maploom/templates/maps/maploom.html
ln -s /MapLoom/build/maploom.html /var/lib/geonode/lib/python2.7/site-packages/maploom/templates/maps/maploom.html

echo 'Done.'

