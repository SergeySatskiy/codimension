# -*- coding: utf-8 -*-
#
# Codimension - Python 3 experimental IDE
# Copyright (C) 2010-2017 Sergey Satskiy <sergey.satskiy@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

"""Setup script for the Codimension IDE"""

import io
import os.path
import sys

from setuptools import setup


def getVersion():
    """The version is coming from a file in the source tree"""
    verFileName = 'codimension/cdmverspec.py'
    if not os.path.exists(verFileName):
        print('Cannot find the IDE version file. Expected here: ' +
              verFileName, file=sys.stderr)
        sys.exit(1)

    with open(verFileName) as version_file:
        for line in version_file:
            line = line.strip()
            if line.startswith('version'):
                return line.split('=')[1].strip()[1:-1]
    print('Cannot find a version line in the ' + verFileName,
          file=sys.stderr)
    sys.exit(1)


def getDescription():
    """Provides a short description"""
    return 'Experimental Python 3 IDE which aims at both textual and ' \
           'graphical representation of a code. The graphics is ' \
           'automatically re-generated while the code is typed'


def getLongDescription():
    """Provides the long description"""
    try:
        import pypandoc
        converted = pypandoc.convert('README.md', 'rst').splitlines()
        no_travis = [line for line in converted if 'travis-ci.org' not in line]
        long_description = '\n'.join(no_travis)

        # Pypi index does not like this link
        long_description = long_description.replace('|Build Status|', '')
    except Exception as exc:
        print('pypandoc package is not installed: the markdown '
              'README.md convertion to rst failed: ' + str(exc), file=sys.stderr)
        # pandoc is not installed, fallback to using raw contents
        with io.open('README.md', encoding='utf-8') as f:
            long_description = f.read()

    return long_description


