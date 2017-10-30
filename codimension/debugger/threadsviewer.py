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

"""Thread viewer"""


from ui.qt import (Qt, QFrame, QTreeWidget, QToolButton, QTreeWidgetItem,
                   QHeaderView, QVBoxLayout, QLabel, QWidget, QHBoxLayout,
                   QAbstractItemView, QSizePolicy, QSpacerItem)
from ui.itemdelegates import NoOutlineHeightDelegate
from utils.colorfont import getLabelStyle, HEADER_HEIGHT, HEADER_BUTTON
from utils.pixmapcache import getIcon
from utils.settings import Settings


class ThreadItem(QTreeWidgetItem):

    """Single thread item data structure"""

    def __init__(self, tid, name, state):
        QTreeWidgetItem.__init__(self, ["", name, state, str(tid)])

        self.__isCurrent = False
        self.__setTooltip()

    def __setTooltip(self):
        """Sets the tooltip"""
        tooltip = "Current: " + str(self.__isCurrent) + "\n" \
                  "Name: " + self.getName() + "\n" \
                  "State: " + self.getState() + "\n" \
                  "TID: " + str(self.getTID())
        for index in range(4):
            self.setToolTip(index, tooltip)

    def setCurrent(self, value):
        """Mark the current thread with an icon if so"""
        if self.__isCurrent == value:
            return

        self.__isCurrent = value
        if value:
            self.setIcon(0, getIcon('currentthread.png'))
        else:
            self.setIcon(0, getIcon('empty.png'))
        self.__setTooltip()

    def getTID(self):
        """Provides the thread ID"""
        return int(self.text(3))

    def getName(self):
        """Provides the thread name"""
        return str(self.text(1))

    def getState(self):
        """Provides the thread state"""
        return str(self.text(2))

    def isCurrent(self):
        """True if the project is current"""
        return self.__isCurrent


class ThreadsViewer(QWidget):

    """Implements the threads viewer for a debugger"""

    def __init__(self, debugger, parent=None):
        QWidget.__init__(self, parent)

        self.__debugger = debugger
        self.__createLayout()

        if not Settings()['showThreadViewer']:
            self.__onShowHide(True)

    def __createLayout(self):
        """Creates the widget layout"""
        verticalLayout = QVBoxLayout(self)
        verticalLayout.setContentsMargins(0, 0, 0, 0)
        verticalLayout.setSpacing(0)

        self.headerFrame = QFrame()
        self.headerFrame.setObjectName('threadheader')
        self.headerFrame.setStyleSheet('QFrame#threadheader {' +
                                       getLabelStyle(self) + '}')
        self.headerFrame.setFixedHeight(HEADER_HEIGHT)

        self.__threadsLabel = QLabel("Threads")

        expandingSpacer = QSpacerItem(10, 10, QSizePolicy.Expanding)

        self.__showHideButton = QToolButton()
        self.__showHideButton.setAutoRaise(True)
        self.__showHideButton.setIcon(getIcon('less.png'))
        self.__showHideButton.setFixedSize(HEADER_BUTTON, HEADER_BUTTON)
        self.__showHideButton.setToolTip("Hide threads list")
        self.__showHideButton.setFocusPolicy(Qt.NoFocus)
        self.__showHideButton.clicked.connect(self.__onShowHide)

        headerLayout = QHBoxLayout()
        headerLayout.setContentsMargins(0, 0, 0, 0)
        headerLayout.addSpacing(3)
        headerLayout.addWidget(self.__threadsLabel)
        headerLayout.addSpacerItem(expandingSpacer)
        headerLayout.addWidget(self.__showHideButton)
        self.headerFrame.setLayout(headerLayout)

        self.__threadsList = QTreeWidget()
        self.__threadsList.setSortingEnabled(False)
        # I might not need that because of two reasons:
        # - the window has no focus
        # - the window has custom current indicator
        # self.__threadsList.setAlternatingRowColors( True )
        self.__threadsList.setRootIsDecorated(False)
        self.__threadsList.setItemsExpandable(False)
        self.__threadsList.setUniformRowHeights(True)
        self.__threadsList.setSelectionMode(QAbstractItemView.NoSelection)
        self.__threadsList.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.__threadsList.setItemDelegate(NoOutlineHeightDelegate(4))
        self.__threadsList.setFocusPolicy(Qt.NoFocus)

        self.__threadsList.itemClicked.connect(self.__onThreadClicked)
        self.__threadsList.setHeaderLabels(["", "Name", "State", "TID"])

        verticalLayout.addWidget(self.headerFrame)
        verticalLayout.addWidget(self.__threadsList)

    def __onShowHide(self, startup=False):
        """Triggered when show/hide button is clicked"""
        if startup or self.__threadsList.isVisible():
            self.__threadsList.setVisible(False)
            self.__showHideButton.setIcon(getIcon('more.png'))
            self.__showHideButton.setToolTip("Show threads list")

            self.__minH = self.minimumHeight()
            self.__maxH = self.maximumHeight()

            self.setMinimumHeight(self.headerFrame.height())
            self.setMaximumHeight(self.headerFrame.height())

            Settings()['showThreadViewer'] = False
        else:
            self.__threadsList.setVisible(True)
            self.__showHideButton.setIcon(getIcon('less.png'))
            self.__showHideButton.setToolTip("Hide threads list")

            self.setMinimumHeight(self.__minH)
            self.setMaximumHeight(self.__maxH)

            Settings()['showThreadViewer'] = True

    def __resizeColumns(self):
        """Resize the files list columns"""
        self.__threadsList.header().setStretchLastSection(True)
        self.__threadsList.header().resizeSections(
            QHeaderView.ResizeToContents)
        self.__threadsList.header().resizeSection(0, 22)
        self.__threadsList.header().setSectionResizeMode(0, QHeaderView.Fixed)

    def clear(self):
        """Clears the content"""
        self.__threadsList.clear()
        self.__threadsLabel.setText("Threads")

    def populate(self, currentThreadID, threadList):
        """Populates the thread list from the client"""
        self.clear()
        for thread in threadList:
            if thread['broken']:
                state = "Waiting at breakpoint"
            else:
                state = "Running"
            item = ThreadItem(thread['id'], thread['name'], state)
            if thread['id'] == currentThreadID:
                item.setCurrent(True)
            self.__threadsList.addTopLevelItem(item)

        self.__resizeColumns()
        self.__threadsLabel.setText("Threads (total: " +
                                    str(len(threadList)) + ")")

    def switchControl(self, isInIDE):
        """Switches the UI depending where the control flow is"""
        self.__threadsList.setEnabled(isInIDE)

    # Arguments: item, column
    def __onThreadClicked(self, item, _):
        """Triggered when a thread is clicked"""
        if item.isCurrent():
            return

        for index in range(self.__threadsList.topLevelItemCount()):
            listItem = self.__threadsList.topLevelItem(index)
            if listItem.isCurrent():
                listItem.setCurrent(False)
                break
        item.setCurrent(True)

        self.__debugger.remoteSetThread(item.getTID())
