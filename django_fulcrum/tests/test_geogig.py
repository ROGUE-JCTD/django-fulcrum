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
from ..geogig import get_all_geogig_repos, create_geogig_datastore, create_geogig_repo, get_geogig_repo_name, \
    set_geoserver_permissions


class DjangoFulcrumTests(TestCase):
    def setUp(self):
        pass

    def test_create_geogig_repo(self):
        new_repo = 'fulcrum_geogig'
        # repo_dir = create_geogig_repo(new_repo)
        # if repo_dir:
        #     set_geoserver_permissions(repo_dir)
        # repo = get_geogig_repo_name(new_repo)
        # self.assertEqual(new_repo, repo)
        repos = get_all_geogig_repos()
        create_geogig_datastore(new_repo)
        for repo in repos:
            print repo
