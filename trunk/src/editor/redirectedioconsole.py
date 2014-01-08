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

" Redirected IO console implementation "


from texteditor import TextEditor
from PyQt4.QtCore import Qt, SIGNAL, QSize, QPoint
from PyQt4.QtGui import ( QToolBar, QFont, QFontMetrics, QHBoxLayout, QWidget,
                          QAction, QSizePolicy, QToolTip )
from PyQt4.Qsci import QsciScintilla
from ui.mainwindowtabwidgetbase import MainWindowTabWidgetBase
from utils.fileutils import TexFileType
from utils.pixmapcache import PixmapCache
from utils.globals import GlobalData
from utils.settings import Settings
from ui.importlist import ImportListWidget



class RedirectedIOConsole( TextEditor ):

    TIMESTAMP_MARGIN = 1     # Introduced here

    def __init__( self, parent ):
        self.__maxLength = None

        TextEditor.__init__( self, parent, None )
        self.__initGeneralSettings()

        self.__timestampTooltipShown = False
        self.__initIDEMessageMarker()
        self._updateDwellingTime()
        return

    def __initGeneralSettings( self ):
        " Sets some generic look and feel "
        skin = GlobalData().skin

        self.setPaper( skin.ioconsolePaper )
        self.setColor( skin.ioconsoleColor )

        self.setModified( False )
        self.setReadOnly( True )
        self.bindLexer( "", TexFileType )
        return

    def __initIDEMessageMarker( self ):
        " Initializes the marker used for the IDE messages "
        skin = GlobalData().skin
        self.__ideMessageMarker = self.markerDefine( QsciScintilla.Background )
        self.setMarkerBackgroundColor( skin.ioconsoleIDEMsgPaper,
                                       self.__ideMessageMarker )
        return

    def detectRevisionMarginWidth( self ):
        """ Caculates the margin width depending on
            the margin font and the current zoom """
        skin = GlobalData().skin
        font = QFont( skin.lineNumFont )
        font.setPointSize( font.pointSize() + self.getZoom() )
        fontMetrics = QFontMetrics( font, self )
        return fontMetrics.width( 'W' * self.__maxLength ) + 3

    def setRevisionMarginWidth( self ):
        " Called when zooming is done to keep the width wide enough "
        if self.__maxLength:
            self.setMarginWidth( self.REVISION_MARGIN,
                                 self.detectRevisionMarginWidth() )
        else:
            self.setMarginWidth( self.REVISION_MARGIN, 0 )
        return

    def __initAnnotateMargins( self ):
        " Initializes the editor margins "
        self.setMarginType( self.REVISION_MARGIN, self.TextMargin )
        self.setMarginMarkerMask( self.REVISION_MARGIN, 0 )

        # Together with overriding _marginClicked(...) this
        # prevents selecting a line when the margin is clicked.
        self.setMarginSensitivity( self.REVISION_MARGIN, True )
        return

    def _marginClicked( self, margin, line, modifiers ):
        return

    def __getRevisionMarginTooltip( self, lineNumber ):
        " lineNumber is zero based "
        revisionNumber = self.__lineRevisions[ lineNumber ]
        if not revisionNumber in self.__revisionInfo:
            return None

        tooltip = "Revision: " + \
                    str( revisionNumber ) + "\n" \
                  "Author: " + \
                    self.__revisionInfo[ revisionNumber ][ 'author' ] + "\n" \
                  "Date: " + \
                    str( self.__revisionInfo[ revisionNumber ][ 'date' ] )
        comment = self.__revisionInfo[ revisionNumber ][ 'message' ]
        if comment:
            tooltip += "\nComment: " + comment
        return tooltip

    def _updateDwellingTime( self ):
        " There is always something to show "
        self.SendScintilla( self.SCI_SETMOUSEDWELLTIME, 250 )
        return

    def _onDwellStart( self, position, x, y ):
        " Triggered when mouse started to dwell "
        if not self.underMouse():
            return

        marginNumber = self._marginNumber( x )
        if marginNumber == self.REVISION_MARGIN:
            self.__showRevisionTooltip( position, x, y )
            return

        TextEditor._onDwellStart( self, position, x, y )
        return

    def __showRevisionTooltip( self, position, x, y ):
        # Calculate the line
        pos = self.SendScintilla( self.SCI_POSITIONFROMPOINT, x, y )
        line, posInLine = self.lineIndexFromPosition( pos )

        tooltip = self.__getRevisionMarginTooltip( line )
        if not tooltip:
            return

        QToolTip.showText( self.mapToGlobal( QPoint( x, y ) ), tooltip )
        self.__timestampTooltipShown = True
        return

    def _onDwellEnd( self, position, x, y ):
        " Triggered when mouse ended to dwell "
        if self.__timestampTooltipShown:
            self.__timestampTooltipShown = False
            QToolTip.hideText()
        return

    def setLineNumMarginWidth( self ):
        self.setRevisionMarginWidth()
        return



