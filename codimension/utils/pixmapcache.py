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

"""codimension pixmap cache"""

from os.path import dirname, realpath, sep, isabs, exists
import sys
from ui.qt import QPixmap, QIcon


class PixmapCache():

    """pixmap cache"""

    def __init__(self):
        self.__cache = {}
        self.__dir = dirname(realpath(sys.argv[0])) + sep + 'pixmaps' + sep

    def getPath(self, path):
        """Provides an absolute path"""
        if isabs(path):
            return path
        return self.__dir + path

    def getSearchPath(self):
        """Provides the path where pixmaps are"""
        return self.__dir

    def getPixmap(self, name):
        """Provides the required pixmap"""
        try:
            return self.__cache[name]
        except KeyError:
            path = self.getPath(name)
            if not exists(path):
                pixmap = QPixmap()
                self.__cache[name] = pixmap
                return pixmap

            try:
                pixmap = QPixmap(path)
            except:
                pixmap = QPixmap()
            self.__cache[name] = pixmap
            return pixmap

    def getIcon(self, name):
        """Provides a pixmap as an icon"""
        return QIcon(self.getPixmap(name))


# Pixmap cache: should be only one
# Access functions are below
PIXMAP_CACHE = PixmapCache()


def getIcon(name):
    """Syntactic shugar"""
    return PIXMAP_CACHE.getIcon(name)


def getPixmap(name):
    """Syntactic shugar"""
    return PIXMAP_CACHE.getPixmap(name)


def getPixmapPath():
    """Provides the path where pixmaps are"""
    return PIXMAP_CACHE.getSearchPath()
