#
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

" Provides the storage for the debugger environment "

import os.path
from copy import deepcopy
from .fileutils import loadJSON, saveJSON


__DEFAULT_DEBUGGER_PROPS = {'breakpoints': [],          # [[file, line], ...]
                            'watchpoints': [],          # [[file, expr], ...]
                            'ignoredexceptions': []}    # [type name, ... ]


class DebuggerEnvironment:
    " Loads/stores/saves the debugger environment "

    def __init__(self):
        self.__props = deepcopy(__DEFAULT_DEBUGGER_PROPS)
        self.__fileName = None

    def reset(self):
        self.__props = deepcopy(__DEFAULT_DEBUGGER_PROPS)
        self.__fileName = None

    def setup(self, dirName):
        " Binds the parameters to a disk file "
        # Just in case - flush the previous data if they were bound
        self.save()

        dirName = os.path.realpath(dirName)
        if not dirName.endswith(os.path.sep):
            dirName += os.path.sep
        if not os.path.isdir(dirName):
            raise Exception('Directory name is expected for the debugger '
                            'environment. The given ' + dirName + ' is not.')

        self.__fileName = dirName + "debuggerenv.json"
        if os.path.exists(self.__fileName):
            self.load()

    def load(self):
        " Loads the saved debugger environment "
        if self.__fileName:
            default = deepcopy(__DEFAULT_DEBUGGER_PROPS)
            self.__props = loadJSON(self.__fileName, 'debugger environment',
                                    default)

    def save(self):
        " Saves the debugger environment into a file "
        if self.__fileName:
            saveJSON(self.__fileName, self.__props, 'debugger environment')

    @property
    def breakpoints(self):
        " Provides the breakpoints "
        return self.__props['breakpoints']

    @breakpoints.setter
    def breakpoints(self, bpointList):
        self.__props['breakpoints'] = bpointList
        self.save()

    @property
    def watchpoints(self):
        " Provides the watchpoints "
        return self.__props['watchpoints']

    @watchpoints.setter
    def watchpoints(self, wpointList):
        self.__props['watchpoints'] = wpointList
        self.save()

    @property
    def exceptionFilters(self):
        " Provides the ignored exceptions "
        return self.__props['ignoredexceptions']

    @exceptionFilters.setter
    def exceptionFilters(self, newFilters):
        self.__props['ignoredexceptions'] = newFilters
        self.save()

    def addExceptionFilter(self, excptType):
        " Adds a new ignored exception type "
        if excptType not in self.__props['ignoredexceptions']:
            self.__props['ignoredexceptions'].append(excptType)
            self.save()

    def deleteExceptionFilter(self, excptType):
        " Remove ignored exception type "
        if excptType in self.__props['ignoredexceptions']:
            self.__props['ignoredexceptions'].remove(excptType)
            self.save()

    def addBreakpoint(self, fName, line):
        " Adds serialized breakpoint "
        value = [fName, line]
        if value not in self.__props['breakpoints']:
            self.__props['breakpoints'].append(value)
            self.save()

    def deleteBreakpoint(self, fName, line):
        " Deletes serialized breakpoint "
        value = [fName, line]
        if value in self.__props['breakpoints']:
            self.__props['breakpoints'].remove(value)
            self.save()

    def addWatchpoint(self, fName, expression):
        " Adds serialized watchpoint "
        value = [fName, expression]
        if value not in self.__props['watchpoints']:
            self.__props['watchpoints'].append(value)
            self.save()

    def deleteWatchpoint(self, fName, expression):
        " Deletes serialized watchpoint "
        value = [fName, expression]
        if value in self.__props['watchpoints']:
            self.__props['watchpoints'].remove(value)
            self.save()
