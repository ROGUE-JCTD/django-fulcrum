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
import os
import argparse
import re


def create_mvp(name='mvp', dir_path=os.getcwd()):
    """
    Args:
        name: The name of the project to be created.
        dir_path: The directory to place the new project files in,
        (i.e. -dir_path/name
                   -name
                        -settings.py
                        -urls.py
                        -wsgi.py
                        -celery.py
                   -manage.py)
    Returns: None
    """
    proj_root = os.path.join(dir_path, name)
    proj_dir = os.path.join(proj_root, name)
    if not os.path.exists(dir_path):
        os.mkdir(dir_path)
    if not os.path.exists(proj_root):
        os.mkdir(proj_root)
    if not os.path.exists(proj_dir):
        os.mkdir(proj_dir)
    templates = os.path.dirname(os.path.abspath(__file__))
    proj_templates = os.path.join(templates, 'mvp')
    for file_name in os.listdir(proj_templates):
        copy_template(os.path.join(proj_templates, file_name),
                      os.path.join(proj_dir, file_name),
                      name)
    copy_template(os.path.join(templates, 'manage.py'),
                  os.path.join(proj_root, 'manage.py'),
                  name)


def copy_template(template, new_file, name):
    """
    Args:
        template: The absolute path to the template.
        new_file: The absolute path to the new file.
        name: The name of the new project

    Returns: None
    """
    if os.path.isfile(new_file):
        print("Warning: The file {}, was overwritten.".format(new_file))
    with open(template, 'r') as temp_file, open(new_file, 'w') as proj_file:
        for line in temp_file:
            line = re.sub('mvp', name, line)
            proj_file.write(line)


def main():
    parser = argparse.ArgumentParser(description='Script to create a minimal django project,'
                                                 'for use with Django-Fulcrum.')
    parser.add_argument('-dir_path', default=os.getcwd(), help='Location to store the project.')
    parser.add_argument('-name', default='mvp', help='The name of the project.')
    args = parser.parse_args()
    create_mvp(name=args.name, dir_path=args.dir_path)


if __name__ == "__main__":
    main()
