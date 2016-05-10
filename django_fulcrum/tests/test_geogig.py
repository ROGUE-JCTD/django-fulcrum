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
from ..django_fulcrum import update_geoshape_layers
from ..geogig import get_all_geogig_repos, create_geogig_datastore, create_geogig_repo, get_geogig_repo_name, \
    set_geoserver_permissions, import_from_pg, post_wfs_transaction


class DjangoFulcrumGeogigTests(TestCase):

    def test_create_geogig_repo(self):
        new_repo = 'fulcrum_geogig'
        repo_dir, created = create_geogig_repo(new_repo)
        if created:
            set_geoserver_permissions(repo_dir)
        #repos = get_all_geogig_repos()
        import_from_pg(new_repo, "fulcrum_test3")
        create_geogig_datastore(new_repo, "fulcrum_test3")
        update_geoshape_layers()
        #for repo in repos:
        #    print repo

    # def test_get_geometry_point_element(self):
    #     test_feature = {
    #         "type": "Feature",
    #         "geometry": {
    #             "type": "Point",
    #             "coordinates": [125.6, 10.1]
    #         },
    #         "properties": {
    #             "name": "Dinagat Islands",
    #             "version": 1,
    #             "fulcrum_id": "123",
    #             "meta": "OK"
    #         }
    #     }
    #
    #     wfst = get_wfs_transaction(test_feature, 'fulcrum_test2')
    #     print(wfst)
    #     print(post_wfs_transaction(wfst))