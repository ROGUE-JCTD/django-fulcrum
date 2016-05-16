import requests
from django.conf import settings
import gzip
from StringIO import StringIO
import xml.etree.ElementTree as ET
from geoserver.catalog import Catalog
import os
import subprocess
import shutil
import sys
import json


def import_to_geogig(repo_name, layer_name):
    """
    Creates a geogig repo, imports initial layer data to the repo, and publishes the layer
    Args:
        repo_name: A name for the datastore to be created in geoserver
        layer_name: The layer name to be published
    Returns:
        No return
    """
    repo_name = layer_name  # this should be changed once we can import things into existing geogig/geoserver repos.
    repo_dir, created = create_geogig_repo(repo_name)
    import_from_pg(repo_name, layer_name)
    if created:
        set_geoserver_permissions(repo_dir)
    if created:
        publish_geogig_layer(repo_name, layer_name)
        set_geoserver_permissions(repo_dir)


def publish_geogig_layer(store_name, layer_name):
    """
    Takes a layer in a geoserver datastore and publishes it
    Args:
        store_name: name of geogig repo
        layer_name: name of the layer to be published
    Returns:
        None
    """

    ogc_server = get_ogc_server()
    url = "{}/rest".format(ogc_server.get('LOCATION').rstrip('/'))
    workspace_name = "geonode"
    workspace_uri = "http://www.geonode.org/"
    cat = Catalog(url)
    # Check if local workspace exists and if not create it
    workspace = cat.get_workspace(workspace_name)
    if workspace is None:
        cat.create_workspace(workspace_name, workspace_uri)
        print "Workspace " + workspace_name + " created."

    # Get list of datastores
    datastores = cat.get_stores()
    datastore = None
    # Check if remote datastore exists on local system
    for ds in datastores:
        if ds.name.lower() == store_name.lower():
            datastore = ds

    if not datastore:
        datastore = cat.create_datastore(store_name, workspace_name)
        datastore.connection_parameters.update(geogig_repository=os.path.join(ogc_server.get('GEOGIG_DATASTORE_DIR'),
                                                                              store_name),
                                               branch='master')
        cat.save(datastore)

    # Check if remote layer already exists on local system
    layers = cat.get_layers()
    srs = "EPSG:4326"
    layer = None
    for lyr in layers:
        if lyr.resource.name.lower() == layer_name.lower():
            layer = lyr

    if not layer:
        # Publish remote layer
        layer = cat.publish_featuretype(layer_name.lower(), datastore, srs, srs=srs)
        return layer, True
    else:
        return layer, False


def is_geogig_layer_published(layer_name):
    """
    Check if the layer has been published in geoserver
    Args:
        layer_name: The layer to be checked
    Returns:
        If the layer has been published yet (True/False)
    """
    ogc_server = get_ogc_server()
    url = "{}/rest".format(ogc_server.get('LOCATION').rstrip('/'))
    cat = Catalog(url)
    # Check if remote layer already exists on local system
    layers = cat.get_layers()
    layer = None
    for lyr in layers:
        if lyr.resource.name.lower() == layer_name.lower():
            layer = lyr
    if not layer:
        return False
    else:
        return True


def create_geogig_repo(repo_name,
                       user_name=getattr(settings, 'SITENAME', None),
                       user_email=getattr(settings, 'SERVER_EMAIL', None)):
    """
    Creates a new geogig repo in the geogig datastore directory
    Args:
        repo_name: Name to be used for geogig repo
        user_name: User name to set for the geogig repo
        user_email: Email address to set for the geogig repo
    Returns:
        A tuple containing the repo directory path and boolean for if it was created
    """
    created = False
    repo_dir = os.path.join(get_ogc_server().get('GEOGIG_DATASTORE_DIR'), repo_name)
    # geogigpy.Repository(repo_dir, init=True)
    if not os.path.exists(repo_dir):
        os.mkdir(repo_dir)
    if os.path.exists(os.path.join(repo_dir, '.geogig')):
        print("Cannot create new geogig repo {}, because one already exists.".format(repo_name))
        return repo_dir, created
    prev_dir = os.getcwd()
    os.chdir(os.path.dirname(repo_dir))
    subprocess.call(['/var/lib/geogig/bin/geogig', 'init', repo_name])
    os.chdir(repo_dir)
    subprocess.call(['/var/lib/geogig/bin/geogig', 'config', 'user.name', user_name])
    subprocess.call(['/var/lib/geogig/bin/geogig', 'config', 'user.email', user_email])
    created = True
    os.chdir(prev_dir)
    return repo_dir, created


def set_geoserver_permissions(dir_path):
    """
    Sets permissions for a geogig repo so that geoserver can properly access it
    Args:
        dir_path: Path to the repo for which permissions will be changed
    Returns:
        Nothing
    """
    if not 'linux' in sys.platform:
        return
    import pwd
    import grp
    if not os.path.exists(dir_path):
        return
    # uid = pwd.getpwnam("tomcat").pw_uid
    # gid = grp.getgrnam("geoservice").gr_gid
    try:
        os.chmod(dir_path, 0775)
        for root, dirs, files in os.walk(dir_path):
            for directory in dirs:
                os.chmod(os.path.join(root, directory), 0775)
                # os.chmod(os.path.join(root, directory), uid, gid)
            for file_path in files:
                os.chmod(os.path.join(root, file_path), 0775)
                # os.chown(os.path.join(root, file_path), uid, gid)
    except OSError as e:
        print("Could not change permissions for all repo files.")
        print("The error is {}".format(e.message))


