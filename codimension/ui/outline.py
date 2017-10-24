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

"""The file outline viewer implementation"""

import os.path
import logging
from utils.pixmapcache import getIcon
from utils.globals import GlobalData
from utils.settings import Settings
from utils.fileutils import isPythonMime, isPythonFile
from cdmpyparser import getBriefModuleInfoFromMemory
from .qt import (Qt, QSize, QTimer, QCursor, QPalette, QMenu, QWidget, QAction,
                 QVBoxLayout, QToolBar, QFrame, QLabel)
from .outlinebrowser import OutlineBrowser
from .viewitems import (FunctionItemType, ClassItemType, AttributeItemType,
                        GlobalItemType)
from .mainwindowtabwidgetbase import MainWindowTabWidgetBase
from .parsererrors import ParserErrorsDialog


class OutlineAttributes:

    """Holds all the attributes associated with an outline browser"""

    def __init__(self):
        self.browser = None
        self.contextItem = None
        self.info = None
        self.shortFileName = ""
        self.changed = False
        return


class FileOutlineViewer(QWidget):

    """ The file outline viewer widget """

    def __init__(self, editorsManager, parent=None):
        QWidget.__init__(self, parent)

        self.__editorsManager = editorsManager
        self.__mainWindow = parent
        self.__editorsManager.currentChanged.connect(self.__onTabChanged)
        self.__editorsManager.sigTabClosed.connect(self.__onTabClosed)
        self.__editorsManager.sigBufferSavedAs.connect(self.__onSavedBufferAs)
        self.__editorsManager.sigFileTypeChanged.connect(
            self.__onFileTypeChanged)

        self.__outlineBrowsers = {}  # UUID -> OutlineAttributes
        self.__currentUUID = None
        self.__updateTimer = QTimer(self)
        self.__updateTimer.setSingleShot(True)
        self.__updateTimer.timeout.connect(self.__updateView)

        self.findButton = None
        self.outlineViewer = None
        self.toolbar = None
        self.__createLayout()

        self.__modifiedFormat = Settings()['modifiedFormat']

        # create the context menu
        self.__menu = QMenu(self)
        self.__findMenuItem = self.__menu.addAction(
            getIcon('findusage.png'), 'Find where used', self.__findWhereUsed)

    def setTooltips(self, switchOn):
        """Sets the tooltips mode"""
        for key in self.__outlineBrowsers:
            self.__outlineBrowsers[key].browser.setTooltips(switchOn)

    def __connectOutlineBrowser(self, browser):
        """Connects a new buffer signals"""
        browser.setContextMenuPolicy(Qt.CustomContextMenu)
        browser.customContextMenuRequested.connect(
            self.__handleShowContextMenu)
        browser.sigFirstSelectedItem.connect(self.__selectionChanged)

    def __createLayout(self):
        """Helper to create the viewer layout"""
        # Toolbar part - buttons
        self.findButton = QAction(
            getIcon('findusage.png'), 'Find where highlighted item is used',
            self)
        self.findButton.setVisible(False)
        self.findButton.triggered.connect(self.__findWhereUsed)
        self.showParsingErrorsButton = QAction(
            getIcon('showparsingerrors.png'), 'Show lexer/parser errors', self)
        self.showParsingErrorsButton.triggered.connect(self.__showParserError)
        self.showParsingErrorsButton.setEnabled(False)

        self.toolbar = QToolBar(self)
        self.toolbar.setMovable(False)
        self.toolbar.setAllowedAreas(Qt.TopToolBarArea)
        self.toolbar.setIconSize(QSize(16, 16))
        self.toolbar.setFixedHeight(28)
        self.toolbar.setContentsMargins(0, 0, 0, 0)
        self.toolbar.addAction(self.findButton)
        self.toolbar.addAction(self.showParsingErrorsButton)

        # Prepare members for reuse
        self.__noneLabel = QLabel("\nNot a python file")
        self.__noneLabel.setFrameShape(QFrame.StyledPanel)
        self.__noneLabel.setAlignment(Qt.AlignHCenter)
        headerFont = self.__noneLabel.font()
        headerFont.setPointSize(headerFont.pointSize() + 2)
        self.__noneLabel.setFont(headerFont)
        self.__noneLabel.setAutoFillBackground(True)
        noneLabelPalette = self.__noneLabel.palette()
        noneLabelPalette.setColor(QPalette.Background,
                                  GlobalData().skin['nolexerPaper'])
        self.__noneLabel.setPalette(noneLabelPalette)

        self.__layout = QVBoxLayout()
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.__layout.setSpacing(0)
        self.__layout.addWidget(self.toolbar)
        self.__layout.addWidget(self.__noneLabel)

        self.setLayout(self.__layout)

    def __selectionChanged(self, index):
        """Handles the changed selection"""
        if index.isValid():
            self.__outlineBrowsers[self.__currentUUID].contentItem = \
                self.__outlineBrowsers[
                    self.__currentUUID].browser.model().item(index)
        else:
            self.__outlineBrowsers[self.__currentUUID].contentItem = None
        self.__updateButtons()

    def __handleShowContextMenu(self, coord):
        """ Show the context menu """
        browser = self.__outlineBrowsers[self.__currentUUID].browser
        index = browser.indexAt(coord)
        if not index.isValid():
            return

        # This will update the contextItem
        self.__selectionChanged(index)

        contextItem = self.__outlineBrowsers[self.__currentUUID].contentItem
        if contextItem:
            self.__findMenuItem.setEnabled(self.findButton.isEnabled())
            self.__menu.popup(QCursor.pos())

    def __goToDefinition(self):
        """Jump to definition context menu handler"""
        contextItem = self.__outlineBrowsers[self.__currentUUID].contentItem
        if contextItem is not None:
            self.__outlineBrowsers[
                self.__currentUUID].browser.openItem(contextItem)

    def __findWhereUsed(self):
        """Find where used context menu handler"""
        contextItem = self.__outlineBrowsers[self.__currentUUID].contentItem
        if contextItem is not None:
            GlobalData().mainWindow.findWhereUsed(
                contextItem.getPath(),
                contextItem.sourceObj)

    def __updateButtons(self):
        """Updates the toolbar buttons depending on what is selected"""
        self.findButton.setEnabled(False)

        contextItem = self.__outlineBrowsers[self.__currentUUID].contentItem
        if contextItem is None:
            if contextItem.itemType in [FunctionItemType, ClassItemType,
                                        AttributeItemType, GlobalItemType]:
                self.findButton.setEnabled(True)

    def __onTabChanged(self, index):
        """Triggered when another tab becomes active"""
        # If the timer is still active that means the tab was switched before
        # the handler had a chance to work. Therefore update the previous tab
        # first if so.
        if self.__updateTimer.isActive():
            self.__updateTimer.stop()
            self.__updateView()

        # Now, switch the outline browser to the new tab
        if index == -1:
            widget = self.__editorsManager.currentWidget()
        else:
            widget = self.__editorsManager.getWidgetByIndex(index)
        if widget is None:
            if self.__currentUUID is not None:
                self.__outlineBrowsers[self.__currentUUID].browser.hide()
                self.__currentUUID = None
            self.__noneLabel.show()
            self.showParsingErrorsButton.setEnabled(False)
            return
        if widget.getType() not in [MainWindowTabWidgetBase.PlainTextEditor,
                                    MainWindowTabWidgetBase.VCSAnnotateViewer]:
            if self.__currentUUID is not None:
                self.__outlineBrowsers[self.__currentUUID].browser.hide()
                self.__currentUUID = None
            self.__noneLabel.show()
            self.showParsingErrorsButton.setEnabled(False)
            return

        # This is text editor, detect the file type
        if not isPythonMime(widget.getMime()):
            if self.__currentUUID is not None:
                self.__outlineBrowsers[self.__currentUUID].browser.hide()
                self.__currentUUID = None
            self.__noneLabel.show()
            self.showParsingErrorsButton.setEnabled(False)
            return

        # This is a python file, check if we already have the parsed info in
        # the cache
        uuid = widget.getUUID()
        if uuid in self.__outlineBrowsers:
            # We have it, hide the current and show the existed
            if self.__currentUUID is not None:
                self.__outlineBrowsers[self.__currentUUID].browser.hide()
                self.__currentUUID = None
            else:
                self.__noneLabel.hide()
            self.__currentUUID = uuid
            self.__outlineBrowsers[self.__currentUUID].browser.show()

            info = self.__outlineBrowsers[self.__currentUUID].info
            self.showParsingErrorsButton.setEnabled(info.isOK != True)
            return

        # It is first time we are here, create a new
        editor = widget.getEditor()
        editor.textChanged.connect(self.__onBufferChanged)
        editor.cursorPositionChanged.connect(self.__cursorPositionChanged)
        info = getBriefModuleInfoFromMemory(editor.text)

        self.showParsingErrorsButton.setEnabled(info.isOK != True)

        shortFileName = widget.getShortName()
        browser = OutlineBrowser(uuid, shortFileName, info, self)
        browser.setHeaderHighlight(info.isOK != True)
        self.__connectOutlineBrowser(browser)
        self.__layout.addWidget(browser)
        if self.__currentUUID is not None:
            self.__outlineBrowsers[self.__currentUUID].browser.hide()
            self.__currentUUID = None
        else:
            self.__noneLabel.hide()

        self.__currentUUID = uuid
        attributes = OutlineAttributes()
        attributes.browser = browser
        attributes.contextItem = None
        attributes.info = info
        attributes.shortFileName = shortFileName
        attributes.changed = False
        self.__outlineBrowsers[self.__currentUUID] = attributes
        self.__outlineBrowsers[self.__currentUUID].browser.show()

    def getCurrentUsedInfo(self):
        """Provides the info used to show the current outline window"""
        if self.__currentUUID in self.__outlineBrowsers:
            return self.__outlineBrowsers[self.__currentUUID].info
        return None

    def __cursorPositionChanged(self):
        """Triggered when a cursor position is changed"""
        if self.__updateTimer.isActive():
            # If a file is very large and the cursor is moved
            # straight after changes this will delay the update till
            # the real pause.
            self.__updateTimer.stop()
            self.__updateTimer.start(1500)

    def __onBufferChanged(self):
        """Triggered when a change in the buffer is identified"""
        if self.__currentUUID is None:
            return
        widget = self.__editorsManager.getWidgetByUUID(self.__currentUUID)
        if widget is None:
            return
        if self.__mainWindow.debugMode:
            return

        self.__updateTimer.stop()
        if self.__currentUUID in self.__outlineBrowsers:
            if not self.__outlineBrowsers[self.__currentUUID].changed:
                self.__outlineBrowsers[self.__currentUUID].changed = True
                browser = self.__outlineBrowsers[self.__currentUUID].browser
                fName = self.__outlineBrowsers[
                    self.__currentUUID].shortFileName
                title = self.__modifiedFormat % fName
                browser.model().sourceModel().updateRootData(0, title)
        self.__updateTimer.start(1500)

    def __updateView(self):
        """Updates the view when a file is changed"""
        self.__updateTimer.stop()
        info = self.getCurrentBufferInfo()
        if info is None:
            return

        self.showParsingErrorsButton.setEnabled(info.isOK != True)
        browser = self.__outlineBrowsers[self.__currentUUID].browser
        fName = self.__outlineBrowsers[self.__currentUUID].shortFileName
        browser.setHeaderHighlight(info.isOK != True)

        if not info.isOK:
            title = self.__modifiedFormat % fName
            browser.model().sourceModel().updateRootData(0, title)
            return

        browser.model().sourceModel().updateRootData(0, fName)
        self.__outlineBrowsers[self.__currentUUID].changed = False

        browser.updateFileItem(browser.model().sourceModel().rootItem, info)
        self.__outlineBrowsers[self.__currentUUID].info = info

    def getCurrentBufferInfo(self):
        """Provides the current buffer parsed info"""
        if self.__currentUUID is None:
            return None
        widget = self.__editorsManager.getWidgetByUUID(self.__currentUUID)
        if widget is None:
            return None

        editor = widget.getEditor()
        info = getBriefModuleInfoFromMemory(editor.text)
        return info

    def __onTabClosed(self, uuid):
        """Triggered when a tab is closed"""
        if uuid in self.__outlineBrowsers:
            del self.__outlineBrowsers[uuid]

    def __onSavedBufferAs(self, fileName, uuid):
        """Triggered when a file is saved with a new name"""
        if uuid in self.__outlineBrowsers:
            baseName = os.path.basename(fileName)
            if not isPythonFile(fileName):
                # It's not a python file anymore
                if uuid == self.__currentUUID:
                    self.__outlineBrowsers[uuid].browser.hide()
                    self.__noneLabel.show()
                    self.__currentUUID = None

                del self.__outlineBrowsers[uuid]
                self.showParsingErrorsButton.setEnabled(False)
                self.findButton.setEnabled(False)
                return

            # Still python file with a different name
            browser = self.__outlineBrowsers[uuid].browser
            self.__outlineBrowsers[uuid].shortFileName = baseName
            if self.__outlineBrowsers[uuid].changed:
                title = self.__modifiedFormat % baseName
            else:
                title = baseName
            browser.model().sourceModel().updateRootData(0, title)

    def __onFileTypeChanged(self, fileName, uuid, newFileType):
        """Triggered when the current buffer file type is changed, e.g. .cgi"""
        del fileName    # unused argument
        if isPythonMime(newFileType):
            # The file became a python one
            if uuid not in self.__outlineBrowsers:
                self.__onTabChanged(-1)
        else:
            if uuid in self.__outlineBrowsers:
                # It's not a python file any more
                if uuid == self.__currentUUID:
                    self.__outlineBrowsers[uuid].browser.hide()
                    self.__noneLabel.show()
                    self.__currentUUID = None

                del self.__outlineBrowsers[uuid]
                self.showParsingErrorsButton.setEnabled(False)
                self.findButton.setEnabled(False)

    def __showParserError(self):
        """Shows the parser errors window"""
        if self.__currentUUID is None:
            return

        try:
            widget = self.__editorsManager.getWidgetByUUID(self.__currentUUID)
            if widget is None:
                return

            editor = widget.getEditor()
            info = getBriefModuleInfoFromMemory(editor.text)
            fName = self.__outlineBrowsers[self.__currentUUID].shortFileName
            dialog = ParserErrorsDialog(fName, info)
            dialog.exec_()
        except Exception as ex:
            logging.error(str(ex))

    def highlightContextItem(self, context, line):
        """Highlights the context item"""
        if not self.__currentUUID in self.__outlineBrowsers:
            return False
        browser = self.__outlineBrowsers[self.__currentUUID].browser
        info = self.__outlineBrowsers[self.__currentUUID].info
        return browser.highlightContextItem(context, line, info)
