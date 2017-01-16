# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2016  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""QComboBox extension:
   - allows editing
   - limits the number of saved entries
   - does not allow duplications
   - disables auto completion
   - inserts items at top
"""

from .qt import Qt, pyqtSignal, QComboBox


class EnterSensitiveComboBox(QComboBox):

    """Combo box which emits 'enterClicked' signal"""

    enterClicked = pyqtSignal()

    def __init__(self, parent=None):
        QComboBox.__init__(self, parent)

    def keyReleaseEvent(self, event):
        """Triggered when a key is released"""
        QComboBox.keyReleaseEvent(self, event)
        key = event.key()
        if key == Qt.Key_Enter or key == Qt.Key_Return:
            self.enterClicked.emit()


class CDMComboBox(QComboBox):

    """QComboBox minor extension"""

    enterClicked = pyqtSignal()
    itemAdded = pyqtSignal()

    itemsLimit = 32

    def __init__(self, insertOnEnter=True, parent=None):
        QComboBox.__init__(self, parent)
        self.setEditable(True)
        self.setCompleter(None)
        self.setDuplicatesEnabled(False)
        self.setInsertPolicy(QComboBox.NoInsert)
        self.insert = insertOnEnter

    def addItem(self, text):
        """Adds an item to the top"""
        text = str(text).strip()
        if text != "":
            if self.findText(text, Qt.MatchFixedString) == -1:
                self.insertItem(0, text)
                self.__enforceLimit()
        self.itemAdded.emit()

    def getItems(self):
        """Provides the list of items (text only)"""
        items = []
        for index in range(self.count()):
            items.append(str(self.itemText(index)))
        return items

    def keyReleaseEvent(self, event):
        """Triggered when a key is released"""
        QComboBox.keyReleaseEvent(self, event)
        if self.insert:
            key = event.key()
            if key == Qt.Key_Enter or key == Qt.Key_Return:
                self.addItem(self.lineEdit().text())
                self.__enforceLimit()
                self.enterClicked.emit()

    def __enforceLimit(self):
        """checks the number of memorized items"""
        # Check that the number of items is not exceeded
        while self.count() > self.itemsLimit:
            self.removeItem(self.count() - 1)
