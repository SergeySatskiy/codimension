#
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

"""imports/definitions selection widget"""

import os.path
from utils.globals import GlobalData
from utils.fileutils import isPythonFile
from .qt import (Qt, QEventLoop, QSizePolicy, QFrame, QTreeWidget,
                 QApplication, QTreeWidgetItem, QHeaderView, QVBoxLayout,
                 QAbstractItemView)
from .itemdelegates import NoOutlineHeightDelegate


class ImportsList(QTreeWidget):

    """Need to derive for overloading focusOutEvent()"""

    def __init__(self, parent):
        QTreeWidget.__init__(self, parent)

    def focusOutEvent(self, _):
        """Hides the imports list widget"""
        self.parent().hide()


class ImportListWidget(QFrame):

    """Frameless dialogue to select an import to open"""

    IMPORT_MODE = 0
    DEFINITION_MODE = 1

    def __init__(self, parent=None):
        QFrame.__init__(self, parent)

        # Make the frame nice looking
        self.setFrameShape(QFrame.Panel)
        self.setLineWidth(1)

        self.__importList = None
        self.__mode = None
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
        verticalLayout.setContentsMargins(0, 0, 0, 0)

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizeHint = self.__importList.minimumSizeHint()
        self.setFixedHeight(sizeHint.height())
        self.move(5, 5)

    def showResolvedImports(self, importsList):
        """Pops up the dialogue"""
        self.__importList.clear()
        self.__populateImports(importsList)
        self.__mode = ImportListWidget.IMPORT_MODE

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

    def __populateImports(self, importsList):
        """Populates the dialogue with imports"""
        count = len(importsList)
        info = str(count) + " resolved import"
        if count > 1:
            info += "s"
        headerItem = QTreeWidgetItem(["Import (" + info + ")", "Path"])
        self.__importList.setHeaderItem(headerItem)
        for item in importsList:
            importName = item[0]
            resolvedPath = item[1]
            if resolvedPath is None:
                resolvedPath = ''
            importItem = QTreeWidgetItem([importName, resolvedPath])
            importItem.setToolTip(0, self.__getFileTooltip(resolvedPath))
            self.__importList.addTopLevelItem(importItem)

        self.__importList.header().resizeSections(
            QHeaderView.ResizeToContents)

    def showDefinitions(self, definitions):
        """Pops up the dialog"""
        self.__importList.clear()
        self.__populateDefinitions(definitions)
        self.__mode = ImportListWidget.DEFINITION_MODE

        self.__importList.setCurrentItem(self.__importList.topLevelItem(0))

        QApplication.processEvents(QEventLoop.ExcludeUserInputEvents)

        self.resize()
        self.show()
        self.__importList.setFocus()

    def __populateDefinitions(self, definitions):
        """Populates the dialogue with definitions"""
        headerItem = QTreeWidgetItem(["Type", "Path", "Line", "Column"])
        self.__importList.setHeaderItem(headerItem)
        for item in definitions:
            defItem = QTreeWidgetItem([item[3], item[0],
                                       str(item[1]), str(item[2] + 1)])
            self.__importList.addTopLevelItem(defItem)

        self.__importList.header().resizeSections(
            QHeaderView.ResizeToContents)

    @staticmethod
    def __getFileTooltip(path):
        """Provides the python file docstring for a tooltip"""
        path = os.path.normpath(path)
        if os.path.exists(path):
            if isPythonFile(path):
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

    def __importActivated(self, item, _):
        """Handles the import selection"""
        path = str(item.text(1))
        if self.__mode == ImportListWidget.IMPORT_MODE:
            if os.path.exists(path):
                GlobalData().mainWindow.openFile(path, -1)
        else:
            line = int(item.text(2))
            column = int(item.text(3))
            GlobalData().mainWindow.openFile(path, line, column)
