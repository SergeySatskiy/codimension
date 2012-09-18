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

" stack viewer "


from PyQt4.QtCore       import Qt, SIGNAL, QStringList, QEventLoop
from PyQt4.QtGui        import QFrame, QTreeWidget, QToolButton, \
                               QTreeWidgetItem, QHeaderView, \
                               QVBoxLayout, QLabel, QWidget, \
                               QAbstractItemView, QSizePolicy, QSpacerItem, \
                               QHBoxLayout, QPalette
from utils.globals      import GlobalData
from ui.itemdelegates   import NoOutlineHeightDelegate
from utils.pixmapcache  import PixmapCache
import os.path


class ThreadsViewer( QWidget ):
    " Implements the threads viewer for a debugger "

    def __init__( self, parent = None ):
        QWidget.__init__( self, parent )

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

        self.__threadsLabel = QLabel( "Threads" )

        expandingSpacer = QSpacerItem( 10, 10, QSizePolicy.Expanding )
        fixedSpacer = QSpacerItem( 3, 3 )

        self.__showHideButton = QToolButton()
        self.__showHideButton.setAutoRaise( True )
        self.__showHideButton.setIcon( PixmapCache().getIcon( 'less.png' ) )
        self.__showHideButton.setFixedSize( 20, 20 )
        self.__showHideButton.setToolTip( "Hide threads list" )
        self.__showHideButton.setFocusPolicy( Qt.NoFocus )
        self.connect( self.__showHideButton, SIGNAL( 'clicked()' ),
                      self.__onShowHide )

        headerLayout = QHBoxLayout()
        headerLayout.setContentsMargins( 0, 0, 0, 0 )
        headerLayout.addSpacerItem( fixedSpacer )
        headerLayout.addWidget( self.__threadsLabel )
        headerLayout.addSpacerItem( expandingSpacer )
        headerLayout.addWidget( self.__showHideButton )
        self.headerFrame.setLayout( headerLayout )

        self.__threadsList = QTreeWidget()
        self.__threadsList.setAlternatingRowColors( True )
        self.__threadsList.setRootIsDecorated( False )
        self.__threadsList.setItemsExpandable( False )
        self.__threadsList.setUniformRowHeights( True )
        self.__threadsList.setSelectionMode( QAbstractItemView.SingleSelection )
        self.__threadsList.setSelectionBehavior( QAbstractItemView.SelectRows )
        self.__threadsList.setItemDelegate( NoOutlineHeightDelegate( 4 ) )

        headerLabels = QStringList() << "TID" << "Name" << "State"
        self.__threadsList.setHeaderLabels( headerLabels )

        verticalLayout.addWidget( self.headerFrame )
        verticalLayout.addWidget( self.__threadsList )
        return

    def __onShowHide( self ):
        " Triggered when show/hide button is clicked "
        if self.__threadsList.isVisible():
            self.__threadsList.setVisible( False )
            self.__showHideButton.setIcon( PixmapCache().getIcon( 'more.png' ) )
            self.__showHideButton.setToolTip( "Show threads list" )

            self.__minH = self.minimumHeight()
            self.__maxH = self.maximumHeight()

            self.setMinimumHeight( self.headerFrame.height() )
            self.setMaximumHeight( self.headerFrame.height() )
        else:
            self.__threadsList.setVisible( True )
            self.__showHideButton.setIcon( PixmapCache().getIcon( 'less.png' ) )
            self.__showHideButton.setToolTip( "Hide threads list" )

            self.setMinimumHeight( self.__minH )
            self.setMaximumHeight( self.__maxH )
        return

