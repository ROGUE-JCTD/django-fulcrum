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


def import_to_geogig(repo_name, layer_name):
    repo_dir = create_geogig_repo(repo_name)
    if repo_dir:
        set_geoserver_permissions(repo_dir)
    import_from_pg(repo_name, layer_name)
    create_geogig_datastore(repo_name, layer_name)


def create_geogig_datastore(store_name, layer_name):
    """
    Args:
        store_name: name of geogig repo
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
    repo_dir = os.path.join(get_ogc_server().get('GEOGIG_DATASTORE_DIR'), repo_name)
    # geogigpy.Repository(repo_dir, init=True)
    if not os.path.exists(repo_dir):
        os.mkdir(repo_dir)
    if os.path.exists(os.path.join(repo_dir, '.geogig')):
        print("Cannot create new geogig repo {}, because one already exists.".format(repo_name))
        return repo_dir
    prev_dir = os.getcwd()
    os.chdir(os.path.dirname(repo_dir))
    subprocess.call(['/var/lib/geogig/bin/geogig', 'init', repo_name])
    os.chdir(repo_dir)
    subprocess.call(['/var/lib/geogig/bin/geogig', 'config', 'user.name', user_name])
    subprocess.call(['/var/lib/geogig/bin/geogig', 'config', 'user.email', user_email])
    os.chdir(prev_dir)
    return repo_dir


def set_geoserver_permissions(dir_path):
    if not 'linux' in sys.platform:
        return
    import pwd
    import grp
    if not os.path.exists(dir_path):
        return
    uid = pwd.getpwnam("tomcat").pw_uid
    gid = grp.getgrnam("geoservice").gr_gid
    for root, dirs, files in os.walk(dir_path):
        for directory in dirs:
            os.chown(os.path.join(root, directory), uid, gid)
        for file_path in files:
            os.chown(os.path.join(root, file_path), uid, gid)


def delete_geogig_repo(repo_name):
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


def send_wfs(xml=None, url=None):
    client = requests.session()
    URL = 'https://{}/account/login'.format('geoshape.dev')
    client.get(URL, verify=False)
    csrftoken = client.cookies['csrftoken']
    login_data = dict(username='admin', password='geoshape', csrfmiddlewaretoken=csrftoken)
    client_resp = client.post(URL, data=login_data, headers=dict(Referer=URL), verify=False)
    print("login reponse:{}".format(client_resp.status_code))
    print("login reponse:{}".format(str(client_resp.headers)))
    url = "https://geoshape.dev/proxy/"
    params = {"url": "https://geoshape.dev/geoserver/wfs/WfsDispatcher"}
    headers = {'Referer': "https://geoshape.dev/maploom/maps/new?layer=geonode%3Afulcrum_starbucks",
               'X-CSRFToken': client.cookies['csrftoken'],
               'Authorization': ""}
    data = geojson_to_wfs()
    response = client.post(url, data=data, headers=headers, params=params, verify=False)
    print(response.status_code)
    print(str(response.headers))
    print(str(response.request.headers))
    print(str(client.cookies))
    body = handle_double_zip(response)
    with open('/var/lib/geonode/fulcrum_data/output.html', 'wb') as out_html:
        out_html.write(body.encode('utf-8'))


def geojson_to_wfs(geojson=None):
    root = ET.fromstring(get_wfs_template())
    return ET.tostring(root)


def get_wfs_template():
    import xml.etree.ElementTree as ET
    ET.register_namespace('wfs', "http://www.opengis.net/wfs")
    ET.register_namespace('gml', "http://www.opengis.org/gml")
    ET.register_namespace('feature', "http://www.geonode.org/")
    wfs_template = '<?xml version="1.0" encoding="UTF-8"?>\
    <wfs:Transaction xmlns:wfs="http://www.opengis.net/wfs" ' \
                   'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ' \
                   'service="WFS" version="1.0.0" ' \
                   'handle="Added 1 feature." ' \
                   'xsi:schemaLocation="http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.0.0/wfs.xsd">\
        <wfs:Insert handle="Added 1 feature to '' via MapLoom.">\
        </wfs:Insert>\
    </wfs:Transaction>'
    wfs = ET.fromstring(wfs_template)
    return wfs


def get_wfs_transaction(feature_dict, layer):
    from lxml import etree as ET
    ns_map = {"xsi": "http://www.w3.org/2001/XMLSchema-instance",
             "wfs":  "http://www.opengis.net/wfs",
              "gml": "http://www.opengis.org/gml",
              "feature": "http://www.geonode.org/"}

    transactionName = ET.QName("http://www.opengis.net/wfs", 'Transaction')
    transaction = ET.Element(transactionName, nsmap=ns_map)
    # sheet = ET.ElementTree(root)

    insert = ET.SubElement(transaction, ET.QName(ns_map.get('wfs'), "Insert"), attrib={'handle':'Added {} feature(s) via django-fulcrum'.format(1)})
    feature = ET.SubElement(insert, ET.QName(ns_map.get('feature'), layer))
    geometry = ET.SubElement(feature, ET.QName(ns_map.get('feature'), 'wkb_geometry'))
    point = ET.SubElement(geometry, ET.QName(ns_map.get('gml'), 'Point'), attrib={'srsName':'urn:ogc:def:crs:EPSG::4326'})
    coordinates = ET.SubElement(point, ET.QName(ns_map.get('gml'), 'coordinates'), attrib={'decimal':'.',
                                                                                           'cs':',',
                                                                                           'ts':' '})
    coords = feature_dict.get('geometry').get('coordinates')
    coordinates.text = "{},{}".format(coords[1], coords[0])
    for prop in feature_dict.get('properties'):
        feature_element = ET.SubElement(feature, ET.QName(ns_map.get('feature'), prop))
        feature_element.text = str(feature_dict.get('properties').get(prop))
    return ET.tostring(transaction, xml_declaration=True, encoding="UTF-8")


def post_wfs_transaction(wfst):
    if not getattr(settings, "SITEURL", None):
        return None
    # url_login = "{}/account/login".format(getattr(settings, "SITEURL", None).rstrip('/'))
    # url_proxy = "{}/proxy".format(getattr(settings, "SITEURL", None).rstrip('/'))
    url = "{}/geoserver/wfs/WfsDispatcher".format(getattr(settings, "SITEURL", None).rstrip('/'))
    # s = requests.Session()
    # s.post(url_login, params={'username': 'admin', 'password': 'geoserver'})
    headers = {'Content-Type': 'application/xml'}
    ogc_server = get_ogc_server()
    auth=(ogc_server.get('USER'),
          ogc_server.get('PASSWORD'))
    print(requests.post(url, auth=auth, data=wfst, headers=headers).text)


def import_from_pg(repo_name, table_name):
    from django.db import connections
    db_conn = connections['fulcrum']
    repo_dir = os.path.join(get_ogc_server().get('GEOGIG_DATASTORE_DIR'), repo_name)
    prev_dir = os.getcwd()
    os.chdir(repo_dir)
    subprocess.call(['/var/lib/geogig/bin/geogig', 'pg', 'import',
                     '--database', 'geoshape_data', #db_conn.settings_dict.get('NAME'),
                     '--host', db_conn.settings_dict.get('HOST'),
                     '--port', db_conn.settings_dict.get('PORT'),
                     '--user', db_conn.settings_dict.get('USER'),
                     '--password', db_conn.settings_dict.get('PASSWORD'),
                     '--table', table_name])
    subprocess.call(['/var/lib/geogig/bin/geogig', 'add'])
    subprocess.call(['/var/lib/geogig/bin/geogig', 'commit', '-m', "'Imported table {} from postgis.'".format(table_name)])
    os.chdir(prev_dir)
