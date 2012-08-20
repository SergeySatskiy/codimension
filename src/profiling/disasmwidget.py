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

from proftable import ProfileTableViewer
from ui.mainwindowtabwidgetbase import MainWindowTabWidgetBase
from PyQt4.QtCore import Qt, SIGNAL, QSize
from PyQt4.QtGui import QWidget, QToolBar, QHBoxLayout, QAction, \
                        QLabel, QFrame, QPalette, QVBoxLayout, \
                        QTextEdit
from utils.pixmapcache import PixmapCache



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
        self.connect( self.__printButton, SIGNAL( 'triggered()' ),
                      self.__onPrint )
        self.__printButton.setEnabled( False )

        self.__printPreviewButton = QAction( \
                PixmapCache().getIcon( 'printpreview.png' ),
                'Print preview', self )
        self.connect( self.__printPreviewButton, SIGNAL( 'triggered()' ),
                      self.__onPrintPreview )
        self.__printPreviewButton.setEnabled( False )


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

        summary = QLabel( "<b>Script:</b> " + scriptName + "<br>" \
                          "<b>Name:</b> " + name + "<br>" \
                          "<b>Disassembed at:</b> " + reportTime )
        summary.setFrameStyle( QFrame.StyledPanel )
        summary.setAutoFillBackground( True )
        summaryPalette = summary.palette()
        summaryBackground = summaryPalette.color( QPalette.Background )
        summaryBackground.setRgb( min( summaryBackground.red() + 30, 255 ),
                                  min( summaryBackground.green() + 30, 255 ),
                                  min( summaryBackground.blue() + 30, 255 ) )
        summaryPalette.setColor( QPalette.Background, summaryBackground )
        summary.setPalette( summaryPalette )

        self.__text = QTextEdit( self )
        self.__text.setAcceptRichText( False )
        self.__text.setLineWrapMode( QTextEdit.NoWrap )
        self.__text.setFontFamily( "Monospace" )
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

    def keyPressEvent( self, event ):
        " Handles the key press events "
        if event.key() == Qt.Key_Escape:
            self.emit( SIGNAL('ESCPressed') )
            event.accept()
        else:
            QWidget.keyPressEvent( self, event )
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

