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

"""Client exceptions viewer"""


import os.path
from ui.qt import (Qt, pyqtSignal, QSize, QSizePolicy, QFrame, QTreeWidget,
                   QTreeWidgetItem, QVBoxLayout, QLabel, QWidget,
                   QAbstractItemView, QMenu, QHBoxLayout,
                   QCursor, QAction, QToolBar)
from ui.itemdelegates import NoOutlineHeightDelegate
from utils.pixmapcache import getIcon
from utils.globals import GlobalData
from utils.colorfont import getLabelStyle, HEADER_HEIGHT
from utils.project import CodimensionProject
from .variableitems import getDisplayValue, getTooltipValue


STACK_FRAME_ITEM = 0
EXCEPTION_ITEM = 1


class StackFrameItem(QTreeWidgetItem):

    """One stack trace frame"""

    def __init__(self, parentItem, fileName, lineNumber, funcName, funcArgs):
        QTreeWidgetItem.__init__(self, parentItem)

        self.__fileName = fileName
        self.__lineNumber = lineNumber
        self.__funcName = funcName
        self.__funcArgs = funcArgs
        self.setText(0, os.path.basename(fileName) + ":" + str(lineNumber))
        self.setToolTip(0, fileName + ":" + str(lineNumber))
        self.setText(1, funcName)
        self.setToolTip(1, funcName)
        self.setText(2, funcArgs)
        self.setToolTip(2, funcArgs)

    @staticmethod
    def getType():
        """Provides the item type"""
        return STACK_FRAME_ITEM

    def getLocation(self):
        """Provides the location in the code"""
        return self.toolTip(0)

    def getFileName(self):
        """Provides the file name"""
        return self.__fileName

    def getLineNumber(self):
        """Provides the line number"""
        return self.__lineNumber


class ExceptionItem(QTreeWidgetItem):

    """One exception item"""

    def __init__(self, parentItem, exceptionType, exceptionMessage,
                 stackTrace):
        QTreeWidgetItem.__init__(self, parentItem)
        self.__count = 1
        self.__exceptionType = exceptionType
        self.__exceptionMessage = exceptionMessage

        if not exceptionMessage:
            self.setText(0, str(exceptionType))
            self.setToolTip(0, "Type: " + str(exceptionType))
        else:
            self.setText(0, str(exceptionType) + ", " +
                         getDisplayValue(exceptionMessage))
            tooltip = "Type: " + str(exceptionType) + "\n" + "Message: "
            tooltipMessage = getTooltipValue(exceptionMessage)
            if '\r' in tooltipMessage or '\n' in tooltipMessage:
                tooltip += "\n" + tooltipMessage
            else:
                tooltip += tooltipMessage
            self.setToolTip(0, tooltip)

        if stackTrace:
            for entry in stackTrace:
                fileName = entry[0]
                lineNumber = entry[1]
                funcName = entry[2]
                funcArguments = entry[3]
                StackFrameItem(self, fileName, lineNumber,
                               funcName, funcArguments)

    @staticmethod
    def getType():
        """Provides the item type"""
        return EXCEPTION_ITEM

    def getCount(self):
        """Provides the number of same exceptions"""
        return self.__count

    def getExceptionType(self):
        """Provides the exception type"""
        return self.__exceptionType

    def incrementCounter(self):
        """Increments the counter of the same exceptions"""
        self.__count += 1
        if self.__exceptionMessage == "" or self.__exceptionMessage is None:
            self.setText(0, str(self.__exceptionType) +
                         " (" + str(self.__count) + " times)")
        else:
            self.setText(0, str(self.__exceptionType) +
                         " (" + str(self.__count) + " times), " +
                         getDisplayValue(self.__exceptionMessage))

    def equal(self, exceptionType, exceptionMessage, stackTrace):
        """Returns True if the exceptions are equal"""
        if exceptionType != self.__exceptionType:
            return False
        if exceptionMessage != self.__exceptionMessage:
            return False

        if stackTrace is None:
            stackTrace = []

        count = self.childCount()
        if count != len(stackTrace):
            return False

        for index in range(count):
            child = self.child(index)
            otherLocation = stackTrace[index][0] + ":" + \
                            str(stackTrace[index][1])
            if otherLocation != child.getLocation():
                return False
        return True


