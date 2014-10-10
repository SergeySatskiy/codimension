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

#
# The file was taken from eric 4 and adopted for codimension.
# Original copyright:
# Copyright (c) 2007 - 2013 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Watch expression model
"""

from PyQt4.QtCore import ( QAbstractItemModel, QVariant, Qt, QModelIndex,
                           SIGNAL )



class WatchPointModel( QAbstractItemModel ):
    " Class implementing a custom model for watch expressions "
    def __init__( self, parent = None ):
        QAbstractItemModel.__init__( self, parent )

        self.watchpoints = []
        self.header = [
            QVariant( 'Condition' ),
            QVariant( 'Special' ),
            QVariant( 'Temporary' ),
            QVariant( 'Enabled' ),
            QVariant( 'Ignore Count' ),
                      ]
        self.alignments = [
            QVariant( Qt.Alignment( Qt.AlignLeft ) ),
            QVariant( Qt.Alignment( Qt.AlignLeft ) ),
            QVariant( Qt.Alignment( Qt.AlignHCenter ) ),
            QVariant( Qt.Alignment( Qt.AlignHCenter ) ),
            QVariant( Qt.Alignment( Qt.AlignRight ) ),
                          ]
        return

    def columnCount( self, parent = QModelIndex() ):
        " Provides the current column count "
        return len( self.header ) + 1

    def rowCount( self, parent = QModelIndex() ):
        " Provides the current row count "
        # we do not have a tree, parent should always be invalid
        if not parent.isValid():
            return len( self.watchpoints )
        return 0

    def data( self, index, role ):
        """ Provides the requested data.

        @param index index of the requested data (QModelIndex)
        @param role role of the requested data (Qt.ItemDataRole)
        @return the requested data (QVariant)
        """
        if not index.isValid():
            return QVariant()

        if role == Qt.DisplayRole or role == Qt.ToolTipRole:
            if index.column() < len( self.header ):
                return QVariant(
                        self.watchpoints[ index.row() ][ index.column() ] )

        if role == Qt.TextAlignmentRole:
            if index.column() < len( self.alignments ):
                return self.alignments[ index.column() ]

        return QVariant()

    def flags( self, index ):
        """ Provides the item flags.

        @param index index of the requested flags (QModelIndex)
        @return item flags for the given index (Qt.ItemFlags)
        """
        if not index.isValid():
            return Qt.ItemIsEnabled

        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def headerData( self, section, orientation, role = Qt.DisplayRole ):
        """
        Public method to get header data.

        @param section section number of the requested header data (integer)
        @param orientation orientation of the header (Qt.Orientation)
        @param role role of the requested data (Qt.ItemDataRole)
        @return header data (QVariant)
        """
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section >= len( self.header ):
                return QVariant( "" )
            return self.header[ section ]

        return QVariant()

    def index( self, row, column, parent = QModelIndex() ):
        """
        Public method to create an index.

        @param row row number for the index (integer)
        @param column column number for the index (integer)
        @param parent index of the parent item (QModelIndex)
        @return requested index (QModelIndex)
        """
        if parent.isValid() or \
           row < 0 or row >= len( self.watchpoints ) or \
           column < 0 or column >= len( self.header ):
            return QModelIndex()

        return self.createIndex( row, column, self.watchpoints[ row ] )

    def parent( self, index ):
        """
        Public method to get the parent index.

        @param index index of item to get parent (QModelIndex)
        @return index of parent (QModelIndex)
        """
        return QModelIndex()

    def hasChildren( self, parent = QModelIndex() ):
        """
        Public method to check for the presence of child items.

        @param parent index of parent item (QModelIndex)
        @return flag indicating the presence of child items (boolean)
        """
        if not parent.isValid():
            return len( self.watchpoints ) > 0
        return False


    def addWatchPoint( self, cond, special, properties ):
        """
        Public method to add a new watch expression to the list.

        @param cond expression of the watch expression (string)
        @param special special condition of the watch expression (string)
        @param properties properties of the watch expression
            (tuple of temporary flag (bool), enabled flag (bool), ignore count (integer))
        """
        wpoint = [ unicode( cond ), unicode( special ) ] + list( properties )
        cnt = len( self.watchpoints )
        self.beginInsertRows( QModelIndex(), cnt, cnt )
        self.watchpoints.append( wpoint )
        self.endInsertRows()
        return

    def setWatchPointByIndex( self, index, cond, special, properties ):
        """
        Public method to set the values of a watch expression given by index.

        @param index index of the watch expression (QModelIndex)
        @param cond expression of the watch expression (string)
        @param special special condition of the
               watch expression (string)
        @param properties properties of the watch expression
            (tuple of temporary flag (bool), enabled flag (bool),
                      ignore count (integer))
        """
        if index.isValid():
            row = index.row()
            index1 = self.createIndex( row, 0, self.watchpoints[row] )
            index2 = self.createIndex( row, len( self.watchpoints[ row ] ),
                                       self.watchpoints[ row ] )
            self.emit(
                SIGNAL( "dataAboutToBeChanged(const QModelIndex&, const QModelIndex&)"),
                index1, index2 )
            i = 0
            for value in [ unicode( cond ), unicode( special ) ] + \
                         list( properties ):
                self.watchpoints[ row ][ i ] = value
                i += 1
            self.emit(
                SIGNAL( "dataChanged(const QModelIndex&, const QModelIndex&)" ),
                        index1, index2 )
        return

    def setWatchPointEnabledByIndex( self, index, enabled ):
        """
        Public method to set the enabled state of a
        watch expression given by index.

        @param index index of the watch expression (QModelIndex)
        @param enabled flag giving the enabled state (boolean)
        """
        if index.isValid():
            row = index.row()
            col = 3
            index1 = self.createIndex( row, col, self.watchpoints[ row ] )
            self.emit(
                SIGNAL( "dataAboutToBeChanged(const QModelIndex&, const QModelIndex&)" ),
                        index1, index1 )
            self.watchpoints[ row ][ col ] = enabled
            self.emit(
                SIGNAL( "dataChanged(const QModelIndex&, const QModelIndex&)" ),
                        index1, index1 )
        return

    def deleteWatchPointByIndex( self, index ):
        """
        Public method to set the values of a watch expression given by index.

        @param index index of the watch expression (QModelIndex)
        """
        if index.isValid():
            row = index.row()
            self.beginRemoveRows( QModelIndex(), row, row )
            del self.watchpoints[ row ]
            self.endRemoveRows()
        return

    def deleteWatchPoints( self, idxList ):
        """
        Public method to delete a list of watch expressions
        given by their indexes.

        @param idxList list of watch expression indexes (list of QModelIndex)
        """
        rows = []
        for index in idxList:
            if index.isValid():
                rows.append(index.row())
        rows.sort(reverse = True)
        for row in rows:
            self.beginRemoveRows( QModelIndex(), row, row )
            del self.watchpoints[ row ]
            self.endRemoveRows()
        return

    def deleteAll( self ):
        " Deletes all watch expressions "
        if self.watchpoints:
            self.beginRemoveRows( QModelIndex(), 0,
                                  len( self.watchpoints ) - 1 )
            self.watchpoints = []
            self.endRemoveRows()
        return

    def getWatchPointByIndex( self, index ):
        """
        Public method to get the values of a watch expression given by index.

        @param index index of the watch expression (QModelIndex)
        @return watch expression (list of six values (expression,
                special condition, temporary flag, enabled flag,
                ignore count, index))
        """
        if index.isValid():
            return self.watchpoints[ index.row() ][ : ] # return a copy
        return []

    def getWatchPointIndex( self, cond, special = "" ):
        """
        Public method to get the index of a watch expression
        given by expression.

        @param cond expression of the watch expression (string)
        @param special special condition of the
               watch expression (string)
        @return index (QModelIndex)
        """
        cond = unicode( cond )
        special = unicode( special )
        for row in xrange( len( self.watchpoints ) ):
            wpoint = self.watchpoints[ row ]
            if unicode( wpoint[ 0 ] ) == cond:
                if special and unicode( wpoint[ 1 ] ) != special:
                    continue
                return self.createIndex( row, 0, self.watchpoints[ row ] )

        return QModelIndex()
