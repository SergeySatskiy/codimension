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

""" The classes viewer implementation """

from PyQt4.QtCore       import Qt, SIGNAL, QSize, QRect
from PyQt4.QtGui        import QMenu, QWidget, QAction, QVBoxLayout, \
                               QToolBar, QCursor, QLabel, QSizePolicy, \
                               QItemSelectionModel
from combobox           import CDMComboBox
from utils.pixmapcache  import PixmapCache
from utils.globals      import GlobalData
from utils.project      import CodimensionProject
from classesbrowser     import ClassesBrowser
from viewitems          import DecoratorItemType, FunctionItemType, \
                               ClassItemType, AttributeItemType, GlobalItemType


class ClassesViewer( QWidget ):
    """ The classes viewer widget """

    def __init__( self, parent = None ):
        QWidget.__init__( self, parent )

        self.filterEdit = None
        self.definitionButton = None
        self.findButton = None
        self.copyPathButton = None
        self.clViewer = None
        self.__createLayout()

        # create the context menu
        self.__menu = QMenu( self )
        self.__jumpMenuItem = self.__menu.addAction( \
                                PixmapCache().getIcon( 'definition.png' ),
                                'Jump to definition', self.__goToDefinition )
        self.__menu.addSeparator()
        self.__findMenuItem = self.__menu.addAction( \
                                PixmapCache().getIcon( 'findusage.png' ),
                                'Find where used', self.__findWhereUsed )
        self.__menu.addSeparator()
        self.__copyMenuItem = self.__menu.addAction( \
                                PixmapCache().getIcon( 'copytoclipboard.png' ),
                                'Copy path to clipboard',
                                self.clViewer.copyToClipboard )
        self.clViewer.setContextMenuPolicy( Qt.CustomContextMenu )
        self.connect( self.clViewer,
                      SIGNAL( "customContextMenuRequested(const QPoint &)" ),
                      self.__handleShowContextMenu )

        self.connect( GlobalData().project, SIGNAL( 'projectChanged' ),
                      self.__onProjectChanged )
        self.connect( self.clViewer, SIGNAL( "selectionChanged" ),
                      self.__selectionChanged )
        self.connect( self.clViewer, SIGNAL( "openingItem" ),
                      self.itemActivated )

        self.filterEdit.lineEdit().setFocus()
        self.__contextItem = None
        return

    def __createLayout( self ):
        " Helper to create the viewer layout "

        self.clViewer = ClassesBrowser()

        # Toolbar part - buttons
        self.definitionButton = QAction( \
                PixmapCache().getIcon( 'definition.png' ),
                'Jump to highlighted class definition', self )
        self.connect( self.definitionButton, SIGNAL( "triggered()" ),
                      self.__goToDefinition )
        self.findButton = QAction( \
                PixmapCache().getIcon( 'findusage.png' ),
                'Find where highlighted class is used', self )
        self.connect( self.findButton, SIGNAL( "triggered()" ),
                      self.__findWhereUsed )
        self.copyPathButton = QAction( \
                PixmapCache().getIcon( 'copytoclipboard.png' ),
                'Copy path to clipboard', self )
        self.connect( self.copyPathButton, SIGNAL( "triggered()" ),
                      self.clViewer.copyToClipboard )

        self.findNotUsedButton = QAction( \
                PixmapCache().getIcon( 'notused.png' ),
                'Unused class analysis', self )
        self.connect( self.findNotUsedButton, SIGNAL( "triggered()" ),
                      self.__findNotUsed )

        toolbar = QToolBar( self )
        toolbar.setMovable( False )
        toolbar.setAllowedAreas( Qt.TopToolBarArea )
        toolbar.setIconSize( QSize( 16, 16 ) )
        toolbar.setFixedHeight( 28 )
        toolbar.setContentsMargins( 0, 0, 0, 0 )
        toolbar.addAction( self.definitionButton )
        toolbar.addAction( self.findButton )
        toolbar.addAction( self.copyPathButton )

        filterLabel = QLabel( "  Filter " )
        toolbar.addWidget( filterLabel )
        self.filterEdit = CDMComboBox( True, toolbar )
        self.filterEdit.setSizePolicy( QSizePolicy.Expanding,
                                       QSizePolicy.Expanding )
        self.filterEdit.lineEdit().setToolTip( "Space separated regular expressions" )
        toolbar.addWidget( self.filterEdit )
        toolbar.addAction( self.findNotUsedButton )
        self.connect( self.filterEdit,
                      SIGNAL( "editTextChanged(const QString &)" ),
                      self.__filterChanged )
        self.connect( self.filterEdit, SIGNAL( 'itemAdded' ),
                      self.__filterItemAdded )
        self.connect( self.filterEdit, SIGNAL( 'enterClicked' ),
                      self.__enterInFilter )

        layout = QVBoxLayout()
        layout.setContentsMargins( 0, 0, 0, 0 )
        layout.setSpacing( 0 )
        layout.addWidget( toolbar )
        layout.addWidget( self.clViewer )

        self.setLayout( layout )
        return

    def __filterChanged( self, text ):
        " Triggers when the filter text changed "
        self.clViewer.setFilter( text )
        self.clViewer.updateCounter()
        return

    def __selectionChanged( self, index ):
        " Handles the changed selection "
        if index is None:
            self.__contextItem = None
        else:
            self.__contextItem = self.clViewer.model().item( index )
        self.__updateButtons()
        return

    def itemActivated( self, path, line ):
        " Handles the item activation "
        self.filterEdit.addItem( self.filterEdit.lineEdit().text() )
        return

    def __filterItemAdded( self ):
        " The filter item has been added "
        project = GlobalData().project
        if project.fileName != "":
            project.setFindClassHistory( self.filterEdit.getItems() )
        return

    def __enterInFilter( self ):
        " ENTER key has been clicked in the filter "

        # check if there any records displayed
        if self.clViewer.model().rowCount() == 0:
            return

        # Move the focus to the list and select the first row
        self.clViewer.clearSelection()
        flags = QItemSelectionModel.SelectCurrent | QItemSelectionModel.Rows
        self.clViewer.setSelection( QRect( 0, 0, self.clViewer.width(), 1 ),
                                    flags )
        self.clViewer.setFocus()
        return

    def __onProjectChanged( self, what ):
        " Triggered when a project is changed "

        if what == CodimensionProject.CompleteProject:
            self.__contextItem = None
            self.__updateButtons()
            self.filterEdit.clear()

            project = GlobalData().project
            if project.isLoaded():
                self.disconnect( self.filterEdit,
                                 SIGNAL( "editTextChanged(const QString &)" ),
                                 self.__filterChanged )
                self.filterEdit.addItems( project.findClassHistory )
                self.connect( self.filterEdit,
                              SIGNAL( "editTextChanged(const QString &)" ),
                              self.__filterChanged )
                self.findNotUsedButton.setEnabled( True )
            else:
                self.findNotUsedButton.setEnabled( False )
            self.filterEdit.clearEditText()
        return

    def __handleShowContextMenu( self, coord ):
        """ Show the context menu """

        index = self.clViewer.indexAt( coord )
        if not index.isValid():
            return

        # This will update the __contextItem
        self.__selectionChanged( index )

        if self.__contextItem is None:
            return

        self.__jumpMenuItem.setEnabled( self.definitionButton.isEnabled() )
        self.__findMenuItem.setEnabled( self.findButton.isEnabled() )
        self.__copyMenuItem.setEnabled( self.copyPathButton.isEnabled() )

        self.__menu.popup( QCursor.pos() )
        return

    def __goToDefinition( self ):
        """ Jump to definition context menu handler """
        if self.__contextItem is not None:
            self.clViewer.openItem( self.__contextItem )
        return

    def __findWhereUsed( self ):
        """ Find where used context menu handler """
        if self.__contextItem is not None:
            GlobalData().mainWindow.findWhereUsed( \
                    self.__contextItem.getPath(),
                    self.__contextItem.sourceObj )
        return

    def __findNotUsed( self ):
        " Runs the unused class analysis "
        GlobalData().mainWindow.onNotUsedClasses()
        return

    def __updateButtons( self ):
        " Updates the toolbar buttons depending on what is selected "

        self.definitionButton.setEnabled( False )
        self.findButton.setEnabled( False )
        self.copyPathButton.setEnabled( False )
        if self.__contextItem is None:
            return

        if self.__contextItem.itemType == DecoratorItemType:
            self.definitionButton.setEnabled( True )
            self.copyPathButton.setEnabled( True )
            return

        if self.__contextItem.itemType in [ FunctionItemType, ClassItemType,
                                            AttributeItemType, GlobalItemType ]:
            self.definitionButton.setEnabled( True )
            self.findButton.setEnabled( True )
            self.copyPathButton.setEnabled( True )
        return

    def onFileUpdated( self, fileName, uuid ):
        " Triggered when the file is updated "
        self.clViewer.onFileUpdated( fileName )
        return

