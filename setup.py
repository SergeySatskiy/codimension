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

from setuptools import setup
import os.path
import sys

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
    except:
        print('pypandoc package is not installed: the markdown '
              'README.md convertion to rst failed', file=sys.stderr)
        import io
        # pandoc is not installed, fallback to using raw contents
        with io.open('README.md', encoding='utf-8') as f:
            long_description = f.read()
    return long_description


def getRequirements():
    """Provides the requirements list"""
    if not os.path.exists('requirements.txt'):
        print('Could not find requirements.txt', file=sys.stderr)
        sys.exit(1)

    with open('requirements.txt') as f:
        required = f.read().splitlines()
    return required


def getDataFiles():
    """Provides the data files"""
    extensions = ['.png', '.svg', '.svgz', '.json', '.css']
    data_files = [('/codimension/pixmaps', 'codimension/pixmaps/'),
                  ('/codimension/skins/default', 'codimension/skins/default/')]

    result = [('share/applications', ['resources/codimension.desktop']),
              ('share/pixmaps', ['resources/codimension.png']),
              ('share/metainfo', ['resources/codimension.appdata.xml'])]

    for item in data_files:
        targetDir = item[0]
        matchFiles = []
        for fName in os.listdir(item[1]):
            for ext in extensions:
                if fName.endswith(ext):
                    matchFiles.append(item[1] + fName)
                    break
        if matchFiles:
            result.append((targetDir, matchFiles))

    return result


def getPackages():
    """Provides packages"""
    return ['codimension',
            'codimension/analysis',
            'codimension/autocomplete',
            'codimension/diagram',
            'codimension/editor',
            'codimension/flowui',
            'codimension/profiling',
            'codimension/ui',
            'codimension/utils',
            'codimension/debugger', 'codimension/debugger/client',
            'codimension/plugins',
            'codimension/plugins/categories',
            'codimension/plugins/manager',
            'codimension/plugins/vcssupport']


# install_requires=['pypandoc'] could be added but really it needs to only
# at the time of submitting a package to Pypi so it is excluded from the
# dependencies
setup(name='codimension',
      description=getDescription(),
      python_requires='>=3.5',
      long_description=getLongDescription(),
      version=getVersion(),
      author='Sergey Satskiy',
      author_email='sergey.satskiy@gmail.com',
      url='https://github.com/SergeySatskiy/codimension',
      license='GPLv3',
      classifiers=[
           'Development Status :: 5 - Production/Stable',
           'Intended Audience :: Developers',
           'License :: OSI Approved :: GNU General Public License (GPL)',
           'Operating System :: POSIX :: Linux',
           'Programming Language :: Python :: 3'],
      platforms=['any'],
      packages=getPackages(),
      install_requires=getRequirements(),
      data_files=getDataFiles(),
      entry_points={'gui_scripts':
                    ['codimension = codimension.codimension:main']})
