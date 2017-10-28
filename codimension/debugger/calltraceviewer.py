# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2017 Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Call trace viewer"""


import logging
from ui.qt import (QTreeWidget, QAbstractItemView, QWidget, QVBoxLayout, Qt,
                   QFrame, QAction, QHBoxLayout, QToolBar, QSize, QLabel,
                   QSizePolicy, QRegExp, QTreeWidgetItem, QApplication)
from ui.itemdelegates import NoOutlineHeightDelegate
from utils.colorfont import getLabelStyle, HEADER_HEIGHT
from utils.settings import Settings
from utils.globals import GlobalData
from utils.pixmapcache import getIcon
from utils.project import CodimensionProject


class CallTraceBrowser(QTreeWidget):

    """Call trace browser implementation"""

    def __init__(self, parent=None):
        QTreeWidget.__init__(self, parent)

        self.setExpandsOnDoubleClick(False)
        self.setAlternatingRowColors(True)
        self.setUniformRowHeights(True)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setItemDelegate(NoOutlineHeightDelegate(4))

        self.setHeaderLabels(["", "From", "To"])

        self.__callStack = []
        self.__callIcon = getIcon('calltracecall.png')
        self.__retIcon = getIcon('calltracereturn.png')

        self.projectLoaded = False
        self.count = 0

        self.__entryRe = QRegExp(r"""(.+):(\d+)\s\((.*)\)""")
        self.__entryFormat = "{0}:{1} ({2})"

        self.itemActivated.connect(self.__itemActivated)

    def onProjectChanged(self):
        """Triggered when a project is changed"""
        self.projectLoaded = GlobalData().project.isLoaded()

    def clear(self):
        """Clears the data"""
        QTreeWidget.clear(self)
        self.__callStack = []
        self.count = 0

    def addCallTrace(self, isCall, fromFile, fromLine, fromFunction,
                     toFile, toLine, toFunction):
        """Adds a record to the list"""
        tooltip = 'Return\n'
        icon = self.__retIcon
        if isCall:
            tooltip = 'Call\n'
            icon = self.__callIcon

        if self.projectLoaded:
            project = GlobalData().project
            fromFile = project.getRelativePath(fromFile)
            toFile = project.getRelativePath(toFile)

        parentItem = self
        if self.__callStack:
            parentItem = self.__callStack[-1]

        fromItem = self.__entryFormat.format(fromFile, fromLine, fromFunction)
        toItem = self.__entryFormat.format(toFile, toLine, toFunction)
        item = QTreeWidgetItem(parentItem, ['', fromItem, toItem])
        item.setIcon(0, icon)
        item.setData(0, Qt.UserRole, isCall)
        item.setExpanded(True)

        tooltip += 'From: ' + fromItem + '\nTo: ' + toItem
        item.setToolTip(1, tooltip)
        item.setToolTip(2, tooltip)

        if isCall:
            self.__callStack.append(item)
        else:
            if self.__callStack:
                self.__callStack.pop(-1)

        self.count += 1

    def __itemActivated(self, item, column):
        """Double click on the item"""
        if item is not None and column > 0:
            columnStr = item.text(column)
            if self.__entryRe.exactMatch(columnStr.strip()):
                filename, lineno, _ = self.__entryRe.capturedTexts()[1:]
                try:
                    lineno = int(lineno)
                except ValueError:
                    return

            if self.projectLoaded:
                filename = GlobalData().project.getAbsolutePath(filename)

            editorsManager = GlobalData().mainWindow.editorsManager()
            editorsManager.openFile(filename, lineno)
            editor = editorsManager.currentWidget().getEditor()
            editor.gotoLine(lineno)
            editorsManager.currentWidget().setFocus()


