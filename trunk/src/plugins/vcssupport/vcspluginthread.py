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
VCS plugin support: plugin thread
"""

from PyQt4.QtCore import QThread, QMutex, QMutexLocker, QWaitCondition, SIGNAL
from collections import deque


# Indicator used by IDE to display errors while retrieving item status
IND_VCS_ERROR = -2


class VCSPluginThread( QThread ):
    " Wrapper for the plugin thread "

    def __init__( self, plugin, parent = None ):
        QThread.__init__( self, parent )

        self.__plugin = plugin
        self.__requestQueue = deque()

        self.__stopRequest = False
        self.__lock = QMutex()
        self.__condition = QWaitCondition()
        return

    def run( self ):
        " Thread loop "
        while not self.__stopRequest:
            self.__lock.lock()
            while self.__requestQueue:
                path, flag = self.__requestQueue.pop()
                self.__lock.unlock()
                self.__processRequest( path, flag )
                if self.__stopRequest:
                    break
                self.__lock.lock()
            if self.__stopRequest:
                self.__lock.unlock()
                break
            self.__condition.wait( self.__lock )
            self.__lock.unlock()
        return

    def __processRequest( self, path, flag ):
        " Processes a single request. It must be exception safe. "
        try:
            for status in self.__plugin.getObject().getStatus( path, flag ):
                if len( status ) == 3:
                    self.emit( SIGNAL( "VCSStatus" ), path + status[ 0 ],
                               status[ 1 ], status[ 2 ] )
                else:
                    self.emit( SIGNAL( "VCSStatus" ), path, IND_VCS_ERROR,
                               "The " + self.__plugin.getName() + " plugin "
                               "does not follow the getStatus() interface "
                               "agreement" )
        except Exception, exc:
            self.emit( SIGNAL( "VCSStatus" ), path, IND_VCS_ERROR,
                       "Exception in " + self.__plugin.getName() +
                       " plugin while retrieving VCS status: " + str( exc ) )
        return

    def addRequest( self, path, flag, urgent = False ):
        " Adds a request to the queue "
        self.__lock.lock()
        if urgent:
            self.__requestQueue.append( (path, flag) )
        else:
            self.__requestQueue.appendleft( (path, flag) )
        self.__lock.unlock()
        self.__condition.wakeAll()
        return

    def stop( self ):
        " Delivers the stop request "
        self.__stopRequest = True
        self.__condition.wakeAll()
        return

    def clearRequestQueue( self ):
        " Clears the thread request queue "
        self.__lock.lock()
        self.__requestQueue.clear()
        self.__lock.unlock()
        return


