#
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

"""imports list selection widget"""

import os.path
from PyQt5.QtCore import Qt, QEventLoop
from PyQt5.QtGui import (QSizePolicy, QFrame, QTreeWidget, QApplication,
                         QTreeWidgetItem, QHeaderView, QVBoxLayout,
                         QAbstractItemView)
from utils.globals import GlobalData
from .itemdelegates import NoOutlineHeightDelegate


class ImportsList(QTreeWidget):

    """Need to derive for overloading focusOutEvent()"""

    def __init__(self, parent):
        QTreeWidget.__init__(self, parent)

    def focusOutEvent(self, event):
        """Hides the imports list widget"""
        self.parent().hide()


class ImportListWidget(QFrame):

    """Frameless dialogue to select an import to open"""

    def __init__(self, parent=None):
        QFrame.__init__(self, parent)

        # Make the frame nice looking
        self.setFrameShape(QFrame.StyledPanel)
        self.setLineWidth(2)

        self.__importList = None
        self.__createLayout()

    def __createLayout(self):
        """Creates the widget layout"""
        verticalLayout = QVBoxLayout(self)

        self.__importList = ImportsList(self)
        self.__importList.setAlternatingRowColors(True)
        self.__importList.setRootIsDecorated(False)
        self.__importList.setItemsExpandable(False)
        self.__importList.setUniformRowHeights(True)
        self.__importList.setSelectionMode(QAbstractItemView.SingleSelection)
        self.__importList.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.__importList.setItemDelegate(NoOutlineHeightDelegate(4))

        self.__importList.itemActivated.connect(self.__importActivated)

        verticalLayout.addWidget(self.__importList)
        verticalLayout.setMargin(0)

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizeHint = self.__importList.minimumSizeHint()
        self.setFixedHeight(sizeHint.height())
        self.move(5, 5)

    def showResolvedList(self, importsList):
        """Pops up the dialogue"""
        self.__importList.clear()
        self.__populate(importsList)

        self.__importList.setCurrentItem(self.__importList.topLevelItem(0))

        QApplication.processEvents(QEventLoop.ExcludeUserInputEvents)

        self.resize()
        self.show()
        self.__importList.setFocus()

    def resize(self):
        """Resizes the dialogue to match the editor size"""
        scroll = self.parent().verticalScrollBar()
        scrollWidth = scroll.width()

        width = self.parent().width()
        widgetWidth = width - scrollWidth - 10

        self.setFixedWidth(widgetWidth)

    def __populate(self, importsList):
        """Populates the dialogue with imports"""
        count = len(importsList)
        info = str(count) + " resolved import"
        if count > 1:
            info += "s"
        self.__importList.setHeaderLabels(["Import (" + info + ")", "Path"])
        for item in importsList:
            importItem = QTreeWidgetItem([item[0], item[1]])
            importItem.setToolTip(0, self.__getFileTooltip(item[1]))
            self.__importList.addTopLevelItem(importItem)

        self.__importList.header().resizeSections(
            QHeaderView.ResizeToContents)

    @staticmethod
    def __getFileTooltip(path):
        """Provides the python file docstring for a tooltip"""
        path = os.path.normpath(path)
        modInfo = GlobalData().briefModinfoCache.get(path)
        if modInfo.docstring is not None:
            return modInfo.docstring.text
        return ''

    def setFocus(self):
        """Sets the focus to the list of imports"""
        self.__importList.setFocus()

    def keyPressEvent(self, event):
        """Handles the key press events"""
        if event.key() == Qt.Key_Escape:
            editorsManager = GlobalData().mainWindow.editorsManager()
            activeWindow = editorsManager.currentWidget()
            if activeWindow:
                activeWindow.setFocus()
            event.accept()
            self.hide()

    def __importActivated(self, item, column):
        """Handles the import selection"""
        path = str(item.text(1))
        GlobalData().mainWindow.editorsManager().openFile(path, -1)
