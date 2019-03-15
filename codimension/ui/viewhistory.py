# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2019  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Viewing history support"""

from .qt import QObject, pyqtSignal


class ViewEntry:

    """One history entry"""

    def __init__(self, fName, pos):
        self.fName = fName
        self.pos = pos

    def __eq__(self, other):
        """Compares two entries"""
        return self.fName == other.fName and self.pos == other.pos


class ViewHistory(QObject):

    """Holds the view history"""

    historyChanged = pyqtSignal()

    LIMIT = 128

    def __init__(self):
        QObject.__init__(self)

        self.__history = []

        # The index always points to the history position which is currently
        # displayed
        self.__index = -1

    def backAvailable(self):
        """True if step back available"""
        return self.__index > 0

    def forwardAvailable(self):
        """True if step forward available"""
        if self.__index == -1:
            return False
        return self.__index < len(self.__history) - 1

    def clear(self):
        """Clears the history"""
        if self.__history:
            self.__history = []
            self.__index = -1
            self.historyChanged.emit()

    def addEntry(self, entry):
        """Adds the entry the history"""
        if self.__index != -1:
            self.__history = self.__history[:self.__index + 1]

        self.__history.append(entry)
        self.__enforceLimit()

        self.__index = len(self.__history) - 1
        self.historyChanged.emit()

    def __enforceLimit(self):
        """Dismisses too old records if required"""
        if len(self.__history) <= self.LIMIT:
            return

        # Strip some items in the history
        self.__history = self.__history[-1 * self.LIMIT:]

    def getSize(self):
        """Provides the total number of the history steps"""
        return len(self.__history)

    def getCurrentIndex(self):
        """Provides the current history index"""
        return self.__index

    def getEntry(self, index):
        """Provides the required history entry"""
        if index < 0 or index >= len(self.__history):
            raise Exception("Invalid history index to get (" +
                            str(index) + ")")
        return self.__history[index]

    def getCurrentEntry(self):
        """Provides the current history entry"""
        if self.__index == -1 or self.__index >= len(self.__history):
            raise Exception("No current history entry (index=" +
                            str(self.__index) + ")")
        return self.__history[self.__index]

    def stepBack(self):
        """Makes one step back in the history if possible"""
        if self.__index <= 0:
            return False
        self.__index -= 1
        self.historyChanged.emit()
        return True

    def stepForward(self):
        """Makes one step forward in the history if possible"""
        if self.__index >= len(self.__history) - 1:
            return False
        self.__index += 1
        self.historyChanged.emit()
        return True