def getRequirements():
    """Runtime install_requires from ``requirements-runtime.txt`` (not tooling)."""
    req_path = "requirements-runtime.txt"
    if not os.path.exists(req_path):
        print("Could not find requirements-runtime.txt", file=sys.stderr)
        sys.exit(1)

    required = []
    with open(req_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            required.append(line)
    return required


def getDataFiles():
    """Provides the data files"""
    result = [('share/applications', ['resources/codimension.desktop']),
              ('share/pixmaps', ['resources/codimension.png']),
              ('share/metainfo', ['resources/codimension.appdata.xml'])]
    return result


def _load_product_package_doc_filter():
    """Load shared filter without importing the installed package (setup-time)."""
    import importlib.util

    filter_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'codimension', 'utils', 'package_docs_filter.py')
    spec = importlib.util.spec_from_file_location(
        'codimension_package_docs_filter', filter_path)
    if spec is None or spec.loader is None:
        raise RuntimeError('Cannot load package_docs_filter from ' + filter_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.is_product_package_doc


def getPackageData():
    """Provides the data files"""
    is_product_package_doc = _load_product_package_doc_filter()
    extensions = ['.png', '.svg', '.svgz', '.json', '.css', '.md', '.jar',
                  'README', 'COPYING', '.cdmp']
    package_data = [('codimension.pixmaps',
                     'codimension/pixmaps/'),
                    ('codimension.skins',
                     'codimension/skins/'),
                    ('doc',
                     'doc/'),
                    ('doc.user',
                     'doc/user'),
                    ('doc.md',
                     'doc/md'),
                    ('doc.cml',
                     'doc/cml'),
                    ('doc.plugins',
                     'doc/plugins'),
                    ('doc.technology',
                     'doc/technology'),
                    ('doc.smartzoom',
                     'doc/smartzoom'),
                    ('doc.grouping',
                     'doc/grouping'),
                    ('doc.deadcode',
                     'doc/deadcode'),
                    ('doc.complexity',
                     'doc/complexity'),
                    ('doc.pyflakes',
                     'doc/pyflakes'),
                    ('doc.disassembling',
                     'doc/disassembling'),
                    ('doc.colorschemes',
                     'doc/colorschemes'),
                    ('doc.editorsettings',
                     'doc/editorsettings'),
                    ('doc.dependencies',
                     'doc/dependencies'),
                    ('doc.project',
                     'doc/project'),
                    ('plantuml',
                     'plantuml/'),
                    ('cdmplugins.ruff',
                     'cdmplugins/ruff/'),
                    ('cdmplugins.mypy',
                     'cdmplugins/mypy/'),
                    ('cdmplugins.pytest',
                     'cdmplugins/pytest/'),
                    ('cdmplugins.coverage',
                     'cdmplugins/coverage/'),
                    ('cdmplugins.bandit',
                     'cdmplugins/bandit/'),
                    ('cdmplugins.pipaudit',
                     'cdmplugins/pipaudit/'),
                    ('cdmplugins.ruffformat',
                     'cdmplugins/ruffformat/'),
                    ('cdmplugins.todopanel',
                     'cdmplugins/todopanel/'),
                    ('cdmplugins.git',
                     'cdmplugins/git/')]

    # If a skin needs to be added, then the following item should be also
    # appended:
    # package_data.append(('codimension.skins.myskin',
    #                      'codimension/skins/myskin/'))

    result = {}
    for item in package_data:
        package = item[0]
        matchFiles = []
        for fName in os.listdir(item[1]):
            for ext in extensions:
                if fName.endswith(ext):
                    if is_product_package_doc(package, fName):
                        matchFiles.append(fName)
                    break
        if matchFiles:
            result[package] = matchFiles
    return result


def getPackages():
    """Provides packages"""
    return ['codimension',
            'codimension.core',
            'codimension.app',
            'codimension.infrastructure',
            'codimension.parsers',
            'codimension.analysis',
            'codimension.autocomplete',
            'codimension.diagram',
            'codimension.editor',
            'codimension.flowui',
            'codimension.profiling',
            'codimension.ui',
            'codimension.utils',
            'codimension.search',
            'codimension.debugger', 'codimension.debugger.client',
            'codimension.plugins',
            'codimension.plugins.categories',
            'codimension.plugins.manager',
            'codimension.plugins.vcssupport',
            'codimension.pixmaps',
            'codimension.skins',
            'doc', 'doc.user', 'doc.cml', 'doc.plugins', 'doc.technology',
            'doc.md',
            'doc.smartzoom', 'doc.grouping', 'doc.deadcode',
            'doc.complexity', 'doc.pyflakes', 'doc.disassembling',
            'doc.colorschemes', 'doc.editorsettings',
            'doc.dependencies', 'doc.project',
            'plantuml',
            'cdmplugins',
            'cdmplugins.ruff',
            'cdmplugins.mypy',
            'cdmplugins.pytest',
            'cdmplugins.coverage',
            'cdmplugins.bandit',
            'cdmplugins.pipaudit',
            'cdmplugins.ruffformat',
            'cdmplugins.todopanel',
            'cdmplugins.git']
    # If a myskin skin is to be added as well, then one more package should
    # be mentioned: ..., 'codimension.skins.myskin']


# install_requires=['pypandoc'] could be added but really it needs to only
# at the time of submitting a package to Pypi so it is excluded from the
# dependencies
# Runtime dependencies live in pyproject.toml [project.dependencies] (T060–T061).
# setup.py remains for package discovery / data files; install_requires kept in sync
# with requirements.txt for older tooling that still invokes setup.py directly.
setup(name='codimension',
      description=getDescription(),
      python_requires='>=3.10',
      long_description=getLongDescription(),
      # long_description_content_type does not really work so far
      # long_description_content_type='text/markdown',
      version=getVersion(),
      author='Sergey Satskiy',
      author_email='sergey.satskiy@gmail.com',
      url='https://github.com/sesquicadaver/codimension',
      license='GPLv3',
      classifiers=['Development Status :: 3 - Alpha',
                   'Intended Audience :: Developers',
                   'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
                   'Operating System :: POSIX :: Linux',
                   'Programming Language :: Python :: 3',
                   'Programming Language :: Python :: 3.10',
                   'Programming Language :: Python :: 3.11',
                   'Programming Language :: Python :: 3.12',
                   'Programming Language :: Python :: 3.13'],
      platforms=['any'],
      packages=getPackages(),
      package_data=getPackageData(),
      install_requires=getRequirements(),
      data_files=getDataFiles(),
      entry_points={'gui_scripts':
                   ['codimension = codimension.codimension:main']})
