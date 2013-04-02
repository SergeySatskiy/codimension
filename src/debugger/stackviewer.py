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
                          QLabel, QWidget, QAbstractItemView,
                          QSpacerItem, QHBoxLayout, QPalette )
from ui.itemdelegates import NoOutlineHeightDelegate
from utils.pixmapcache import PixmapCache
import os.path


class StackFrameItem( QTreeWidgetItem ):
    " Single stack frame item data structure "

    def __init__( self, fileName, lineNumber, funcName ):

        shortened = os.path.basename( fileName ) + ":" + str( lineNumber )
        full = fileName + ":" + str( lineNumber )

        self.__lineNumber = lineNumber
        QTreeWidgetItem.__init__( self,
                QStringList() << "" << shortened << funcName << fileName )

        self.__isCurrent = False

        for index in xrange( 4 ):
            self.setToolTip( index, full )
        return

    def setCurrent( self, value ):
        """ Mark the current stack frame with an icon if so """
        self.__isCurrent = value
        if value:
            self.setIcon( 0, PixmapCache().getIcon( 'currentframe.png' ) )
        else:
            self.setIcon( 0, None )
        return

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

    def __init__( self, parent = None ):
        QWidget.__init__( self, parent )

        self.currentStack = None
        self.currentFrame = 0
        self.__createLayout()
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

        self.__framesList = QTreeWidget()
        self.__framesList.setSortingEnabled( False )
        self.__framesList.setAlternatingRowColors( True )
        self.__framesList.setRootIsDecorated( False )
        self.__framesList.setItemsExpandable( False )
        self.__framesList.setUniformRowHeights( True )
        self.__framesList.setSelectionMode( QAbstractItemView.NoSelection )
        self.__framesList.setSelectionBehavior( QAbstractItemView.SelectRows )
        self.__framesList.setItemDelegate( NoOutlineHeightDelegate( 4 ) )

        self.connect( self.__framesList,
                      SIGNAL( "clicked(const QModelIndex&)" ),
                      self.__onFrameClicked )
        self.connect( self.__framesList,
                      SIGNAL( "doubleClicked(const QModelIndex&)" ),
                      self.__onFrameDoubleClicked )

        headerLabels = QStringList() << "" << "File:line" \
                                     << "Function" << "Full path"
        self.__framesList.setHeaderLabels( headerLabels )

        verticalLayout.addWidget( self.headerFrame )
        verticalLayout.addWidget( self.__framesList )
        return

    def __onShowHide( self ):
        " Triggered when show/hide button is clicked "
        if self.__framesList.isVisible():
            self.__framesList.setVisible( False )
            self.__showHideButton.setIcon( PixmapCache().getIcon( 'more.png' ) )
            self.__showHideButton.setToolTip( "Show frames list" )

            self.__minH = self.minimumHeight()
            self.__maxH = self.maximumHeight()

            self.setMinimumHeight( self.headerFrame.height() )
            self.setMaximumHeight( self.headerFrame.height() )
        else:
            self.__framesList.setVisible( True )
            self.__showHideButton.setIcon( PixmapCache().getIcon( 'less.png' ) )
            self.__showHideButton.setToolTip( "Hide frames list" )

            self.setMinimumHeight( self.__minH )
            self.setMaximumHeight( self.__maxH )
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
        for s in stack:
            item = StackFrameItem( s[ 0 ], s[ 1 ], s[ 2 ] )
            self.__framesList.addTopLevelItem( item )
        self.__resizeColumns()
        self.__framesList.topLevelItem( 0 ).setCurrent( True )
        self.__stackLabel.setText( "Stack (total: " +
                                   str( len( stack ) ) + ")" )
        return

    def getFrameNumber( self ):
        " Provides the current frame number "
        return self.currentFrame

    def __onFrameClicked( self, index ):
        " Triggered when a frame is clicked "
        # Must update the current frame number
        print "Frame clicked"

    def __onFrameDoubleClicked( self, index ):
        " Triggered when a frame is double clicked "
        # Must update the current frame number
        print "Frame double clicked"


