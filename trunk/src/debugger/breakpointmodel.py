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
Module implementing the Breakpoint model
"""

from PyQt4.QtCore import ( QAbstractItemModel, QVariant, Qt, QModelIndex,
                           SIGNAL )


class BreakPointModel( QAbstractItemModel ):
    " Class implementing a custom model for breakpoints "

    def __init__(self, parent = None):
        QAbstractItemModel.__init__( self, parent )

        self.breakpoints = []
        self.header = [
            QVariant( 'File:line' ),
            QVariant( 'Condition' ),
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
        self.__columnCount = len( self.header )
        return

    def columnCount( self, parent = QModelIndex() ):
        " Provides the current column count "
        return self.__columnCount

    def rowCount( self, parent = QModelIndex() ):
        " Provides the current row count "

        # we do not have a tree, parent should always be invalid
        if not parent.isValid():
            return len( self.breakpoints )
        return 0

    def data( self, index, role ):
        " Provides the requested data "
        if not index.isValid():
            return QVariant()

        if role == Qt.DisplayRole:
            column = index.column()
            if column < self.__columnCount:
                bpoint = self.breakpoints[ index.row() ]
                if column == 0:
                    value = bpoint.getLocation()
                elif column == 1:
                    value = bpoint.getCondition()
                elif column == 2:
                    value = bpoint.isTemporary()
                elif column == 3:
                    value = bpoint.isEnabled()
                else:
                    value = bpoint.getIgnoreCount()
                return QVariant( value )
        if role == Qt.ToolTipRole:
            column = index.column()
            if column < self.__columnCount:
                return QVariant( self.breakpoints[ index.row() ].getTooltip() )
            else:
                return QVariant()

        if role == Qt.TextAlignmentRole:
            if index.column() < self.__columnCount:
                return self.alignments[ index.column() ]

        return QVariant()

    def flags( self, index ):
        """
        Public method to get item flags.

        @param index index of the requested flags (QModelIndex)
        @return item flags for the given index (Qt.ItemFlags)
        """
        if not index.isValid():
            return Qt.ItemIsEnabled

        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def headerData( self, section, orientation, role = Qt.DisplayRole ):
        " Provides header data "
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section < self.__columnCount:
                return self.header[ section ]
            return QVariant( "" )

        return QVariant()

    def index( self, row, column, parent = QModelIndex() ):
        " Creates an index "
        if parent.isValid() or \
           row < 0 or row >= len( self.breakpoints ) or \
           column < 0 or column >= len( self.header ):
            return QModelIndex()

        return self.createIndex( row, column, self.breakpoints[ row ] )

    def parent( self, index ):
        " Provides the parent index "
        return QModelIndex()

    def hasChildren( self, parent = QModelIndex() ):
        " Checks if there are child items "
        if not parent.isValid():
            return len( self.breakpoints ) > 0
        return False

    def addBreakpoint( self, bpoint ):
        " Adds a new breakpoint to the list "
        cnt = len( self.breakpoints )
        self.beginInsertRows( QModelIndex(), cnt, cnt )
        self.breakpoints.append( bpoint )
        self.endInsertRows()
        self.emit( SIGNAL( 'BreakpoinsChanged' ) )
        return

    def setBreakPointByIndex( self, index, bpoint ):
        " Set the values of a breakpoint given by index "

        if index.isValid():
            row = index.row()
            index1 = self.createIndex( row, 0, self.breakpoints[ row ] )
            index2 = self.createIndex( row, self.__columnCount - 1,
                                       self.breakpoints[ row ] )
            self.emit(
                SIGNAL( "dataAboutToBeChanged(const QModelIndex&, const QModelIndex&)" ),
                index1, index2 )

            self.breakpoints[ row ].update( bpoint )

            self.emit(
                SIGNAL( "dataChanged(const QModelIndex&, const QModelIndex&)" ),
                        index1, index2 )
        self.emit( SIGNAL( 'BreakpoinsChanged' ) )
        return

    def updateLineNumberByIndex( self, index, newLineNumber ):
        " Update the line number by index "

        if index.isValid():
            row = index.row()
            index1 = self.createIndex( row, 0, self.breakpoints[ row ] )
            index2 = self.createIndex( row, self.__columnCount - 1,
                                       self.breakpoints[ row ] )
            self.emit(
                SIGNAL( "dataAboutToBeChanged(const QModelIndex&, const QModelIndex&)" ),
                index1, index2 )

            self.breakpoints[ row ].updateLineNumber( newLineNumber )

            self.emit(
                SIGNAL( "dataChanged(const QModelIndex&, const QModelIndex&)" ),
                        index1, index2 )
        self.emit( SIGNAL( 'BreakpoinsChanged' ) )
        return

    def setBreakPointEnabledByIndex( self, index, enabled ):
        """
        Public method to set the enabled state of a breakpoint given by index.

        @param index index of the breakpoint (QModelIndex)
        @param enabled flag giving the enabled state (boolean)
        """
        if index.isValid():
            row = index.row()
            index1 = self.createIndex( row, 0, self.breakpoints[ row ] )
            index2 = self.createIndex( row, self.__columnCount - 1,
                                       self.breakpoints[ row ] )
            self.emit(
                SIGNAL( "dataAboutToBeChanged(const QModelIndex &, const QModelIndex &)" ),
                index1, index2 )
            self.breakpoints[ row ].setEnabled( enabled )
            self.emit(
                SIGNAL( "dataChanged(const QModelIndex&, const QModelIndex&)" ),
                        index1, index2 )
        self.emit( SIGNAL( 'BreakpoinsChanged' ) )
        return

    def deleteBreakPointByIndex( self, index ):
        " Deletes the breakpoint by its index "
        if index.isValid():
            row = index.row()
            self.beginRemoveRows( QModelIndex(), row, row )
            del self.breakpoints[ row ]
            self.endRemoveRows()
        self.emit( SIGNAL( 'BreakpoinsChanged' ) )
        return

    def deleteBreakPoints( self, idxList ):
        """
        Public method to delete a list of breakpoints given by their indexes.

        @param idxList list of breakpoint indexes (list of QModelIndex)
        """
        rows = []
        for index in idxList:
            if index.isValid():
                rows.append( index.row() )
        rows.sort( reverse = True )
        for row in rows:
            self.beginRemoveRows( QModelIndex(), row, row )
            del self.breakpoints[ row ]
            self.endRemoveRows()
        self.emit( SIGNAL( 'BreakpoinsChanged' ) )
        return

    def deleteAll( self ):
        " Deletes all breakpoints "
        if self.breakpoints:
            self.beginRemoveRows( QModelIndex(), 0,
                                  len( self.breakpoints ) - 1 )
            self.breakpoints = []
            self.endRemoveRows()
        self.emit( SIGNAL( 'BreakpoinsChanged' ) )
        return

    def getBreakPointByIndex( self, index ):
        " Provides a breakpoint by index "
        if index.isValid():
            return self.breakpoints[ index.row() ]
        return None

    def getBreakPointIndex( self, fname, lineno ):
        """
        Public method to get the index of a breakpoint
        given by filename and line number.

        @param fname filename of the breakpoint (string or QString)
        @param line line number of the breakpoint (integer)
        @return index (QModelIndex)
        """
        fname = unicode( fname )
        for row in xrange( len( self.breakpoints ) ):
            bpoint = self.breakpoints[ row ]
            if unicode( bpoint.getAbsoluteFileName() ) == fname and \
               bpoint.getLineNumber() == lineno:
                return self.createIndex( row, 0, self.breakpoints[ row ] )

        return QModelIndex()

    def isBreakPointTemporaryByIndex( self, index ):
        """
        Public method to test, if a breakpoint given by it's index is temporary.

        @param index index of the breakpoint to test (QModelIndex)
        @return flag indicating a temporary breakpoint (boolean)
        """
        if index.isValid():
            return self.breakpoints[ index.row() ].isTemporary()
        return False

    def getCounts( self ):
        " Provides enable/disable counters "
        enableCount = 0
        disableCount = 0
        for bp in self.breakpoints:
            if bp.isEnabled():
                enableCount += 1
            else:
                disableCount += 1
        return enableCount, disableCount
