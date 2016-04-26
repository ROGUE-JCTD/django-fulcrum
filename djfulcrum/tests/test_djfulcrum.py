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

from django.test import TestCase, TransactionTestCase
from ..djfulcrum import *
import inspect
from ..models import *
import copy
from django.db import IntegrityError, transaction, connections


class DjangoFulcrumTests(TestCase):
    @classmethod
    def setUpClass(self):
        try:
            cur = connection.cursor()
            cur.execute('CREATE EXTENSION postgis;')
        except ProgrammingError:
            pass
        finally:
            cur.close()

    def test_find_media_keys_from_urls(self):
        """

        Returns:Given a geojson containing a Fulcrum API media url,
        a json should be returned with those keys and types.
        This assumes that 'photos', 'videos', or 'audio' is in the media url. If not it assumes photo.
        The test proves that even if the key is arbitrary the url will prove valid.

        """

        geojson1 = {'type': 'feature',
                    'properties': {'pics_url': '',
                                   'vids_url': 'https://api.fulcrumapp.com/api/v2/videos',
                                   'sounds_url': ''}}
        expected_keymap1 = {'pics': 'photos', 'vids': 'videos', 'sounds': 'photos'}
        geojson2 = {'type': 'feature',
                    'properties': {'pics_url': 'https://api.fulcrumapp.com/api/v2/photos',
                                   'vids_url': 'https://api.fulcrumapp.com/api/v2/videos',
                                   'sounds_url': 'https://api.fulcrumapp.com/api/v2/audio'}}
        expected_keymap2 = {'pics': 'photos', 'vids': 'videos', 'sounds': 'audio'}

        self.assertEqual(find_media_keys([geojson1]), expected_keymap1)
        self.assertEqual(find_media_keys([geojson2]), expected_keymap2)

    def test_update_layer_media_keys(self):
        example_layer = Layer.objects.create(layer_name="example", layer_uid="unique")
        geojson1 = {'type': 'feature',
                    'properties': {'pics_url': '',
                                   'vids_url': 'https://api.fulcrumapp.com/api/v2/videos',
                                   'sounds_url': ''}}
        expected_keymap1 = {'pics': 'photos', 'vids': 'videos', 'sounds': 'photos'}
        geojson2 = {'type': 'feature',
                    'properties': {'pics_url': 'https://api.fulcrumapp.com/api/v2/photos',
                                   'vids_url': 'https://api.fulcrumapp.com/api/v2/videos',
                                   'sounds_url': 'https://api.fulcrumapp.com/api/v2/audio'}}
        expected_keymap2 = {'pics': 'photos', 'vids': 'videos', 'sounds': 'audio'}

        get_update_layer_media_keys(media_keys=find_media_keys([geojson1]),
                                    layer=example_layer)
        self.assertNotEqual(example_layer.layer_media_keys, "{}")
        self.assertEqual(example_layer.layer_media_keys, json.dumps(expected_keymap1))
        get_update_layer_media_keys(media_keys=find_media_keys([geojson2]),
                                    layer=example_layer)
        self.assertEqual(example_layer.layer_media_keys, json.dumps(expected_keymap2))

    def test_feature_model_for_duplicates(self):
        """Ensures that constraints work as intended for feature model."""
        example_layer = Layer.objects.create(layer_name="example", layer_uid="unique")
        first_feature = {
            "type": "Feature",
            "properties": {
                "fulcrum_id": "5daf7ab7-e257-48d1-b1e6-0bb049b49d98",
                "version": 1,
            }}
        second_feature = copy.deepcopy(first_feature)
        second_feature['properties']['version'] = 2
        feature1 = Feature.objects.create(layer=example_layer,
                                          feature_uid=first_feature.get('properties').get('fulcrum_id'),
                                          feature_version=first_feature.get('properties').get('version'),
                                          feature_data=json.dumps(first_feature))
        self.assertIsNotNone(feature1)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Feature.objects.create(layer=example_layer,
                                       feature_uid=first_feature.get('properties').get('fulcrum_id'),
                                       feature_version=first_feature.get('properties').get('version'),
                                       feature_data=json.dumps(first_feature))
        feature2 = Feature.objects.create(layer=example_layer,
                                          feature_uid=second_feature.get('properties').get('fulcrum_id'),
                                          feature_version=second_feature.get('properties').get('version'),
                                          feature_data=json.dumps(second_feature))
        self.assertIsNotNone(feature2)

    def test_sort_features(self):
        """Ensures that features are properly sorted (in ascending order)."""
        unsorted_features = [{'properties': {'id': 'cdec0e00-f511-44bf-a94e-165f930ce7d4', 'version': 2}},
                             {'properties': {'id': 'cdec0e00-f511-44bf-a94e-165f930ce7d5', 'version': 2}},
                             {'properties': {'id': 'cdec0e00-f511-44bf-a94e-165f930ce7d4', 'version': 1}},
                             {'properties': {'id': 'cdec0e00-f511-44bf-a94e-165f930ce7d5', 'version': 1}}]
        expected_sorted_by_version_features = [
            {'properties': {'id': 'cdec0e00-f511-44bf-a94e-165f930ce7d4', 'version': 1}},
            {'properties': {'id': 'cdec0e00-f511-44bf-a94e-165f930ce7d5', 'version': 1}},
            {'properties': {'id': 'cdec0e00-f511-44bf-a94e-165f930ce7d4', 'version': 2}},
            {'properties': {'id': 'cdec0e00-f511-44bf-a94e-165f930ce7d5', 'version': 2}}]
        expected_sorted_by_id_features = [{'properties': {'id': 'cdec0e00-f511-44bf-a94e-165f930ce7d4', 'version': 2}},
                                          {'properties': {'id': 'cdec0e00-f511-44bf-a94e-165f930ce7d4', 'version': 1}},
                                          {'properties': {'id': 'cdec0e00-f511-44bf-a94e-165f930ce7d5', 'version': 2}},
                                          {'properties': {'id': 'cdec0e00-f511-44bf-a94e-165f930ce7d5', 'version': 1}}]
        expected_sorted_by_version_then_id = [
            {'properties': {'id': 'cdec0e00-f511-44bf-a94e-165f930ce7d4', 'version': 1}},
            {'properties': {'id': 'cdec0e00-f511-44bf-a94e-165f930ce7d4', 'version': 2}},
            {'properties': {'id': 'cdec0e00-f511-44bf-a94e-165f930ce7d5', 'version': 1}},
            {'properties': {'id': 'cdec0e00-f511-44bf-a94e-165f930ce7d5', 'version': 2}}]

        sorted_by_version_features = sort_features(unsorted_features, properties_key='version')
        self.assertEqual(sorted_by_version_features, expected_sorted_by_version_features)

        sorted_by_id_features = sort_features(unsorted_features, properties_key='id')
        self.assertEqual(expected_sorted_by_id_features, sorted_by_id_features)

        sorted_by_version_then_id = sort_features(sort_features(unsorted_features, properties_key='version')
                                                  , properties_key='id')
        self.assertEqual(sorted_by_version_then_id, expected_sorted_by_version_then_id)

    def test_get_duplicate_features(self):
        """Ensures that feature duplicates can be found and that they are all accounted for."""
        unsorted_features = [{'properties': {'id': 'cdec0e00-f511-44bf-a94e-165f930ce7d4', 'version': 2}},
                             {'properties': {'id': 'cdec0e00-f511-44bf-a94e-165f930ce7d5', 'version': 2}},
                             {'properties': {'id': 'cdec0e00-f511-44bf-a94e-165f930ce7d4', 'version': 1}},
                             {'properties': {'id': 'cdec0e00-f511-44bf-a94e-165f930ce7d5', 'version': 1}},
                             {'properties': {'id': 'cdec0e00-f511-44bf-a94e-165f931ee7d5', 'version': 2}}]

        expected_unique_features = [{'properties': {'id': 'cdec0e00-f511-44bf-a94e-165f930ce7d4', 'version': 1}},
                                    {'properties': {'id': 'cdec0e00-f511-44bf-a94e-165f930ce7d5', 'version': 1}},
                                    {'properties': {'id': 'cdec0e00-f511-44bf-a94e-165f931ee7d5', 'version': 2}}]

        expected_non_unique_features = [{'properties': {'id': 'cdec0e00-f511-44bf-a94e-165f930ce7d4', 'version': 2}},
                                        {'properties': {'id': 'cdec0e00-f511-44bf-a94e-165f930ce7d5', 'version': 2}}]

        unique_features, non_unique_features = get_duplicate_features(features=unsorted_features, properties_id='id')

        self.assertEqual(expected_unique_features, unique_features)
        self.assertEqual(expected_non_unique_features, non_unique_features)

    def test_features_to_file(self):
        """Ensures that features are written into a file and that the file is in a format which can be read back."""
        test_dir = os.path.dirname(os.path.abspath(__file__))
        test_name = 'test_geojson.json'
        test_path = os.path.join(test_dir, test_name)
        test_features = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [125.6, 10.1]
            },
            "properties": {
                "name": "Dinagat Islands"
            }
        }
        expected_result = {"type": "FeatureCollection", "features": [test_features]}
        try:
            self.assertFalse(os.path.isfile(test_path))
        except AssertionError:
            os.remove(test_path)

        features_to_file(test_features, file_path=test_path)

        self.assertTrue(os.path.isfile(test_path))

        with open(test_path, 'r') as test_file:
            imported_geojson = json.load(test_file)

        os.remove(test_path)
        self.assertEqual(expected_result, imported_geojson)
        self.assertFalse(os.path.isfile(test_path))

    def test_convert_to_epoch_time(self):
        """Maintains the integrity of the time conversion function."""
        date = "2016-01-28 14:36:59 UTC"
        expected_time_stamp = 1453991819
        returned_time = convert_to_epoch_time(date)
        self.assertEqual(expected_time_stamp, returned_time)

    def test_append_time_to_features(self):
        """Ensures that the proper values are appended. Time correctness is assumed."""
        test_feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [125.6, 10.1]
            },
            "properties": {
                "name": "Dinagat Islands",
                "version": 1,
                "fulcrum_id": "123",
                "updated_at": "2016-01-28 14:36:59 UTC",
            }
        }
        expected_feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [125.6, 10.1]
            },
            "properties": {
                "name": "Dinagat Islands",
                "version": 1,
                "fulcrum_id": "123",
                "updated_at": "2016-01-28 14:36:59 UTC",
                "updated_at_time": 1453991819
            }
        }

        results = append_time_to_features(test_feature, properties_key_of_date="updated_at")
        self.assertEqual(expected_feature, results[0])

    def test_get_element_map(self):
        """Ensures that the element map is returned as expected, and provides implicit documentation."""
        fi = DjangoFulcrum(fulcrum_api_key='1234')
        form = {'elements': [{
            "type": "TextField",
            "key": "3320",
            "label": "Name",
            "data_name": "name",
        }, {
            "type": "PhotoField",
            "key": "a1b0",
            "label": "Photos",
            "data_name": "photos",
        }, {
            "type": "VideoField",
            "key": "5834",
            "label": "Videos",
            "data_name": "videos",
        }, {
            "type": "AudioField",
            "key": "2f32",
            "label": "Audio",
            "data_name": "audio",
        }
        ]}
        result_element_map = fi.get_element_map(form)
        expected_element_map = {'3320': 'name',
                                'a1b0': 'photos',
                                '5834': 'videos',
                                '2f32': 'audio'}
        self.assertEqual(expected_element_map, result_element_map)

    def test_get_media_map(self):
        """Ensures that the media map is returned as expected, and provides implicit documentation."""
        fi = DjangoFulcrum(fulcrum_api_key='1234')
        form = {'elements': [{
            "type": "TextField",
            "key": "3320",
            "label": "Name",
            "data_name": "name",
        }, {
            "type": "PhotoField",
            "key": "a1b0",
            "label": "Photos",
            "data_name": "pics",
        }, {
            "type": "VideoField",
            "key": "5834",
            "label": "Videos",
            "data_name": "vids",
        }, {
            "type": "AudioField",
            "key": "2f32",
            "label": "Audio",
            "data_name": "sounds",
        }
        ]}
        element_map = {'3320': 'name',
                       'a1b0': 'pics',
                       '5834': 'vids',
                       '2f32': 'sounds'}
        expected_media_map = {'pics': 'photos',
                              'vids': 'videos',
                              'sounds': 'audio'}
        result_element_map = fi.get_media_map(form, element_map)
        self.assertEqual(expected_media_map, result_element_map)

        form2 = {'elements': [{
            "type": "TextField",
            "key": "3320",
            "label": "Name",
            "data_name": "name",
        }, {
            "type": "PhotoField",
            "key": "a1b0",
            "label": "Photos",
            "data_name": "photos",
        }, {
            "type": "VideoField",
            "key": "5834",
            "label": "Videos",
            "data_name": "videos",
        }, {
            "type": "AudioField",
            "key": "2f32",
            "label": "Audio",
            "data_name": "audio",
        }
        ]}
        element_map2 = {'3320': 'name',
                        'a1b0': 'photos',
                        '5834': 'videos',
                        '2f32': 'audio'}
        expected_media_map2 = {'photos': 'photos',
                               'videos': 'videos',
                               'audio': 'audio'}

        result_element_map2 = fi.get_media_map(form2, element_map2)
        self.assertEqual(expected_media_map2, result_element_map2)

    def test_convert_to_geojson(self):
        """Ensures that the record structure from fulcrum is converted properly to a geojson"""
        fi = DjangoFulcrum(fulcrum_api_key='1234')

        element_map = {'3320': 'name',
                       'a1b0': 'pics',
                       '5834': 'vids',
                       '2f32': 'sounds'}
        expected_media_map = {'pics': 'photos',
                              'vids': 'videos',
                              'sounds': 'audio'}

        records = [{
            "status": None,
            "version": 1,
            "id": "b5da0b90-d325-4299-b6cd-0d0baacc0c62",
            "created_at": "2016-01-21T15:18:28Z",
            "updated_at": "2016-01-21T15:18:28Z",
            "client_created_at": "2016-01-21T15:18:28Z",
            "client_updated_at": "2016-01-21T15:18:28Z",
            "created_by_id": "bbf56001-a5b0-40a6-9ae6-607771983c62",
            "updated_by_id": "bbf56001-a5b0-40a6-9ae6-607771983c62",
            "form_id": "d82f38c2-4ecd-400a-a4cc-7c2c93427d1e",
            "project_id": None,
            "assigned_to": None,
            "assigned_to_id": None,
            "form_values": {
                "3320": "Example",
                "a1b0": ["561bb279-d9f7-486a-a4b8-dd34d820b003.jpg"],
                "5834": [{"caption": None, "video_id": "bbae4aed-48ac-48f4-8f85-d9f3ada7a942"}],
                "2f32": ["5dcd8385-d46c-4856-a689-6ce3ec8da8ed.m4a"],
            },
            "latitude": 18.5177634347377,
            "longitude": -69.8680442584387,
            "altitude": None,
            "speed": None,
            "course": None,
            "horizontal_accuracy": None,
            "vertical_accuracy": None
        }]

        returned_geojson = fi.convert_to_geojson(records, element_map, expected_media_map)

        expected_geojson = {
            'type': 'FeatureCollection',
            'features': [{
                'geometry': {
                    'type': 'Point',
                    'coordinates': [-69.8680442584387, 18.5177634347377]
                },
                'type': 'Feature',
                'properties': {
                    'form_id': 'd82f38c2-4ecd-400a-a4cc-7c2c93427d1e',
                    'latitude': 18.5177634347377,
                    'created_at': '2016-01-21T15:18:28Z',
                    'updated_at': '2016-01-21T15:18:28Z',
                    'pics': ['561bb279-d9f7-486a-a4b8-dd34d820b003.jpg'],
                    'client_created_at': '2016-01-21T15:18:28Z',
                    'version': 1,
                    'updated_by_id': 'bbf56001-a5b0-40a6-9ae6-607771983c62',
                    'longitude': -69.8680442584387,
                    'client_updated_at': '2016-01-21T15:18:28Z',
                    'vids': ['bbae4aed-48ac-48f4-8f85-d9f3ada7a942'],
                    'created_by_id': 'bbf56001-a5b0-40a6-9ae6-607771983c62',
                    'sounds': ['5dcd8385-d46c-4856-a689-6ce3ec8da8ed.m4a'],
                    'id': 'b5da0b90-d325-4299-b6cd-0d0baacc0c62',
                    'name': 'Example'
                }
            }]
        }

        self.assertEqual(expected_geojson, returned_geojson)

    def test_prepare_features_for_geoshape(self):
        """Ensures that the geojson structure from fulcrum is converted properly to a format suitable for maploom."""
        test_feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [125.6, 10.1]
            },
            "properties": {
                "name": "Dinagat Islands",
                "version": 1,
                "fulcrum_id": "123",
                "image": "test",
                "image_url": "image.jpg",
                "movie": "test",
                "movie_url": "movie.mp4",
                "sound": "test",
                "sound_url": "sound.m4a"
            }
        }

        media_keys = {'image': 'photos', 'movie': 'videos', 'sound': 'audio'}

        # Note that the expected feature contains json objects as strings, as opposed to an array of strings.
        expected_feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [125.6, 10.1]
            },
            "properties": {
                "name": "Dinagat Islands",
                "version": 1,
                "fulcrum_id": "123",
                "photos_image": '["test.jpg"]',
                "videos_movie": '["test.mp4"]',
                "audios_sound": '["test.m4a"]',
                "image": "test",
                "movie": "test",
                "sound": "test",
            }
        }

        returned_features = prepare_features_for_geoshape(test_feature, media_keys=media_keys)
        self.assertEqual(expected_feature, returned_features[0])

    def test_is_valid_photo(self):
        import os
        from PIL import Image

        script_path = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_path, 'good_photo.jpg')
        good_photo = Image.open(file_path)
        info = good_photo._getexif()
        properties = get_gps_info(info)
        self.assertNotIn("GPSInfo", properties)

        file2 = os.path.join(script_path, 'bad_photo.jpg')
        bad_photo = Image.open(file2)
        info2 = bad_photo._getexif()
        properties2 = get_gps_info(info2)
        self.assertIn("GPSInfo", properties2)

        coords = get_gps_coords(properties)
        self.assertIsNone(coords)

        coords2 = get_gps_coords(properties2)
        self.assertEqual([38.889775, -77.456342], coords2)

    # def test_create_geogig_repo(self):
    #     new_repo = 'test_repo'
    #     repos = get_all_geogig_repos()
    #     for repo in repos:
    #         print repo
    #         # create_geogig_repo(new_repo)
    #         # repo = get_geogig_repo(new_repo)
    #         # self.assertEqual(new_repo,repo)


