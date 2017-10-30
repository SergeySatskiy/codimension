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

"""Tabs history support implementation"""

import os.path
from .qt import QObject, pyqtSignal
from .mainwindowtabwidgetbase import MainWindowTabWidgetBase


class TabHistoryEntry:

    """Holds a single history entry"""

    def __init__(self):
        self.icon = None
        self.uuid = None
        self.displayName = ""
        self.line = -1
        self.pos = -1
        self.firstVisible = -1
        self.tabType = MainWindowTabWidgetBase.Unknown

    def __eq__(self, other):
        """Compares two entries"""
        return self.uuid == other.uuid and \
               self.line == other.line and \
               self.pos == other.pos


class TabsHistory(QObject):

    """Holds the editors manager history"""

    historyChanged = pyqtSignal()
    limit = 32

    def __init__(self, editorsManager):
        QObject.__init__(self)

        self.__editorsManger = editorsManager
        self.__history = []

        # The index always points to the history position which is currently
        # displayed
        self.__index = -1

        # Sequence of the history entries as they have appeared on the screen
        self.__tabsSequence = []

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
        self.__history = []
        self.__index = -1
        self.__tabsSequence = []
        self.historyChanged.emit()

    def addCurrent(self):
        """Adds the current editors manager tab to the history"""
        currentWidget = self.__editorsManger.currentWidget()

        newEntry = TabHistoryEntry()
        newEntry.tabType = currentWidget.getType()
        newEntry.displayName = currentWidget.getShortName()

        newEntry.icon = self.__editorsManger.tabIcon(
            self.__editorsManger.currentIndex())
        newEntry.uuid = currentWidget.getUUID()

        if newEntry.tabType in [MainWindowTabWidgetBase.PlainTextEditor,
                                MainWindowTabWidgetBase.VCSAnnotateViewer]:
            newEntry.line = currentWidget.getLine()
            newEntry.pos = currentWidget.getPos()
            newEntry.firstVisible = currentWidget.getEditor().firstVisibleLine()

        if self.__index != -1:
            if newEntry == self.__history[self.__index]:
                # The new entry is the same as the current - ignore request
                return
            # Cut the tail of the history if needed
            self.__history = self.__history[:self.__index + 1]

        self.__history.append(newEntry)
        self.__enforceLimit()

        self.__index = len(self.__history) - 1
        self.__tabsSequence.append(self.__index)

        self.historyChanged.emit()

    def __enforceLimit(self):
        """Dismisses too old records if required"""
        if len(self.__history) <= self.limit:
            return

        stripCount = len(self.__history) - self.limit
        index = 0
        while index < stripCount:
            # The indexes must be removed from the tabs seq list
            seqIndex = len(self.__tabsSequence) - 1
            while seqIndex >= 0:
                if self.__tabsSequence[seqIndex] == index:
                    del self.__tabsSequence[seqIndex]
                seqIndex -= 1
            index += 1

        # Adjust the indexes in the tabs seq list
        seqIndex = len(self.__tabsSequence) - 1
        while seqIndex >= 0:
            self.__tabsSequence[seqIndex] = \
                self.__tabsSequence[seqIndex] - stripCount
            seqIndex -= 1

        # Strip some items in the history
        self.__history = self.__history[-1 * self.limit:]

    def updateForCurrentIndex(self):
        """Called when the current tab is left"""
        if self.__index < 0:
            return

        # The file could be saved under the different name and get even a
        # different type, so update everything
        uuid = self.__history[self.__index].uuid
        widget = self.__editorsManger.getWidgetByUUID(uuid)

        self.__history[self.__index].tabType = widget.getType()
        self.__history[self.__index].displayName = widget.getShortName()

        if self.__history[self.__index].tabType in \
                            [MainWindowTabWidgetBase.PlainTextEditor,
                             MainWindowTabWidgetBase.VCSAnnotateViewer]:
            self.__history[self.__index].line = widget.getLine()
            self.__history[self.__index].pos = widget.getPos()
            self.__history[self.__index].firstVisible = \
                                    widget.getEditor().firstVisibleLine()
        else:
            self.__history[self.__index].line = -1
            self.__history[self.__index].pos = -1
            self.__history[self.__index].firstVisible = -1

        tabIndex = self.__editorsManger.getIndexByUUID(uuid)
        self.__history[self.__index].icon = \
                                self.__editorsManger.tabIcon(tabIndex)

    def testAdjacent(self, index):
        """tests if an adjacent history item is the same as the given"""
        if index > 0:
            if self.__history[index] == self.__history[index - 1]:
                return True
        if index < len(self.__history) - 1:
            if self.__history[index] == self.__history[index + 1]:
                return True
        return False

    def testAdjacentSeq(self, index):
        """tests if an adjacent seq item is the same as the given"""
        if index > 0:
            if self.__tabsSequence[index] == self.__tabsSequence[index - 1]:
                return True
        if index < len(self.__tabsSequence) - 1:
            if self.__tabsSequence[index] == self.__tabsSequence[index + 1]:
                return True
        return False

    def tabClosed(self, uuid):
        """Called when a tab is closed"""
        # Test if the current was closed
        oldCurrentIndex = self.__index

        # Build a list of history entries which were closed
        removedIndexes = []
        index = len(self.__history) - 1
        while index >= 0:
            if self.__history[index].uuid == uuid or \
               self.testAdjacent(index):
                removedIndexes.insert(0, index)
                del self.__history[index]
                if index < self.__index:
                    self.__index -= 1
            index -= 1

        if len(self.__history) == 0:
            # No history any more
            self.clear()
            return

        # Remove all such entries from the tabs seq and adjust indexes of those
        # which survived
        seqIndex = len(self.__tabsSequence) - 1
        while seqIndex >= 0:
            if self.__tabsSequence[seqIndex] in removedIndexes:
                del self.__tabsSequence[seqIndex]
            else:
                oldIndex = self.__tabsSequence[seqIndex]
                for item in removedIndexes:
                    if item < oldIndex:
                        self.__tabsSequence[seqIndex] -= 1
            seqIndex -= 1

        # Remove adjacent same entries in the tabs sequence
        seqIndex = len(self.__tabsSequence) - 1
        while seqIndex >= 0:
            if self.testAdjacentSeq(seqIndex):
                del self.__tabsSequence[seqIndex]
            seqIndex -= 1

        if oldCurrentIndex in removedIndexes:
            # Update it to the last visible
            self.__index = self.__tabsSequence[len(self.__tabsSequence) - 1]

        self.historyChanged.emit()

    def getSize(self):
        """Provides the total number of the history steps"""
        return len(self.__history)

    def getCurrentIndex(self):
        """Provides the current history index"""
        return self.__index

    def getEntry(self, index):
        """Provides the required history entry"""
        if index < 0 or index >= len(self.__history):
            raise Exception("Invalid history index to set (" +
                            str(index) + ")")
        return self.__history[index]

    def setCurrentIndex(self, index):
        """Sets the given history index as current"""
        if index < 0 or index >= len(self.__history):
            raise Exception("Invalid history index to set (" +
                            str(index) + ")")
        if self.__index != index:
            self.__index = index
            self.__tabsSequence.append(index)
            self.historyChanged.emit()

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
        self.__tabsSequence.append(self.__index)
        self.historyChanged.emit()
        return True

    def stepForward(self):
        """Makes one step forward in the history if possible"""
        if self.__index >= len(self.__history) - 1:
            return False
        self.__index += 1
        self.__tabsSequence.append(self.__index)
        self.historyChanged.emit()
        return True

    def flip(self):
        """Flips between last two history steps"""
        if len(self.__history) < 1:
            return False
        lastSeqIndex = len(self.__tabsSequence) - 1
        self.__index = self.__tabsSequence[lastSeqIndex - 1]
        self.__tabsSequence.append(self.__index)
        self.historyChanged.emit()
        return True

    def updateFileNameForTab(self, uuid, newFileName):
        """After SaveAs the file name should be updated"""
        newDisplayName = os.path.basename(newFileName)
        for item in self.__history:
            if item.uuid == uuid:
                item.displayName = newDisplayName

    def updateIconForTab(self, uuid, icon):
        """Broken/disappeared/modified icons could appear for a file"""
        for item in self.__history:
            if item.uuid == uuid:
                item.icon = icon
