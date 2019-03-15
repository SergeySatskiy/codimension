# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2018  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Markdown viewer tab widget"""

import logging
import os.path
from .qt import (QWidget, Qt, pyqtSignal, QAction, QSize, QToolBar,
                 QPrintDialog, QDialog, QHBoxLayout)
from .mainwindowtabwidgetbase import MainWindowTabWidgetBase
from .viewhistory import ViewEntry, ViewHistory
from editor.mdwidget import MDViewer
from utils.globals import GlobalData
from utils.fileutils import getFileContent
from utils.md import renderMarkdown
from utils.pixmapcache import getIcon


class MDFullViewer(MDViewer):

    """Markdown viewer specific for non-editing mode (full view)"""

    def __init__(self, history, parent):
        MDViewer.__init__(self, parent)
        self.__history = history
        self.__parentWidget = parent

    def _onAnchorClicked(self, link):
        """Overwritten URL click handler"""
        if link == 'javascript:history.back()' or link == 'history.back()':
            if self.__parentWidget.viewerHistory.backAvailable():
                self.__parentWidget.onBack()
            else:
                logging.warning('No step back avaialable')
            return

        if link == 'javascript:history.forward()' or link == 'history.forward()':
            if self.__parentWidget.viewerHistory.forwardAvailable():
                self.__parentWidget.onForward()
            else:
                logging.warning('No step forward available')
            return

        fileName, lineNo = self._resolveLink(link)
        if fileName:
            self.__parentWidget.updateCurrentHistoryPosition()
            self.__parentWidget.setFileName(fileName)



