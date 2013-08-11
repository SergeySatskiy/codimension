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
                      self.onClientStack )
        self.connect( self.__debugger, SIGNAL( 'ClientThreadList' ),
                      self.__onClientThreadList )
        self.connect( self.__debugger, SIGNAL( 'ClientVariables' ),
                      self.__onClientVariables )
        self.connect( self.__debugger, SIGNAL( 'ClientVariable' ),
                      self.__onClientVariable )
        self.connect( self.__debugger, SIGNAL( 'ClientThreadSet' ),
                      self.__onClientThreadSet )

        self.currentStack = None
        self.__createLayout()
        return

    def __createLayout( self ):
        " Creates the widget layout "

        verticalLayout = QVBoxLayout( self )
        verticalLayout.setContentsMargins( 1, 1, 1, 1 )

        self.splitter = QSplitter( Qt.Vertical )

        self.variablesViewer = VariablesViewer( self.__debugger,
                                                  self.splitter )
        self.stackViewer = StackViewer( self.__debugger, self.splitter )
        self.threadsViewer = ThreadsViewer( self.__debugger, self.splitter )

        self.splitter.addWidget( self.variablesViewer )
        self.splitter.addWidget( self.stackViewer )
        self.splitter.addWidget( self.threadsViewer )

        self.splitter.setCollapsible( 0, False )
        self.splitter.setCollapsible( 1, False )
        self.splitter.setCollapsible( 2, False )

        verticalLayout.addWidget( self.splitter )
        return

    def clear( self ):
        " Clears everything "
        self.variablesViewer.clear()
        self.stackViewer.clear()
        self.threadsViewer.clear()
        return

    def __onClientLine( self, fileName, line, forStack ):
        " Handles the signal from the debugged program "
        if not forStack:
            self.__debugger.remoteThreadList()
            self.__debugger.remoteClientVariables( 1, 0 )  # globals
            self.__debugger.remoteClientVariables( 0, 0 )  # locals
        return

    def onClientStack( self, stack ):
        " Handles the signal from the debugged program "
        self.stackViewer.populate( stack )
        return

    def __onClientThreadList( self, currentThreadID, threadList ):
        " Handles the thread list from the remote client "
        self.threadsViewer.populate( currentThreadID, threadList )
        return

    def __onClientVariables( self, scope, variables ):
        " Handles the client variables lists "
        frameNumber = self.stackViewer.getFrameNumber()
        if scope in [ -1, 0 ]:
            # Empty list for local variables
            self.variablesViewer.updateVariables( False, frameNumber, variables )
        else:
            self.variablesViewer.updateVariables( True, frameNumber, variables )
        return

    def __onClientVariable( self, scope, variables ):
        " Handles the client variable list "
        if scope in [ -1, 0 ]:
            self.variablesViewer.updateVariable( False, variables )
        else:
            self.variablesViewer.updateVariable( True, variables )
        return

    def __onClientThreadSet( self ):
        " Handles the event of setting the current thread by the client "
        self.__debugger.remoteClientVariables( 1, 0 )   # globals
        self.__debugger.remoteClientVariables( 0, 0 )   # locals
        return

    def switchControl( self, isInIDE ):
        " Switches the UI depending where the control flow is "
        self.variablesViewer.switchControl( isInIDE )
        self.stackViewer.switchControl( isInIDE )
        self.threadsViewer.switchControl( isInIDE )
        return

    def getCurrentFrameNumber( self ):
        " Provides the current frame number "
        return self.stackViewer.getFrameNumber()

