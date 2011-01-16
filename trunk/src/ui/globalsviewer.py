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

""" The globals viewer implementation """

from PyQt4.QtCore       import Qt, SIGNAL, QSize, QRegExp
from PyQt4.QtGui        import QMenu, QWidget, QAction, QVBoxLayout, \
                               QToolBar, QCursor, QLabel, QSizePolicy
from combobox           import CDMComboBox
from utils.pixmapcache  import PixmapCache
from utils.globals      import GlobalData
from utils.project      import CodimensionProject
from globalsbrowser     import GlobalsBrowser
from viewitems          import DecoratorItemType, FunctionItemType, \
                               ClassItemType, AttributeItemType, GlobalItemType


class GlobalsViewer( QWidget ):
    """ The globals viewer widget """

    def __init__( self, parent = None ):
        QWidget.__init__( self, parent )

        self.filterEdit = None
        self.definitionButton = None
        self.findButton = None
        self.globalsViewer = None
        self.copyPathButton = None
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
                                self.globalsViewer.copyToClipboard )
        self.globalsViewer.setContextMenuPolicy( Qt.CustomContextMenu )
        self.connect( self.globalsViewer,
                      SIGNAL( "customContextMenuRequested(const QPoint &)" ),
                      self.__handleShowContextMenu )

        self.connect( GlobalData().project, SIGNAL( 'projectChanged' ),
                      self.__onProjectChanged )
        self.connect( self.globalsViewer,
                      SIGNAL( "clicked(const QModelIndex &)" ),
                      self.__selectionChanged )

        self.filterEdit.lineEdit().setFocus()
        self.__contextItem = None
        return

    def __createLayout( self ):
        " Helper to create the viewer layout "

        self.globalsViewer = GlobalsBrowser()

        # Toolbar part - buttons
        self.definitionButton = QAction( \
                PixmapCache().getIcon( 'definition.png' ),
                'Jump to highlighted global variable definition', self )
        self.connect( self.definitionButton, SIGNAL( "triggered()" ),
                      self.__goToDefinition )
        self.findButton = QAction( \
                PixmapCache().getIcon( 'findusage.png' ),
                'Find where highlighted global variable is used', self )
        self.connect( self.findButton, SIGNAL( "triggered()" ),
                      self.__findWhereUsed )
        self.copyPathButton = QAction( \
                PixmapCache().getIcon( 'copytoclipboard.png' ),
                'Copy path to clipboard', self )
        self.connect( self.copyPathButton, SIGNAL( "triggered()" ),
                      self.globalsViewer.copyToClipboard )

        toolbar = QToolBar()
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
        self.filterEdit = CDMComboBox()
        self.filterEdit.setSizePolicy( QSizePolicy.Expanding,
                                       QSizePolicy.Expanding )
        self.filterEdit.setToolTip( "Type regular expression " \
                                    "or text to filter" )
        toolbar.addWidget( self.filterEdit )
        self.connect( self.filterEdit,
                      SIGNAL( "editTextChanged(const QString &)" ),
                      self.__filterChanged )

        layout = QVBoxLayout()
        layout.setContentsMargins( 0, 0, 0, 0 )
        layout.setSpacing( 0 )
        layout.addWidget( toolbar )
        layout.addWidget( self.globalsViewer )

        self.setLayout( layout )
        return

    def __filterChanged( self, text ):
        " Triggers when the filter text changed "
        regexp = QRegExp( text, Qt.CaseInsensitive, QRegExp.RegExp2 )
        self.globalsViewer.setFilter( regexp )
        return

    def __selectionChanged( self, index ):
        " Handles the changed selection "
        self.__contextItem = self.globalsViewer.model().item( index )
        self.__updateButtons()
        return

    def __onProjectChanged( self, what ):
        " Triggered when a project is changed "

        if what == CodimensionProject.CompleteProject:
            self.__contextItem = None
            self.__updateButtons()
            self.filterEdit.clear()
            self.filterEdit.clearEditText()
        return

    def __handleShowContextMenu( self, coord ):
        """ Show the context menu """

        index = self.globalsViewer.indexAt( coord )
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
            self.openItem( self.__contextItem )
        return

    def __findWhereUsed( self ):
        """ Find where used context menu handler """

        if self.__contextItem is not None:
            GlobalData().mainWindow.findWhereUsed( \
                    self.__contextItem.getPath(),
                    self.__contextItem.sourceObj )
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
        self.globalsViewer.onFileUpdated( fileName )
        return

