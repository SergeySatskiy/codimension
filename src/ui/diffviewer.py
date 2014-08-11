#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2011  Sergey Satskiy <sergey.satskiy@gmail.com>
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

""" The diff viewer implementation """

from PyQt4.QtCore import Qt, QSize
from PyQt4.QtGui import ( QHBoxLayout, QWidget, QAction, QToolBar,
                          QSizePolicy, QVBoxLayout )
from utils.pixmapcache import PixmapCache
from htmltabwidget import HTMLTabWidget
from utils.globals import GlobalData
from utils.settings import Settings


class DiffViewer( QWidget ):
    """ The diff viewer widget at the bottom """

    NODIFF = '<html><body bgcolor="#ffffe6"></body></html>'

    def __init__( self, parent = None ):
        QWidget.__init__( self, parent )

        self.viewer = None
        self.__clearButton = None
        self.__sendUpButton = None
        self.__createLayout()
        self.__isEmpty = True
        self.__tooltip = ""
        self.__inClear = False

        self.viewer.setHTML( self.NODIFF )
        self.__updateToolbarButtons()
        return

    def __createLayout( self ):
        " Helper to create the viewer layout "

        self.viewer = HTMLTabWidget()

        # Buttons
        self.__sendUpButton = QAction(
            PixmapCache().getIcon( 'senddiffup.png' ),
            'Send to Main Editing Area', self )
        self.__sendUpButton.triggered.connect( self.__sendUp )
        spacer = QWidget()
        spacer.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )
        self.__clearButton = QAction(
            PixmapCache().getIcon( 'trash.png' ),
            'Clear Generated Diff', self )
        self.__clearButton.triggered.connect( self.__clear )

        # Toolbar
        self.toolbar = QToolBar()
        self.toolbar.setOrientation( Qt.Vertical )
        self.toolbar.setMovable( False )
        self.toolbar.setAllowedAreas( Qt.LeftToolBarArea )
        self.toolbar.setIconSize( QSize( 16, 16 ) )
        self.toolbar.setFixedWidth( 28 )
        self.toolbar.setContentsMargins( 0, 0, 0, 0 )
        self.toolbar.addAction( self.__sendUpButton )
        self.toolbar.addWidget( spacer )
        self.toolbar.addAction( self.__clearButton )

        verticalLayout = QVBoxLayout()
        verticalLayout.setContentsMargins( 2, 2, 2, 2 )
        verticalLayout.setSpacing( 2 )
        verticalLayout.addWidget( self.viewer )

        # layout
        layout = QHBoxLayout()
        layout.setContentsMargins( 0, 0, 0, 0 )
        layout.setSpacing( 0 )
        layout.addWidget( self.toolbar )
        layout.addLayout( verticalLayout )

        self.setLayout( layout )
        return

    def setHTML( self, content, tooltip ):
        """ Shows the given content """
        if self.__inClear:
            self.viewer.setHTML( content )
            self.viewer.zoomTo( Settings().zoom )
            return

        if content == '' or content is None:
            self.__clear()
        else:
            self.viewer.setHTML( content )
            self.viewer.zoomTo( Settings().zoom )
            self.__isEmpty = False
            self.__updateToolbarButtons()
            self.__tooltip = tooltip
        return

    def zoomTo( self, zoomValue ):
        " Sets the required zoom "
        self.viewer.zoomTo( zoomValue )
        return

    def __sendUp( self ):
        """ Triggered when the content should be sent
            to the main editor area """
        if not self.__isEmpty:
            GlobalData().mainWindow.showDiffInMainArea( self.viewer.getHTML(),
                                                        self.__tooltip )
        return

    def __clear( self ):
        """ Triggered when the content should be cleared """
        self.__inClear = True
        # Dirty hack - reset the tooltip
        GlobalData().mainWindow.showDiff( "", "No diff shown" )
        self.viewer.setHTML( DiffViewer.NODIFF )
        self.__inClear = False

        self.__isEmpty = True
        self.__tooltip = ""
        self.__updateToolbarButtons()
        return

    def __updateToolbarButtons( self ):
        " Contextually updates toolbar buttons "
        self.__sendUpButton.setEnabled( not self.__isEmpty )
        self.__clearButton.setEnabled( not self.__isEmpty )
        return
