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

from ui.qt import pyqtSignal, QAbstractItemModel, QVariant, Qt, QModelIndex


class BreakPointModel(QAbstractItemModel):

    """Class implementing a custom model for breakpoints"""

    sigDataAboutToBeChanged = pyqtSignal(QModelIndex, QModelIndex)
    sigBreakpoinsChanged = pyqtSignal()

    def __init__(self, parent=None):
        QAbstractItemModel.__init__(self, parent)

        self.breakpoints = []
        self.header = [
            QVariant('File:line'),
            QVariant('Condition'),
            QVariant('Temporary'),
            QVariant('Enabled'),
            QVariant('Ignore Count')]
        self.alignments = [
            QVariant(Qt.Alignment(Qt.AlignLeft)),
            QVariant(Qt.Alignment(Qt.AlignLeft)),
            QVariant(Qt.Alignment(Qt.AlignHCenter)),
            QVariant(Qt.Alignment(Qt.AlignHCenter)),
            QVariant(Qt.Alignment(Qt.AlignRight))]
        self.__columnCount = len(self.header)

    def columnCount(self, parent=QModelIndex()):
        """Provides the current column count"""
        return self.__columnCount

    def rowCount(self, parent=QModelIndex()):
        """Provides the current row count"""
        # we do not have a tree, parent should always be invalid
        if not parent.isValid():
            return len(self.breakpoints)
        return 0

    def data(self, index, role):
        """Provides the requested data"""
        if not index.isValid():
            return QVariant()

        if role == Qt.DisplayRole:
            column = index.column()
            if column < self.__columnCount:
                bpoint = self.breakpoints[index.row()]
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
                return QVariant(value)
        if role == Qt.ToolTipRole:
            column = index.column()
            if column < self.__columnCount:
                return QVariant(self.breakpoints[index.row()].getTooltip())
            else:
                return QVariant()

        if role == Qt.TextAlignmentRole:
            if index.column() < self.__columnCount:
                return self.alignments[index.column()]

        return QVariant()

    def flags(self, index):
        """Provides the item flags"""
        if not index.isValid():
            return Qt.ItemIsEnabled
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Provides header data"""
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section < self.__columnCount:
                return self.header[section]
            return QVariant("")
        return QVariant()

    def index(self, row, column, parent=QModelIndex()):
        """Creates an index"""
        if parent.isValid() or \
           row < 0 or row >= len(self.breakpoints) or \
           column < 0 or column >= len(self.header):
            return QModelIndex()

        return self.createIndex(row, column, self.breakpoints[row])

    def parent(self, index):
        """Provides the parent index"""
        return QModelIndex()

    def hasChildren(self, parent=QModelIndex()):
        """Checks if there are child items"""
        if not parent.isValid():
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
            self.beginRemoveRows(QModelIndex(), 0,
                                 len(self.breakpoints) - 1)
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
