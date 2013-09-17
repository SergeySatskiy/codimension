#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010  Sergey Satskiy sergey.satskiy@gmail.com
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

"""
VCS plugin support: status cache
"""

import datetime


class VCSStatus:
    " Holds the VCS file status "

    def __init__( self ):
        self.pluginID = None        # integer
        self.indicatorID = None     # integer
        self.message = None         # string or None
        self.lastUpdate = None      # time
        return



class VCSStatusCache:
    " Caches the file statuses which came from various plugins "

    def __init__( self ):
        self.__cache = {}   # path -> VCSStatus
        return

    def getStatus( self, path ):
        " Provides the status if it is in the cache "
        if path in self.__cache:
            return self.__cache[ path ]
        return None

    def updateStatus( self, path, pluginID,
                            indicatorID, message ):
        " Updates the status in the cache "
        if path in self.__cache:
            item = self.__cache[ path ]
            item.pluginID = pluginID
            item.indicatorID = indicatorID
            item.message = message
            item.lastUpdate = datetime.datetime.now()
            return

        item = VCSStatus()
        item.pluginID = pluginID
        item.indicatorID = indicatorID
        item.message = message
        item.lastUpdate = datetime.datetime.now()
        self.__cache[ path ] = item
        return

    def clear( self ):
        " Purges the cache "
        self.__cache = {}
        return

    def dismissPlugin( self, pluginID, callback ):
        " Removes all the certain plugin entries from the cache "
        for path, status in self.__cache.iteritems():
            if status.pluginID == pluginID:
                status.lastUpdate = None
                status.pluginID = None
                status.message = None
                oldIndicator = status.indicatorID
                status.indicatorID = None
                if oldIndicator:
                    callback( path, None, None, None )
        return


