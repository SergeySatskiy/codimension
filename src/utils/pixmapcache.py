#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010  Sergey Satskiy <sergey.satskiy@gmail.com>
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
# $Id$
#


""" codimension pixmap cache singleton """

import os.path, sys
from PyQt4.QtGui import QPixmap, QIcon


class PixmapCache( object ):
    """
    Implementation idea is taken from here:
    http://wiki.forum.nokia.com/index.php/How_to_make_a_singleton_in_Python
    """

    _iInstance = None
    class Singleton:
        """ Provides pixmap cache singleton facility """

        def __init__( self ):

            self.__cache = {}
            self.__searchPath = os.path.dirname( os.path.abspath( sys.argv[0] ) ) + \
                                os.path.sep + 'pixmaps' + os.path.sep
            return

        def getPixmap( self, name ):
            """ Provides the required pixmap """

            try:
                return self.__cache[ name ]
            except KeyError:
                if os.path.isabs( name ):
                    path = name
                else:
                    path = self.__searchPath + name
                if not os.path.exists( path ):
                    pixmap = QPixmap()
                    self.__cache[ name ] = pixmap
                    return pixmap

                pixmap = QPixmap( path )
                self.__cache[ name ] = pixmap
                return pixmap


        def getIcon( self, name ):
            """ Provides a pixmap as an icon """

            return QIcon( self.getPixmap( name ) )


    def __init__( self ):
        if PixmapCache._iInstance is None:
            PixmapCache._iInstance = PixmapCache.Singleton()

        self.__dict__[ '_PixmapCache__iInstance' ] = PixmapCache._iInstance
        return

    def __getattr__( self, aAttr ):
        return getattr( self._iInstance, aAttr )

