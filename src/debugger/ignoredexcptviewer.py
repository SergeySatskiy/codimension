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

" Ignored exceptions viewer "


from PyQt4.QtCore import Qt, SIGNAL, QStringList
from PyQt4.QtGui import ( QSizePolicy, QFrame, QTreeWidget, QToolButton,
                          QTreeWidgetItem, QHeaderView, QVBoxLayout,
                          QLabel, QWidget, QAbstractItemView, QMenu,
                          QSpacerItem, QHBoxLayout, QPalette, QCursor,
                          QLineEdit, QPushButton )
from ui.itemdelegates import NoOutlineHeightDelegate
from utils.pixmapcache import PixmapCache
from utils.globals import GlobalData
from utils.project import CodimensionProject
from utils.settings import Settings
import os.path




class IgnoredExceptionsViewer( QWidget ):
    " Implements the client exceptions viewer for a debugger "

    def __init__( self, parent = None ):
        QWidget.__init__( self, parent )

        self.__createPopupMenu()
        self.__createLayout()
        self.__ignored = []
        self.__currentItem = None

        self.connect( GlobalData().project, SIGNAL( 'projectChanged' ),
                      self.__onProjectChanged )

        if Settings().showIgnoredExcViewer == False:
            self.__onShowHide( True )
        return

    def __createPopupMenu( self ):
        " Creates the popup menu "
        self.__excptMenu = QMenu()
        self.__removeMenuItem = self.__excptMenu.addAction(
                    "Remove from ignore list", self.__onRemoveFromIgnore )
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

        self.__excptLabel = QLabel( "Ignored exception types" )

        expandingSpacer = QSpacerItem( 10, 10, QSizePolicy.Expanding )
        fixedSpacer = QSpacerItem( 3, 3 )

        self.__showHideButton = QToolButton()
        self.__showHideButton.setAutoRaise( True )
        self.__showHideButton.setIcon( PixmapCache().getIcon( 'less.png' ) )
        self.__showHideButton.setFixedSize( 20, 20 )
        self.__showHideButton.setToolTip( "Hide ignored exceptions list" )
        self.__showHideButton.setFocusPolicy( Qt.NoFocus )
        self.connect( self.__showHideButton, SIGNAL( 'clicked()' ),
                      self.__onShowHide )

        headerLayout = QHBoxLayout()
        headerLayout.setContentsMargins( 1, 1, 1, 1 )
        headerLayout.addSpacerItem( fixedSpacer )
        headerLayout.addWidget( self.__excptLabel )
        headerLayout.addSpacerItem( expandingSpacer )
        headerLayout.addWidget( self.__showHideButton )
        self.headerFrame.setLayout( headerLayout )

        self.__exceptionsList = QTreeWidget( self )
        self.__exceptionsList.setSortingEnabled( False )
        self.__exceptionsList.setAlternatingRowColors( True )
        self.__exceptionsList.setRootIsDecorated( False )
        self.__exceptionsList.setItemsExpandable( True )
        self.__exceptionsList.setUniformRowHeights( True )
        self.__exceptionsList.setSelectionMode( QAbstractItemView.SingleSelection )
        self.__exceptionsList.setSelectionBehavior( QAbstractItemView.SelectRows )
        self.__exceptionsList.setItemDelegate( NoOutlineHeightDelegate( 4 ) )
        self.__exceptionsList.setContextMenuPolicy( Qt.CustomContextMenu )

        self.connect( self.__exceptionsList,
                      SIGNAL( "customContextMenuRequested(const QPoint &)" ),
                      self.__showContextMenu )
        self.connect( self.__exceptionsList, SIGNAL( "itemSelectionChanged()" ),
                      self.__onSelectionChanged )

        headerLabels = QStringList() << "Exception type"
        self.__exceptionsList.setHeaderLabels( headerLabels )

        self.__excTypeEdit = QLineEdit()
        self.__excTypeEdit.setFixedHeight( 26 )
        self.connect( self.__excTypeEdit, SIGNAL( 'textChanged(const QString &)' ),
                      self.__onNewFilterChanged )
        self.connect( self.__excTypeEdit, SIGNAL( 'returnPressed()' ),
                      self.__onAddExceptionFilter )
        self.__addButton = QPushButton( "Add" )
        self.__addButton.setFocusPolicy( Qt.NoFocus )
        self.__addButton.setEnabled( False )
        self.connect( self.__addButton, SIGNAL( 'clicked()' ),
                      self.__onAddExceptionFilter )

        expandingSpacer2 = QSpacerItem( 1, 1, QSizePolicy.Expanding )
        self.__removeButton = QToolButton()
        self.__removeButton.setIcon( PixmapCache().getIcon( 'ignexcptdel.png' ) )
        self.__removeButton.setFixedSize( 24, 24 )
        self.__removeButton.setToolTip( "Remove from the ignored exception type list" )
        self.__removeButton.setFocusPolicy( Qt.NoFocus )
        self.__removeButton.setEnabled( False )
        self.connect( self.__removeButton, SIGNAL( 'clicked()' ),
                      self.__onRemoveFromIgnore )

        fixedSpacer1 = QSpacerItem( 5, 5 )

        self.__removeAllButton = QToolButton()
        self.__removeAllButton.setIcon( PixmapCache().getIcon( 'ignexcptdelall.png' ) )
        self.__removeAllButton.setFixedSize( 24, 24 )
        self.__removeAllButton.setToolTip( "Remove all the ignored exception types" )
        self.__removeAllButton.setFocusPolicy( Qt.NoFocus )
        self.__removeAllButton.setEnabled( False )
        self.connect( self.__removeAllButton, SIGNAL( 'clicked()' ),
                      self.__onRemoveAllFromIgnore )

        toolbarLayout = QHBoxLayout()
        toolbarLayout.addSpacerItem( expandingSpacer2 )
        toolbarLayout.addWidget( self.__removeButton )
        toolbarLayout.addSpacerItem( fixedSpacer1 )
        toolbarLayout.addWidget( self.__removeAllButton )

        addLayout = QHBoxLayout()
        addLayout.setContentsMargins( 1, 1, 1, 1 )
        addLayout.setSpacing( 1 )
        addLayout.addWidget( self.__excTypeEdit )
        addLayout.addWidget( self.__addButton )

        verticalLayout.addWidget( self.headerFrame )
        verticalLayout.addLayout( toolbarLayout )
        verticalLayout.addWidget( self.__exceptionsList )
        verticalLayout.addLayout( addLayout )
        return

    def clear( self ):
        " Clears the content "
        self.__exceptionsList.clear()
        self.__excTypeEdit.clear()
        self.__addButton.setEnabled( False )
        self.__updateTitle()
        self.__currentItem = None
        return

    def __onShowHide( self, startup = False ):
        " Triggered when show/hide button is clicked "
        if startup or self.__exceptionsList.isVisible():
            self.__exceptionsList.setVisible( False )
            self.__excTypeEdit.setVisible( False )
            self.__addButton.setVisible( False )
            self.__removeButton.setVisible( False )
            self.__showHideButton.setIcon( PixmapCache().getIcon( 'more.png' ) )
            self.__showHideButton.setToolTip( "Show ignored exceptions list" )

            self.__minH = self.minimumHeight()
            self.__maxH = self.maximumHeight()

            self.setMinimumHeight( self.headerFrame.height() )
            self.setMaximumHeight( self.headerFrame.height() )

            Settings().showIgnoredExcViewer = False
        else:
            self.__exceptionsList.setVisible( True )
            self.__excTypeEdit.setVisible( True )
            self.__addButton.setVisible( True )
            self.__removeButton.setVisible( True )
            self.__showHideButton.setIcon( PixmapCache().getIcon( 'less.png' ) )
            self.__showHideButton.setToolTip( "Hide ignored exceptions list" )

            self.setMinimumHeight( self.__minH )
            self.setMaximumHeight( self.__maxH )

            Settings().showIgnoredExcViewer = True
        return

    def __onSelectionChanged( self ):
        " Triggered when the current item is changed "
        selected = list( self.__exceptionsList.selectedItems() )
        if selected:
            self.__currentItem = selected[ 0 ]
            self.__removeButton.setEnabled( True )
        else:
            self.__currentItem = None
            self.__removeButton.setEnabled( False )
        return

    def __showContextMenu( self, coord ):
        " Shows the frames list context menu "
        contextItem = self.__exceptionsList.itemAt( coord )
        if contextItem is not None:
            self.__currentItem = contextItem
            self.__excptMenu.popup( QCursor.pos() )
        return

    def __updateTitle( self ):
        " Updates the section title "
        count = self.__exceptionsList.topLevelItemCount()
        if count == 0:
            self.__excptLabel.setText( "Ignored exception types" )
        else:
            self.__excptLabel.setText( "Ignored exception types (total: " +
                                       str( count ) + ")" )
        self.__delAllButton.setEnabled( count != 0 )
        return

    def __onProjectChanged( self, what ):
        " Triggered when a project is changed "
        if what != CodimensionProject.CompleteProject:
            return

        self.clear()
        project = GlobalData().project
        if project.isLoaded():
            self.__ignored = list( project.ignoredExcpt )
        else:
            self.__ignored = list( Settings().ignoredExceptions )

        for exceptionType in self.__ignored:
            item = QTreeWidgetItem( self.__exceptionsList )
            item.setText( 0, exceptionType )
        self.__updateTitle()
        return

    def __onNewFilterChanged( self, text ):
        " Triggered when the text is changed "
        text = str( text ).strip()
        if text == "":
            self.__addButton.setEnabled( False )
            return
        if " " in text:
            self.__addButton.setEnabled( False )
            return

        if text in self.__ignored:
            self.__addButton.setEnabled( False )
            return

        self.__addButton.setEnabled( True )
        return

    def __onAddExceptionFilter( self ):
        " Adds an item into the ignored exceptions list "
        text = str( self.__excTypeEdit.text() ).strip()
        self.addExceptionFilter( text )

    def addExceptionFilter( self, excType ):
        " Adds a new item into the ignored exceptions list "
        if excType == "":
            return
        if " " in excType:
            return
        if excType in self.__ignored:
            return

        item = QTreeWidgetItem( self.__exceptionsList )
        item.setText( 0, excType )

        project = GlobalData().project
        if project.isLoaded():
            project.addExceptionFilter( excType )
        else:
            Settings().addExceptionFilter( excType )
        self.__ignored.append( excType )
        self.__updateTitle()
        return


    def __onRemoveFromIgnore( self ):
        " Removes an item from the ignored exception types list "
        if self.__currentItem is None:
            return

        text = self.__currentItem.text( 0 )

        # Find the item index and remove it
        index = 0
        while True:
            if self.__exceptionsList.topLevelItem( index ).text( 0 ) == text:
                self.__exceptionsList.takeTopLevelItem( index )
                break
            index += 1

        project = GlobalData().project
        if project.isLoaded():
            project.deleteExceptionFilter( text )
        else:
            Settings().deleteExceptionFilter( text )
        self.__ignored.remove( text )
        self.__updateTitle()
        return

    def __onRemoveAllFromIgnore( self ):
        " Triggered when all the ignored exceptions should be deleted "
        self.clear()
        return

    def isIgnored( self, exceptionType ):
        " Returns True if this exception type should be ignored "
        return exceptionType in self.__ignored