class DjFulcrumDBTests(TransactionTestCase):
    """Test cases for model functions to prevent locking issues due to transactions."""
    @classmethod
    def setUpClass(self):
        try:
            cur = connection.cursor()
            cur.execute('CREATE EXTENSION postgis;')
        except ProgrammingError:
            pass
        finally:
            cur.close()

    def test_table_exist(self):
        """Ensure table is properly created and that the function properly checks for it."""
        table_name = "test_table_exist"
        self.assertFalse(table_exists(table=table_name))

        cur = connection.cursor()
        query = "CREATE TABLE {}(id integer);".format(table_name)

        with transaction.atomic():
            cur.execute(query)
        cur.close()

        self.assertTrue(table_exists(table=table_name))

    def test_upload_to_db(self):
        """Ensures data is properly updated to a presumed remote database or separate table."""
        table_name = "test_upload_to_db"

        test_feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [125.6, 10.1]
            },
            "properties": {
                "name": "Dinagat Islands",
                "version": 1,
                "fulcrum_id": "123",
                "meta": "OK"
            }
        }

        media_keys = None

        upload_to_db(test_feature, table_name, media_keys)

        with transaction.atomic():
            cur = connection.cursor()
            cur.execute("SELECT * FROM {} WHERE fulcrum_id = '123' LIMIT 1;".format(table_name))
            imported_feature = dictfetchall(cur)[0]
            cur.close()

        expected_version = 1

        self.assertEqual("Dinagat Islands", imported_feature.get('name'))
        self.assertEqual(expected_version, imported_feature.get('version'))
        self.assertEqual("OK", imported_feature.get('meta'))

        test_feature2 = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [125.6, 10.1]
            },
            "properties": {
                "name": "Dinagat Islands",
                "version": 2,
                "fulcrum_id": "123",
                "meta": "GOOD"
            }
        }

        upload_to_db(test_feature2, table_name, media_keys)

        with transaction.atomic():
            cur = connection.cursor()
            cur.execute("SELECT * FROM {} WHERE fulcrum_id = '123' LIMIT 1;".format(table_name))
            imported_feature = dictfetchall(cur)[0]
            cur.close()

        expected_version = 2

        self.assertEqual("Dinagat Islands", imported_feature.get('name'))
        self.assertEqual(expected_version, imported_feature.get('version'))
        self.assertEqual("GOOD", imported_feature.get('meta'))

        test_feature3 = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [125.6, 10.1]
            },
            "properties": {
                "name": "Dinagat Islands",
                "version": 1,
                "fulcrum_id": "123",
                "meta": "BAD"
            }
        }

        upload_to_db(test_feature3, table_name, media_keys)

        with transaction.atomic():
            cur = connection.cursor()
            cur.execute("SELECT * FROM {} WHERE fulcrum_id = '123' LIMIT 1;".format(table_name))
            imported_feature = dictfetchall(cur)[0]
            cur.close()

        # There should be no change because the server should reject an older version.
        expected_version = 2

        self.assertEqual("Dinagat Islands", imported_feature.get('name'))
        self.assertEqual(expected_version, imported_feature.get('version'))
        self.assertEqual("GOOD", imported_feature.get('meta'))

    def test_ogr2ogr_geojson_to_db(self):
        """Ensure ogr2ogr and any associated functions are maintained."""
        table_name = 'test_ogr2ogr_geojson_to_db'
        test_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
        test_name = 'test_geojson.json'
        test_path = os.path.join(test_dir, test_name)
        test_features = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [125.6, 10.1]
            },
            "properties": {
                "name": "Dinagat Islands",
                "fulcrum_id": "123"
            }
        }

        self.assertFalse(table_exists(table=table_name))

        geojson_file = features_to_file(test_features, file_path=test_path)
        self.assertTrue(os.path.isfile(geojson_file))

        ogr2ogr_geojson_to_db(geojson_file=geojson_file,
                              table=table_name)

        self.assertTrue(table_exists(table=table_name))

        cur = connection.cursor()
        cur.execute("SELECT name FROM {} WHERE fulcrum_id = '123' LIMIT 1;".format(table_name))

        imported_name = dictfetchall(cur)[0].get('name')
        cur.close()
        self.assertEqual("Dinagat Islands", imported_name)
        os.remove(geojson_file)

    def test_add_unique_constraint(self):
        """Ensures logic behind adding unique constraint is consistent."""

        table_name = 'test_unique'

        with transaction.atomic():
            cur = connection.cursor()
            cur.execute("CREATE TABLE {}(id integer);".format(table_name))
            cur.close()

        self.assertTrue(table_exists(table=table_name))

        with transaction.atomic():
            cur = connection.cursor()
            cur.execute("INSERT INTO {} values(1);".format(table_name))
            cur.close()

        add_unique_constraint(database_alias=None, table=table_name, key_name='id')

        with transaction.atomic():
            try:
                cur = connection.cursor()
                cur.execute("INSERT INTO {} values(1);".format(table_name))

                added_duplicate_value = True
            except ProgrammingError:
                added_duplicate_value = False
            except OperationalError:
                added_duplicate_value = False
            except IntegrityError:
                added_duplicate_value = False
            finally:
                cur.close()
                connection.close()

        self.assertFalse(added_duplicate_value)

    def test_update_db_feature(self):
        """Ensures logic behind updating a feature is consistent."""
        table_name = 'test_update_db_feature'
        test_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
        test_name = 'test_geojson.json'
        test_path = os.path.join(test_dir, test_name)

        test_feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [125.6, 10.1]
            },
            "properties": {
                "name": "Dinagat Islands",
                "version": 1,
                "fulcrum_id": "123"
            }
        }

        test_feature_2 = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [125.6, 10.1]
            },
            "properties": {
                "name": "Dinagat Islands",
                "version": 2,
                "fulcrum_id": "123"
            }
        }
        self.assertFalse(table_exists(table=table_name))

        geojson_file = features_to_file(test_feature, file_path=test_path)
        self.assertTrue(os.path.isfile(geojson_file))

        ogr2ogr_geojson_to_db(geojson_file=geojson_file,
                              table=table_name)

        cur = connection.cursor()
        cur.execute("SELECT * FROM {} WHERE fulcrum_id = '123' LIMIT 1;".format(table_name))

        results = dictfetchall(cur)
        cur.close()
        if results:
            imported_feature = results[0]
        else:
            imported_feature = {}

        expected_version = 1

        self.assertEqual("Dinagat Islands", imported_feature.get('name'))
        self.assertEqual(expected_version, imported_feature.get("version"))

        os.remove(geojson_file)

        update_db_feature(test_feature_2, layer=table_name)

        cur = connection.cursor()
        cur.execute("SELECT * FROM {} WHERE fulcrum_id = '123' LIMIT 1;".format(table_name))
        results = dictfetchall(cur)
        if results:
            imported_feature = results[0]

        expected_version = 2

        self.assertEqual("Dinagat Islands", imported_feature.get('name'))
        self.assertEqual(expected_version, imported_feature.get('version'))
        cur.close()
        connection.close()

    def test_s3_credentials_admin(self):
        """Ensure the expected structure of the s3 credentials is maintained."""
        s3_cred = S3Credential.objects.create(s3_key='key',
                                              s3_secret='secret',
                                              s3_gpg='encrypt')
        s3_bucket = S3Bucket.objects.create(s3_bucket='bucket', s3_credential=s3_cred)
        expected_bucket_dict = {'s3_bucket': ['bucket'],
                                's3_key': 'key',
                                's3_secret': 'secret',
                                's3_gpg': 'encrypt'}

        cred = dict()
        cred['s3_bucket'] = [s3_bucket.s3_bucket]
        cred['s3_key'] = s3_bucket.s3_credential.s3_key
        cred['s3_secret'] = s3_bucket.s3_credential.s3_secret
        cred['s3_gpg'] = s3_bucket.s3_credential.s3_gpg

        self.assertEqual(expected_bucket_dict, cred)
