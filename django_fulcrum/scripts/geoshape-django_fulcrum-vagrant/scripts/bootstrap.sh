#!/usr/bin/env bash

# exit if anything returns failure
set -e
cd /etc/yum.repos.d/
wget  https://yum.boundlessps.com/geoshape.repo
yum -y install geoshape geoshape-geoserver elasticsearch postgis-postgresql95

mkfs.ext4 -F /dev/sdb
echo "/dev/sdb                /var/lib/geoserver_data/file-service-store ext4 defaults 1 2" >> /etc/fstab
mount -a
chown tomcat:geoservice /var/lib/geoserver_data/file-service-store
chmod 775 /var/lib/geoserver_data/file-service-store
