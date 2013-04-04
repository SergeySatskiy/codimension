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

" debugger context viewer "


from stackviewer import StackViewer
from threadsviewer import ThreadsViewer
from variablesviewer import VariablesViewer

from PyQt4.QtCore import Qt, SIGNAL
from PyQt4.QtGui import QVBoxLayout, QWidget, QSplitter


class DebuggerContext( QWidget ):
    " Implements the debugger context viewer "

    def __init__( self, debugger, parent = None ):
        QWidget.__init__( self, parent )
        self.__debugger = debugger
        self.connect( self.__debugger, SIGNAL( 'ClientLine' ),
                      self.__onClientLine )
        self.connect( self.__debugger, SIGNAL( 'ClientStack' ),
                      self.__onClientStack )
        self.connect( self.__debugger, SIGNAL( 'ClientThreadList' ),
                      self.__onClientThreadList )
        self.connect( self.__debugger, SIGNAL( 'ClientVariables' ),
                      self.__onClientVariables )
        self.connect( self.__debugger, SIGNAL( 'ClientVariable' ),
                      self.__onClientVariable )

        self.currentStack = None
        self.__createLayout()
        return

    def __createLayout( self ):
        " Creates the widget layout "

        verticalLayout = QVBoxLayout( self )
        verticalLayout.setContentsMargins( 1, 1, 1, 1 )

        self.splitter = QSplitter( Qt.Vertical )

        self.__variablesViewer = VariablesViewer( self.__debugger,
                                                  self.splitter )
        self.__stackViewer = StackViewer( self.splitter )
        self.__threadsViewer = ThreadsViewer( self.splitter )

        self.splitter.addWidget( self.__variablesViewer )
        self.splitter.addWidget( self.__stackViewer )
        self.splitter.addWidget( self.__threadsViewer )

        self.splitter.setCollapsible( 0, False )
        self.splitter.setCollapsible( 1, False )
        self.splitter.setCollapsible( 2, False )

        verticalLayout.addWidget( self.splitter )
        return

    def clear( self ):
        " Clears everything "
        self.__variablesViewer.clear()
        self.__stackViewer.clear()
        self.__threadsViewer.clear()
        return

    def __onClientLine( self, fileName, line, forStack ):
        " Handles the signal from the debugged program "
        if not forStack:
            self.__variablesViewer.clear()
            self.__debugger.remoteThreadList()
            self.__debugger.remoteClientVariables( 1 )  # globals
            self.__debugger.remoteClientVariables( 0 )  # locals
        return

    def __onClientStack( self, stack ):
        " Handles the signal from the debugged program "
        self.__stackViewer.populate( stack )
        return

    def __onClientThreadList( self, currentThreadID, threadList ):
        " Handles the thread list from the remote client "
        self.__threadsViewer.populate( currentThreadID, threadList )
        return

    def __onClientVariables( self, scope, variables ):
        " Handles the client variables lists "
        frameNumber = self.__stackViewer.getFrameNumber()
        if scope in [ -1, 0 ]:
            # Empty list for local variables
            self.__variablesViewer.updateVariables( False, frameNumber, variables )
        else:
            self.__variablesViewer.updateVariables( True, frameNumber, variables )
        return

    def __onClientVariable( self, scope, variables ):
        " Handles the client variable list "
        if scope in [ -1, 0 ]:
            self.__variablesViewer.updateVariable( False, variables )
        else:
            self.__variablesViewer.updateVariable( True, variables )
        return

