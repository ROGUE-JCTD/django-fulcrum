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
import geogigpy


def create_geogig_datastore(store_name):
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
                                                                              store_name))
        cat.save(datastore)


def create_geogig_repo(repo_name,
                       user_name=getattr(settings, 'SITENAME', None),
                       user_email=getattr(settings, 'SERVER_EMAIL', None)):
    repo_dir = os.path.join(get_ogc_server().get('GEOGIG_DATASTORE_DIR'), repo_name)
    # geogigpy.Repository(repo_dir, init=True)
    if not os.path.exists(repo_dir):
        os.mkdir(repo_dir)
    if os.path.exists(os.path.join(repo_dir,'.geogig')):
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
    repo_xml_path = os.path.join(os.path.join(os.path.join(get_ogc_server().get('GEOGIG_DATASTORE_DIR'), 'config'), 'repos'))
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

    repos={}
    for i in range(0,len(ids)):
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
    with open('/var/lib/geonode/fulcrum_data/output.html','wb') as out_html:
        out_html.write(body.encode('utf-8'))


def geojson_to_wfs(geojson=None):
    root = ET.fromstring(get_xml_template())
    return ET.tostring(root)


def get_xml_template():

    wfs_template = '<?xml version="1.0" encoding="UTF-8"?>\
    <wfs:Transaction xmlns:wfs="http://www.opengis.net/wfs" ' \
                   'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ' \
                   'service="WFS" version="1.0.0" ' \
                   'handle="Added 1 feature." ' \
                   'xsi:schemaLocation="http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.0.0/wfs.xsd">\
        <wfs:Insert handle="Added 1 feature to '' via MapLoom.">\
            <feature:fulcrum_starbucks xmlns:feature="http://www.geonode.org/">\
                <feature:wkb_geometry>\
                    <gml:Point xmlns:gml="http://www.opengis.net/gml" srsName="urn:ogc:def:crs:EPSG::4326">\
                        <gml:coordinates decimal="." cs="," ts=" ">0,0</gml:coordinates>\
                    </gml:Point>\
                </feature:wkb_geometry>\
                <feature:updated_at>1</feature:updated_at>\
                <feature:updated_at_time>1</feature:updated_at_time>\
                <feature:updated_by_id>1</feature:updated_by_id>\
                <feature:form_id>1</feature:form_id>\
                <feature:city>1</feature:city>\
                <feature:created_by>1</feature:created_by>\
                <feature:client_created_at>1</feature:client_created_at>\
                <feature:version>1</feature:version>\
                <feature:latitude>1</feature:latitude>\
                <feature:phone_number>1</feature:phone_number>\
                <feature:store_number>1</feature:store_number>\
                <feature:updated_by>1</feature:updated_by>\
                <feature:client_updated_at>1</feature:client_updated_at>\
                <feature:created_by_id>1</feature:created_by_id>\
                <feature:name>new</feature:name>\
                <feature:fulcrum_id>40</feature:fulcrum_id>\
                <feature:country>1</feature:country>\
                <feature:created_at>1</feature:created_at>\
                <feature:longitude>1</feature:longitude>\
                <feature:address_1>1</feature:address_1>\
                <feature:address_2>1</feature:address_2>\
                <feature:address_3>1</feature:address_3>\
                <feature:postal_code>1</feature:postal_code>\
            </feature:fulcrum_starbucks>\
        </wfs:Insert>\
    </wfs:Transaction>'
    return wfs_template
