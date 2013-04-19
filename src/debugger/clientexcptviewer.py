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

" Client exceptions viewer "


from PyQt4.QtCore import Qt, SIGNAL, QStringList
from PyQt4.QtGui import ( QSizePolicy, QFrame, QTreeWidget, QToolButton,
                          QTreeWidgetItem, QHeaderView, QVBoxLayout,
                          QLabel, QWidget, QAbstractItemView, QMenu,
                          QSpacerItem, QHBoxLayout, QPalette, QCursor )
from ui.itemdelegates import NoOutlineHeightDelegate
from utils.pixmapcache import PixmapCache
from utils.globals import GlobalData
import os.path




class ClientExceptionsViewer( QWidget ):
    " Implements the client exceptions viewer for a debugger "

    def __init__( self, parent = None ):
        QWidget.__init__( self, parent )

        self.__createPopupMenu()
        self.__createLayout()
        return

    def __createPopupMenu( self ):
        " Creates the popup menu "
        self.__excptMenu = QMenu()
        self.__addToIgnoreMenuItem = self.__excptMenu.addAction(
                    "Add to ignore list", self.__onAddToIgnore )
        return

    def __createLayout( self ):
        " Creates the widget layout "

        verticalLayout = QVBoxLayout( self )
        verticalLayout.setContentsMargins( 0, 0, 0, 0 )
        verticalLayout.setSpacing( 0 )

        self.headerFrame = QFrame()
        self.headerFrame.setFrameStyle( QFrame.StyledPanel )
        self.headerFrame.setAutoFillBackground( True )
        headerPalette = self.headerFrame.palette()
        headerBackground = headerPalette.color( QPalette.Background )
        headerBackground.setRgb( min( headerBackground.red() + 30, 255 ),
                                 min( headerBackground.green() + 30, 255 ),
                                 min( headerBackground.blue() + 30, 255 ) )
        headerPalette.setColor( QPalette.Background, headerBackground )
        self.headerFrame.setPalette( headerPalette )
        self.headerFrame.setFixedHeight( 24 )

        self.__excptLabel = QLabel( "Exceptions" )

        fixedSpacer = QSpacerItem( 3, 3 )

        headerLayout = QHBoxLayout()
        headerLayout.setContentsMargins( 0, 0, 0, 0 )
        headerLayout.addSpacerItem( fixedSpacer )
        headerLayout.addWidget( self.__excptLabel )
        self.headerFrame.setLayout( headerLayout )

        self.__exceptionsList = QTreeWidget( self )
        self.__exceptionsList.setSortingEnabled( False )
        self.__exceptionsList.setAlternatingRowColors( True )
        self.__exceptionsList.setRootIsDecorated( True )
        self.__exceptionsList.setItemsExpandable( True )
        self.__exceptionsList.setUniformRowHeights( True )
        self.__exceptionsList.setSelectionMode( QAbstractItemView.SingleSelection )
        self.__exceptionsList.setSelectionBehavior( QAbstractItemView.SelectRows )
        self.__exceptionsList.setItemDelegate( NoOutlineHeightDelegate( 4 ) )
        self.__exceptionsList.setContextMenuPolicy( Qt.CustomContextMenu )

        self.connect( self.__exceptionsList,
                      SIGNAL( "itemDoubleClicked(QTreeWidgetItem*,int)" ),
                      self.__onExceptionDoubleClicked )
        self.connect( self.__exceptionsList,
                      SIGNAL( "customContextMenuRequested(const QPoint &)" ),
                      self.__showContextMenu )

        headerLabels = QStringList() << "Exception"
        self.__exceptionsList.setHeaderLabels( headerLabels )

        verticalLayout.addWidget( self.headerFrame )
        verticalLayout.addWidget( self.__exceptionsList )
        return

    def clear( self ):
        " Clears the content "
        self.__exceptionsList.clear()
        self.__excptLabel.setText( "Exceptions" )
        return

    def __onExceptionDoubleClicked( self, item, column ):
        " Triggered when an exception is double clicked "
        # The frame has been switched already because the double click
        # signal always comes after the single click one
#        fileName = item.getFilename()
#        lineNumber = item.getLineNumber()

#        editorsManager = GlobalData().mainWindow.editorsManager()
#        editorsManager.openFile( fileName, lineNumber )
#        editor = editorsManager.currentWidget().getEditor()
#        editor.gotoLine( lineNumber )
#        editorsManager.currentWidget().setFocus()
        return

    def __showContextMenu( self, coord ):
        " Shows the frames list context menu "
        self.__contextItem = self.__exceptionsList.itemAt( coord )
        if self.__contextItem is not None:
            self.__excptMenu.popup( QCursor.pos() )
        return

    def __onAddToIgnore( self ):
        pass

