#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010  Sergey Satskiy <sergey.satskiy@gmail.com>
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

#
# The file was taken from eric 4.4.3 and adopted for codimension.
# Original copyright:
# Copyright (c) 2007 - 2010 Detlev Offenbach <detlev@die-offenbachs.de>
#

""" The log viewer implementation """

from PyQt4.QtCore import Qt, QSize
from PyQt4.QtGui import ( QPlainTextEdit, QColor, QBrush, QMenu, QTextCursor,
                          QCursor, QHBoxLayout, QWidget, QAction, QToolBar,
                          QSizePolicy, QFont )
from utils.pixmapcache import PixmapCache
from utils.globals import GlobalData


MAX_LINES = 10000

class LogViewer( QWidget ):
    """ The log (+stdout, +stderr) viewer widget """

    def __init__( self, parent = None ):
        QWidget.__init__( self, parent )

        self.__isEmpty = True
        self.__copyAvailable = False
        self.clearButton = None
        self.messages = None
        self.copyButton = None
        self.selectAllButton = None
        self.__createLayout( parent )

        # create the context menu
        self.__menu = QMenu( self )
        self.__selectAllMenuItem = self.__menu.addAction(
                            PixmapCache().getIcon( 'selectall.png' ),
                            'Select All', self.messages.selectAll )
        self.__copyMenuItem = self.__menu.addAction(
                            PixmapCache().getIcon( 'copytoclipboard.png' ),
                            'Copy', self.messages.copy )
        self.__menu.addSeparator()
        self.__clearMenuItem = self.__menu.addAction(
                            PixmapCache().getIcon( 'trash.png' ),
                            'Clear', self.__clear )

        self.messages.setContextMenuPolicy( Qt.CustomContextMenu )
        self.messages.customContextMenuRequested.connect(
                                                self.__handleShowContextMenu )
        self.messages.copyAvailable.connect( self.__onCopyAvailable )

        self.cNormalFormat = self.messages.currentCharFormat()
        self.cErrorFormat = self.messages.currentCharFormat()
        self.cErrorFormat.setForeground( QBrush( QColor( Qt.red ) ) )
        self.__updateToolbarButtons()
        return

    def __createLayout( self, parent ):
        " Helper to create the viewer layout "

        # Messages list area
        self.messages = QPlainTextEdit( parent )
        self.messages.setLineWrapMode( QPlainTextEdit.NoWrap )
        self.messages.setFont( QFont( GlobalData().skin.baseMonoFontFace ) )
        self.messages.setReadOnly( True )
        self.messages.setMaximumBlockCount( MAX_LINES )

        # Default font size is good enough for most of the systems.
        # 12.0 might be good only in case of the XServer on PC (Xming).
        # self.messages.setFontPointSize( 12.0 )

        # Buttons
        self.selectAllButton = QAction(
            PixmapCache().getIcon( 'selectall.png' ),
            'Select all', self )
        self.selectAllButton.triggered.connect( self.messages.selectAll )
        self.copyButton = QAction(
            PixmapCache().getIcon( 'copytoclipboard.png' ),
            'Copy to clipboard', self )
        self.copyButton.triggered.connect( self.messages.copy )
        spacer = QWidget()
        spacer.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )
        self.clearButton = QAction(
            PixmapCache().getIcon( 'trash.png' ),
            'Clear all', self )
        self.clearButton.triggered.connect( self.__clear )

        # Toolbar
        self.toolbar = QToolBar()
        self.toolbar.setOrientation( Qt.Vertical )
        self.toolbar.setMovable( False )
        self.toolbar.setAllowedAreas( Qt.LeftToolBarArea )
        self.toolbar.setIconSize( QSize( 16, 16 ) )
        self.toolbar.setFixedWidth( 28 )
        self.toolbar.setContentsMargins( 0, 0, 0, 0 )
        self.toolbar.addAction( self.selectAllButton )
        self.toolbar.addAction( self.copyButton )
        self.toolbar.addWidget( spacer )
        self.toolbar.addAction( self.clearButton )

        # layout
        layout = QHBoxLayout()
        layout.setContentsMargins( 0, 0, 0, 0 )
        layout.setSpacing( 0 )
        layout.addWidget( self.toolbar )
        layout.addWidget( self.messages )

        self.setLayout( layout )
        return

    def __handleShowContextMenu( self, coord ):
        """ Show the context menu """

        self.__selectAllMenuItem.setEnabled( not self.__isEmpty )
        self.__copyMenuItem.setEnabled( self.__copyAvailable )
        self.__clearMenuItem.setEnabled( not self.__isEmpty )

        self.__menu.popup( QCursor.pos() )
        return

    def __appendText( self, txt, isError ):
        " Append the text "

        if len( txt ) == 0:
            return

        self.__isEmpty = False
        cursor = self.messages.textCursor()
        cursor.movePosition( QTextCursor.End )
        self.messages.setTextCursor( cursor )
        if isError:
            self.messages.setCurrentCharFormat( self.cErrorFormat )
        else:
            self.messages.setCurrentCharFormat( self.cNormalFormat )
        self.messages.insertPlainText( txt )
        self.messages.insertPlainText( '\n' )
        self.messages.ensureCursorVisible()
        self.__updateToolbarButtons()
        return

    def appendMessage( self, txt ):
        " Append the regular message "

        self.__appendText( txt, False )
        #QApplication.processEvents()
        return

    def appendError( self, txt ):
        " Append the error message "

        self.__appendText( txt, True )
        #QApplication.processEvents()
        return

    def append( self, txt ):
        " Decides what the message is - error or not - and append it then "

        if txt.startswith( 'CRITICAL' ) or \
           txt.startswith( 'ERROR' ) or \
           txt.startswith( 'WARNING' ):
            self.appendError( txt )
        else:
            self.appendMessage( txt )
        return

    def __updateToolbarButtons( self ):
        " Contextually updates toolbar buttons "

        self.selectAllButton.setEnabled( not self.__isEmpty )
        self.copyButton.setEnabled( self.__copyAvailable )
        self.clearButton.setEnabled( not self.__isEmpty )
        return

    def __clear( self ):
        " Triggers when the clear function is selected "
        self.__isEmpty = True
        self.__copyAvailable = False
        self.messages.clear()
        self.__updateToolbarButtons()
        return

    def __onCopyAvailable( self, isAvailable ):
        " Triggers on the copyAvailable signal "
        self.__copyAvailable = isAvailable
        self.__updateToolbarButtons()
        return

    def getText( self ):
        " Provides the content as a plain text "
        return str( self.messages.toPlainText() )

