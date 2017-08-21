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


"""codimension brief module info cache"""

from os.path import realpath, getmtime, exists
from cdmpyparser import getBriefModuleInfoFromFile


class BriefModuleInfoCache():

    """Provides the module info cache"""

    def __init__(self):
        # abs file path -> (modification time, mod info)
        self.__cache = {}

    def get(self, path):
        """Provides the required modinfo"""
        path = realpath(path)
        try:
            modInfo = self.__cache[path]
            if not exists(path):
                del self.__cache[path]
                raise Exception("Cannot open " + path)

            lastModTime = getmtime(path)
            if lastModTime <= modInfo[0]:
                return modInfo[1]

            # update the key
            info = getBriefModuleInfoFromFile(path)
            self.__cache[path] = (lastModTime, info)
            return info
        except KeyError:
            if not exists(path):
                raise Exception("Cannot open " + path)

            info = getBriefModuleInfoFromFile(path)
            self.__cache[path] = (getmtime(path), info)
            return info

    def remove(self, path):
        """Removes one file from the map"""
        path = realpath(path)
        try:
            del self.__cache[path]
        except KeyError:
            return

    def clear(self):
        """Clears the cache"""
        self.__cache = {}
