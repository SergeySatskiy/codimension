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
from variableitems import getDisplayValue, getTooltipValue


STACK_FRAME_ITEM = 0
EXCEPTION_ITEM = 1

class StackFrameItem( QTreeWidgetItem ):
    " One stack trace frame "

    def __init__( self, parentItem, fileName, lineNumber ):
        QTreeWidgetItem.__init__( self, parentItem )

        self.__fileName = fileName
        self.__lineNumber = lineNumber
        self.setText( 0, os.path.basename( fileName ) + ":" + str( lineNumber ) )
        self.setToolTip( 0, fileName + ":" + str( lineNumber ) )
        return

    def getType( self ):
        " Provides the item type "
        return STACK_FRAME_ITEM

    def getLocation( self ):
        " Provides the location in the code "
        return self.toolTip( 0 )

    def getFileName( self ):
        " Provides the file name "
        return self.__fileName

    def getLineNumber( self ):
        " Provides the line number "
        return self.__lineNumber


class ExceptionItem( QTreeWidgetItem ):
    " One exception item "

    def __init__( self, parentItem, exceptionType, exceptionMessage,
                  stackTrace ):
        QTreeWidgetItem.__init__( self, parentItem )
        self.__count = 1
        self.__exceptionType = exceptionType
        self.__exceptionMessage = exceptionMessage

        if exceptionMessage == "":
            self.setText( 0, exceptionType )
            self.setToolTip( 0, "Type: " + exceptionType )
        else:
            self.setText( 0, exceptionType + ", " +
                             getDisplayValue( exceptionMessage ) )
            tooltip = "Type: " + exceptionType + "\n" + \
                      "Message: "
            tooltipMessage = getTooltipValue( exceptionMessage )
            if '\r' in tooltipMessage or '\n' in tooltipMessage:
                tooltip += "\n" + tooltipMessage
            else:
                tooltip += tooltipMessage
            self.setToolTip( 0, tooltip )

        for fileName, lineNumber in stackTrace:
            StackFrameItem( self, fileName, lineNumber )
        return

    def getType( self ):
        " Provides the item type "
        return STACK_FRAME_ITEM

    def getCount( self ):
        " Provides the number of same exceptions "
        return self.__count

    def incrementCounter( self ):
        " Increments the counter of the same exceptions "
        self.__count += 1
        if self.__exceptionMessage == "":
            self.setText( 0, self.__exceptionType +
                             " (" + str( self.__count ) + " times)" )
        else:
            self.setText( 0, self.__exceptionType +
                             " (" + str( self.__count ) + " times), " +
                             getDisplayValue( self.__exceptionMessage ) )
        return

    def equal( self, exceptionType, exceptionMessage, stackTrace ):
        " Returns True if the exceptions are equal "
        if exceptionType != self.__exceptionType:
            return False
        if exceptionMessage != self.__exceptionMessage:
            return False

        count = self.childCount()
        if count != len( stackTrace ):
            return False

        for index in xrange( self.childCount() ):
            child = self.child( index )
            otherLocation = stackTrace[ index ][ 0 ] + ":" + str( stackTrace[ index ][ 1 ] )
            if otherLocation != child.getLocation():
                return False
        return True



class ClientExceptionsViewer( QWidget ):
    " Implements the client exceptions viewer for a debugger "

    def __init__( self, parent = None ):
        QWidget.__init__( self, parent )

        self.__createPopupMenu()
        self.__createLayout()
        return

    def setFocus( self ):
        " Sets the widget focus "
        self.__exceptionsList.setFocus()
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

        self.__addToIgnoreButton = QToolButton()
        self.__addToIgnoreButton.setIcon( PixmapCache().getIcon( 'add.png' ) )
        self.__addToIgnoreButton.setFixedSize( 24, 24 )
        self.__addToIgnoreButton.setToolTip( "Add exception to the list of ignored" )
        self.__addToIgnoreButton.setFocusPolicy( Qt.NoFocus )
        self.__addToIgnoreButton.setEnabled( False )

        expandingSpacer = QSpacerItem( 10, 10, QSizePolicy.Expanding )

        self.__jumpToCodeButton = QToolButton()
        self.__jumpToCodeButton.setIcon( PixmapCache().getIcon( 'gotoline.png' ) )
        self.__jumpToCodeButton.setFixedSize( 24, 24 )
        self.__jumpToCodeButton.setToolTip( "Jump to the code" )
        self.__jumpToCodeButton.setFocusPolicy( Qt.NoFocus )
        self.__jumpToCodeButton.setEnabled( False )

        toolbarLayout = QHBoxLayout()
        toolbarLayout.addWidget( self.__addToIgnoreButton )
        toolbarLayout.addSpacerItem( expandingSpacer )
        toolbarLayout.addWidget( self.__jumpToCodeButton )

        self.connect( self.__exceptionsList,
                      SIGNAL( "itemDoubleClicked(QTreeWidgetItem*,int)" ),
                      self.__onExceptionDoubleClicked )
        self.connect( self.__exceptionsList,
                      SIGNAL( "customContextMenuRequested(const QPoint &)" ),
                      self.__showContextMenu )

        headerLabels = QStringList() << "Exception"
        self.__exceptionsList.setHeaderLabels( headerLabels )

        verticalLayout.addWidget( self.headerFrame )
        verticalLayout.addLayout( toolbarLayout )
        verticalLayout.addWidget( self.__exceptionsList )
        return

    def clear( self ):
        " Clears the content "
        self.__exceptionsList.clear()
        self.__excptLabel.setText( "Exceptions" )
        self.__addToIgnoreButton.setEnabled( False )
        self.__jumpToCodeButton.setEnabled( False )
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

    def addException( self, exceptionType, exceptionMessage,
                            stackTrace ):
        " Adds the exception to the view "
        for index in xrange( self.__exceptionsList.topLevelItemCount() ):
            item = self.__exceptionsList.topLevelItem( index )
            if item.equal( exceptionType, exceptionMessage, stackTrace ):
                item.incrementCounter()
                self.__exceptionsList.clearSelection()
                self.__exceptionsList.setCurrentItem( item )
                self.__updateExceptionsLabel()
                return

        item = ExceptionItem( self.__exceptionsList, exceptionType,
                              exceptionMessage, stackTrace )
        self.__exceptionsList.clearSelection()
        self.__exceptionsList.setCurrentItem( item )
        self.__updateExceptionsLabel()
        return

    def __updateExceptionsLabel( self ):
        " Updates the exceptions header label "
        total = self.getTotalCount()
        if total > 1:
            self.__excptLabel.setText( "Exceptions (total: " +
                                       str( total ) + ")" )
        return

    def getTotalCount( self ):
        " Provides the total number of exceptions "
        count = 0
        for index in xrange( self.__exceptionsList.topLevelItemCount() ):
            count += self.__exceptionsList.topLevelItem( index ).getCount()
        return count

