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

"""The globals viewer implementation"""

from utils.pixmapcache import getIcon
from utils.globals import GlobalData
from utils.project import CodimensionProject
from .qt import (Qt, QSize, QRect, QItemSelectionModel, QMenu, QWidget,
                 QAction, QVBoxLayout, QToolBar, QLabel, QSizePolicy,
                 QCursor)
from .combobox import CDMComboBox
from .globalsbrowser import GlobalsBrowser
from .viewitems import (DecoratorItemType, FunctionItemType,
                        ClassItemType, AttributeItemType,
                        GlobalItemType)


class GlobalsViewer(QWidget):

    """The globals viewer widget"""

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

        self.filterEdit = None
        self.definitionButton = None
        self.findButton = None
        self.globalsViewer = None
        self.copyPathButton = None
        self.__createLayout()

        # create the context menu
        self.__menu = QMenu(self)
        self.__jumpMenuItem = self.__menu.addAction(
            getIcon('definition.png'),
            'Jump to definition', self.__goToDefinition)
        self.__menu.addSeparator()
        self.__findMenuItem = self.__menu.addAction(
            getIcon('findusage.png'), 'Find occurence', self.__findWhereUsed)
        self.__menu.addSeparator()
        self.__copyMenuItem = self.__menu.addAction(
            getIcon('copymenu.png'),
            'Copy path to clipboard', self.globalsViewer.copyToClipboard)
        self.globalsViewer.setContextMenuPolicy(Qt.CustomContextMenu)
        self.globalsViewer.customContextMenuRequested.connect(
            self.__handleShowContextMenu)

        GlobalData().project.sigProjectChanged.connect(self.__onProjectChanged)
        self.globalsViewer.sigSelectionChanged.connect(self.__selectionChanged)
        self.globalsViewer.sigOpeningItem.connect(self.itemActivated)
        self.globalsViewer.sigModelFilesChanged.connect(self.modelFilesChanged)

        self.filterEdit.lineEdit().setFocus()
        self.__contextItem = None

    def __createLayout(self):
        """Helper to create the viewer layout"""
        self.globalsViewer = GlobalsBrowser()

        # Toolbar part - buttons
        self.definitionButton = QAction(
            getIcon('definition.png'),
            'Jump to highlighted item definition', self)
        self.definitionButton.triggered.connect(self.__goToDefinition)
        self.findButton = QAction(
            getIcon('findusage.png'), 'Find highlighted item occurences', self)
        self.findButton.triggered.connect(self.__findWhereUsed)
        self.copyPathButton = QAction(
            getIcon('copymenu.png'), 'Copy path to clipboard', self)
        self.copyPathButton.triggered.connect(
            self.globalsViewer.copyToClipboard)

        self.toolbar = QToolBar(self)
        self.toolbar.setMovable(False)
        self.toolbar.setAllowedAreas(Qt.TopToolBarArea)
        self.toolbar.setIconSize(QSize(16, 16))
        self.toolbar.setFixedHeight(28)
        self.toolbar.setContentsMargins(0, 0, 0, 0)
        self.toolbar.addAction(self.definitionButton)
        self.toolbar.addAction(self.findButton)
        self.toolbar.addAction(self.copyPathButton)

        filterLabel = QLabel("  Filter ")
        self.toolbar.addWidget(filterLabel)
        self.filterEdit = CDMComboBox(True, self.toolbar)
        self.filterEdit.setSizePolicy(QSizePolicy.Expanding,
                                      QSizePolicy.Expanding)
        self.filterEdit.lineEdit().setToolTip(
            "Space separated regular expressions")
        self.toolbar.addWidget(self.filterEdit)
        self.filterEdit.editTextChanged.connect(self.__filterChanged)
        self.filterEdit.itemAdded.connect(self.__filterItemAdded)
        self.filterEdit.enterClicked.connect(self.__enterInFilter)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.globalsViewer)

        self.setLayout(layout)

    def __filterChanged(self, text):
        """Triggers when the filter text changed"""
        self.globalsViewer.setFilter(text)
        self.globalsViewer.updateCounter()

    def __selectionChanged(self, index):
        """Handles the changed selection"""
        if index.isValid():
            self.__contextItem = self.globalsViewer.model().item(index)
        else:
            self.__contextItem = None
        self.__updateButtons()

    def getItemCount(self):
        """Provides the # of items in the model - total, not only visible"""
        return self.globalsViewer.model().sourceModel().rowCount()

    def itemActivated(self, path, line):
        """Handles the item activation"""
        del path    # unused argument
        del line    # unused argument
        self.filterEdit.addItem(self.filterEdit.lineEdit().text())

    def __filterItemAdded(self):
        """The filter item has been added"""
        project = GlobalData().project
        if project.isLoaded():
            project.findGlobalHistory = self.filterEdit.getItems()

    def __enterInFilter(self):
        """ENTER key has been clicked in the filter"""
        # check if there any records displayed
        if self.globalsViewer.model().rowCount() == 0:
            return

        # Move the focus to the list and select the first row
        self.globalsViewer.clearSelection()
        flags = QItemSelectionModel.SelectCurrent | QItemSelectionModel.Rows
        self.globalsViewer.setSelection(
            QRect(0, 0, self.globalsViewer.width(), 1), flags)
        self.globalsViewer.setFocus()

    def __onProjectChanged(self, what):
        """Triggered when a project is changed"""
        if what == CodimensionProject.CompleteProject:
            self.__contextItem = None
            self.__updateButtons()
            self.filterEdit.clear()

            project = GlobalData().project
            if project.isLoaded():
                self.filterEdit.editTextChanged.disconnect(self.__filterChanged)
                self.filterEdit.addItems(project.findGlobalHistory)
                self.filterEdit.editTextChanged.connect(self.__filterChanged)
            self.filterEdit.clearEditText()

    def __handleShowContextMenu(self, coord):
        """Show the context menu"""
        index = self.globalsViewer.indexAt(coord)
        if not index.isValid():
            return

        # This will update the __contextItem
        self.__selectionChanged(index)

        if self.__contextItem is None:
            return

        self.__jumpMenuItem.setEnabled(self.definitionButton.isEnabled())
        self.__findMenuItem.setEnabled(self.findButton.isEnabled())
        self.__copyMenuItem.setEnabled(self.copyPathButton.isEnabled())

        self.__menu.popup(QCursor.pos())

    def __goToDefinition(self):
        """Jump to definition context menu handler"""
        if self.__contextItem is not None:
            self.globalsViewer.openItem(self.__contextItem)

    def __findWhereUsed(self):
        """Find where used context menu handler"""
        if self.__contextItem is not None:
            GlobalData().mainWindow.findWhereUsed(
                self.__contextItem.getPath(),
                self.__contextItem.sourceObj)

    def __updateButtons(self):
        """Updates the toolbar buttons depending on what is selected"""
        self.definitionButton.setEnabled(False)
        self.findButton.setEnabled(False)
        self.copyPathButton.setEnabled(False)
        if self.__contextItem is None:
            return

        if self.__contextItem.itemType == DecoratorItemType:
            self.definitionButton.setEnabled(True)
            self.copyPathButton.setEnabled(True)
            return

        if self.__contextItem.itemType in [FunctionItemType, ClassItemType,
                                           AttributeItemType, GlobalItemType]:
            self.definitionButton.setEnabled(True)
            self.findButton.setEnabled(True)
            self.copyPathButton.setEnabled(True)

    def onFileUpdated(self, fileName, uuid):
        """Triggered when the file is updated"""
        del uuid    # unused argument
        self.globalsViewer.onFileUpdated(fileName)

    def modelFilesChanged(self):
        """Triggered when the source model has files added or deleted"""
        pass
