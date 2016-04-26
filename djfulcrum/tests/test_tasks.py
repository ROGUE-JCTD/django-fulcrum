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
from __future__ import absolute_import

from django.test import TestCase
from ..djfulcrum import *
from ..models import *
from ..s3_downloader import is_loaded


class TasksTests(TestCase):

    def setUp(self):
        pass

    def test_store_s3_state(self):
        """

        Returns: Passes if S3Sync model exists and is writable and
        prevents duplicates.
        """
        file_name = "Test"
        self.assertFalse(is_loaded(file_name))
        s3 = S3Sync.objects.create(s3_filename=file_name)
        self.assertIsNotNone(s3)
        self.assertTrue(is_loaded(file_name))
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                S3Sync.objects.create(s3_filename=file_name)


