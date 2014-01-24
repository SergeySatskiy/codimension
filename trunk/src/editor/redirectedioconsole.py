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
                          QAction, QSizePolicy, QToolTip, QMenu, QToolButton,
                          QActionGroup )
from PyQt4.Qsci import QsciScintilla
from ui.mainwindowtabwidgetbase import MainWindowTabWidgetBase
from utils.fileutils import TexFileType
from utils.pixmapcache import PixmapCache
from utils.globals import GlobalData
from utils.settings import Settings



class RedirectedIOConsole( TextEditor ):

    TIMESTAMP_MARGIN = 0     # Introduced here

    def __init__( self, parent ):
        self.__maxLength = None

        TextEditor.__init__( self, parent, None )
        self.__initGeneralSettings()
        self.__initMargins()

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

        self.SendScintilla( self.SCI_SETCARETSTYLE, self.CARETSTYLE_BLOCK )
        self.SendScintilla( self.SCI_SETCARETPERIOD, 750 )
        self.setEdgeMode( QsciScintilla.EdgeNone )
        return

    def __initMargins( self ):
        " Initializes the editor margins "

        # The supported margins: timestamp

        # reset standard margins settings
        for margin in xrange( 5 ):
            self.setMarginLineNumbers( margin, False )
            self.setMarginMarkerMask( margin, 0 )
            self.setMarginWidth( margin, 0 )
            self.setMarginSensitivity( margin, False )

        skin = GlobalData().skin
        self.setMarginsBackgroundColor( skin.ioconsolemarginPaper )
        self.setMarginsForegroundColor( skin.ioconsolemarginColor )

        # Set margin 0 for timestamps
        self.setMarginsFont( skin.ioconsolemarginFont )
        self.setTimestampMarginWidth()
        return

    def __initIDEMessageMarker( self ):
        " Initializes the marker used for the IDE messages "
        skin = GlobalData().skin
        self.__ideMessageMarker = self.markerDefine( QsciScintilla.Background )
        self.setMarkerBackgroundColor( skin.ioconsoleIDEMsgPaper,
                                       self.__ideMessageMarker )
        return

    def _marginClicked( self, margin, line, modifiers ):
        return

    def _updateDwellingTime( self ):
        " There is always something to show "
        self.SendScintilla( self.SCI_SETMOUSEDWELLTIME, 250 )
        return

    def _onDwellStart( self, position, x, y ):
        " Triggered when mouse started to dwell "
        if not self.underMouse():
            return

        marginNumber = self._marginNumber( x )
        if marginNumber == self.TIMESTAMP_MARGIN:
            self.__showTimestampTooltip( position, x, y )
            return

        TextEditor._onDwellStart( self, position, x, y )
        return

    def __showTimestampTooltip( self, position, x, y ):
        # Calculate the line
        pos = self.SendScintilla( self.SCI_POSITIONFROMPOINT, x, y )
        line, posInLine = self.lineIndexFromPosition( pos )

        tooltip = self.__getTimestampMarginTooltip( line )
        if not tooltip:
            return

        QToolTip.showText( self.mapToGlobal( QPoint( x, y ) ), tooltip )
        self.__timestampTooltipShown = True
        return

    def __getTimestampMarginTooltip( self, line ):
        return None

    def _onDwellEnd( self, position, x, y ):
        " Triggered when mouse ended to dwell "
        if self.__timestampTooltipShown:
            self.__timestampTooltipShown = False
            QToolTip.hideText()
        return

    def _initContextMenu( self ):
        " Called to initialize a context menu "
        return

    def setTimestampMarginWidth( self ):
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
        self.__printButton = QAction( PixmapCache().getIcon( 'printer.png' ),
                                      'Print', self )
        self.connect( self.__printButton, SIGNAL( 'triggered()' ),
                      self.__onPrint )
        self.__printButton.setEnabled( False )
        self.__printButton.setVisible( False )

        self.__printPreviewButton = QAction(
                                PixmapCache().getIcon( 'printpreview.png' ),
                                'Print preview', self )
        self.connect( self.__printPreviewButton, SIGNAL( 'triggered()' ),
                      self.__onPrintPreview )
        self.__printPreviewButton.setEnabled( False )
        self.__printPreviewButton.setVisible( False )

        self.__sendUpButton = QAction( PixmapCache().getIcon( 'sendioup.png' ),
                                       'Send to Main Editing Area', self )
        self.connect( self.__sendUpButton, SIGNAL( "triggered()" ),
                      self.__sendUp )

        self.__selectAllButton = QAction(
                                    PixmapCache().getIcon( 'selectall.png' ),
                                    'Select all', self )
        self.connect( self.__selectAllButton, SIGNAL( "triggered()" ),
                      self.__onSelectAll )
        self.__copyButton = QAction(
                                PixmapCache().getIcon( 'copytoclipboard.png' ),
                                'Copy to clipboard', self )
        self.connect( self.__copyButton, SIGNAL( "triggered()" ),
                      self.__onCopy )

        self.__filterMenu = QMenu( self )
        self.connect( self.__filterMenu, SIGNAL( "aboutToShow()" ),
                      self.__filterAboutToShow )
        self.__filterGroup = QActionGroup( self )
        self.__filterShowAllAct = self.__filterMenu.addAction( "Show all" )
        self.__filterShowAllAct.setCheckable( True )
        self.__filterShowAllAct.setActionGroup( self.__filterGroup )
        self.connect( self.__filterShowAllAct, SIGNAL( 'triggered()' ),
                      self.__onFilterShowAll )
        self.__filterShowStdoutAct = self.__filterMenu.addAction( "Show stdin and stdout" )
        self.__filterShowStdoutAct.setCheckable( True )
        self.__filterShowStdoutAct.setActionGroup( self.__filterGroup )
        self.connect( self.__filterShowStdoutAct, SIGNAL( 'triggered()' ),
                      self.__onFilterShowStdout )
        self.__filterShowStderrAct = self.__filterMenu.addAction( "Show stdin and stderr" )
        self.__filterShowStderrAct.setCheckable( True )
        self.__filterShowStderrAct.setActionGroup( self.__filterGroup )
        self.connect( self.__filterShowStderrAct, SIGNAL( 'triggered()' ),
                      self.__onFilterShowStderr )
        self.__filterButton = QToolButton( self )
        self.__filterButton.setIcon( PixmapCache().getIcon( 'iofilter.png' ) )
        self.__filterButton.setToolTip( 'Filtering settings' )
        self.__filterButton.setPopupMode( QToolButton.InstantPopup )
        self.__filterButton.setMenu( self.__filterMenu )
        self.__filterButton.setFocusPolicy( Qt.NoFocus )

        self.__settingsMenu = QMenu( self )
        self.connect( self.__settingsMenu, SIGNAL( "aboutToShow()" ),
                      self.__settingsAboutToShow )
        self.__wrapLongLinesAct = self.__settingsMenu.addAction( "Wrap long lines" )
        self.__wrapLongLinesAct.setCheckable( True )
        self.connect( self.__wrapLongLinesAct, SIGNAL( 'triggered()' ),
                      self.__onWrapLongLines )
        self.__showEOLAct = self.__settingsMenu.addAction( "Show EOL" )
        self.__showEOLAct.setCheckable( True )
        self.connect( self.__showEOLAct, SIGNAL( 'triggered()' ),
                      self.__onShowEOL )
        self.__showWhitespacesAct = self.__settingsMenu.addAction( "Show whitespaces" )
        self.__showWhitespacesAct.setCheckable( True )
        self.connect( self.__showWhitespacesAct, SIGNAL( 'triggered()' ),
                      self.__onShowWhitespaces )
        self.__autoscrollAct = self.__settingsMenu.addAction( "Autoscroll" )
        self.__autoscrollAct.setCheckable( True )
        self.connect( self.__autoscrollAct, SIGNAL( 'triggered()' ),
                      self.__onAutoscroll )
        self.__showMarginAct = self.__settingsMenu.addAction( "Show timestamp margin" )
        self.__showMarginAct.setCheckable( True )
        self.connect( self.__showMarginAct, SIGNAL( 'triggered()' ),
                      self.__onShowMargin )

        self.__settingsButton = QToolButton( self )
        self.__settingsButton.setIcon( PixmapCache().getIcon( 'iosettings.png' ) )
        self.__settingsButton.setToolTip( 'View settings' )
        self.__settingsButton.setPopupMode( QToolButton.InstantPopup )
        self.__settingsButton.setMenu( self.__settingsMenu )
        self.__settingsButton.setFocusPolicy( Qt.NoFocus )

        spacer = QWidget()
        spacer.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )
        self.__clearButton = QAction( PixmapCache().getIcon( 'trash.png' ),
                                      'Clear', self )
        self.connect( self.__clearButton, SIGNAL( "triggered()" ),
                      self.__clear )

        # The toolbar
        toolbar = QToolBar( self )
        toolbar.setOrientation( Qt.Vertical )
        toolbar.setMovable( False )
        toolbar.setAllowedAreas( Qt.RightToolBarArea )
        toolbar.setIconSize( QSize( 16, 16 ) )
        toolbar.setFixedWidth( 28 )
        toolbar.setContentsMargins( 0, 0, 0, 0 )

        toolbar.addAction( self.__sendUpButton )
        toolbar.addAction( self.__printPreviewButton )
        toolbar.addAction( self.__printButton )
        toolbar.addAction( self.__selectAllButton )
        toolbar.addAction( self.__copyButton )
        toolbar.addWidget( self.__filterButton )
        toolbar.addWidget( self.__settingsButton )
        toolbar.addWidget( spacer )
        toolbar.addAction( self.__clearButton )

        hLayout = QHBoxLayout()
        hLayout.setContentsMargins( 0, 0, 0, 0 )
        hLayout.setSpacing( 0 )
        hLayout.addWidget( toolbar )
        hLayout.addWidget( self.__viewer )

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

    def __sendUp( self ):
        " Triggered when requested to move the console up "
        return

    def __onSelectAll( self ):
        " Triggered when select all is clicked "
        return

    def __onCopy( self ):
        " Triggered when copy is clicked "
        return

    def __filterAboutToShow( self ):
        " Triggered when filter menu is about to show "
        showAll = Settings().ioconsoleshowstdin and \
                  Settings().ioconsoleshowstdout and \
                  Settings().ioconsoleshowstderr
        onlyStdout = not Settings().ioconsoleshowstdin and \
                     Settings().ioconsoleshowstdout and \
                     not Settings().ioconsoleshowstderr
        onlyStderr = not Settings().ioconsoleshowstdin and \
                     not Settings().ioconsoleshowstdout and \
                     Settings().ioconsoleshowstderr
        self.__filterShowAllAct.setChecked( showAll )
        self.__filterShowStdoutAct.setChecked( onlyStdout )
        self.__filterShowStderrAct.setChecked( onlyStderr )
        return

    def __onFilterShowAll( self ):
        " Triggered when filter show all is clicked "
        Settings().ioconsoleshowstdin = True
        Settings().ioconsoleshowstdout = True
        Settings().ioconsoleshowstderr = True
        return

    def __onFilterShowStdout( self ):
        " Triggered when filter show stdout only is clicked "
        Settings().ioconsoleshowstdin = True
        Settings().ioconsoleshowstdout = True
        Settings().ioconsoleshowstderr = False
        return

    def __onFilterShowStderr( self ):
        " Triggered when filter show stderr only is clicked "
        Settings().ioconsoleshowstdin = True
        Settings().ioconsoleshowstdout = False
        Settings().ioconsoleshowstderr = True
        return

    def __settingsAboutToShow( self ):
        " Settings menu is about to show "
        self.__wrapLongLinesAct.setChecked( Settings().ioconsolelinewrap )
        self.__showEOLAct.setChecked( Settings().ioconsoleshoweol )
        self.__showWhitespacesAct.setChecked( Settings().ioconsoleshowspaces )
        self.__autoscrollAct.setChecked( Settings().ioconsoleautoscroll )
        self.__showMarginAct.setChecked( Settings().ioconsoleshowmargin )
        return

    def __onWrapLongLines( self ):
        " Triggered when long lines setting is changed "
        Settings().ioconsolelinewrap = not Settings().ioconsolelinewrap
        return

    def __onShowEOL( self ):
        " Triggered when show EOL is changed "
        Settings().ioconsoleshoweol = not Settings().ioconsoleshoweol
        return

    def __onShowWhitespaces( self ):
        " Triggered when show whitespaces is changed "
        Settings().ioconsoleshowspaces = not Settings().ioconsoleshowspaces
        return

    def __onAutoscroll( self ):
        " Triggered when autoscroll is changed "
        Settings().ioconsoleautoscroll = not Settings().ioconsoleautoscroll
        return

    def __onShowMargin( self ):
        " Triggered when show margin is changed "
        Settings().ioconsoleshowmargin = not Settings().ioconsoleshowmargin
        return

    def __clear( self ):
        " Triggered when requested to clear the console "
        return



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