class CallTraceViewer(QWidget):

    """Implements the call trace viewer"""

    def __init__(self, debugger, parent=None):
        QWidget.__init__(self, parent)

        self.__debugger = debugger
        self.__createLayout()

        self.__debugger.sigClientCallTrace.connect(self.__onCallTrace)
        GlobalData().project.sigProjectChanged.connect(self.__onProjectChanged)

    def __onProjectChanged(self, what):
        """Triggered when a project is changed"""
        if what == CodimensionProject.CompleteProject:
            self.clear()
            self.calltraceList.onProjectChanged()

    def __createLayout(self):
        """Creates the widget layout"""
        verticalLayout = QVBoxLayout(self)
        verticalLayout.setContentsMargins(0, 0, 0, 0)
        verticalLayout.setSpacing(0)

        self.headerFrame = QFrame()
        self.headerFrame.setObjectName('calltraceheader')
        self.headerFrame.setStyleSheet('QFrame#calltraceheader {' +
                                       getLabelStyle(self) + '}')
        self.headerFrame.setFixedHeight(HEADER_HEIGHT)

        self.__calltraceLabel = QLabel("Call Trace")

        headerLayout = QHBoxLayout()
        headerLayout.setContentsMargins(0, 0, 0, 0)
        headerLayout.addSpacing(3)
        headerLayout.addWidget(self.__calltraceLabel)
        self.headerFrame.setLayout(headerLayout)

        self.calltraceList = CallTraceBrowser(self)

        self.__startButton = QAction(
            getIcon('calltracestart.png'), "Start call tracing", self)
        self.__startButton.triggered.connect(self.__onStart)
        self.__startButton.setEnabled(not Settings()['calltrace'])

        self.__stopButton = QAction(
            getIcon('calltracestop.png'), "Stop call tracing", self)
        self.__stopButton.triggered.connect(self.__onStop)
        self.__stopButton.setEnabled(Settings()['calltrace'])

        self.__resizeButton = QAction(
            getIcon('resizecolumns.png'),
            "Resize the columns to their contents", self)
        self.__resizeButton.triggered.connect(self.__onResize)
        self.__resizeButton.setEnabled(True)

        self.__clearButton = QAction(
            getIcon('trash.png'), "Clear", self)
        self.__clearButton.triggered.connect(self.__onClear)
        self.__clearButton.setEnabled(False)

        self.__copyButton = QAction(
            getIcon('copymenu.png'), "Copy to clipboard", self)
        self.__copyButton.triggered.connect(self.__onCopy)
        self.__copyButton.setEnabled(False)

        # Toolbar
        self.toolbar = QToolBar()
        self.toolbar.setOrientation(Qt.Horizontal)
        self.toolbar.setMovable(False)
        self.toolbar.setAllowedAreas(Qt.TopToolBarArea)
        self.toolbar.setIconSize(QSize(16, 16))
        self.toolbar.setFixedHeight(28)
        self.toolbar.setContentsMargins(0, 0, 0, 0)
        self.toolbar.addAction(self.__startButton)
        self.toolbar.addAction(self.__stopButton)

        fixedSpacer2 = QWidget()
        fixedSpacer2.setFixedWidth(15)
        self.toolbar.addWidget(fixedSpacer2)
        self.toolbar.addAction(self.__resizeButton)
        self.toolbar.addAction(self.__copyButton)
        expandingSpacer = QWidget()
        expandingSpacer.setSizePolicy(QSizePolicy.Expanding,
                                      QSizePolicy.Expanding)
        fixedSpacer4 = QWidget()
        fixedSpacer4.setFixedWidth(5)
        self.toolbar.addWidget(fixedSpacer4)
        self.toolbar.addWidget(expandingSpacer)
        self.toolbar.addAction(self.__clearButton)

        verticalLayout.addWidget(self.headerFrame)
        verticalLayout.addWidget(self.toolbar)
        verticalLayout.addWidget(self.calltraceList)

    def __onCallTrace(self, isCall, fromFile, fromLine, fromFunction,
                      toFile, toLine, toFunction):
        """Call trace message received"""
        self.calltraceList.addCallTrace(isCall, fromFile, fromLine,
                                        fromFunction, toFile, toLine,
                                        toFunction)
        self.__clearButton.setEnabled(True)
        self.__copyButton.setEnabled(True)
        self.__updateHeader()

    def __updateHeader(self):
        """Updates the header"""
        count = self.calltraceList.count
        if count:
            self.__calltraceLabel.setText('Call Trace (' + str(count) + ')')
        else:
            self.__calltraceLabel.setText('Call Trace')

    def __onStart(self):
        """Start collecting calltrace"""
        self.__startButton.setEnabled(False)
        self.__stopButton.setEnabled(True)
        Settings()['calltrace'] = True
        self.__debugger.startCalltrace()

    def __onStop(self):
        """Stop collecting calltrace"""
        self.__startButton.setEnabled(True)
        self.__stopButton.setEnabled(False)
        Settings()['calltrace'] = False
        self.__debugger.stopCalltrace()

    def __onResize(self):
        """Resize the columns to its width"""
        for column in range(self.calltraceList.columnCount()):
            self.calltraceList.resizeColumnToContents(column)

    def __onClear(self):
        """Clears the view"""
        self.calltraceList.clear()
        self.__clearButton.setEnabled(False)
        self.__copyButton.setEnabled(False)
        self.__updateHeader()

    def clear(self):
        """Clears the view"""
        self.__onClear()

    def __onCopy(self):
        """Copy the content as text to clipboard"""
        content = []
        lhsMaxLength = 0
        try:
            item = self.calltraceList.topLevelItem(0)
            while item is not None:
                call = '<-'
                if item.data(0, Qt.UserRole):
                    call = '->'
                lhs = item.text(1)
                lhsLength = len(lhs)
                lhsMaxLength = max(lhsMaxLength, lhsLength)

                content.append([lhs, lhsLength, call + ' ' + item.text(2)])
                item = self.calltraceList.itemBelow(item)

            for index in range(len(content)):
                content[index] = \
                    content[index][0] + \
                    ' ' * (lhsMaxLength - content[index][1] + 1) + \
                    content[index][2]

            QApplication.clipboard().setText('\n'.join(content))
        except Exception as exc:
            logging.error('Error copying the call trace to clipboard: ' +
                          str(exc))
