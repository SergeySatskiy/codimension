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

"""Ignored exceptions viewer"""

from ui.qt import (Qt, QSize, QSizePolicy, QFrame, QTreeWidget, QToolButton,
                   QTreeWidgetItem, QVBoxLayout, QToolBar, QLabel, QWidget,
                   QAbstractItemView, QMenu, QSpacerItem, QHBoxLayout,
                   QCursor, QLineEdit, QPushButton, QAction)
from ui.itemdelegates import NoOutlineHeightDelegate
from utils.pixmapcache import getIcon
from utils.globals import GlobalData
from utils.project import CodimensionProject
from utils.settings import Settings
from utils.colorfont import getLabelStyle, HEADER_HEIGHT, HEADER_BUTTON


class IgnoredExceptionsViewer(QWidget):

    """Implements the client exceptions viewer for a debugger"""

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

        self.__createPopupMenu()
        self.__createLayout()
        self.__ignored = []
        self.__currentItem = None

        GlobalData().project.sigProjectChanged.connect(self.__onProjectChanged)

        if not Settings()['showIgnoredExcViewer']:
            self.__onShowHide(True)

    def __createPopupMenu(self):
        """Creates the popup menu"""
        self.__excptMenu = QMenu()
        self.__removeMenuItem = self.__excptMenu.addAction(
            getIcon('ignexcptdel.png'), "Remove from ignore list",
            self.__onRemoveFromIgnore)

    def __createLayout(self):
        """Creates the widget layout"""
        verticalLayout = QVBoxLayout(self)
        verticalLayout.setContentsMargins(0, 0, 0, 0)
        verticalLayout.setSpacing(0)

        self.headerFrame = QFrame()
        self.headerFrame.setObjectName('ignexcpt')
        self.headerFrame.setStyleSheet('QFrame#ignexcpt {' +
                                       getLabelStyle(self) + '}')
        self.headerFrame.setFixedHeight(HEADER_HEIGHT)

        self.__excptLabel = QLabel("Ignored exception types")

        expandingSpacer = QSpacerItem(10, 10, QSizePolicy.Expanding)

        self.__showHideButton = QToolButton()
        self.__showHideButton.setAutoRaise(True)
        self.__showHideButton.setIcon(getIcon('less.png'))
        self.__showHideButton.setFixedSize(HEADER_BUTTON, HEADER_BUTTON)
        self.__showHideButton.setToolTip("Hide ignored exceptions list")
        self.__showHideButton.setFocusPolicy(Qt.NoFocus)
        self.__showHideButton.clicked.connect(self.__onShowHide)

        headerLayout = QHBoxLayout()
        headerLayout.setContentsMargins(0, 0, 0, 0)
        headerLayout.addSpacing(3)
        headerLayout.addWidget(self.__excptLabel)
        headerLayout.addSpacerItem(expandingSpacer)
        headerLayout.addWidget(self.__showHideButton)
        self.headerFrame.setLayout(headerLayout)

        self.exceptionsList = QTreeWidget(self)
        self.exceptionsList.setSortingEnabled(False)
        self.exceptionsList.setAlternatingRowColors(True)
        self.exceptionsList.setRootIsDecorated(False)
        self.exceptionsList.setItemsExpandable(True)
        self.exceptionsList.setUniformRowHeights(True)
        self.exceptionsList.setSelectionMode(QAbstractItemView.SingleSelection)
        self.exceptionsList.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.exceptionsList.setItemDelegate(NoOutlineHeightDelegate(4))
        self.exceptionsList.setContextMenuPolicy(Qt.CustomContextMenu)

        self.exceptionsList.customContextMenuRequested.connect(
            self.__showContextMenu)
        self.exceptionsList.itemSelectionChanged.connect(
            self.__onSelectionChanged)
        self.exceptionsList.setHeaderLabels(["Exception type"])

        self.__excTypeEdit = QLineEdit()
        self.__excTypeEdit.setFixedHeight(26)
        self.__excTypeEdit.textChanged.connect(self.__onNewFilterChanged)
        self.__excTypeEdit.returnPressed.connect(self.__onAddExceptionFilter)
        self.__addButton = QPushButton("Add")
        # self.__addButton.setFocusPolicy(Qt.NoFocus)
        self.__addButton.setEnabled(False)
        self.__addButton.clicked.connect(self.__onAddExceptionFilter)

        expandingSpacer2 = QWidget()
        expandingSpacer2.setSizePolicy(QSizePolicy.Expanding,
                                       QSizePolicy.Expanding)

        self.__removeButton = QAction(
            getIcon('delitem.png'), "Remove selected exception type", self)
        self.__removeButton.triggered.connect(self.__onRemoveFromIgnore)
        self.__removeButton.setEnabled(False)

        fixedSpacer1 = QWidget()
        fixedSpacer1.setFixedWidth(5)

        self.__removeAllButton = QAction(
            getIcon('ignexcptdelall.png'), "Remove all the exception types",
            self)
        self.__removeAllButton.triggered.connect(self.__onRemoveAllFromIgnore)
        self.__removeAllButton.setEnabled(False)

        self.toolbar = QToolBar()
        self.toolbar.setOrientation(Qt.Horizontal)
        self.toolbar.setMovable(False)
        self.toolbar.setAllowedAreas(Qt.TopToolBarArea)
        self.toolbar.setIconSize(QSize(16, 16))
        self.toolbar.setFixedHeight(28)
        self.toolbar.setContentsMargins(0, 0, 0, 0)
        self.toolbar.addWidget(expandingSpacer2)
        self.toolbar.addAction(self.__removeButton)
        self.toolbar.addWidget(fixedSpacer1)
        self.toolbar.addAction(self.__removeAllButton)

        addLayout = QHBoxLayout()
        addLayout.setContentsMargins(1, 1, 1, 1)
        addLayout.setSpacing(1)
        addLayout.addWidget(self.__excTypeEdit)
        addLayout.addWidget(self.__addButton)

        verticalLayout.addWidget(self.headerFrame)
        verticalLayout.addWidget(self.toolbar)
        verticalLayout.addWidget(self.exceptionsList)
        verticalLayout.addLayout(addLayout)

    def clear(self):
        """Clears the content"""
        self.exceptionsList.clear()
        self.__excTypeEdit.clear()
        self.__addButton.setEnabled(False)
        self.__ignored = []
        self.__currentItem = None
        self.__updateTitle()

    def __onShowHide(self, startup=False):
        """Triggered when show/hide button is clicked"""
        if startup or self.exceptionsList.isVisible():
            self.exceptionsList.setVisible(False)
            self.__excTypeEdit.setVisible(False)
            self.__addButton.setVisible(False)
            self.__removeButton.setVisible(False)
            self.__removeAllButton.setVisible(False)
            self.__showHideButton.setIcon(getIcon('more.png'))
            self.__showHideButton.setToolTip("Show ignored exceptions list")

            self.__minH = self.minimumHeight()
            self.__maxH = self.maximumHeight()

            self.setMinimumHeight(self.headerFrame.height())
            self.setMaximumHeight(self.headerFrame.height())

            Settings()['showIgnoredExcViewer'] = False
        else:
            self.exceptionsList.setVisible(True)
            self.__excTypeEdit.setVisible(True)
            self.__addButton.setVisible(True)
            self.__removeButton.setVisible(True)
            self.__removeAllButton.setVisible(True)
            self.__showHideButton.setIcon(getIcon('less.png'))
            self.__showHideButton.setToolTip("Hide ignored exceptions list")

            self.setMinimumHeight(self.__minH)
            self.setMaximumHeight(self.__maxH)

            Settings()['showIgnoredExcViewer'] = True

    def __onSelectionChanged(self):
        """Triggered when the current item is changed"""
        selected = list(self.exceptionsList.selectedItems())
        if selected:
            self.__currentItem = selected[0]
            self.__removeButton.setEnabled(True)
        else:
            self.__currentItem = None
            self.__removeButton.setEnabled(False)

    def __showContextMenu(self, coord):
        """Shows the frames list context menu"""
        contextItem = self.exceptionsList.itemAt(coord)
        if contextItem is not None:
            self.__currentItem = contextItem
            self.__excptMenu.popup(QCursor.pos())

    def __updateTitle(self):
        """Updates the section title"""
        count = self.exceptionsList.topLevelItemCount()
        if count == 0:
            self.__excptLabel.setText("Ignored exception types")
        else:
            self.__excptLabel.setText("Ignored exception types (total: " +
                                      str(count) + ")")
        self.__removeAllButton.setEnabled(count != 0)

    def __onProjectChanged(self, what):
        """Triggered when a project is changed"""
        if what != CodimensionProject.CompleteProject:
            return

        self.clear()
        project = GlobalData().project
        if project.isLoaded():
            self.__ignored = list(project.exceptionFilters)
        else:
            self.__ignored = Settings()['ignoredExceptions']

        for exceptionType in self.__ignored:
            item = QTreeWidgetItem(self.exceptionsList)
            item.setText(0, exceptionType)
        self.__updateTitle()

    def __onNewFilterChanged(self, text):
        """Triggered when the text is changed"""
        text = str(text).strip()
        if text == "":
            self.__addButton.setEnabled(False)
            return
        if " " in text:
            self.__addButton.setEnabled(False)
            return

        if text in self.__ignored:
            self.__addButton.setEnabled(False)
            return

        self.__addButton.setEnabled(True)

    def __onAddExceptionFilter(self):
        """Adds an item into the ignored exceptions list"""
        text = self.__excTypeEdit.text().strip()
        self.addExceptionFilter(text)

    def addExceptionFilter(self, excType):
        """Adds a new item into the ignored exceptions list"""
        if excType == "":
            return
        if " " in excType:
            return
        if excType in self.__ignored:
            return

        item = QTreeWidgetItem(self.exceptionsList)
        item.setText(0, excType)

        project = GlobalData().project
        if project.isLoaded():
            project.addExceptionFilter(excType)
        else:
            Settings().addExceptionFilter(excType)
        self.__ignored.append(excType)
        self.__updateTitle()

    def __onRemoveFromIgnore(self):
        """Removes an item from the ignored exception types list"""
        if self.__currentItem is None:
            return

        text = self.__currentItem.text(0)

        # Find the item index and remove it
        index = 0
        while True:
            if self.exceptionsList.topLevelItem(index).text(0) == text:
                self.exceptionsList.takeTopLevelItem(index)
                break
            index += 1

        project = GlobalData().project
        if project.isLoaded():
            project.deleteExceptionFilter(text)
        else:
            Settings().deleteExceptionFilter(text)
        self.__ignored.remove(text)
        self.__updateTitle()

    def __onRemoveAllFromIgnore(self):
        """Triggered when all the ignored exceptions should be deleted"""
        self.clear()

        project = GlobalData().project
        if project.isLoaded():
            project.setExceptionFilters([])
        else:
            Settings().setExceptionFilters([])

    def isIgnored(self, exceptionType):
        """Returns True if this exception type should be ignored"""
        return exceptionType in self.__ignored
