# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2016  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""codimension run parameters cache"""

import json
import logging
import os.path
from copy import deepcopy
from .runparams import RunParameters, toJSON, fromJSON
from .config import DEFAULT_ENCODING


class RunParametersCache:

    """Provides the run parameters cache"""

    def __init__(self):
        # path -> RunParameters, see runparams.py
        # The path can be relative or absolute:
        # relative for project files, absolute for non-project ones
        self.__cache = {}
        self.__rpFileName = None

    def reset(self):
        """Resets the binding to the file system"""
        self.__cache = {}
        self.__rpFileName = None

    def setup(self, dirName):
        """Binds the cache to a disk file"""
        # Just in case - flush the previous data if they were bound
        RunParametersCache.save(self)

        dirName = os.path.realpath(dirName)
        if not dirName.endswith(os.path.sep):
            dirName += os.path.sep
        if not os.path.isdir(dirName):
            raise Exception('Directory name is expected for the '
                            'run parameters cache. The given ' +
                            dirName + ' is not.')

        self.__rpFileName = dirName + 'runparams.json'
        if os.path.exists(self.__rpFileName):
            RunParametersCache.load(self)

    def load(self):
        """Loads the cache from the given file"""
        if self.__rpFileName:
            try:
                with open(self.__rpFileName, 'r',
                          encoding=DEFAULT_ENCODING) as diskfile:
                    self.__cache = json.load(diskfile, object_hook=fromJSON)
            except Exception as exc:
                logging.error('Error loading run paramaters cache (from ' +
                              self.__rpFileName + '): ' + str(exc))
                self.__cache = {}

    def save(self):
        """Saves the cache into the given file"""
        if self.__rpFileName:
            try:
                with open(self.__rpFileName, 'w',
                          encoding=DEFAULT_ENCODING) as diskfile:
                    json.dump(self.__cache, diskfile, default=toJSON)
            except Exception as exc:
                logging.error('Error saving run paramaters cache (to ' +
                              self.__rpFileName + '): ' + str(exc))

    def getRunParameters(self, path):
        """Provides the required parameters object"""
        try:
            return deepcopy(self.__cache[path])
        except KeyError:
            return RunParameters()

    def addRunParameters(self, path, params):
        """Adds run params into cache if needed"""
        if params.isDefault():
            self.removeRunParameters(path)
            return
        # Non-default, so need to insert
        self.__cache[path] = deepcopy(params)
        RunParametersCache.save(self)

    def removeRunParameters(self, path):
        """Removes one item from the map"""
        try:
            del self.__cache[path]
            RunParametersCache.save(self)
        except KeyError:
            return
