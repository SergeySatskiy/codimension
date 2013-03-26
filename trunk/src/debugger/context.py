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
from namespacesviewer import NamespacesViewer

from PyQt4.QtCore import Qt, SIGNAL, QStringList, QEventLoop
from PyQt4.QtGui import ( QSizePolicy, QSizePolicy, QFrame, QTreeWidget,
                          QApplication, QTreeWidgetItem, QHeaderView,
                          QVBoxLayout, QLabel, QWidget, QApplication,
                          QAbstractItemView, QHeaderView, QSizePolicy,
                          QSplitter )
from utils.globals import GlobalData
import os.path


class DebuggerContext( QWidget ):
    " Implements the debugger context viewer "

    def __init__( self, debugger, parent = None ):
        QWidget.__init__( self, parent )
        self.__debugger = debugger
        self.__createLayout()
        return

    def __createLayout( self ):
        " Creates the widget layout "

        verticalLayout = QVBoxLayout( self )
        verticalLayout.setContentsMargins( 1, 1, 1, 1 )

        self.splitter = QSplitter( Qt.Vertical )

        self.__namespacesViewer = NamespacesViewer( self.splitter )
        self.__stackViewer = StackViewer( self.splitter )
        self.__threadsViewer = ThreadsViewer( self.splitter )

        self.splitter.addWidget( self.__namespacesViewer )
        self.splitter.addWidget( self.__stackViewer )
        self.splitter.addWidget( self.__threadsViewer )

        self.splitter.setCollapsible( 0, False )
        self.splitter.setCollapsible( 1, False )
        self.splitter.setCollapsible( 2, False )

        verticalLayout.addWidget( self.splitter )
        return

