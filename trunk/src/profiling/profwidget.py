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

import pstats
from proftable import ProfileTableViewer
from profgraph import ProfileGraphViewer
from ui.mainwindowtabwidgetbase import MainWindowTabWidgetBase
from PyQt4.QtCore import Qt, SIGNAL, QSize
from PyQt4.QtGui import QWidget, QToolBar, QHBoxLayout, QAction
from utils.pixmapcache import PixmapCache



class ProfileResultsWidget( QWidget, MainWindowTabWidgetBase ):
    " Profiling results widget "

    def __init__( self, scriptName, params, reportTime, dataFile, parent = None ):

        MainWindowTabWidgetBase.__init__( self )
        QWidget.__init__( self, parent )

        # The same stats object is needed for both - a table and a graph
        # So, parse profile output once and then pass the object further
        stats = pstats.Stats( dataFile )
        stats.calc_callees()

        self.__profTable = ProfileTableViewer( scriptName, params, reportTime,
                                               dataFile, stats, self )
        self.__profGraph = ProfileGraphViewer( scriptName, params, reportTime,
                                               dataFile, stats, self )
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

        self.__togglePathButton = QAction( PixmapCache().getIcon( 'longpath.png' ),
                                           'Show full paths for item location', self )
        self.__togglePathButton.setCheckable( True )
        self.connect( self.__togglePathButton, SIGNAL( 'toggled(bool)' ),
                      self.__togglePath )
        self.__togglePathButton.setEnabled( False )

        self.__printButton = QAction( PixmapCache().getIcon( 'printer.png' ),
                                      'Print', self )
        self.connect( self.__printButton, SIGNAL( 'triggered()' ),
                      self.__onPrint )
        self.__printButton.setEnabled( False )

        self.__printPreviewButton = QAction( \
                PixmapCache().getIcon( 'printpreview.png' ),
                'Print preview', self )
        self.connect( self.__printPreviewButton, SIGNAL( 'triggered()' ),
                      self.__onPrintPreview )
        self.__printPreviewButton.setEnabled( False )

        fixedSpacer = QWidget()
        fixedSpacer.setFixedHeight( 16 )

        self.__zoomInButton = QAction( PixmapCache().getIcon( 'zoomin.png' ),
                                       'Zoom in (Ctrl+=)', self )
        self.__zoomInButton.setShortcut( 'Ctrl+=' )
        self.connect( self.__zoomInButton, SIGNAL( 'triggered()' ), self.onZoomIn )

        self.__zoomOutButton = QAction( PixmapCache().getIcon( 'zoomout.png' ),
                                        'Zoom out (Ctrl+-)', self )
        self.__zoomOutButton.setShortcut( 'Ctrl+-' )
        self.connect( self.__zoomOutButton, SIGNAL( 'triggered()' ), self.onZoomOut )

        self.__zoomResetButton = QAction( PixmapCache().getIcon( 'zoomreset.png' ),
                                          'Zoom reset (Ctrl+0)', self )
        self.__zoomResetButton.setShortcut( 'Ctrl+0' )
        self.connect( self.__zoomResetButton, SIGNAL( 'triggered()' ),
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
        toolbar.addAction( self.__togglePathButton )
        toolbar.addAction( self.__printPreviewButton )
        toolbar.addAction( self.__printButton )
        toolbar.addWidget( fixedSpacer )
        toolbar.addAction( self.__zoomInButton )
        toolbar.addAction( self.__zoomOutButton )
        toolbar.addAction( self.__zoomResetButton )

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
            self.__toggleViewButton.setIcon( PixmapCache().getIcon( 'profdgmview.png' ) )
            self.__toggleViewButton.setToolTip( 'Switch to diagram view' )
            self.__zoomInButton.setEnabled( False )
            self.__zoomOutButton.setEnabled( False )
            self.__zoomResetButton.setEnabled( False )
            self.__togglePathButton.setEnabled( True )
            self.__profTable.setFocus()
        else:
            self.__profTable.hide()
            self.__profGraph.show()
            self.__toggleViewButton.setIcon( PixmapCache().getIcon( 'tableview.png' ) )
            self.__toggleViewButton.setToolTip( 'Switch to table view' )
            self.__zoomInButton.setEnabled( True )
            self.__zoomOutButton.setEnabled( True )
            self.__zoomResetButton.setEnabled( True )
            self.__togglePathButton.setEnabled( False )
            self.__profGraph.setFocus()
        return

    def __togglePath( self, state ):
        " Triggered when full path/file name is switched "
        self.__profTable.togglePath( state )
        if state:
            self.__togglePathButton.setIcon( PixmapCache().getIcon( 'shortpath.png' ) )
            self.__togglePathButton.setToolTip( 'Show file names only for item location' )
        else:
            self.__togglePathButton.setIcon( PixmapCache().getIcon( 'longpath.png' ) )
            self.__togglePathButton.setToolTip( 'Show full paths for item location' )
        return

    def __onPrint( self ):
        " Triggered on the 'print' button "
        pass

    def __onPrintPreview( self ):
        " Triggered on the 'print preview' button "
        pass

    def isZoomApplicable( self ):
        " Should the zoom menu items be available "
        return self.__profGraph.isVisible()

    def onZoomIn( self ):
        " Triggered on the 'zoom in' button "
        if self.__profGraph.isVisible():
            self.__profGraph.zoomIn()
        return

    def onZoomOut( self ):
        " Triggered on the 'zoom out' button "
        if self.__profGraph.isVisible():
            self.__profGraph.zoomOut()
        return

    def onZoomReset( self ):
        " Triggered on the 'zoom reset' button "
        if self.__profGraph.isVisible():
            self.__profGraph.resetZoom()
        return

    def isCopyAvailable( self ):
        " Tells id the main menu copy item should be switched on "
        return self.__profGraph.isVisible()

    def isDiagramActive( self ):
        " Tells if the diagram is active "
        return self.__profGraph.isVisible()

    def onCopy( self ):
        " Ctrl+C triggered "
        if self.__profGraph.isVisible():
            self.__profGraph.onCopy()
        return

    def onSaveAs( self, fileName ):
        " Saves the diagram into a file "
        if self.__profGraph.isVisible():
            self.__profGraph.onSaveAs( fileName )
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

