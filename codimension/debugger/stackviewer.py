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

"""Stack viewer"""

import os.path
from ui.qt import (Qt, QSizePolicy, QFrame, QTreeWidget, QToolButton,
                   QTreeWidgetItem, QHeaderView, QVBoxLayout, QLabel, QWidget,
                   QAbstractItemView, QMenu, QSpacerItem, QHBoxLayout,
                   QCursor)
from ui.itemdelegates import NoOutlineHeightDelegate
from utils.colorfont import getLabelStyle, HEADER_HEIGHT, HEADER_BUTTON
from utils.pixmapcache import getIcon
from utils.globals import GlobalData
from utils.settings import Settings


class StackFrameItem(QTreeWidgetItem):

    """Single stack frame item data structure"""

    def __init__(self, fileName, lineNumber, funcName, funcArgs, frameNumber):
        shortened = os.path.basename(fileName) + ":" + str(lineNumber)

        self.__lineNumber = lineNumber
        QTreeWidgetItem.__init__(self, ["", shortened,
                                        funcName, funcArgs, fileName])

        self.__isCurrent = False
        self.__frameNumber = frameNumber

        tooltip = ['Location: ' + fileName + ':' + str(lineNumber)]
        if funcName:
            tooltip += ['Function: ' + funcName,
                        'Arguments: ' + funcArgs]
        self.setToolTip(0, '\n'.join(tooltip))

    def setCurrent(self, value):
        """Mark the current stack frame with an icon if so"""
        self.__isCurrent = value
        if value:
            self.setIcon(0, getIcon('currentframe.png'))
        else:
            self.setIcon(0, getIcon('empty.png'))

    def getFrameNumber(self):
        """Provides the frame number"""
        return self.__frameNumber

    def getFilename(self):
        """Provides the full project filename"""
        return str(self.text(4))

    def getLineNumber(self):
        """Provides the line number"""
        return self.__lineNumber

    def isCurrent(self):
        """True if the project is current"""
        return self.__isCurrent


