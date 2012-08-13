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

" Profiling results widget "

from proftable import ProfileTableViewer
from profgraph import ProfileGraphViewer
from ui.mainwindowtabwidgetbase import MainWindowTabWidgetBase
from PyQt4.QtCore import Qt, SIGNAL, QSize
from PyQt4.QtGui import QWidget, QToolBar, QHBoxLayout, QAction
from utils.pixmapcache import PixmapCache



class ProfileResultsWidget( QWidget, MainWindowTabWidgetBase ):
    " Profiling results widget "

    def __init__( self, scriptName, dataFile, parent = None ):

        MainWindowTabWidgetBase.__init__( self )
        QWidget.__init__( self, parent )

        self.__profTable = ProfileTableViewer( scriptName, dataFile )
        self.__profGraph = ProfileGraphViewer()
        self.__profTable.hide()

        self.connect( self.__profTable, SIGNAL( 'ESCPressed' ),
                      self.__onEsc )
        self.connect( self.__profGraph, SIGNAL( 'ESCPressed' ),
                      self.__onEsc )

        self.__createLayout()
        return

    def __createLayout( self ):
        " Creates the toolbar and layout "

        # Buttons
        self.__toggleViewButton = QAction( PixmapCache().getIcon( 'tableview.png' ),
                                           'Switch to table view', self )
        self.__toggleViewButton.setCheckable( True )
        self.connect( self.__toggleViewButton, SIGNAL( 'toggled(bool)' ),
                      self.__switchView )

        printButton = QAction( PixmapCache().getIcon( 'printer.png' ),
                               'Print', self )
        self.connect( printButton, SIGNAL( 'triggered()' ),
                      self.__onPrint )

        printPreviewButton = QAction( \
                PixmapCache().getIcon( 'printpreview.png' ),
                'Print preview', self )
        self.connect( printPreviewButton, SIGNAL( 'triggered()' ),
                      self.__onPrintPreview )

        fixedSpacer = QWidget()
        fixedSpacer.setFixedHeight( 16 )

        zoomInButton = QAction( PixmapCache().getIcon( 'zoomin.png' ),
                                'Zoom in (Ctrl+=)', self )
        zoomInButton.setShortcut( 'Ctrl+=' )
        self.connect( zoomInButton, SIGNAL( 'triggered()' ), self.onZoomIn )

        zoomOutButton = QAction( PixmapCache().getIcon( 'zoomout.png' ),
                                'Zoom out (Ctrl+-)', self )
        zoomOutButton.setShortcut( 'Ctrl+-' )
        self.connect( zoomOutButton, SIGNAL( 'triggered()' ), self.onZoomOut )

        zoomResetButton = QAction( PixmapCache().getIcon( 'zoomreset.png' ),
                                   'Zoom reset (Ctrl+0)', self )
        zoomResetButton.setShortcut( 'Ctrl+0' )
        self.connect( zoomResetButton, SIGNAL( 'triggered()' ),
                      self.onZoomReset )


        # Toolbar
        toolbar = QToolBar( self )
        toolbar.setOrientation( Qt.Vertical )
        toolbar.setMovable( False )
        toolbar.setAllowedAreas( Qt.RightToolBarArea )
        toolbar.setIconSize( QSize( 16, 16 ) )
        toolbar.setFixedWidth( 28 )
        toolbar.setContentsMargins( 0, 0, 0, 0 )

        toolbar.addAction( self.__toggleViewButton )
        toolbar.addAction( printPreviewButton )
        toolbar.addAction( printButton )
        toolbar.addWidget( fixedSpacer )
        toolbar.addAction( zoomInButton )
        toolbar.addAction( zoomOutButton )
        toolbar.addAction( zoomResetButton )

        hLayout = QHBoxLayout()
        hLayout.setContentsMargins( 0, 0, 0, 0 )
        hLayout.setSpacing( 0 )
        hLayout.addWidget( self.__profTable )
        hLayout.addWidget( self.__profGraph )
        hLayout.addWidget( toolbar )

        self.setLayout( hLayout )
        return

    def setFocus( self ):
        " Overriden setFocus "
        if self.__profTable.isVisible():
            self.__profTable.setFocus()
        else:
            self.__profGraph.setFocus()
        return

    def __onEsc( self ):
        " Triggered when Esc is pressed "
        self.emit( SIGNAL( 'ESCPressed' ) )
        return

    def __switchView( self, state ):
        " Triggered when view is to be switched "
        if state:
            self.__profGraph.hide()
            self.__profTable.show()
            self.__toggleViewButton.setIcon( PixmapCache().getIcon( 'treeview.png' ) )
            self.__toggleViewButton.setToolTip( 'Switch to diagram view' )
        else:
            self.__profTable.hide()
            self.__profGraph.show()
            self.__toggleViewButton.setIcon( PixmapCache().getIcon( 'tableview.png' ) )
            self.__toggleViewButton.setToolTip( 'Switch to table view' )
        return

    def __onPrint( self ):
        " Triggered on the 'print' button "
        pass

    def __onPrintPreview( self ):
        " Triggered on the 'print preview' button "
        pass

    def onZoomIn( self ):
        " Triggered on the 'zoom in' button "
        self.__profGraph.zoomIn()
        return

    def onZoomOut( self ):
        " Triggered on the 'zoom out' button "
        self.__profGraph.zoomOut()
        return

    def onZoomReset( self ):
        " Triggered on the 'zoom reset' button "
        self.__profGraph.resetZoom()
        return



    # Mandatory interface part is below

    def isModified( self ):
        " Tells if the file is modified "
        return False

    def getRWMode( self ):
        " Tells if the file is read only "
        return "RO"

    def getType( self ):
        " Tells the widget type "
        return MainWindowTabWidgetBase.ProfileViewer

    def getLanguage( self ):
        " Tells the content language "
        return "Profiler"

    def getFileName( self ):
        " Tells what file name of the widget content "
        return "N/A"

    def setFileName( self, name ):
        " Sets the file name - not applicable"
        raise Exception( "Setting a file name for profile results is not applicable" )

    def getEol( self ):
        " Tells the EOL style "
        return "N/A"

    def getLine( self ):
        " Tells the cursor line "
        return "N/A"

    def getPos( self ):
        " Tells the cursor column "
        return "N/A"

    def getEncoding( self ):
        " Tells the content encoding "
        return "N/A"

    def setEncoding( self, newEncoding ):
        " Sets the new encoding - not applicable for the profiler results viewer "
        return

    def getShortName( self ):
        " Tells the display name "
        return "Profiling results"

    def setShortName( self, name ):
        " Sets the display name - not applicable "
        raise Exception( "Setting a file name for profiler results is not applicable" )

