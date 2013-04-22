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

" Stack viewer "


from PyQt4.QtCore import Qt, SIGNAL, QStringList
from PyQt4.QtGui import ( QSizePolicy, QFrame, QTreeWidget, QToolButton,
                          QTreeWidgetItem, QHeaderView, QVBoxLayout,
                          QLabel, QWidget, QAbstractItemView, QMenu,
                          QSpacerItem, QHBoxLayout, QPalette, QCursor )
from ui.itemdelegates import NoOutlineHeightDelegate
from utils.pixmapcache import PixmapCache
from utils.globals import GlobalData
from utils.settings import Settings
import os.path


class StackFrameItem( QTreeWidgetItem ):
    " Single stack frame item data structure "

    def __init__( self, fileName, lineNumber, funcName, frameNumber ):

        shortened = os.path.basename( fileName ) + ":" + str( lineNumber )
        full = fileName + ":" + str( lineNumber )

        self.__lineNumber = lineNumber
        QTreeWidgetItem.__init__( self,
                QStringList() << "" << shortened << funcName << fileName )

        self.__isCurrent = False
        self.__frameNumber = frameNumber

        for index in xrange( 4 ):
            self.setToolTip( index, full )
        return

    def setCurrent( self, value ):
        """ Mark the current stack frame with an icon if so """
        self.__isCurrent = value
        if value:
            self.setIcon( 0, PixmapCache().getIcon( 'currentframe.png' ) )
        else:
            self.setIcon( 0, PixmapCache().getIcon( 'empty.png' ) )
        return

    def getFrameNumber( self ):
        " Provides the frame number "
        return self.__frameNumber

    def getFilename( self ):
        """ Provides the full project filename """
        return str( self.text( 3 ) )

    def getLineNumber( self ):
        " Provides the line number "
        return self.__lineNumber

    def isCurrent( self ):
        " True if the project is current "
        return self.__isCurrent