class MarkdownTabWidget(QWidget, MainWindowTabWidgetBase):

    """Markdown widget"""

    sigEscapePressed = pyqtSignal()

    def __init__(self, readOnly, parent=None):
        MainWindowTabWidgetBase.__init__(self)
        QWidget.__init__(self, parent)

        self.viewerHistory = ViewHistory()
        self.viewerHistory.historyChanged.connect(self.__onHistoryChanged)
        self.__viewer = MDFullViewer(self.viewerHistory, self)
        self.__viewer.sigEscapePressed.connect(self.__onEsc)
        self.__readOnly = readOnly
        self.__fName = None

        self.__createLayout()

    def __onEsc(self):
        """Triggered when Esc is pressed"""
        self.sigEscapePressed.emit()

    def __createLayout(self):
        """Creates the toolbar and layout"""
        printButton = QAction(getIcon('printer.png'), 'Print', self)
        printButton.triggered.connect(self.__onPrint)

        fixedSpacer = QWidget()
        fixedSpacer.setFixedHeight(16)

        self.__backButton = QAction(getIcon('mdback.png'), 'Back', self)
        self.__backButton.triggered.connect(self.onBack)
        self.__backButton.setEnabled(False)

        self.__fwdButton = QAction(getIcon('mdfwd.png'), 'Forward', self)
        self.__fwdButton.triggered.connect(self.onForward)
        self.__fwdButton.setEnabled(False)

        if not self.__readOnly:
            self.__switchToEditButton = QAction(getIcon('switchtoedit.png'),
                                                'Switch to Editing', self)
            self.__switchToEditButton.triggered.connect(self.__onSwitchToEdit)
            self.__switchToEditButton.setEnabled(True)

            self.__reloadButton = QAction(getIcon('mdreload.png'),
                                          'Reload content', self)
            self.__reloadButton.triggered.connect(self.__onReload)
            self.__reloadButton.setEnabled(True)

        # Toolbar
        toolbar = QToolBar(self)
        toolbar.setOrientation(Qt.Vertical)
        toolbar.setMovable(False)
        toolbar.setAllowedAreas(Qt.RightToolBarArea)
        toolbar.setIconSize(QSize(16, 16))
        toolbar.setFixedWidth(28)
        toolbar.setContentsMargins(0, 0, 0, 0)

        toolbar.addAction(printButton)
        toolbar.addWidget(fixedSpacer)
        toolbar.addAction(self.__backButton)
        toolbar.addAction(self.__fwdButton)

        if not self.__readOnly:
            fixedSpacer2 = QWidget()
            fixedSpacer2.setFixedHeight(16)
            toolbar.addWidget(fixedSpacer2)
            toolbar.addAction(self.__switchToEditButton)

            fixedSpacer3 = QWidget()
            fixedSpacer3.setFixedHeight(16)
            toolbar.addWidget(fixedSpacer3)
            toolbar.addAction(self.__reloadButton)

        hLayout = QHBoxLayout()
        hLayout.setContentsMargins(0, 0, 0, 0)
        hLayout.setSpacing(0)
        hLayout.addWidget(self.__viewer)
        hLayout.addWidget(toolbar)

        self.setLayout(hLayout)

    def setFocus(self):
        """Overridden setFocus"""
        self.__viewer.setFocus()

    def isReadOnly(self):
        """True if it is a read only mode"""
        return self.__readOnly

    def __onPrint(self):
        """Print the markdown page"""
        dialog = QPrintDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            printer = dialog.printer()
            self.__viewer.print_(printer)

    def updateCurrentHistoryPosition(self):
        """Updates the current history entry position value"""
        pos = tuple(self.__viewer.getScrollbarPositions())
        self.viewerHistory.getCurrentEntry().pos = pos

    def onBack(self):
        """Back in the history"""
        if self.viewerHistory.backAvailable():
            self.updateCurrentHistoryPosition()
            self.viewerHistory.stepBack()
            entry = self.viewerHistory.getCurrentEntry()
            self.setFileName(entry.fName, True)
            self.__viewer.setScrollbarPositions(entry.pos[0], entry.pos[1])

    def onForward(self):
        """Forward in the history"""
        if self.viewerHistory.forwardAvailable():
            self.updateCurrentHistoryPosition()
            self.viewerHistory.stepForward()
            entry = self.viewerHistory.getCurrentEntry()
            self.setFileName(entry.fName, True)
            self.__viewer.setScrollbarPositions(entry.pos[0], entry.pos[1])

    def __onSwitchToEdit(self):
        """Switch to editing mode"""
        fName = self.getFileName()
        if fName:
            mainWindow = GlobalData().mainWindow
            mainWindow.em.onCloseTab()
            mainWindow.em.openFile(fName, -1)

    def __onReload(self):
        """Reloads the file content"""
        if self.getFileName():
            hPos, vPos = self.__viewer.getScrollbarPositions()
            self.setFileName(self.getFileName(), True)
            self.__viewer.setScrollbarPositions(hPos, vPos)

    def __onHistoryChanged(self):
        """Updates the back and forward buttons"""
        self.__backButton.setEnabled(self.viewerHistory.backAvailable())
        self.__fwdButton.setEnabled(self.viewerHistory.forwardAvailable())

    # Mandatory interface part is below

    def isModified(self):
        """Tells if the file is modified"""
        return False

    def getRWMode(self):
        """Tells if the file is read only"""
        return "RO"

    def getType(self):
        """Tells the widget type"""
        return MainWindowTabWidgetBase.MDViewer

    def getLanguage(self):
        """Tells the content language"""
        return "Markdown"

    def setFileName(self, path, fromHistory=False):
        """Sets the file name"""
        try:
            content = getFileContent(path)
        except Exception as exc:
            logging.error(str(exc))
            return

        renderedText, errors, warnings = renderMarkdown(content, path)
        if errors:
            for error in errors:
                logging.error(error)
            return

        if not fromHistory:
            # Need to add an entry for the new item
            newEntry = ViewEntry(path, (0, 0))
            self.viewerHistory.addEntry(newEntry)

        self.__fName = path
        self.__viewer.setHtml(renderedText)
        if warnings:
            for warning in warnings:
                logging.warning(warning)

        mainWindow = GlobalData().mainWindow
        mainWindow.em.setTabText(mainWindow.em.currentIndex(),
                                 self.getShortName())
        mainWindow.em.updateStatusBar()

    def getFileName(self):
        """Tells what file name of the widget"""
        return self.__fName

    def setEncoding(self, newEncoding):
        """Sets the new encoding - not applicable for the markdown viewer"""
        return

    def getShortName(self):
        """Tells the display name"""
        if self.__fName:
            return os.path.basename(self.__fName)
        return 'n/a'

    def setShortName(self, name):
        """Sets the display name - not applicable"""
        raise Exception("Setting a short name for a markdown viewer "
                        "is not applicable")
