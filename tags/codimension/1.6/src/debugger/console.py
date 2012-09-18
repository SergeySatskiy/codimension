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

""" The debugger console implementation """

from PyQt4.QtCore import Qt, SIGNAL, QSize
from PyQt4.QtGui import QTextEdit, QMenu, QComboBox, \
                        QApplication, QCursor, QToolButton, \
                        QHBoxLayout, QWidget, QAction, QToolBar, \
                        QSizePolicy, QLabel, QVBoxLayout, QFrame
from utils.pixmapcache import PixmapCache


class DebuggerConsole( QWidget ):
    """ The debugger console widget """

    def __init__( self, parent = None ):
        QWidget.__init__( self, parent )

        self.__isEmpty = True
        self.__copyAvailable = False
        self.__clearButton = None
        self.__textEdit = None
        self.__header = None
        self.__copyButton = None
        self.__selectAllButton = None
        self.__createLayout( parent )

        # create the context menu
        self.__menu = QMenu( self )
        self.__selectAllMenuItem = self.__menu.addAction( \
                            PixmapCache().getIcon( 'selectall.png' ),
                            'Select All', self.__textEdit.selectAll )
        self.__copyMenuItem = self.__menu.addAction( \
                            PixmapCache().getIcon( 'copytoclipboard.png' ),
                            'Copy', self.__textEdit.copy )
        self.__menu.addSeparator()
        self.__clearMenuItem = self.__menu.addAction( \
                            PixmapCache().getIcon( 'trash.png' ),
                            'Clear', self.__clear )

        self.__textEdit.setContextMenuPolicy( Qt.CustomContextMenu )
        self.connect( self.__textEdit,
                      SIGNAL( "customContextMenuRequested(const QPoint &)" ),
                      self.__handleShowContextMenu )
        self.connect( self.__textEdit, SIGNAL( "copyAvailable(bool)" ),
                      self.__onCopyAvailable )

        self.__updateToolbarButtons()
        return

    def __createLayout( self, parent ):
        " Helper to create the viewer layout "

        # __textEdit list area
        self.__textEdit = QTextEdit( parent )
        self.__textEdit.setAcceptRichText( False )
        self.__textEdit.setLineWrapMode( QTextEdit.NoWrap )
        self.__textEdit.setFontFamily( "Monospace" )
        self.__textEdit.setReadOnly( True )

        # Default font size is good enough for most of the systems.
        # 12.0 might be good only in case of the XServer on PC (Xming).
        # self.__textEdit.setFontPointSize( 12.0 )

        # Buttons
        self.__selectAllButton = QAction( \
            PixmapCache().getIcon( 'selectall.png' ),
            'Select all', self )
        self.connect( self.__selectAllButton, SIGNAL( "triggered()" ),
                      self.__textEdit.selectAll )
        self.__copyButton = QAction( \
            PixmapCache().getIcon( 'copytoclipboard.png' ),
            'Copy to clipboard', self )
        self.connect( self.__copyButton, SIGNAL( "triggered()" ),
                      self.__textEdit.copy )
        spacer = QWidget()
        spacer.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )
        self.__clearButton = QAction( \
            PixmapCache().getIcon( 'trash.png' ),
            'Clear all', self )
        self.connect( self.__clearButton, SIGNAL( "triggered()" ),
                      self.__clear )

        # Toolbar
        toolbar = QToolBar()
        toolbar.setOrientation( Qt.Vertical )
        toolbar.setMovable( False )
        toolbar.setAllowedAreas( Qt.LeftToolBarArea )
        toolbar.setIconSize( QSize( 16, 16 ) )
        toolbar.setFixedWidth( 28 )
        toolbar.setContentsMargins( 0, 0, 0, 0 )
        toolbar.addAction( self.__selectAllButton )
        toolbar.addAction( self.__copyButton )
        toolbar.addWidget( spacer )
        toolbar.addAction( self.__clearButton )

        commandLabel = QLabel( "Command:" )
        self.commandEdit = QComboBox()
        self.commandEdit.setEditable( True )
        self.commandEdit.setInsertPolicy( QComboBox.InsertAtTop )
        self.commandEdit.setAutoCompletion( False )
        self.commandEdit.setDuplicatesEnabled( False )
        sizePolicy = QSizePolicy( QSizePolicy.Expanding, QSizePolicy.Fixed )
        sizePolicy.setHorizontalStretch( 0 )
        sizePolicy.setVerticalStretch( 0 )
        sizePolicy.setHeightForWidth( \
                    self.commandEdit.sizePolicy().hasHeightForWidth() )
        self.commandEdit.setSizePolicy( sizePolicy )

        self.execButton = QToolButton()
        self.execButton.setToolTip( "Execute command (ENTER)" )
        self.execButton.setIcon( PixmapCache().getIcon( "execdbgcmd.png" ) )
        self.execButton.setFocusPolicy( Qt.NoFocus )
        self.execButton.setEnabled( False )

        spacer = QWidget()
        spacer.setFixedWidth( 1 )

        horizontalLayout = QHBoxLayout()
        horizontalLayout.setMargin( 0 )

        horizontalLayout.addWidget( commandLabel )
        horizontalLayout.addWidget( self.commandEdit )
        horizontalLayout.addWidget( self.execButton )
        horizontalLayout.addWidget( spacer )

        verticalLayout = QVBoxLayout()
        verticalLayout.setContentsMargins( 2, 2, 2, 2 )
        verticalLayout.setSpacing( 2 )
        verticalLayout.addWidget( self.__textEdit )
        verticalLayout.addLayout( horizontalLayout )

        # layout
        layout = QHBoxLayout()
        layout.setContentsMargins( 0, 0, 0, 0 )
        layout.setSpacing( 0 )
        layout.addWidget( toolbar )
        layout.addLayout( verticalLayout )

        self.setLayout( layout )
        return

    def __handleShowContextMenu( self, coord ):
        """ Show the context menu """

        self.__selectAllMenuItem.setEnabled( not self.__isEmpty )
        self.__copyMenuItem.setEnabled( self.__copyAvailable )
        self.__clearMenuItem.setEnabled( not self.__isEmpty )

        self.__menu.popup( QCursor.pos() )
        return

    def display( self, message ):
        " Displays the given message "

        message = str( message )
        if not message.endswith( '\n' ):
            message += '\n'

        self.__textEdit.append( message )
        self.__updateToolbarButtons()
        QApplication.processEvents()
        return

    def __updateToolbarButtons( self ):
        " Contextually updates toolbar buttons "
        self.__selectAllButton.setEnabled( not self.__isEmpty )
        self.__copyButton.setEnabled( self.__copyAvailable )
        self.__clearButton.setEnabled( not self.__isEmpty )
        return

    def __clear( self ):
        " Triggers when the clear function is selected "
        self.__isEmpty = True
        self.__copyAvailable = False
        self.__textEdit.clear()
        self.__updateToolbarButtons()
        return

    def __onCopyAvailable( self, isAvailable ):
        " Triggers on the copyAvailable signal "
        self.__copyAvailable = isAvailable
        self.__updateToolbarButtons()
        return

