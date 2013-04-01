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

""" The debugger namespace viewer implementation """

from PyQt4.QtCore import ( Qt, SIGNAL, QModelIndex, QRegExp,
                           QAbstractItemModel, QVariant )
from PyQt4.QtGui import ( QSortFilterProxyModel, QAbstractItemView,
                          QTreeView, QHeaderView )
from utils.pixmapcache import PixmapCache
from ui.itemdelegates  import NoOutlineHeightDelegate



class VariableItemRoot( object ):
    " Variables list root item "
    def __init__( self, values ):
        self.itemData = values
        self.childItems = []
        self.childItemsSize = 0
        return

    def columnCount( self ):
        " Provides the number of columns "
        return len( self.itemData )

    def data( self, column ):
        " Provides a value of the given column "
        try:
            return self.itemData[ column ]
        except:
            return ""

    def appendChild( self, child ):
        " Add a child item "
        self.childItems.append( child )
        self.childItemsSize += 1
        return

    def childCount( self ):
        " Provides the number of children "
        return self.childItemsSize

    def removeChildren( self ):
        " Removes all the children "
        self.childItems = []
        self.childItemsSize = 0
        return

    def child( self, row ):
        " Provides a reference to a child "
        return self.childItems[ row ]

    def parent( self ):
        " Provides a reference to the parent item "
        return None

    def lessThan( self, other, column, order ):
        " Check, if the item is less than another "
        try:
            self.itemData[ column ] < other.itemData[ column ]
        except:
            return False


class VariableItem( object ):
    " Represents a single variable item "
    def __init__( self, parent, isGlobal, varName, varType, varValue ):
        self.parentItem = parent
        if isGlobal:
            self.icon = PixmapCache().getIcon( 'globvar.png' )
        else:
            self.icon = PixmapCache().getIcon( 'locvar.png' )
        return




class VariablesModel( QAbstractItemModel ):
    " Find file data model implementation "

    def __init__( self, parent = None ):
        QAbstractItemModel.__init__( self, parent )

        self.rootItem = VariableItemRoot( [ "Name", "Type", "Representation" ] )
        self.count = 0
        return

    def populateModel( self, variables ):
        " Populates the variables model "
        self.clear()
        return

    def columnCount( self, parent = QModelIndex() ):
        " Provides the number of columns "
        if parent.isValid():
            return parent.internalPointer().columnCount()
        return self.rootItem.columnCount()

    def rowCount( self, parent = QModelIndex() ):
        " Provides the number of rows "

        # Only the first column should have children
        if parent.column() > 0:
            return 0

        if not parent.isValid():
            return self.rootItem.childCount()

        parentItem = parent.internalPointer()
        return parentItem.childCount()

    def data( self, index, role ):
        " Provides data of an item "
        if not index.isValid():
            return QVariant()

        if role == Qt.DisplayRole:
            item = index.internalPointer()
            if index.column() < item.columnCount():
                return QVariant( item.data( index.column() ) )
            elif index.column() == item.columnCount() and \
                 index.column() < self.columnCount( self.parent( index ) ):
                # This is for the case when an item under a multi-column
                # parent doesn't have a value for all the columns
                return QVariant( "" )
        elif role == Qt.DecorationRole:
            if index.column() == 0:
                return QVariant( index.internalPointer().icon )
        elif role == Qt.ToolTipRole:
            item = index.internalPointer()
            if item.tooltip != "":
                return QVariant( item.tooltip )

        return QVariant()

    def flags( self, index ):
        " Provides the item flags "
        if not index.isValid():
            return Qt.ItemIsEnabled
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def headerData( self, section, orientation, role = Qt.DisplayRole ):
        " Provides the header data "
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section >= self.rootItem.columnCount():
                return QVariant( "" )
            return self.rootItem.data( section )
        return QVariant()

    def index( self, row, column, parent = QModelIndex() ):
        " Creates an index "

        # The model/view framework considers negative values out-of-bounds,
        # however in python they work when indexing into lists. So make sure
        # we return an invalid index for out-of-bounds row/col
        if row < 0 or column < 0 or \
           row >= self.rowCount( parent ) or \
           column >= self.columnCount( parent ):
            return QModelIndex()

        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        try:
            childItem = parentItem.child( row )
        except IndexError:
            childItem = None
            return QModelIndex()

        if childItem:
            return self.createIndex( row, column, childItem )
        return QModelIndex()

    def parent( self, index ):
        " Provides the index of the parent object "

        if not index.isValid():
            return QModelIndex()

        childItem = index.internalPointer()
        parentItem = childItem.parent()

        if parentItem == self.rootItem:
            return QModelIndex()

        return self.createIndex( parentItem.row(), 0, parentItem )

    def hasChildren( self, parent = QModelIndex() ):
        " Checks for the presence of child items "

        # Only the first column should have children
        if parent.column() > 0:
            return False

        if not parent.isValid():
            return self.rootItem.childCount() > 0
        return parent.internalPointer().childCount() > 0

    def clear( self ):
        " Clears the model "
        self.rootItem.removeChildren()
        self.reset()
        return

    def item( self, index ):
        " Provides a reference to an item "
        if not index.isValid():
            return None
        return index.internalPointer()



