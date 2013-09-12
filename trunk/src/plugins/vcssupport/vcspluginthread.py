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
                request = self.__requestQueue.pop()
                self.__lock.unlock()
                self.__processRequest( request )
                if self.__stopRequest:
                    break
                self.__lock.lock()
            if self.__stopRequest:
                self.__lock.unlock()
                break
            self.__condition.wait( self.__lock )
            self.__lock.unlock()
        return

    def __processRequest( self, request ):
        " Processes a single request. It must be exception safe. "
        pass


    def addRequest( self, request, urgent = False ):
        " Adds a request to the queue "
        self.__lock.lock()
        if urgent:
            self.__requestQueue.append( request )
        else:
            self.__requestQueue.appendleft( request )
        self.__lock.unlock()
        self.__condition.wakeAll()
        return

    def stop( self ):
        " Delivers the stop request "
        self.__stopRequest = True
        self.__condition.wakeAll()
        return

