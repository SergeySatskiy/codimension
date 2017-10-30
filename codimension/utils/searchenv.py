# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2017  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Provides the storage for the search environment"""

import os.path
from copy import deepcopy
from .fileutils import loadJSON, saveJSON


# The 'find' item is for the search in the buffer dialogue. Each item is a
# dictionary of the following structure:
# { 'what': <string>,
#   'case': <bool>, 'word': <bool>, 'regexp': <bool> }
#
# The 'replace' item is for the replace in the buffer dialogue. Each item is a
# dictionary of the following structure:
# { 'what': <string>, 'with': <string>,
#   'case': <bool>, 'word': <bool>, 'regexp': <bool> }
#
# The 'findinfiles' item is for a modal find in files dialogue box. Each item
# is a dictionary of the following structure:
# { 'what': <string>,
#   'case': <bool>, 'word': <bool>, 'regexp': <bool>,
#   'inproject': <bool>, 'inopened': <bool>, 'indir': <bool>, 'dir': <string>,
#   'filter': <string> }
_DEFAULT_SEARCH_HISTORY = {
    'class': [],        # [term, ...]
    'function': [],     # [term, ...]
    'global': [],       # [term, ...]
    'findname': [],     # [term, ...]
    'findfile': [],     # [term, ...]
    'find': [],         # [ {'term': , 'replace': ,
                        #    'cbCase': , 'cbWord': , 'cbRegexp': }, ... ]
    'findinfiles': []}  # [ {'term': , 'dir': , 'filters': ,
                        #    'cbCase': , 'cbWord': , 'cbRegexp': ,
                        #    'rbProject': , 'rbOpen': , 'rbDir': }, ... ]

class SearchEnvironment:

    """Loads/stores/saves the search environment"""

    def __init__(self):
        self.__props = deepcopy(_DEFAULT_SEARCH_HISTORY)
        self.__seFileName = None

        # Default. Could be updated later
        self.__limit = 32

    def reset(self):
        """Un-binds from the file system"""
        self.__props = deepcopy(_DEFAULT_SEARCH_HISTORY)
        self.__seFileName = None

    def setup(self, dirName):
        """Binds the parameters to a disk file"""
        # Just in case - flush the previous data if they were bound
        SearchEnvironment.save(self)

        dirName = os.path.realpath(dirName)
        if not dirName.endswith(os.path.sep):
            dirName += os.path.sep
        if not os.path.isdir(dirName):
            raise Exception('Directory name is expected for the search '
                            'environment. The given ' + dirName + ' is not.')

        self.__seFileName = dirName + "searchenv.json"
        if os.path.exists(self.__seFileName):
            SearchEnvironment.load(self)

    def load(self):
        """Loads the saved search environment"""
        if self.__seFileName:
            default = deepcopy(_DEFAULT_SEARCH_HISTORY)
            self.__props = loadJSON(self.__seFileName, 'search environment',
                                    default)

    def save(self):
        """Saves the search environment into a file"""
        if self.__seFileName:
            saveJSON(self.__seFileName, self.__props, 'search environment')

    def __addToContainer(self, element, item):
        """Common implementation of adding a search item"""
        if item in self.__props[element]:
            self.__props[element].remove(item)
        self.__props[element].insert(0, item)
        if len(self.__props[element]) > self.__limit:
            self.__props[element] = self.__props[element][0:self.__limit]
        SearchEnvironment.save(self)

    def __setContainer(self, item, history):
        """Generic container setter which respects the limit"""
        if len(history) > self.__limit:
            self.__props[item] = history[0:self.__limit]
        else:
            self.__props[item] = history
        SearchEnvironment.save(self)

    def setLimit(self, newLimit):
        """Sets the new limit"""
        self.__limit = newLimit

    @property
    def findClassHistory(self):
        """Provides the find class history"""
        return self.__props['class']

    @findClassHistory.setter
    def findClassHistory(self, history):
        self.__setContainer('class', history)

    def addToFindClassHistory(self, item):
        """Adds an item to the class history"""
        self.__addToContainer('class', item)

    @property
    def findFunctionHistory(self):
        """Provides the find function history"""
        return self.__props['function']

    @findFunctionHistory.setter
    def findFunctionHistory(self, history):
        self.__setContainer('function', history)

    def addToFindFunctionHistory(self, item):
        """Adds an item to the function history"""
        self.__addToContainer('function', item)

    @property
    def findGlobalHistory(self):
        """Provides the find global history"""
        return self.__props['global']

    @findGlobalHistory.setter
    def findGlobalHistory(self, history):
        self.__setContainer('global', history)

    def addToFindGlobalHistory(self, item):
        """Adds an item to the global history"""
        self.__addToContainer('global', item)

    @property
    def findNameHistory(self):
        """Provides the find name history"""
        return self.__props['findname']

    @findNameHistory.setter
    def findNameHistory(self, history):
        self.__setContainer('findname', history)

    def addToFindNameHistory(self, item):
        """Adds an item to the name history"""
        self.__addToContainer('findname', item)

    @property
    def findFileHistory(self):
        """Provides the find file history"""
        return self.__props['findfile']

    @findFileHistory.setter
    def findFileHistory(self, history):
        self.__setContainer('findfile', history)

    def addToFindFileHistory(self, item):
        """Adds an item to the file history"""
        self.__addToContainer('findfile', item)

    @property
    def findHistory(self):
        """Provides the find history"""
        return self.__props['find']

    @findHistory.setter
    def findHistory(self, history):
        self.__setContainer('find', history)

    def addToFindHistory(self, item):
        """Adds an item to the file history"""
        self.__addToContainer('find', item)

    @property
    def findInFilesHistory(self):
        """Provides the find in files history"""
        return self.__props['findinfiles']

    @findInFilesHistory.setter
    def findInFilesHistory(self, history):
        self.__setContainer('findinfiles', history)

    def addToFindInFilesHistory(self, item):
        """Adds an item to the file history"""
        self.__addToContainer('findinfiles', item)
