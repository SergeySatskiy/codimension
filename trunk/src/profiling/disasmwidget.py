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

" Disassembler widget "

from ui.mainwindowtabwidgetbase import MainWindowTabWidgetBase
from PyQt4.QtCore import Qt, SIGNAL, QSize, QEvent
from PyQt4.QtGui import ( QWidget, QToolBar, QHBoxLayout, QAction,
                          QLabel, QFrame, QPalette, QVBoxLayout,
                          QTextEdit, QSizePolicy, QApplication, QFont )
from utils.pixmapcache import PixmapCache
from utils.globals import GlobalData
from utils.settings import Settings



class DisasmWidget( QTextEdit ):
    " Wraps QTextEdit to have a keyboard handler "

    def __init__( self, parent ):
        QTextEdit.__init__( self, parent )
        self.installEventFilter( self )
        return

    def eventFilter( self, obj, event ):
        " Event filter to catch shortcuts on UBUNTU "
        if event.type() == QEvent.KeyPress:
            key = event.key()
            modifiers = event.modifiers()
            if modifiers == Qt.ControlModifier:
                if key == Qt.Key_Minus:
                    return self.parent().onZoomOut()
                if key == Qt.Key_Equal:
                    return self.parent().onZoomIn()
                if key == Qt.Key_0:
                    return self.parent().onZoomReset()

        return QTextEdit.eventFilter( self, obj, event )

    def wheelEvent( self, event ):
        " Mouse wheel event "
        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            if event.delta() > 0:
                self.parent().onZoomIn()
            else:
                self.parent().onZoomOut()
        else:
            QTextEdit.wheelEvent( self, event )
        return



