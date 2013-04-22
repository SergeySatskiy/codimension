#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2012  Sergey Satskiy <sergey.satskiy@gmail.com>
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

" Debugger exceptions viewer "


from clientexcptviewer import ClientExceptionsViewer
from ignoredexcptviewer import IgnoredExceptionsViewer

from PyQt4.QtCore import Qt, SIGNAL
from PyQt4.QtGui import QVBoxLayout, QWidget, QSplitter


class DebuggerExceptions( QWidget ):
    " Implements the debugger context viewer "

    def __init__( self, parent = None ):
        QWidget.__init__( self, parent )

        self.__createLayout()
        return

    def __createLayout( self ):
        " Creates the widget layout "

        verticalLayout = QVBoxLayout( self )
        verticalLayout.setContentsMargins( 1, 1, 1, 1 )

        self.splitter = QSplitter( Qt.Vertical )

        self.__clientExcptViewer = ClientExceptionsViewer( self.splitter )
        self.__ignoredExcptViewer = IgnoredExceptionsViewer( self.splitter )

        self.splitter.addWidget( self.__clientExcptViewer )
        self.splitter.addWidget( self.__ignoredExcptViewer )

        self.splitter.setCollapsible( 0, False )
        self.splitter.setCollapsible( 1, False )

        verticalLayout.addWidget( self.splitter )
        return

    def clear( self ):
        " Clears everything "
        self.__clientExcptViewer.clear()
        return

    def addException( self, exceptionType, exceptionMessage,
                            stackTrace ):
        " Adds the exception to the view "
        self.__clientExcptViewer.addException( exceptionType, exceptionMessage,
                                               stackTrace )
        return

    def isIgnored( self, exceptionType ):
        " Returns True if this exception type should be ignored "
        return self.__ignoredExcptViewer.isIgnored( exceptionType )

    def setFocus( self ):
        " Sets the focus to the client exception window "
        self.__clientExcptViewer.setFocus()
        return

    def getTotalClientExceptionCount( self ):
        " Provides the total number of the client exceptions "
        return self.__clientExcptViewer.getTotalCount()