class StackViewer( QWidget ):
    " Implements the stack viewer for a debugger "

    def __init__( self, debugger, parent = None ):
        QWidget.__init__( self, parent )

        self.__debugger = debugger
        self.currentStack = None
        self.currentFrame = 0
        self.__createPopupMenu()
        self.__createLayout()

        if Settings().showStackViewer == False:
            self.__onShowHide( True )
        return

    def __createPopupMenu( self ):
        " Creates the popup menu "
        self.__framesMenu = QMenu()
        self.__setCurrentMenuItem = self.__framesMenu.addAction(
                    "Set current (single click)", self.__onSetCurrent )
        self.__jumpMenuItem = self.__framesMenu.addAction(
                    "Set current and jump to the source (double click)",
                    self.__onSetCurrentAndJump )
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

        self.__stackLabel = QLabel( "Stack" )

        expandingSpacer = QSpacerItem( 10, 10, QSizePolicy.Expanding )
        fixedSpacer = QSpacerItem( 3, 3 )

        self.__showHideButton = QToolButton()
        self.__showHideButton.setAutoRaise( True )
        self.__showHideButton.setIcon( PixmapCache().getIcon( 'less.png' ) )
        self.__showHideButton.setFixedSize( 20, 20 )
        self.__showHideButton.setToolTip( "Hide frames list" )
        self.__showHideButton.setFocusPolicy( Qt.NoFocus )
        self.connect( self.__showHideButton, SIGNAL( 'clicked()' ),
                      self.__onShowHide )

        headerLayout = QHBoxLayout()
        headerLayout.setContentsMargins( 0, 0, 0, 0 )
        headerLayout.addSpacerItem( fixedSpacer )
        headerLayout.addWidget( self.__stackLabel )
        headerLayout.addSpacerItem( expandingSpacer )
        headerLayout.addWidget( self.__showHideButton )
        self.headerFrame.setLayout( headerLayout )

        self.__framesList = QTreeWidget( self )
        self.__framesList.setSortingEnabled( False )
        # I might not need that because of two reasons:
        # - the window has no focus
        # - the window has custom current indicator
        # self.__framesList.setAlternatingRowColors( True )
        self.__framesList.setRootIsDecorated( False )
        self.__framesList.setItemsExpandable( False )
        self.__framesList.setUniformRowHeights( True )
        self.__framesList.setSelectionMode( QAbstractItemView.NoSelection )
        self.__framesList.setSelectionBehavior( QAbstractItemView.SelectRows )
        self.__framesList.setItemDelegate( NoOutlineHeightDelegate( 4 ) )
        self.__framesList.setFocusPolicy( Qt.NoFocus )
        self.__framesList.setContextMenuPolicy( Qt.CustomContextMenu )

        self.connect( self.__framesList,
                      SIGNAL( "itemClicked(QTreeWidgetItem*,int)" ),
                      self.__onFrameClicked )
        self.connect( self.__framesList,
                      SIGNAL( "itemDoubleClicked(QTreeWidgetItem*,int)" ),
                      self.__onFrameDoubleClicked )
        self.connect( self.__framesList,
                      SIGNAL( "customContextMenuRequested(const QPoint &)" ),
                      self.__showContextMenu )

        headerLabels = QStringList() << "" << "File:line" \
                                     << "Function" << "Full path"
        self.__framesList.setHeaderLabels( headerLabels )

        verticalLayout.addWidget( self.headerFrame )
        verticalLayout.addWidget( self.__framesList )
        return

    def __onShowHide( self, startup = False ):
        " Triggered when show/hide button is clicked "
        if startup or self.__framesList.isVisible():
            self.__framesList.setVisible( False )
            self.__showHideButton.setIcon( PixmapCache().getIcon( 'more.png' ) )
            self.__showHideButton.setToolTip( "Show frames list" )

            self.__minH = self.minimumHeight()
            self.__maxH = self.maximumHeight()

            self.setMinimumHeight( self.headerFrame.height() )
            self.setMaximumHeight( self.headerFrame.height() )

            Settings().showStackViewer = False
        else:
            self.__framesList.setVisible( True )
            self.__showHideButton.setIcon( PixmapCache().getIcon( 'less.png' ) )
            self.__showHideButton.setToolTip( "Hide frames list" )

            self.setMinimumHeight( self.__minH )
            self.setMaximumHeight( self.__maxH )

            Settings().showStackViewer = True
        return

    def clear( self ):
        " Clears the content "
        self.__framesList.clear()
        self.currentStack = None
        self.__stackLabel.setText( "Stack" )
        return

    def __resizeColumns( self ):
        " Resize the files list columns "
        self.__framesList.header().setStretchLastSection( True )
        self.__framesList.header().resizeSections(
                                    QHeaderView.ResizeToContents )
        self.__framesList.header().resizeSection( 0, 22 )
        self.__framesList.header().setResizeMode( 0, QHeaderView.Fixed )
        return


    def populate( self, stack ):
        " Sets the new call stack and selects the first item in it "
        self.clear()

        self.currentStack = stack
        self.currentFrame = 0
        frameNumber = 0
        for s in stack:
            if len( s ) == 2:
                # This is when an exception comes
                funcName = ""
            else:
                funcName = s[ 2 ]
            item = StackFrameItem( s[ 0 ], s[ 1 ], funcName, frameNumber )
            self.__framesList.addTopLevelItem( item )
            frameNumber += 1
        self.__resizeColumns()
        self.__framesList.topLevelItem( 0 ).setCurrent( True )
        self.__stackLabel.setText( "Stack (total: " +
                                   str( len( stack ) ) + ")" )
        return

    def getFrameNumber( self ):
        " Provides the current frame number "
        return self.currentFrame

    def __onFrameClicked( self, item, column ):
        " Triggered when a frame is clicked "
        if item.isCurrent():
            return

        # Hide the current indicator
        self.__framesList.topLevelItem( self.currentFrame ).setCurrent( False )

        # Show the new indicator
        self.currentFrame = item.getFrameNumber()
        for index in xrange( self.__framesList.topLevelItemCount() ):
            item = self.__framesList.topLevelItem( index )
            if item.getFrameNumber() == self.currentFrame:
                item.setCurrent( True )
        self.__debugger.remoteClientVariables( 1, self.currentFrame )  # globals
        self.__debugger.remoteClientVariables( 0, self.currentFrame )  # locals
        return

    def __onFrameDoubleClicked( self, item, column ):
        " Triggered when a frame is double clicked "
        # The frame has been switched already because the double click
        # signal always comes after the single click one
        fileName = item.getFilename()
        lineNumber = item.getLineNumber()

        editorsManager = GlobalData().mainWindow.editorsManager()
        editorsManager.openFile( fileName, lineNumber )
        editor = editorsManager.currentWidget().getEditor()
        editor.gotoLine( lineNumber )
        editorsManager.currentWidget().setFocus()
        return

    def __showContextMenu( self, coord ):
        " Shows the frames list context menu "
        self.__contextItem = self.__framesList.itemAt( coord )
        if self.__contextItem is not None:
            self.__setCurrentMenuItem.setEnabled(
                                not self.__contextItem.isCurrent() )
            self.__framesMenu.popup( QCursor.pos() )
        return

    def __onSetCurrent( self ):
        " Context menu item handler "
        self.__onFrameClicked( self.__contextItem, 0 )
        return

    def __onSetCurrentAndJump( self ):
        " Context menu item handler "
        self.__onFrameClicked( self.__contextItem, 0 )
        self.__onFrameDoubleClicked( self.__contextItem, 0 )
        return

    def switchControl( self, isInIDE ):
        " Switches the UI depending where the control flow is "
        self.__framesList.setEnabled( isInIDE )
        return