class DisassemblerResultsWidget( QWidget, MainWindowTabWidgetBase ):
    " Disassembling results widget "

    def __init__( self, scriptName, name, code, reportTime, parent = None ):

        MainWindowTabWidgetBase.__init__( self )
        QWidget.__init__( self, parent )

        self.__createLayout( scriptName, name, code, reportTime )
        return

    def __createLayout( self, scriptName, name, code, reportTime ):
        " Creates the toolbar and layout "

        # Buttons
        self.__printButton = QAction( PixmapCache().getIcon( 'printer.png' ),
                                      'Print', self )
        self.__printButton.triggered.connect( self.__onPrint )
        self.__printButton.setEnabled( False )
        self.__printButton.setVisible( False )

        self.__printPreviewButton = QAction(
                PixmapCache().getIcon( 'printpreview.png' ),
                'Print preview', self )
        self.__printPreviewButton.triggered.connect( self.__onPrintPreview )
        self.__printPreviewButton.setEnabled( False )
        self.__printPreviewButton.setVisible( False )

        # Zoom buttons
        self.__zoomInButton = QAction( PixmapCache().getIcon( 'zoomin.png' ),
                                       'Zoom in (Ctrl+=)', self )
        self.__zoomInButton.triggered.connect( self.onZoomIn )

        self.__zoomOutButton = QAction( PixmapCache().getIcon( 'zoomout.png' ),
                                        'Zoom out (Ctrl+-)', self )
        self.__zoomOutButton.triggered.connect( self.onZoomOut )

        self.__zoomResetButton = QAction( PixmapCache().getIcon( 'zoomreset.png' ),
                                          'Zoom reset (Ctrl+0)', self )
        self.__zoomResetButton.triggered.connect( self.onZoomReset )

        spacer = QWidget()
        spacer.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )

        # Toolbar
        toolbar = QToolBar( self )
        toolbar.setOrientation( Qt.Vertical )
        toolbar.setMovable( False )
        toolbar.setAllowedAreas( Qt.RightToolBarArea )
        toolbar.setIconSize( QSize( 16, 16 ) )
        toolbar.setFixedWidth( 28 )
        toolbar.setContentsMargins( 0, 0, 0, 0 )

        toolbar.addAction( self.__printPreviewButton )
        toolbar.addAction( self.__printButton )
        toolbar.addWidget( spacer )
        toolbar.addAction( self.__zoomInButton )
        toolbar.addAction( self.__zoomOutButton )
        toolbar.addAction( self.__zoomResetButton )

        summary = QLabel( "<b>Script:</b> " + scriptName + "<br>"
                          "<b>Name:</b> " + name + "<br>"
                          "<b>Disassembled at:</b> " + reportTime )
        summary.setFrameStyle( QFrame.StyledPanel )
        summary.setAutoFillBackground( True )
        summaryPalette = summary.palette()
        summaryBackground = summaryPalette.color( QPalette.Background )
        summaryBackground.setRgb( min( summaryBackground.red() + 30, 255 ),
                                  min( summaryBackground.green() + 30, 255 ),
                                  min( summaryBackground.blue() + 30, 255 ) )
        summaryPalette.setColor( QPalette.Background, summaryBackground )
        summary.setPalette( summaryPalette )

        self.__text = DisasmWidget( self )
        self.__text.setAcceptRichText( False )
        self.__text.setLineWrapMode( QTextEdit.NoWrap )
        self.__text.setFont( GlobalData().skin.nolexerFont )
        self.zoomTo( Settings().zoom )
        self.__text.setReadOnly( True )
        self.__text.setPlainText( code )

        vLayout = QVBoxLayout()
        vLayout.addWidget( summary )
        vLayout.addWidget( self.__text )

        hLayout = QHBoxLayout()
        hLayout.setContentsMargins( 0, 0, 0, 0 )
        hLayout.setSpacing( 0 )
        hLayout.addLayout( vLayout )
        hLayout.addWidget( toolbar )

        self.setLayout( hLayout )
        return

    def setFocus( self ):
        " Overriden setFocus "
        self.__text.setFocus()
        return

    def __onPrint( self ):
        " Triggered on the 'print' button "
        pass

    def __onPrintPreview( self ):
        " Triggered on the 'print preview' button "
        pass

    def onZoomReset( self ):
        " Triggered when the zoom reset button is pressed "
        zoom = Settings().zoom
        if zoom != 0:
            self.emit( SIGNAL( 'TextEditorZoom' ), 0 )
        return True

    def onZoomIn( self ):
        " Triggered when the zoom in button is pressed "
        zoom = Settings().zoom
        if zoom < 20:
            self.emit( SIGNAL( 'TextEditorZoom' ), zoom + 1 )
        return True

    def onZoomOut( self ):
        " Triggered when the zoom out button is pressed "
        zoom = Settings().zoom
        if zoom > -10:
            self.emit( SIGNAL( 'TextEditorZoom' ), zoom - 1 )
        return True

    def keyPressEvent( self, event ):
        " Handles the key press events "
        if event.key() == Qt.Key_Escape:
            self.emit( SIGNAL('ESCPressed') )
            event.accept()
        else:
            QWidget.keyPressEvent( self, event )
        return

    def zoomTo( self, zoomFactor ):
        " Scales the font in accordance to the given zoom factor "
        font = QFont( GlobalData().skin.nolexerFont )
        newPointSize = font.pointSize() + zoomFactor
        font.setPointSize( newPointSize )
        self.__text.setFont( font )
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
        return MainWindowTabWidgetBase.DisassemblerViewer

    def getLanguage( self ):
        " Tells the content language "
        return "Disassembler"

    def getFileName( self ):
        " Tells what file name of the widget content "
        return "N/A"

    def setFileName( self, name ):
        " Sets the file name - not applicable"
        raise Exception( "Setting a file name for disassembler results is not applicable" )

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
        " Sets the new encoding - not applicable for the disassembler results viewer "
        return

    def getShortName( self ):
        " Tells the display name "
        return "Disassembling results"

    def setShortName( self, name ):
        " Sets the display name - not applicable "
        raise Exception( "Setting a file name for disassembler results is not applicable" )