class ClientExceptionsViewer(QWidget):

    """Implements the client exceptions viewer for a debugger"""

    sigClientExceptionsCleared = pyqtSignal()

    def __init__(self, parent, ignoredExceptionsViewer):
        QWidget.__init__(self, parent)

        self.__ignoredExceptionsViewer = ignoredExceptionsViewer
        self.__currentItem = None

        self.__createPopupMenu()
        self.__createLayout()

        GlobalData().project.sigProjectChanged.connect(self.__onProjectChanged)

    def setFocus(self):
        """Sets the widget focus"""
        self.exceptionsList.setFocus()

    def __createPopupMenu(self):
        """Creates the popup menu"""
        self.__excptMenu = QMenu()
        self.__addToIgnoreMenuItem = self.__excptMenu.addAction(
            "Add to ignore list", self.__onAddToIgnore)
        self.__jumpToCodeMenuItem = self.__excptMenu.addAction(
            "Jump to code", self.__onJumpToCode)

    def __createLayout(self):
        """Creates the widget layout"""
        verticalLayout = QVBoxLayout(self)
        verticalLayout.setContentsMargins(0, 0, 0, 0)
        verticalLayout.setSpacing(0)

        self.headerFrame = QFrame()
        self.headerFrame.setObjectName('excpt')
        self.headerFrame.setStyleSheet('QFrame#excpt {' +
                                       getLabelStyle(self) + '}')
        self.headerFrame.setFixedHeight(HEADER_HEIGHT)

        self.__excptLabel = QLabel("Exceptions")

        headerLayout = QHBoxLayout()
        headerLayout.setContentsMargins(0, 0, 0, 0)
        headerLayout.addSpacing(3)
        headerLayout.addWidget(self.__excptLabel)
        self.headerFrame.setLayout(headerLayout)

        self.exceptionsList = QTreeWidget(self)
        self.exceptionsList.setSortingEnabled(False)
        self.exceptionsList.setAlternatingRowColors(True)
        self.exceptionsList.setRootIsDecorated(True)
        self.exceptionsList.setItemsExpandable(True)
        self.exceptionsList.setUniformRowHeights(True)
        self.exceptionsList.setSelectionMode(QAbstractItemView.SingleSelection)
        self.exceptionsList.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.exceptionsList.setItemDelegate(NoOutlineHeightDelegate(4))
        self.exceptionsList.setContextMenuPolicy(Qt.CustomContextMenu)

        self.__addToIgnoreButton = QAction(
            getIcon('add.png'), "Add exception to the list of ignored", self)
        self.__addToIgnoreButton.triggered.connect(self.__onAddToIgnore)
        self.__addToIgnoreButton.setEnabled(False)

        expandingSpacer = QWidget()
        expandingSpacer.setSizePolicy(QSizePolicy.Expanding,
                                      QSizePolicy.Expanding)

        self.__jumpToCodeButton = QAction(
            getIcon('gotoline.png'), "Jump to the code", self)
        self.__jumpToCodeButton.triggered.connect(self.__onJumpToCode)
        self.__jumpToCodeButton.setEnabled(False)

        self.__delAllButton = QAction(
            getIcon('trash.png'), "Delete all the client exceptions", self)
        self.__delAllButton.triggered.connect(self.__onDelAll)
        self.__delAllButton.setEnabled(False)

        self.toolbar = QToolBar()
        self.toolbar.setOrientation(Qt.Horizontal)
        self.toolbar.setMovable(False)
        self.toolbar.setAllowedAreas(Qt.TopToolBarArea)
        self.toolbar.setIconSize(QSize(16, 16))
        self.toolbar.setFixedHeight(28)
        self.toolbar.setContentsMargins(0, 0, 0, 0)
        self.toolbar.addAction(self.__addToIgnoreButton)
        self.toolbar.addAction(self.__jumpToCodeButton)
        self.toolbar.addWidget(expandingSpacer)
        self.toolbar.addAction(self.__delAllButton)

        self.exceptionsList.itemDoubleClicked.connect(
            self.__onExceptionDoubleClicked)
        self.exceptionsList.customContextMenuRequested.connect(
            self.__showContextMenu)
        self.exceptionsList.itemSelectionChanged.connect(
            self.__onSelectionChanged)

        self.exceptionsList.setHeaderLabels(["Exception",
                                             "Function", "Arguments"])

        verticalLayout.addWidget(self.headerFrame)
        verticalLayout.addWidget(self.toolbar)
        verticalLayout.addWidget(self.exceptionsList)

    def clear(self):
        """Clears the content"""
        self.exceptionsList.clear()
        self.__updateExceptionsLabel()
        self.__addToIgnoreButton.setEnabled(False)
        self.__jumpToCodeButton.setEnabled(False)
        self.__delAllButton.setEnabled(False)
        self.__currentItem = None
        self.sigClientExceptionsCleared.emit()

    def __onExceptionDoubleClicked(self, item, column):
        """Triggered when an exception is double clicked"""
        del item    # unused argument
        del column  # unused argument
        if self.__currentItem is not None:
            if self.__currentItem.getType() == STACK_FRAME_ITEM:
                self.__onJumpToCode()
                return

            # This is an exception item itself.
            # Open a separate dialog window with th detailed info.

    def __showContextMenu(self, coord):
        """Shows the frames list context menu"""
        self.__currentItem = self.exceptionsList.itemAt(coord)

        self.__addToIgnoreMenuItem.setEnabled(
            self.__addToIgnoreButton.isEnabled())
        self.__jumpToCodeMenuItem.setEnabled(
            self.__jumpToCodeButton.isEnabled())

        if self.__currentItem is not None:
            self.__excptMenu.popup(QCursor.pos())

    def __onAddToIgnore(self):
        """Adds an exception into the ignore list"""
        if self.__currentItem is not None:
            self.__ignoredExceptionsViewer.addExceptionFilter(
                str(self.__currentItem.getExceptionType()))
            self.__addToIgnoreButton.setEnabled(False)

    def __onJumpToCode(self):
        """Jumps to the corresponding source code line"""
        if self.__currentItem is not None:
            if self.__currentItem.getType() == STACK_FRAME_ITEM:
                fileName = self.__currentItem.getFileName()
                if '<' not in fileName and '>' not in fileName:
                    lineNumber = self.__currentItem.getLineNumber()

                    editorsManager = GlobalData().mainWindow.editorsManager()
                    editorsManager.openFile(fileName, lineNumber)
                    editor = editorsManager.currentWidget().getEditor()
                    editor.gotoLine(lineNumber)
                    editorsManager.currentWidget().setFocus()

    def __onDelAll(self):
        """Triggered when all the exceptions should be deleted"""
        self.clear()

    def addException(self, exceptionType, exceptionMessage, stackTrace):
        """Adds the exception to the view"""
        for index in range(self.exceptionsList.topLevelItemCount()):
            item = self.exceptionsList.topLevelItem(index)
            if item.equal(exceptionType, exceptionMessage, stackTrace):
                item.incrementCounter()
                self.exceptionsList.clearSelection()
                self.exceptionsList.setCurrentItem(item)
                self.__updateExceptionsLabel()
                return

        item = ExceptionItem(self.exceptionsList, exceptionType,
                             exceptionMessage, stackTrace)
        self.exceptionsList.clearSelection()
        self.exceptionsList.setCurrentItem(item)
        self.__updateExceptionsLabel()
        self.__delAllButton.setEnabled(True)

    def __updateExceptionsLabel(self):
        """Updates the exceptions header label"""
        total = self.getTotalCount()
        if total > 0:
            self.__excptLabel.setText("Exceptions (total: " + str(total) + ")")
        else:
            self.__excptLabel.setText("Exceptions")

    def getTotalCount(self):
        """Provides the total number of exceptions"""
        count = 0
        for index in range(self.exceptionsList.topLevelItemCount()):
            count += self.exceptionsList.topLevelItem(index).getCount()
        return count

    def __onProjectChanged(self, what):
        """Triggered when a project is changed"""
        if what == CodimensionProject.CompleteProject:
            self.clear()

    def __onSelectionChanged(self):
        """Triggered when the current item is changed"""
        selected = list(self.exceptionsList.selectedItems())
        if selected:
            self.__currentItem = selected[0]
            if self.__currentItem.getType() == STACK_FRAME_ITEM:
                fileName = self.__currentItem.getFileName()
                if '<' in fileName or '>' in fileName:
                    self.__jumpToCodeButton.setEnabled(False)
                else:
                    self.__jumpToCodeButton.setEnabled(True)
                self.__addToIgnoreButton.setEnabled(False)
            else:
                self.__jumpToCodeButton.setEnabled(False)
                excType = str(self.__currentItem.getExceptionType())
                if self.__ignoredExceptionsViewer.isIgnored(excType) or \
                   " " in excType or excType.startswith("unhandled"):
                    self.__addToIgnoreButton.setEnabled(False)
                else:
                    self.__addToIgnoreButton.setEnabled(True)
        else:
            self.__currentItem = None
            self.__addToIgnoreButton.setEnabled(False)
            self.__jumpToCodeButton.setEnabled(False)
