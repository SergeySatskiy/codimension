# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2017  Sergey Satskiy <sergey.satskiy@gmail.com>
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

#
# The file was taken from eric 4 and adopted for codimension.
# Original copyright:
# Copyright (c) 2007 - 2013 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""Module implementing the Watch expression model"""

from ui.qt import QAbstractItemModel, Qt, QModelIndex


class WatchPointModel(QAbstractItemModel):

    """Class implementing a custom model for watch expressions"""

    def __init__(self, parent=None):
        QAbstractItemModel.__init__(self, parent)

        self.watchpoints = []
        self.header = ['Condition', 'Special', 'Temporary', 'Enabled',
                       'Ignore Count']
        self.alignments = [Qt.Alignment(Qt.AlignLeft),
                           Qt.Alignment(Qt.AlignLeft),
                           Qt.Alignment(Qt.AlignHCenter),
                           Qt.Alignment(Qt.AlignHCenter),
                           Qt.Alignment(Qt.AlignRight)]

    def columnCount(self, parent=QModelIndex()):
        """Provides the current column count"""
        return len(self.header) + 1

    def rowCount(self, parent=QModelIndex()):
        """Provides the current row count"""
        # we do not have a tree, parent should always be invalid
        if not parent.isValid():
            return len(self.watchpoints)
        return 0

    def data(self, index, role):
        """Provides the requested data"""
        if not index.isValid():
            return None

        if role == Qt.DisplayRole or role == Qt.ToolTipRole:
            if index.column() < len(self.header):
                return self.watchpoints[index.row()][index.column()]

        if role == Qt.TextAlignmentRole:
            if index.column() < len(self.alignments):
                return self.alignments[index.column()]

        return None

    def flags(self, index):
        """Provides the item flags"""
        if not index.isValid():
            return Qt.ItemIsEnabled
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Public method to get header data"""
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section >= len(self.header):
                return ""
            return self.header[section]
        return None

    def index(self, row, column, parent=QModelIndex()):
        """Creates the index"""
        if parent.isValid() or \
           row < 0 or row >= len(self.watchpoints) or \
           column < 0 or column >= len(self.header):
            return QModelIndex()
        return self.createIndex(row, column, self.watchpoints[row])

    def parent(self, index):
        """Provides the parent index"""
        return QModelIndex()

    def hasChildren(self, parent=QModelIndex()):
        """True if has children"""
        if not parent.isValid():
            return len(self.watchpoints) > 0
        return False

    def addWatchPoint(self, cond, special, properties):
        """Adds a new watch expression to the list"""
        wpoint = [cond, special] + list(properties)
        cnt = len(self.watchpoints)
        self.beginInsertRows(QModelIndex(), cnt, cnt)
        self.watchpoints.append(wpoint)
        self.endInsertRows()

    def setWatchPointByIndex(self, index, cond, special, properties):
        """Sets the values of a watch expression given by index"""
        if index.isValid():
            row = index.row()
            index1 = self.createIndex(row, 0, self.watchpoints[row])
            index2 = self.createIndex(row, len(self.watchpoints[row]),
                                      self.watchpoints[row])
            self.dataAboutToBeChanged.emit(index1, index2)
            i = 0
            for value in [cond, special] + list(properties):
                self.watchpoints[row][i] = value
                i += 1
            self.dataChanged.emit(index1, index2)

    def setWatchPointEnabledByIndex(self, index, enabled):
        """Sets the enabled state of a watch expression given by index"""
        if index.isValid():
            row = index.row()
            col = 3
            index1 = self.createIndex(row, col, self.watchpoints[row])
            self.dataAboutToBeChanged.emit(index1, index1)
            self.watchpoints[row][col] = enabled
            self.dataChanged.emit(index1, index1)

    def deleteWatchPointByIndex(self, index):
        """Sets the values of a watch expression given by index"""
        if index.isValid():
            row = index.row()
            self.beginRemoveRows(QModelIndex(), row, row)
            del self.watchpoints[row]
            self.endRemoveRows()

    def deleteWatchPoints(self, idxList):
        """Deletes a list of watch expressions given by their indexes"""
        rows = []
        for index in idxList:
            if index.isValid():
                rows.append(index.row())
        rows.sort(reverse=True)
        for row in rows:
            self.beginRemoveRows(QModelIndex(), row, row)
            del self.watchpoints[row]
            self.endRemoveRows()

    def deleteAll(self):
        """Deletes all watch expressions"""
        if self.watchpoints:
            self.beginRemoveRows(QModelIndex(), 0,
                                 len(self.watchpoints) - 1)
            self.watchpoints = []
            self.endRemoveRows()

    def getWatchPointByIndex(self, index):
        """Provides the values of a watch expression given by index"""
        if index.isValid():
            return self.watchpoints[index.row()][:] # return a copy
        return []

    def getWatchPointIndex(self, cond, special=""):
        """Provides the index of a watch expression given by expression"""
        for row in range(len(self.watchpoints)):
            wpoint = self.watchpoints[row]
            if wpoint[0] == cond:
                if special and wpoint[1] != special:
                    continue
                return self.createIndex(row, 0, self.watchpoints[row])
        return QModelIndex()