def delete_geogig_repo(repo_name):
    """
    Remove a geogig from the geogig datastore directory
    Args:
        repo_name: The name of repo to be deleted
    Returns:
        No return
    """
    repos = get_all_geogig_repos
    repo_id = ''
    for id, name in repos:
        if name == repo_name:
            repo_id = id
    repo_dir = os.path.join(get_ogc_server().get('GEOGIG_DATASTORE_DIR'), repo_name)
    if os.path.exists(repo_dir):
        shutil.rmtree(repo_dir)
    repo_xml_path = os.path.join(
            os.path.join(os.path.join(get_ogc_server().get('GEOGIG_DATASTORE_DIR'), 'config'), 'repos'))
    if os.path.isfile(os.path.join(repo_xml_path, '{}.xml'.format(repo_id))):
        os.remove(repo_dir)


def get_geogig_repo_name(repo):
    url = '{}'.format(get_geogig_base_url(), str(id))
    response = requests.get(url,
                            verify=False)
    pass


def get_all_geogig_repos():
    """
    Call to geoserver to find all geogig repos available
    Returns: Dict containing repo ids and names
    """
    response = requests.get(get_geogig_base_url(),
                            verify=False)

    if response.status_code != 200:
        return

    root = ET.fromstring(handle_double_zip(response))

    ids = []
    for id in root.findall(".//id"):  # Returns []
        ids += [id.text]

    names = []
    for name in root.findall(".//name"):  # Returns []
        names += [name.text]

    repos = {}
    for i in range(0, len(ids)):
        repos[ids[i]] = names[i]

    return repos


def get_geogig_base_url():
    """
    Returns: The full url to the geogig endpoint.
    """
    site_url = getattr(settings, 'SITEURL', None)

    ogc_server = get_ogc_server()
    if not site_url or not ogc_server:
        print("Could not find site_url or ogc_server.")
        return

    return '{}/geogig'.format((ogc_server.get('LOCATION') or site_url).strip('/'))


def handle_double_zip(response):
    """
    This can be used to handle integration issues where its possible that responses are gzipped twice.
    Args:
        response: A python requests response object.
    Returns:
        The body of the response as a string.
    """
    if response.headers.get('content-encoding') == 'gzip, gzip':
        gz_file = gzip.GzipFile(fileobj=StringIO(response.content), mode='rb')
        decompressed_file = gzip.GzipFile(fileobj=StringIO(gz_file.read()), mode='rb')
        body = decompressed_file.read()
    else:
        body = response.text
    return body


def get_ogc_server(alias=None):
    """
    Args:
        alias: An alias for which OGC_SERVER to get from the settings file, default is 'default'.
    Returns:
        A dict containing inormation about the OGC_SERVER.
    """

    ogc_server = getattr(settings, 'OGC_SERVER', None)

    if ogc_server:
        if ogc_server.get(alias):
            return ogc_server.get(alias)
        else:
            return ogc_server.get('default')


def prepare_wfs_transaction(features_dict, layer):
    """
    Creates an xml string for WFS-Transaction to insert features to a layer
    Args:
        features_dict: An array of geojson features to be inserted
        layer: The name of the target layer
    Returns:
        An xml WFS-T in string format
    """
    from lxml import etree as ET
    ns_map = {"xsi": "http://www.w3.org/2001/XMLSchema-instance",
              "wfs": "http://www.opengis.net/wfs",
              "gml": "http://www.opengis.net/gml",
              "feature": "http://www.geonode.org/",
              "ogc": "http://www.opengis.net/ogc"}

    transactionName = ET.QName("http://www.opengis.net/wfs", 'Transaction')
    transaction = ET.Element(transactionName, nsmap=ns_map)
    insert = ET.SubElement(transaction, ET.QName(ns_map.get('wfs'), "Insert"),
                           attrib={'idgen':'UseExisting', 'handle': 'Added {} feature(s) via django-fulcrum'.format(len(features_dict))})

    for feature_dict in features_dict:
        fulcrum_id = feature_dict.get('properties').get('fulcrum_id')
        feature = ET.SubElement(insert, ET.QName(ns_map.get('feature'), layer), attrib={'fid': fulcrum_id})
        geometry = ET.SubElement(feature, ET.QName(ns_map.get('feature'), 'wkb_geometry'))
        point = ET.SubElement(geometry, ET.QName(ns_map.get('gml'), 'Point'),
                              attrib={'srsName': 'urn:ogc:def:crs:EPSG::4326'})
        coordinates = ET.SubElement(point, ET.QName(ns_map.get('gml'), 'coordinates'), attrib={'decimal': '.',
                                                                                               'cs': ',',
                                                                                               'ts': ' '})
        coords = feature_dict.get('geometry').get('coordinates')
        coordinates.text = "{},{}".format(coords[1], coords[0])
        for prop in feature_dict.get('properties'):
            feature_element = ET.SubElement(feature, ET.QName(ns_map.get('feature'), prop))
            feature_element.text = str(feature_dict.get('properties').get(prop))
    return ET.tostring(transaction, xml_declaration=True, encoding="UTF-8")


