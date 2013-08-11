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
        self.connect( self.clientExcptViewer,
                      SIGNAL( 'ClientExceptionsCleared' ),
                      self.__onClientExceptionsCleared )
        return

    def __createLayout( self ):
        " Creates the widget layout "

        verticalLayout = QVBoxLayout( self )
        verticalLayout.setContentsMargins( 1, 1, 1, 1 )

        self.splitter = QSplitter( Qt.Vertical )

        self.ignoredExcptViewer = IgnoredExceptionsViewer( self.splitter )
        self.clientExcptViewer = ClientExceptionsViewer( self.splitter,
                                                           self.ignoredExcptViewer )

        self.splitter.addWidget( self.clientExcptViewer )
        self.splitter.addWidget( self.ignoredExcptViewer )

        self.splitter.setCollapsible( 0, False )
        self.splitter.setCollapsible( 1, False )

        verticalLayout.addWidget( self.splitter )
        return

    def clear( self ):
        " Clears everything "
        self.clientExcptViewer.clear()
        return

    def addException( self, exceptionType, exceptionMessage,
                            stackTrace ):
        " Adds the exception to the view "
        self.clientExcptViewer.addException( exceptionType, exceptionMessage,
                                             stackTrace )
        return

    def isIgnored( self, exceptionType ):
        " Returns True if this exception type should be ignored "
        return self.ignoredExcptViewer.isIgnored( exceptionType )

    def setFocus( self ):
        " Sets the focus to the client exception window "
        self.clientExcptViewer.setFocus()
        return

    def getTotalClientExceptionCount( self ):
        " Provides the total number of the client exceptions "
        return self.clientExcptViewer.getTotalCount()

    def __onClientExceptionsCleared( self ):
        " Triggered when the user cleared exceptions "
        self.emit( SIGNAL( 'ClientExceptionsCleared' ) )
        return

