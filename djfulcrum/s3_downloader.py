# Copyright 2016, RadiantBlue Technologies, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Note to download data from S3 a lock must exist on that process downloading the file or multiple process may destroy
# the workflow. This can be done using just one process of course, or a process safe cache such as memcached.
# Note that django locmem (the default), is NOT multiprocess safe.
from __future__ import absolute_import

from .models import S3Sync, S3Bucket
import os
from django.conf import settings
from django.db import ProgrammingError
import boto3
import botocore
from .djfulcrum import process_fulcrum_data
import glob


def is_loaded(file_name):
    s3_file = S3Sync.objects.filter(s3_filename=file_name)
    if s3_file:
        return True
    return False


def s3_download(s3_bucket_object, s3_file):
    if os.path.exists(os.path.join(settings.FULCRUM_UPLOAD, s3_file.key)):
        if s3_file.size == int(os.path.getsize(os.path.join(settings.FULCRUM_UPLOAD, s3_file.key))):
            return True
    s3_bucket_object.download_file(s3_file.key, os.path.join(settings.FULCRUM_UPLOAD, s3_file.key))
    return True


def pull_all_s3_data():
    # http://docs.celeryproject.org/en/latest/tutorials/task-cookbook.html#ensuring-a-task-is-only-executed-one-at-a-time
    # https://www.mail-archive.com/s3tools-general@lists.sourceforge.net/msg00174.html
    from .tasks import get_lock_id, acquire_lock, release_lock

    try:
        s3_credentials = settings.S3_CREDENTIALS
    except AttributeError:
        s3_credentials = []

    lock_id = get_lock_id("djfulcrum.tasks.pull_s3_data")
    lock_expire = 60 * 2160  # LOCK_EXPIRE IS IN SECONDS (i.e. 60*2160 is 1.5 days)

    if acquire_lock(lock_id, lock_expire):
        try:
            if type(s3_credentials) != list:
                s3_credentials = [s3_credentials]

            try:
                for s3_bucket in S3Bucket.objects.all():
                    cred = dict()
                    cred['s3_bucket'] = s3_bucket.s3_bucket
                    cred['s3_key'] = s3_bucket.s3_credential.s3_key
                    cred['s3_secret'] = s3_bucket.s3_credential.s3_secret
                    cred['s3_gpg'] = s3_bucket.s3_credential.s3_gpg
                    s3_credentials += [cred]
            except ProgrammingError:
                pass

            if s3_credentials:
                for s3_credential in s3_credentials:

                    session = boto3.session.Session()
                    s3 = session.resource('s3',
                                          aws_access_key_id=s3_credential.get('s3_key'),
                                          aws_secret_access_key=s3_credential.get('s3_secret'))

                    buckets = s3_credential.get('s3_bucket')
                    if type(buckets) != list:
                        buckets = [buckets]
                    for bucket in buckets:
                        if not bucket:
                            continue
                        try:
                            print("Getting files from {}".format(bucket))
                            s3_bucket_obj = s3.Bucket(bucket)
                            for s3_file in s3_bucket_obj.objects.all():
                                print str(s3_file.key) + " " + str(s3_file.size)
                                handle_file(s3_bucket_obj, s3_file)
                        except botocore.exceptions.ClientError:
                            print("There is an issue with the bucket and/or credentials,")
                            print("for bucket: {} and access_key {}".format(s3_credential.get('s3_bucket'),
                                                                            s3_credential.get('s3_key')))
                            continue
            else:
                print("There are no S3 Credentials defined in the settings or admin console.")
        except Exception as e:
            # This exception catches everything, which is bad for debugging, but if it isn't here
            # the lock is not released which makes it challenging to restore the proper state.
            print(repr(e))
        finally:
            release_lock(lock_id)


def clean_up_partials(file_name):
    dirs = glob.glob('{}.*'.format(file_name))
    if not dirs:
        return
    for directory in dirs:
        os.remove(directory)


def handle_file(s3_bucket_obj, s3_file):
    if is_loaded(s3_file.key):
        return

    s3_download(s3_bucket_obj, s3_file)

    clean_up_partials(s3_file.key)
    print("Processing: {}".format(s3_file.key))
    process_fulcrum_data(s3_file.key)
    S3Sync.objects.create(s3_filename=s3_file.key)