class VariablesSortFilterProxyModel( QSortFilterProxyModel ):
    " Variables sort filter proxy model "

    def __init__( self, parent = None ):
        QSortFilterProxyModel.__init__( self, parent )
        self.__sortColumn = None    # Avoid pylint complains
        self.__sortOrder = None     # Avoid pylint complains

        self.__filters = []
        self.__filtersCount = 0
        self.__sourceModelRoot = None
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

    def setFilter( self, text ):
        " Sets the new filters "
        self.__filters = []
        self.__filtersCount = 0
        self.__sourceModelRoot = None
        for part in str( text ).strip().split():
            regexp = QRegExp( part, Qt.CaseInsensitive, QRegExp.RegExp2 )
            self.__filters.append( regexp )
            self.__filtersCount += 1
        self.__sourceModelRoot = self.sourceModel().rootItem
        return

    def filterAcceptsRow( self, sourceRow, sourceParent ):
        " Filters rows "
        if self.__filtersCount == 0 or self.__sourceModelRoot is None:
            return True     # No filters

        return True
        nameToMatch = self.__sourceModelRoot.child( sourceRow ).basename
        for regexp in self.__filters:
            if regexp.indexIn( nameToMatch ) == -1:
                return False
        return True


class VariablesBrowser( QTreeView ):
    " Variables browser implementation "

    def __init__( self, parent = None ):
        QTreeView.__init__( self, parent )

        self.__parentDialog = parent
        self.__model = VariablesModel()
        self.__sortModel = VariablesSortFilterProxyModel()
        self.__sortModel.setDynamicSortFilter( True )
        self.__sortModel.setSourceModel( self.__model )
        self.setModel( self.__sortModel )
        self.selectedIndex = None

        self.connect( self, SIGNAL( "activated(const QModelIndex &)" ),
                      self.openCurrentItem )

        self.setRootIsDecorated( False )
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
        return

    def selectionChanged( self, selected, deselected ):
        " Slot is called when the selection has been changed "
        if selected.indexes():
            self.selectedIndex = selected.indexes()[ 0 ]
        else:
            self.selectedIndex = None
        QTreeView.selectionChanged( self, selected, deselected )
        return

    def layoutDisplay( self ):
        " Performs the layout operation "
        self.doItemsLayout()
        self.header().resizeSections( QHeaderView.ResizeToContents )
        self.header().setStretchLastSection( True )
        self._resort()
        return

    def _resort( self ):
        " Re-sorts the tree "
        self.model().sort( self.header().sortIndicatorSection(),
                           self.header().sortIndicatorOrder() )
        return

    def openCurrentItem( self ):
        " Triggers when an item is clicked or double clicked "
        if self.selectedIndex is None:
            return
        item = self.model().item( self.selectedIndex )
        self.openItem( item )
        return

    def openItem( self, item ):
        " Handles the case when an item is activated "
        print "Item requested to open"
        return

    def getTotal( self ):
        " Provides the total number of items "
        return self.model().sourceModel().count

    def getVisible( self ):
        " Provides the number of currently visible items "
        return self.model().rowCount()

    def setFilter( self, text ):
        " Called when the filter has been changed "
        # Notify the filtering model of the new filters
        self.model().setFilter( text )

        # This is to trigger filtering - ugly but I don't know how else
        self.model().setFilterRegExp( "" )
        return