def post_wfs_transaction(wfst):
    """
    Posts a WFS-T to geogig layer exposed through geoserver
    Args:
        wfst: A WFS-T in string format
    Returns:
        None if siteurl is not found
    """
    if not getattr(settings, "SITEURL", None):
        return None
    # url_login = "{}/account/login".format(getattr(settings, "SITEURL", None).rstrip('/'))
    # url_proxy = "{}/proxy".format(getattr(settings, "SITEURL", None).rstrip('/'))
    url = "{}/geoserver/wfs/WfsDispatcher".format(getattr(settings, "SITEURL", None).rstrip('/'))
    # s = requests.Session()
    # s.post(url_login, params={'username': 'admin', 'password': 'geoserver'})
    headers = {'Content-Type': 'application/xml'}
    ogc_server = get_ogc_server()
    auth = (ogc_server.get('USER'),
            ogc_server.get('PASSWORD'))
    print(requests.post(url, auth=auth, data=wfst, headers=headers, verify=getattr(settings, "SSL_VERIFY", True)).text)


def import_from_pg(repo_name, table_name):
    """
    Import a table from postgis into a unpublished geogig repo
    Args:
        repo_name: Name of target geogig repo
        table_name: Name of table in database to be imported (also will be the layer name once in geogig)
    Returns:
        No return
    """
    from django.db import connections
    db_conn = connections['fulcrum']
    repo_dir = os.path.join(get_ogc_server().get('GEOGIG_DATASTORE_DIR'), repo_name)
    prev_dir = os.getcwd()
    os.chdir(repo_dir)
    subprocess.call(['/var/lib/geogig/bin/geogig', 'pg', 'import',
                     '--database', 'geoshape_data',  # db_conn.settings_dict.get('NAME'),
                     '--host', db_conn.settings_dict.get('HOST'),
                     '--port', db_conn.settings_dict.get('PORT'),
                     '--user', db_conn.settings_dict.get('USER'),
                     '--password', db_conn.settings_dict.get('PASSWORD'),
                     '--fid-attrib', 'fulcrum_id',
                     '--table', table_name])
    subprocess.call(['/var/lib/geogig/bin/geogig', 'add'])
    cur = db_conn.cursor()
    cur.execute("SELECT count(*) FROM {};".format(table_name))
    count = cur.fetchone()
    cur.close()
    subprocess.call(
            ['/var/lib/geogig/bin/geogig', 'commit', '-m', "'Imported table {} from postgis, added {} feature(s).'".format(table_name, int(count[0]))])
    os.chdir(prev_dir)

def import_from_geojson(repo_name,table_name, features):
    """
    Import a geojson into a unpublished geogig repo
    Args:
        repo_name: Name of the target geogig repo
        table_name: Name for the layer once in geogig
        features: An array of geojson features
    Returns:
        No return
    """
    geojson = {"type": "FeatureCollection", "features": features}
    file_dir = get_ogc_server().get('GEOGIG_DATASTORE_DIR')
    file_path = os.path.join(file_dir, "{}.geojson".format(table_name))
    with open(file_path, 'w+') as file:
        file.write(json.dumps(geojson))
    repo_dir = os.path.join(get_ogc_server().get('GEOGIG_DATASTORE_DIR'), repo_name)
    prev_dir = os.getcwd()
    os.chdir(repo_dir)
    subprocess.call(['/var/lib/geogig/bin/geogig', 'geojson', 'import', file_path, '-d', '{}'.format(table_name)])
    subprocess.call(['/var/lib/geogig/bin/geogig', 'add'])
    subprocess.call(['/var/lib/geogig/bin/geogig', 'commit', '-m', "'Imported geojson.'"])
    os.remove(file_path)
    os.chdir(prev_dir)


def recalculate_featuretype_extent(datastore, layer_name):
    """
    Tell geoserver to recalculate the bbox for a published layer
    Needed for geogig layers to display properly in GeoSHAPE
    Args:
        datastore: Name of the datastore containing the target layer
        layer_name: Name of the target layer
    Returns:
        HTTP response from PUT request
    """
    if not getattr(settings, "SITEURL", None):
        return None
    url = "{}/geoserver/rest/workspaces/geonode/datastores/{}/featuretypes/{}?recalculate=nativebbox,latlonbbox".format(
        getattr(settings, "SITEURL", None).rstrip('/'), datastore, layer_name)
    headers = {'Content-Type': 'application/xml'}
    xml = '<featureType><name>{}</name><enabled>true</enabled></featureType>'.format(layer_name)
    ogc_server = get_ogc_server()
    auth = (ogc_server.get('USER'),
            ogc_server.get('PASSWORD'))
    return requests.put(url, xml, auth=auth, headers=headers, verify=getattr(settings, "SSL_VERIFY", True))
