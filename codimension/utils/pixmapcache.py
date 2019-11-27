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

# pylint: disable=W0702
# pylint: disable=W0703
# pylint: disable=C0305

from os.path import dirname, realpath, sep, isabs, exists
import sys
from ui.qt import QPixmap, QIcon


class PixmapCache():

    """pixmap cache"""

    def __init__(self):
        self.__cache = {}
        self.__locationCache = {}
        self.__searchDirs = None

    def __initSearchDirs(self):
        """Initializes the search directories list"""
        # There are a few cases here:
        # - default skin does not have a directory in the installation package
        # - Codimension additional skins have a directory in the installation
        #   package
        # - User custom skins do not have directories in the installation
        #   package
        # All type of skins may have a directory in ~/.codimension3/skins

        self.__searchDirs = []

        from utils.globals import GlobalData
        skin = GlobalData().skin

        # First priority search dir is the ~/.codimension3/skins/<name>
        skinDir = skin.getUserDir()
        if skinDir:
            if exists(skinDir):
                self.__searchDirs.append(skinDir)

        # Second piority is the dir where the skin came from
        skinDir = skin.getDir()
        if skinDir:
            if exists(skinDir):
                if skinDir not in self.__searchDirs:
                    self.__searchDirs.append(skinDir)

        # Third priority is the default location of the pixmaps (installation
        # package)
        self.__searchDirs.append(dirname(realpath(sys.argv[0])) + sep +
                                 'pixmaps' + sep)

    def __getPath(self, path):
        """Provides an absolute path"""
        if isabs(path):
            return path if exists(path) else None

        if self.__searchDirs is None:
            self.__initSearchDirs()

        for dirName in self.__searchDirs:
            fullPath = dirName + path
            if exists(fullPath):
                return fullPath
        return None

    def getPixmap(self, name):
        """Provides the required pixmap"""
        try:
            return self.__cache[name]
        except KeyError:
            path = self.__getPath(name)
            if path is None:
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

    def getLocation(self, name):
        """Provides the pixmap location (svg items require a path)"""
        try:
            return self.__locationCache[name]
        except KeyError:
            # The path could be None if not found anywhere
            path = self.__getPath(name)
            self.__locationCache[name] = path
            return path

# Pixmap cache: should be only one
# Access functions are below
PIXMAP_CACHE = PixmapCache()


def getIcon(name):
    """Syntactic shugar"""
    return PIXMAP_CACHE.getIcon(name)

def getPixmap(name):
    """Syntactic shugar"""
    return PIXMAP_CACHE.getPixmap(name)

def getPixmapLocation(name):
    """Syntactic shugar"""
    return PIXMAP_CACHE.getLocation(name)

