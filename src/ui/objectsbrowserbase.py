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


" Base and auxiliary classes for G/F/C browsers "


from PyQt4.QtCore  import Qt, QModelIndex, SIGNAL
from PyQt4.QtGui   import QAbstractItemView, QApplication, \
                          QSortFilterProxyModel, QTreeView
from utils.globals import GlobalData
from utils.project import CodimensionProject
from viewitems     import NoItemType, DirectoryItemType, \
                          SysPathItemType, GlobalsItemType, ImportsItemType, \
                          FunctionsItemType, ClassesItemType, \
                          StaticAttributesItemType, InstanceAttributesItemType
from itemdelegates import NoOutlineHeightDelegate



class ObjectsBrowserSortFilterProxyModel( QSortFilterProxyModel ):
    """
    Objects (globals, functions, classes) browser sort filter proxy model
    implementation. It allows filtering basing on top level items.
    """

    def __init__( self, parent = None ):
        QSortFilterProxyModel.__init__( self, parent )
        self.__sortColumn = None    # Avoid pylint complains
        self.__sortOrder = None     # Avoid pylint complains
        return

    def sort( self, column, order ):
        " Sorts the items "
        self.__sortColumn = column
        self.__sortOrder = order
        QSortFilterProxyModel.sort( self, column, order )
        return

    def lessThan( self, left, right ):
        " Sorts the displayed items "
        lhs = left.model() and left.model().item( left ) or None
        rhs = right.model() and right.model().item( right ) or None

        if lhs and rhs:
            return lhs.lessThan( rhs, self.__sortColumn, self.__sortOrder )
        return False

    def item( self, index ):
        " Provides a reference to the item "
        if not index.isValid():
            return None

        sourceIndex = self.mapToSource( index )
        return self.sourceModel().item( sourceIndex )

    def hasChildren( self, parent = QModelIndex() ):
        " Checks the presence of the child items "
        sourceIndex = self.mapToSource( parent )
        return self.sourceModel().hasChildren( sourceIndex )

    def filterAcceptsRow( self, sourceRow, sourceParent ):
        " Filters rows "
        if not sourceParent.isValid():
            return QSortFilterProxyModel.filterAcceptsRow( self, sourceRow,
                                                           sourceParent )

        # Filter top level items only
        item = sourceParent.internalPointer()
        if item.itemType == NoItemType:
            # This is the top level item
            return QSortFilterProxyModel.filterAcceptsRow( self, sourceRow,
                                                           sourceParent )
        # Show all the nested items
        return True



class ObjectsBrowser( QTreeView ):
    " Common functionality of the G/F/C browsers "

    def __init__( self, sourceModel, parent = None ):
        QTreeView.__init__(self, parent)

        self.__model = sourceModel
        self.__sortModel = ObjectsBrowserSortFilterProxyModel()
        self.__sortModel.setDynamicSortFilter( True )
        self.__sortModel.setSourceModel( self.__model )
        self.setModel( self.__sortModel )
        self.contextItem = None

        self.connect( self, SIGNAL( "activated(const QModelIndex &)" ),
                      self._openItem )
        self.connect( self, SIGNAL( "expanded(const QModelIndex &)" ),
                      self._resizeColumns )
        self.connect( self, SIGNAL( "collapsed(const QModelIndex &)" ),
                      self._resizeColumns )

        self.setRootIsDecorated( True )
        self.setAlternatingRowColors( True )
        self.setUniformRowHeights( True )
        self.setItemDelegate( NoOutlineHeightDelegate( 4 ) )

        header = self.header()
        header.setSortIndicator( 0, Qt.AscendingOrder )
        header.setSortIndicatorShown( True )
        header.setClickable( True )

        self.setSortingEnabled( True )

        self.setSelectionMode( QAbstractItemView.SingleSelection )
        self.setSelectionBehavior( QAbstractItemView.SelectRows )

        self.layoutDisplay()

        self.connect( GlobalData().project, SIGNAL( 'projectChanged' ),
                      self.__onProjectChanged )
        return

    def __onProjectChanged( self, what ):
        " Triggered when a project is changed "

        if what == CodimensionProject.CompleteProject:
            self.__model.reset()
            self.layoutDisplay()
        return

    def setFilter( self, regexp ):
        " Sets the new filter for items "
        self.model().setFilterRegExp( regexp )

        # No need to resort but need to resize columns
        self.doItemsLayout()
        self._resizeColumns( QModelIndex() )
        return

    def layoutDisplay( self ):
        " Performs the layout operation "
        self.doItemsLayout()
        self._resizeColumns( QModelIndex() )
        self._resort()
        return

    def _resizeColumns( self, index ):
        " Resizes the view when items get expanded or collapsed "

        rowCount = self.model().rowCount()
        columnCount = self.model().columnCount()
        self.header().setStretchLastSection( rowCount == 0 )

        index = 0
        while index < columnCount - 1:
            width = max( 100, self.sizeHintForColumn( index ) )
            self.header().resizeSection( index, width )
            index += 1

        # The last column is 'Line' so it should be narrower
        width = max( 40, self.sizeHintForColumn( index ) )
        self.header().resizeSection( index, width )
        return

    def _resort( self ):
        " Re-sorts the tree "
        self.model().sort( self.header().sortIndicatorSection(),
                           self.header().sortIndicatorOrder() )
        return

    def mouseDoubleClickEvent( self, mouseEvent ):
        """
        Reimplemented to disable expanding/collapsing of items when
        double-clicking. Instead the double-clicked entry is opened.
        """

        index = self.indexAt( mouseEvent.pos() )
        if not index.isValid():
            return

        item = self.model().item( index )
        if item.itemType in [ GlobalsItemType,
                              ImportsItemType, FunctionsItemType,
                              ClassesItemType, StaticAttributesItemType,
                              InstanceAttributesItemType,
                              DirectoryItemType, SysPathItemType ]:
            QTreeView.mouseDoubleClickEvent( self, mouseEvent )
        else:
            self.openItem( item )
        return

    def _openItem( self ):
        " Triggers when an item is clicked or double clicked "
        item = self.model().item( self.currentIndex() )
        self.openItem( item )
        return

    def openItem( self, item ):
        " Handles the case when an item is activated "
        if item.itemType in [ GlobalsItemType,
                              ImportsItemType, FunctionsItemType,
                              ClassesItemType, StaticAttributesItemType,
                              InstanceAttributesItemType,
                              DirectoryItemType, SysPathItemType ]:
            return
        GlobalData().mainWindow.openFile( item.getPath(), item.data( 2 ) )
        return

    def copyToClipboard( self ):
        " Copies the path to the file where the element is to the clipboard "
        item = self.model().item( self.currentIndex() )
        QApplication.clipboard().setText( item.getPath() )
        return

    def onFileUpdated( self, fileName ):
        " Triggered when the file is updated "
        self.model().sourceModel().onFileUpdated( fileName )
        return

