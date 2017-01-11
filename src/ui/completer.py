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

"""completer selection widget"""


from .qt import (Qt, QEvent, QModelIndex, QStringListModel, QAction,
                 QAbstractItemView, QCompleter, QListView)
from .itemdelegates import NoOutlineHeightDelegate


class CompleterPopup(QListView):

    """Custom completer popup"""

    def __init__(self, completer):
        QListView.__init__(self, completer.parent())

        self.__completer = completer
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        shiftTabAct = QAction(self)
        shiftTabAct.setShortcut('Shift+Tab')
        shiftTabAct.triggered.connect(self.__completer.moveToPrevious)
        self.addAction(shiftTabAct)

        ctrlSpaceAct = QAction(self)
        ctrlSpaceAct.setShortcut('Ctrl+ ')
        ctrlSpaceAct.triggered.connect(self.__completer.moveToNext)
        self.addAction(ctrlSpaceAct)


class WordsListModel(QStringListModel):

    """Custom model to use the same font as the editor"""

    def __init__(self, words, font):
        words.sort()
        QStringListModel.__init__(self, words)
        self.__font = font
        self.__font.setBold(False)

    def data(self, index, role):
        """Changes the rows font"""
        if role == Qt.FontRole:
            return self.__font
        return QStringListModel.data(self, index, role)


class CodeCompleter(QCompleter):

    """Codimension code completer"""

    maxDisplayedItems = 8

    def __init__(self, parent=None):
        QCompleter.__init__(self, parent)
        self.setCompletionMode(QCompleter.PopupCompletion)

        self.__width = -1
        self.__rect = None
        self.__model = None

        self.setWidget(parent)
        self.setCaseSensitivity(Qt.CaseInsensitive)
        self.setWrapAround(False)

        self.highlighted[QModelIndex].connect(self.__onHighlighted)

    def __onHighlighted(self, index):
        """Sets the current row to have currentCompletion() working properly"""
        self.setCurrentRow(index.row())

    def setWordsList(self, words, font):
        """Sets the words list"""
        self.setPopup(CompleterPopup(self))
        self.popup().setAlternatingRowColors(True)

        self.__model = WordsListModel(words, font)
        self.setModel(self.__model)
        self.setCompletionPrefix("")

        # This call should be given here, i.e. after a new model is set for the
        # completer. Otherwise this will have no effect.
        self.popup().setItemDelegate(NoOutlineHeightDelegate(4))

        self.__width = self.popup().sizeHintForColumn(0) + \
            self.popup().verticalScrollBar().sizeHint().width() + 20
        if self.__width < 100:
            self.__width = 100

    def setPrefix(self, prefix):
        """Sets the prefix"""
        self.setCompletionPrefix(str(prefix))

        count = self.completionCount()
        if count == 0:
            return

        # Make the completer resizable as the number of options changed
        if count < CodeCompleter.maxDisplayedItems:
            if self.maxVisibleItems() != count:
                self.setMaxVisibleItems(count)
                if self.popup().isVisible():
                    self.complete(self.__rect)
        else:
            if self.maxVisibleItems() != CodeCompleter.maxDisplayedItems:
                self.setMaxVisibleItems(CodeCompleter.maxDisplayedItems)
                if self.popup().isVisible():
                    self.complete(self.__rect)

        if self.completionCount() > 0:
            self.__selectFirst()

        self.parent().setFocus()

    def complete(self, rect):
        """Brings the completer up"""
        rect.setWidth(self.__width)
        self.__rect = rect
        QCompleter.complete(self, rect)
        self.__selectFirst()

    def __selectFirst(self):
        """Selects the first item in the list view if nothing is selected"""
        if self.completionCount() <= 0:
            return
        index = self.popup().currentIndex()
        if not index.isValid():
            cidx = self.completionModel().index(0, 0)
            self.popup().setCurrentIndex(cidx)

    def moveToNext(self):
        """Moves the selection one row down"""
        if self.completionCount() <= 1:
            return

        newRow = self.popup().currentIndex().row() + 1
        lastRow = self.completionCount() - 1
        if newRow <= lastRow:
            cidx = self.completionModel().index(newRow, 0)
        else:
            cidx = self.completionModel().index(0, 0)
        self.popup().setCurrentIndex(cidx)

    def moveToPrevious(self):
        """Moves the selection one row up"""
        if self.completionCount() <= 1:
            return

        newRow = self.popup().currentIndex().row() - 1
        if newRow >= 0:
            cidx = self.completionModel().index(newRow, 0)
        else:
            lastRow = self.completionCount() - 1
            cidx = self.completionModel().index(lastRow, 0)
        self.popup().setCurrentIndex(cidx)

    def eventFilter(self, obj, evnt):
        """Custom events filtering"""
        if evnt.type() == QEvent.KeyPress and self.popup().isVisible():
            if evnt.modifiers() != Qt.NoModifier and len(evnt.text()) == 0:
                # Supress
                return True
            key = evnt.key()
            if key in [Qt.Key_Enter, Qt.Key_Return]:
                self.activated.emit(self.currentCompletion())
                return True
            elif key == Qt.Key_Home:
                cidx = self.completionModel().index(0, 0)
                self.popup().setCurrentIndex(cidx)
                return True
            elif key == Qt.Key_End:
                lastRow = self.completionCount() - 1
                cidx = self.completionModel().index(lastRow, 0)
                self.popup().setCurrentIndex(cidx)
                return True
            elif key in [Qt.Key_Tab, Qt.Key_Down, Qt.Key_Right]:
                self.moveToNext()
                return True
            elif key in [Qt.Key_Backtab, Qt.Key_Up, Qt.Key_Left]:
                self.moveToPrevious()
                return True
            elif key == Qt.Key_PageUp:
                cRow = self.popup().currentIndex().row()
                if cRow == 0:
                    self.moveToPrevious()
                    return True
            elif key == Qt.Key_PageDown:
                lastRow = self.completionCount() - 1
                cRow = self.popup().currentIndex().row()
                if lastRow == cRow:
                    self.moveToNext()
                    return True

        return QCompleter.eventFilter(self, obj, evnt)

    def isVisible(self):
        """Returns True if the popup is visible"""
        return self.popup().isVisible()

    def hide(self):
        """Hides the popup"""
        self.popup().hide()
