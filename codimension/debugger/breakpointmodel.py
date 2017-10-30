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

"""Module implementing the Breakpoint model"""

from ui.qt import pyqtSignal, QAbstractItemModel, Qt, QModelIndex


COLUMN_LOCATION = 2
COLUMN_CONDITION = 3
COLUMN_TEMPORARY = 1
COLUMN_ENABLED = 0
COLUMN_IGNORE_COUNT = 4


class BreakPointModel(QAbstractItemModel):

    """Class implementing a custom model for breakpoints"""

    sigDataAboutToBeChanged = pyqtSignal(QModelIndex, QModelIndex)
    sigBreakpoinsChanged = pyqtSignal()

    def __init__(self, parent=None):
        QAbstractItemModel.__init__(self, parent)

        self.breakpoints = []

        self.__fields = {
            COLUMN_LOCATION: ['File:line', Qt.Alignment(Qt.AlignLeft)],
            COLUMN_CONDITION: ['Condition', Qt.Alignment(Qt.AlignLeft)],
            COLUMN_TEMPORARY: ['T', Qt.Alignment(Qt.AlignHCenter)],
            COLUMN_ENABLED: ['E', Qt.Alignment(Qt.AlignHCenter)],
            COLUMN_IGNORE_COUNT: ['Ignore Count', Qt.Alignment(Qt.AlignRight)]}
        self.__columnCount = len(self.__fields)

    def columnCount(self, parent=None):
        """Provides the current column count"""
        return self.__columnCount

    def rowCount(self, parent=None):
        """Provides the current row count"""
        # we do not have a tree, parent should always be invalid
        if parent is None or not parent.isValid():
            return len(self.breakpoints)
        return 0

    def data(self, index, role=Qt.DisplayRole):
        """Provides the requested data"""
        if not index.isValid():
            return None

        column = index.column()
        row = index.row()
        if role == Qt.DisplayRole:
            if column == COLUMN_LOCATION:
                return self.breakpoints[row].getLocation()
            if column == COLUMN_CONDITION:
                return self.breakpoints[row].getCondition()
            if column == COLUMN_IGNORE_COUNT:
                return self.breakpoints[row].getIgnoreCount()
        elif role == Qt.CheckStateRole:
            if column == COLUMN_TEMPORARY:
                return self.breakpoints[row].isTemporary()
            if column == COLUMN_ENABLED:
                return self.breakpoints[row].isEnabled()
        elif role == Qt.ToolTipRole:
            if column < self.__columnCount:
                return self.breakpoints[row].getTooltip()
        elif role == Qt.TextAlignmentRole:
            if column < self.__columnCount:
                return self.__fields[column][1]
        return None

    def setData(self, index, _, role=Qt.EditRole):
        """Change data in the model"""
        if index.isValid():
            if role == Qt.CheckStateRole:
                column = index.column()
                if column in [COLUMN_TEMPORARY, COLUMN_ENABLED]:
                    # Flip the boolean
                    row = index.row()
                    bp = self.breakpoints[row]

                    self.sigDataAboutToBeChanged.emit(index, index)
                    if column == COLUMN_TEMPORARY:
                        bp.setTemporary(not bp.isTemporary())
                    else:
                        bp.setEnabled(not bp.isEnabled())
                    self.dataChanged.emit(index, index)
                    self.sigBreakpoinsChanged.emit()
                    return True
        return False

    def flags(self, index):
        """Provides the item flags"""
        if not index.isValid():
            return Qt.ItemIsEnabled

        column = index.column()
        if column in [COLUMN_TEMPORARY, COLUMN_ENABLED]:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Provides header data"""
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section < self.__columnCount:
                return self.__fields[section][0]
            return ""
        return None

    def index(self, row, column, parent=None):
        """Creates an index"""
        if (parent and parent.isValid()) or \
           row < 0 or row >= len(self.breakpoints) or \
           column < 0 or column >= self.__columnCount:
            return QModelIndex()

        return self.createIndex(row, column, self.breakpoints[row])

    def parent(self, index):
        """Provides the parent index"""
        return QModelIndex()

    def hasChildren(self, parent=None):
        """Checks if there are child items"""
        if parent is None or not parent.isValid():
            return len(self.breakpoints) > 0
        return False

    def addBreakpoint(self, bpoint):
        """Adds a new breakpoint to the list"""
        cnt = len(self.breakpoints)
        self.beginInsertRows(QModelIndex(), cnt, cnt)
        self.breakpoints.append(bpoint)
        self.endInsertRows()
        self.sigBreakpoinsChanged.emit()

    def setBreakPointByIndex(self, index, bpoint):
        """Set the values of a breakpoint given by index"""
        if index.isValid():
            row = index.row()
            index1 = self.createIndex(row, 0, self.breakpoints[row])
            index2 = self.createIndex(row, self.__columnCount - 1,
                                      self.breakpoints[row])

            self.sigDataAboutToBeChanged.emit(index1, index2)
            self.breakpoints[row].update(bpoint)
            self.dataChanged.emit(index1, index2)
            self.sigBreakpoinsChanged.emit()

    def updateLineNumberByIndex(self, index, newLineNumber):
        """Update the line number by index"""
        if index.isValid():
            row = index.row()
            index1 = self.createIndex(row, 0, self.breakpoints[row])
            index2 = self.createIndex(row, self.__columnCount - 1,
                                      self.breakpoints[row])

            self.sigDataAboutToBeChanged.emit(index1, index2)
            self.breakpoints[row].updateLineNumber(newLineNumber)
            self.dataChanged.emit(index1, index2)
            self.sigBreakpoinsChanged.emit()

    def setBreakPointEnabledByIndex(self, index, enabled):
        """Sets the enable state"""
        if index.isValid():
            row = index.row()
            index1 = self.createIndex(row, 0, self.breakpoints[row])
            index2 = self.createIndex(row, self.__columnCount - 1,
                                      self.breakpoints[row])

            self.sigDataAboutToBeChanged.emit(index1, index2)
            self.breakpoints[row].setEnabled(enabled)
            self.dataChanged.emit(index1, index2)
            self.sigBreakpoinsChanged.emit()

    def deleteBreakPointByIndex(self, index):
        """Deletes the breakpoint by its index"""
        if index.isValid():
            row = index.row()
            self.beginRemoveRows(QModelIndex(), row, row)
            del self.breakpoints[row]
            self.endRemoveRows()
            self.sigBreakpoinsChanged.emit()

    def deleteBreakPoints(self, idxList):
        """Deletes a list of breakpoints"""
        rows = []
        for index in idxList:
            if index.isValid():
                rows.append(index.row())
        rows.sort(reverse=True)
        for row in rows:
            self.beginRemoveRows(QModelIndex(), row, row)
            del self.breakpoints[row]
            self.endRemoveRows()
        self.sigBreakpoinsChanged.emit()

    def deleteAll(self):
        """Deletes all breakpoints"""
        if self.breakpoints:
            self.beginRemoveRows(QModelIndex(), 0, len(self.breakpoints) - 1)
            self.breakpoints = []
            self.endRemoveRows()
            self.sigBreakpoinsChanged.emit()

    def getBreakPointByIndex(self, index):
        """Provides a breakpoint by index"""
        if index.isValid():
            return self.breakpoints[index.row()]
        return None

    def getBreakPointIndex(self, fname, lineno):
        """Provides an index of a breakpoint"""
        for row in range(len(self.breakpoints)):
            bpoint = self.breakpoints[row]
            if bpoint.getAbsoluteFileName() == fname and \
               bpoint.getLineNumber() == lineno:
                return self.createIndex(row, 0, self.breakpoints[row])
        return QModelIndex()

    def isBreakPointTemporaryByIndex(self, index):
        """Checks if a breakpoint given by it's index is temporary"""
        if index.isValid():
            return self.breakpoints[index.row()].isTemporary()
        return False

    def getCounts(self):
        """Provides enable/disable counters"""
        enableCount = 0
        disableCount = 0
        for bp in self.breakpoints:
            if bp.isEnabled():
                enableCount += 1
            else:
                disableCount += 1
        return enableCount, disableCount

    def serialize(self):
        """Provides a list of serialized breakpoints"""
        result = []
        for bp in self.breakpoints:
            result.append(bp.serialize())
        return result