class StackViewer(QWidget):

    """Implements the stack viewer for a debugger"""

    def __init__(self, debugger, parent=None):
        QWidget.__init__(self, parent)

        self.__debugger = debugger
        self.currentStack = None
        self.currentFrame = 0
        self.__contextItem = None
        self.__createPopupMenu()
        self.__createLayout()

        if not Settings()['showStackViewer']:
            self.__onShowHide(True)

    def __createPopupMenu(self):
        """Creates the popup menu"""
        self.__framesMenu = QMenu()
        self.__setCurrentMenuItem = self.__framesMenu.addAction(
            "Set current (single click)", self.__onSetCurrent)
        self.__jumpMenuItem = self.__framesMenu.addAction(
            "Set current and jump to the source (double click)",
            self.__onSetCurrentAndJump)

    def __createLayout(self):
        """Creates the widget layout"""
        verticalLayout = QVBoxLayout(self)
        verticalLayout.setContentsMargins(0, 0, 0, 0)
        verticalLayout.setSpacing(0)

        self.headerFrame = QFrame()
        self.headerFrame.setObjectName('stackheader')
        self.headerFrame.setStyleSheet('QFrame#stackheader {' +
                                       getLabelStyle(self) + '}')
        self.headerFrame.setFixedHeight(HEADER_HEIGHT)

        self.__stackLabel = QLabel("Stack")

        expandingSpacer = QSpacerItem(10, 10, QSizePolicy.Expanding)

        self.__showHideButton = QToolButton()
        self.__showHideButton.setAutoRaise(True)
        self.__showHideButton.setIcon(getIcon('less.png'))
        self.__showHideButton.setFixedSize(HEADER_BUTTON, HEADER_BUTTON)
        self.__showHideButton.setToolTip("Hide frames list")
        self.__showHideButton.setFocusPolicy(Qt.NoFocus)
        self.__showHideButton.clicked.connect(self.__onShowHide)

        headerLayout = QHBoxLayout()
        headerLayout.setContentsMargins(0, 0, 0, 0)
        headerLayout.addSpacing(3)
        headerLayout.addWidget(self.__stackLabel)
        headerLayout.addSpacerItem(expandingSpacer)
        headerLayout.addWidget(self.__showHideButton)
        self.headerFrame.setLayout(headerLayout)

        self.__framesList = QTreeWidget(self)
        self.__framesList.setSortingEnabled(False)
        # I might not need that because of two reasons:
        # - the window has no focus
        # - the window has custom current indicator
        # self.__framesList.setAlternatingRowColors(True)
        self.__framesList.setRootIsDecorated(False)
        self.__framesList.setItemsExpandable(False)
        self.__framesList.setUniformRowHeights(True)
        self.__framesList.setSelectionMode(QAbstractItemView.NoSelection)
        self.__framesList.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.__framesList.setItemDelegate(NoOutlineHeightDelegate(4))
        self.__framesList.setFocusPolicy(Qt.NoFocus)
        self.__framesList.setContextMenuPolicy(Qt.CustomContextMenu)

        self.__framesList.itemClicked.connect(self.__onFrameClicked)
        self.__framesList.itemDoubleClicked.connect(
            self.__onFrameDoubleClicked)
        self.__framesList.customContextMenuRequested.connect(
            self.__showContextMenu)

        self.__framesList.setHeaderLabels(["", "File:line",
                                           "Function", "Arguments",
                                           "Full path"])

        verticalLayout.addWidget(self.headerFrame)
        verticalLayout.addWidget(self.__framesList)

    def __onShowHide(self, startup=False):
        """Triggered when show/hide button is clicked"""
        if startup or self.__framesList.isVisible():
            self.__framesList.setVisible(False)
            self.__showHideButton.setIcon(getIcon('more.png'))
            self.__showHideButton.setToolTip("Show frames list")

            self.__minH = self.minimumHeight()
            self.__maxH = self.maximumHeight()

            self.setMinimumHeight(self.headerFrame.height())
            self.setMaximumHeight(self.headerFrame.height())

            Settings()['showStackViewer'] = False
        else:
            self.__framesList.setVisible(True)
            self.__showHideButton.setIcon(getIcon('less.png'))
            self.__showHideButton.setToolTip("Hide frames list")

            self.setMinimumHeight(self.__minH)
            self.setMaximumHeight(self.__maxH)

            Settings()['showStackViewer'] = True

    def clear(self):
        """Clears the content"""
        self.__framesList.clear()
        self.currentStack = None
        self.__stackLabel.setText("Stack")

    def __resizeColumns(self):
        """Resize the files list columns"""
        self.__framesList.header().setStretchLastSection(True)
        self.__framesList.header().resizeSections(
            QHeaderView.ResizeToContents)
        self.__framesList.header().resizeSection(0, 22)
        self.__framesList.header().setSectionResizeMode(0, QHeaderView.Fixed)

    def populate(self, stack):
        """Sets the new call stack and selects the first item in it"""
        self.clear()

        self.currentStack = stack
        self.currentFrame = 0
        frameNumber = 0
        for item in stack:
            fName = item[0]
            lineNo = item[1]
            funcName = ''
            funcArgs = ''
            if len(item) >= 3:
                funcName = item[2]
            if len(item) >= 4:
                funcArgs = item[3]

            if funcName.startswith('<'):
                funcName = ''
                funcArgs = ''

            item = StackFrameItem(fName, lineNo,
                                  funcName, funcArgs, frameNumber)
            self.__framesList.addTopLevelItem(item)
            frameNumber += 1
        self.__resizeColumns()
        self.__framesList.topLevelItem(0).setCurrent(True)
        self.__stackLabel.setText("Stack (total: " +
                                  str(len(stack)) + ")")

    def getFrameNumber(self):
        """Provides the current frame number"""
        return self.currentFrame

    def __onFrameClicked(self, item, column):
        """Triggered when a frame is clicked"""
        del column  # unused argument
        if item.isCurrent():
            return

        # Hide the current indicator
        self.__framesList.topLevelItem(self.currentFrame).setCurrent(False)

        # Show the new indicator
        self.currentFrame = item.getFrameNumber()
        for index in range(self.__framesList.topLevelItemCount()):
            item = self.__framesList.topLevelItem(index)
            if item.getFrameNumber() == self.currentFrame:
                item.setCurrent(True)
        self.__debugger.remoteClientVariables(1, self.currentFrame)  # globals
        self.__debugger.remoteClientVariables(0, self.currentFrame)  # locals

    def __onFrameDoubleClicked(self, item, column):
        """Triggered when a frame is double clicked"""
        del column  # unused argument
        # The frame has been switched already because the double click
        # signal always comes after the single click one
        fileName = item.getFilename()
        lineNumber = item.getLineNumber()

        editorsManager = GlobalData().mainWindow.editorsManager()
        editorsManager.openFile(fileName, lineNumber)
        editor = editorsManager.currentWidget().getEditor()
        editor.gotoLine(lineNumber)
        editorsManager.currentWidget().setFocus()

    def __showContextMenu(self, coord):
        """Shows the frames list context menu"""
        self.__contextItem = self.__framesList.itemAt(coord)
        if self.__contextItem is not None:
            self.__setCurrentMenuItem.setEnabled(
                not self.__contextItem.isCurrent())
            self.__framesMenu.popup(QCursor.pos())

    def __onSetCurrent(self):
        """Context menu item handler"""
        self.__onFrameClicked(self.__contextItem, 0)

    def __onSetCurrentAndJump(self):
        """Context menu item handler"""
        self.__onFrameClicked(self.__contextItem, 0)
        self.__onFrameDoubleClicked(self.__contextItem, 0)

    def switchControl(self, isInIDE):
        """Switches the UI depending where the control flow is"""
        self.__framesList.setEnabled(isInIDE)