class IOConsoleTabWidget( QWidget, MainWindowTabWidgetBase ):
    " IO console tab widget "

    def __init__( self, parent ):

        MainWindowTabWidgetBase.__init__( self )
        QWidget.__init__( self, parent )

        self.__viewer = RedirectedIOConsole( self )

        self.__createLayout()
        self.__viewer.zoomTo( Settings().zoom )
        return

    def __createLayout( self ):
        " Creates the toolbar and layout "

        # Buttons
        printButton = QAction( PixmapCache().getIcon( 'printer.png' ),
                               'Print', self )
        self.connect( printButton, SIGNAL( 'triggered()' ),
                      self.__onPrint )
        printButton.setEnabled( False )
        printButton.setVisible( False )

        printPreviewButton = QAction(
                PixmapCache().getIcon( 'printpreview.png' ),
                'Print preview', self )
        self.connect( printPreviewButton, SIGNAL( 'triggered()' ),
                      self.__onPrintPreview )
        printPreviewButton.setEnabled( False )
        printPreviewButton.setVisible( False )

        spacer = QWidget()
        spacer.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )

        self.lineCounterButton = QAction(
            PixmapCache().getIcon( 'linecounter.png' ),
            'Line counter', self )
        self.connect( self.lineCounterButton, SIGNAL( 'triggered()' ),
                      self.onLineCounter )

        # Zoom buttons
        # It was decided these buttons should be here
        #zoomInButton = QAction( PixmapCache().getIcon( 'zoomin.png' ),
        #                        'Zoom in (Ctrl+=)', self )
        #self.connect( zoomInButton, SIGNAL( 'triggered()' ), self.onZoomIn )

        #zoomOutButton = QAction( PixmapCache().getIcon( 'zoomout.png' ),
        #                        'Zoom out (Ctrl+-)', self )
        #self.connect( zoomOutButton, SIGNAL( 'triggered()' ), self.onZoomOut )

        #zoomResetButton = QAction( PixmapCache().getIcon( 'zoomreset.png' ),
        #                           'Zoom reset (Ctrl+0)', self )
        #self.connect( zoomResetButton, SIGNAL( 'triggered()' ),
        #              self.onZoomReset )

        #fixedSpacer = QWidget()
        #fixedSpacer.setFixedHeight( 16 )

        # The toolbar
        toolbar = QToolBar( self )
        toolbar.setOrientation( Qt.Vertical )
        toolbar.setMovable( False )
        toolbar.setAllowedAreas( Qt.RightToolBarArea )
        toolbar.setIconSize( QSize( 16, 16 ) )
        toolbar.setFixedWidth( 28 )
        toolbar.setContentsMargins( 0, 0, 0, 0 )

        toolbar.addAction( printPreviewButton )
        toolbar.addAction( printButton )
        toolbar.addWidget( spacer )
        toolbar.addAction( self.lineCounterButton )

        self.__importsBar = ImportListWidget( self.__viewer )
        self.__importsBar.hide()

        hLayout = QHBoxLayout()
        hLayout.setContentsMargins( 0, 0, 0, 0 )
        hLayout.setSpacing( 0 )
        hLayout.addWidget( self.__viewer )
        hLayout.addWidget( toolbar )

        self.setLayout( hLayout )
        return

    def onZoomReset( self ):
        " Triggered when the zoom reset button is pressed "
        if self.__viewer.zoom != 0:
            self.emit( SIGNAL( 'TextEditorZoom' ), 0 )
        return True

    def onZoomIn( self ):
        " Triggered when the zoom in button is pressed "
        if self.__viewer.zoom < 20:
            self.emit( SIGNAL( 'TextEditorZoom' ), self.__viewer.zoom + 1 )
        return True

    def onZoomOut( self ):
        " Triggered when the zoom out button is pressed "
        if self.__viewer.zoom > -10:
            self.emit( SIGNAL( 'TextEditorZoom' ), self.__viewer.zoom - 1 )
        return True

    def __onPrint( self ):
        " Triggered when the print button is pressed "
        pass

    def __onPrintPreview( self ):
        " triggered when the print preview button is pressed "
        pass

    def setFocus( self ):
        " Overridden setFocus "
        self.__viewer.setFocus()
        return

    def onOpenImport( self ):
        " Triggered when Ctrl+I is received "
        return True

    def resizeEvent( self, event ):
        QWidget.resizeEvent( self, event )
        return
    def onPylint( self ):
        return True
    def onPymetrics( self ):
        return True
    def onRunScript( self, action = False ):
        return True
    def onRunScriptSettings( self ):
        return True
    def onProfileScript( self, action = False ):
        return True
    def onProfileScriptSettings( self ):
        return True
    def onImportDgm( self, action = None ):
        return True
    def onImportDgmTuned( self ):
        return True
    def shouldAcceptFocus( self ):
        return True

    def writeFile( self, fileName ):
        " Writes the text to a file "
        return self.__viewer.writeFile( fileName )

    def updateModificationTime( self, fileName ):
        return

    # Mandatory interface part is below

    def getEditor( self ):
        " Provides the editor widget "
        return self.__viewer

    def isModified( self ):
        " Tells if the file is modified "
        return False

    def getRWMode( self ):
        " Tells if the file is read only "
        return "IO"

    def getFileType( self ):
        " Provides the file type "
        return TexFileType

    def setFileType( self, typeToSet ):
        """ Sets the file type explicitly.
            It needs e.g. for .cgi files which can change its type """
        raise Exception( "Setting a file type is not supported by the "
                         "IO console widget" )

    def getType( self ):
        " Tells the widget type "
        return MainWindowTabWidgetBase.IOConsole

    def getLanguage( self ):
        " Tells the content language "
        return "IO console"

    def getFileName( self ):
        " Tells what file name of the widget content "
        return "n/a"

    def setFileName( self, name ):
        " Sets the file name "
        raise Exception( "Setting a file name for IO console "
                         "is not applicable" )

    def getEol( self ):
        " Tells the EOL style "
        return self.__viewer.getEolIndicator()

    def getLine( self ):
        " Tells the cursor line "
        line, pos = self.__viewer.getCursorPosition()
        return int( line )

    def getPos( self ):
        " Tells the cursor column "
        line, pos = self.__viewer.getCursorPosition()
        return int( pos )

    def getEncoding( self ):
        " Tells the content encoding "
        return self.__viewer.encoding

    def setEncoding( self, newEncoding ):
        " Sets the new editor encoding "
        raise Exception( "Setting encoding is not supported by the "
                         "IO console widget" )
        return

    def getShortName( self ):
        " Tells the display name "
        return "IO console"

    def setShortName( self, name ):
        " Sets the display name "
        raise Exception( "Setting short name is not supported by the "
                         "IO console widget" )
        return
