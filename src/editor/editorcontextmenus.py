# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2017  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Sets up and handles the text editor conext menus"""


import logging
import os.path
import socket
import urllib.request
from ui.qt import QMenu, QActionGroup, QApplication, Qt, QCursor
from utils.pixmapcache import getIcon
from utils.globals import GlobalData
from utils.encoding import SUPPORTED_CODECS, decodeURLContent
from autocomplete.bufferutils import isImportLine


class EditorContextMenuMixin:

    """Encapsulates the context menu handling"""

    def __init__(self):
        self.supportedEncodings = {}
        self.encodingMenu = None
        self.encodingsActGrp = None

        mainWindow = GlobalData().mainWindow
        editorsManager = mainWindow.editorsManagerWidget.editorsManager

        self._menu = QMenu(self)
        self.__menuUndo = self._menu.addAction(
            getIcon('undo.png'), '&Undo', self.onUndo, "Ctrl+Z")
        self.__menuRedo = self._menu.addAction(
            getIcon('redo.png'), '&Redo', self.onRedo, "Ctrl+Y")
        self._menu.addSeparator()

        self.__menuCut = self._menu.addAction(
            getIcon('cutmenu.png'), 'Cu&t', self.onShiftDel, "Ctrl+X")
        self.__menuCopy = self._menu.addAction(
            getIcon('copymenu.png'), '&Copy', self.onCtrlC, "Ctrl+C")
        self.__menuPaste = self._menu.addAction(
            getIcon('pastemenu.png'), '&Paste', self.paste, "Ctrl+V")
        self.__menuSelectAll = self._menu.addAction(
            getIcon('selectallmenu.png'), 'Select &all',
            self.selectAll, "Ctrl+A")
        self._menu.addSeparator()

        menu = self._menu.addMenu(self.__initEncodingMenu())
        menu.setIcon(getIcon('textencoding.png'))
        self._menu.addSeparator()

        menu = self._menu.addMenu(self.__initToolsMenu())
        menu.setIcon(getIcon('toolsmenu.png'))
        self._menu.addSeparator()

        menu = self._menu.addMenu(self.__initDiagramsMenu())
        menu.setIcon(getIcon('diagramsmenu.png'))
        self._menu.addSeparator()

        self.__menuOpenAsFile = self._menu.addAction(
            getIcon('filemenu.png'), 'O&pen as file', self.openAsFile)
        self.__menuDownloadAndShow = self._menu.addAction(
            getIcon('filemenu.png'), 'Do&wnload and show',
            self.downloadAndShow)
        self.__menuOpenInBrowser = self._menu.addAction(
            getIcon('homepagemenu.png'), 'Open in browser', self.openInBrowser)
        self._menu.addSeparator()

        self.__menuHighlightInPrj = self._menu.addAction(
            getIcon("highlightmenu.png"), "&Highlight in project browser",
            editorsManager.onHighlightInPrj)
        self.__menuHighlightInFS = self._menu.addAction(
            getIcon("highlightmenu.png"), "H&ighlight in file system browser",
            editorsManager.onHighlightInFS)
        self._menuHighlightInOutline = self._menu.addAction(
            getIcon("highlightmenu.png"), "Highlight in &outline browser",
            self.highlightInOutline, 'Ctrl+B')

        self._menu.aboutToShow.connect(self._contextMenuAboutToShow)

        # Plugins support
        self.__pluginMenuSeparator = self._menu.addSeparator()
        mainWindow = GlobalData().mainWindow
        editorsManager = mainWindow.editorsManagerWidget.editorsManager
        registeredMenus = editorsManager.getPluginMenus()
        if registeredMenus:
            for path in registeredMenus:
                self._menu.addMenu(registeredMenus[path])
        else:
            self.__pluginMenuSeparator.setVisible(False)

        editorsManager.sigPluginContextMenuAdded.connect(
            self.__onPluginMenuAdded)
        editorsManager.sigPluginContextMenuRemoved.connect(
            self.__onPluginMenuRemoved)

    def __initEncodingMenu(self):
        """Creates the encoding menu"""
        self.encodingMenu = QMenu("&Encoding")
        self.encodingsActGrp = QActionGroup(self)
        for encoding in sorted(SUPPORTED_CODECS):
            act = self.encodingMenu.addAction(encoding)
            act.setCheckable(True)
            act.setData(encoding)
            self.supportedEncodings[encoding] = act
            self.encodingsActGrp.addAction(act)
        self.encodingMenu.triggered.connect(self.__encodingsMenuTriggered)
        return self.encodingMenu

    def __initToolsMenu(self):
        """Creates the tools menu"""
        self.toolsMenu = QMenu("Too&ls")
        self.runAct = self.toolsMenu.addAction(
            getIcon('run.png'), 'Run script', self._parent.onRunScript)
        self.runParamAct = self.toolsMenu.addAction(
            getIcon('paramsmenu.png'), 'Set parameters and run',
            self._parent.onRunScriptSettings)
        self.toolsMenu.addSeparator()
        self.profileAct = self.toolsMenu.addAction(
            getIcon('profile.png'), 'Profile script',
            self._parent.onProfileScript)
        self.profileParamAct = self.toolsMenu.addAction(
            getIcon('paramsmenu.png'), 'Set parameters and profile',
            self._parent.onProfileScriptSettings)
        return self.toolsMenu

    def __initDiagramsMenu(self):
        """Creates the diagrams menu"""
        self.diagramsMenu = QMenu("&Diagrams")
        self.importsDgmAct = self.diagramsMenu.addAction(
            getIcon('importsdiagram.png'), 'Imports diagram',
            self._parent.onImportDgm)
        self.importsDgmParamAct = self.diagramsMenu.addAction(
            getIcon('paramsmenu.png'), 'Fine tuned imports diagram',
            self._parent.onImportDgmTuned)
        return self.diagramsMenu

    def _contextMenuAboutToShow(self):
        """Context menu is about to show"""
        print("_contextMenuAboutToShow")
        self._menuHighlightInOutline.setEnabled(self.isPythonBuffer())

        self.runAct.setEnabled(self._parent.runScriptButton.isEnabled())
        self.runParamAct.setEnabled(self._parent.runScriptButton.isEnabled())
        self.profileAct.setEnabled(self._parent.runScriptButton.isEnabled())
        self.profileParamAct.setEnabled(
            self._parent.runScriptButton.isEnabled())

    def contextMenuEvent(self, event):
        """Called just before showing a context menu"""
        print("contextMenuEvent")
        event.accept()
        self.__menuUndo.setEnabled(self.document().isUndoAvailable())
        self.__menuRedo.setEnabled(self.document().isRedoAvailable())
        self.__menuCut.setEnabled(not self.isReadOnly())
        self.__menuPaste.setEnabled(QApplication.clipboard().text() != ""
                                    and not self.isReadOnly())

        # Check the proper encoding in the menu
        fileName = self._parent.getFileName()
        self.encodingMenu.setEnabled(True)
        encoding = self.encoding
        if encoding in self.supportedEncodings:
            self.supportedEncodings[encoding].setChecked(True)

        self.__menuOpenAsFile.setEnabled(self.openAsFileAvailable())
        self.__menuDownloadAndShow.setEnabled(
            self.downloadAndShowAvailable())
        self.__menuOpenInBrowser.setEnabled(
            self.downloadAndShowAvailable())
        self.__menuHighlightInPrj.setEnabled(
            os.path.isabs(fileName) and GlobalData().project.isLoaded() and
            GlobalData().project.isProjectFile(fileName))
        self.__menuHighlightInFS.setEnabled(os.path.isabs(fileName))
        self._menuHighlightInOutline.setEnabled(self.isPythonBuffer())
        self._menu.popup(event.globalPos())

    def __encodingsMenuTriggered(self, act):
        """Triggered when encoding is selected"""
        encoding = act.data()
        self.setEncoding(encoding)

    def onUndo(self):
        """Undo implementation"""
        if self.document().isUndoAvailable():
            self.undo()
            self._parent.modificationChanged()

    def onRedo(self):
        """Redo implementation"""
        if self.document().isRedoAvailable():
            self.redo()
            self._parent.modificationChanged()

    def onShiftDel(self):
        """Triggered when Shift+Del is received"""
        if self.hasSelectedText():
            self.cut()
        else:
            self.copyLine()
            self.deleteLine()

    def onCtrlC(self):
        """Handles copying"""
        if self.hasSelectedText():
            self.copy()
        else:
            self.copyLine()

    def openAsFile(self):
        """Opens a selection or a current tag as a file"""
        selectedText = self.selectedText().strip()
        singleSelection = selectedText != "" and \
                          '\n' not in selectedText and \
                          '\r' not in selectedText
        currentWord = ""
        if selectedText == "":
            currentWord = self.getCurrentWord().strip()

        path = currentWord
        if singleSelection:
            path = selectedText

        # Now the processing
        if os.path.isabs(path):
            GlobalData().mainWindow.detectTypeAndOpenFile(path)
            return
        # This is not an absolute path but could be a relative path for the
        # current buffer file. Let's try it.
        fileName = self._parent.getFileName()
        if fileName != "":
            # There is a file name
            fName = os.path.dirname(fileName) + os.path.sep + path
            fName = os.path.abspath(os.path.realpath(fName))
            if os.path.exists(fName):
                GlobalData().mainWindow.detectTypeAndOpenFile(fName)
                return
        if GlobalData().project.isLoaded():
            # Try it as a relative path to the project
            prjFile = GlobalData().project.fileName
            fName = os.path.dirname(prjFile) + os.path.sep + path
            fName = os.path.abspath(os.path.realpath(fName))
            if os.path.exists(fName):
                GlobalData().mainWindow.detectTypeAndOpenFile(fName)
                return
        # The last hope - open as is
        if os.path.exists(path):
            path = os.path.abspath(os.path.realpath(path))
            GlobalData().mainWindow.detectTypeAndOpenFile(path)
            return

        logging.error("Cannot find '" + path + "' to open")

    def downloadAndShow(self):
        """Triggered when the user wants to download and see the file"""
        url = self.selectedText().strip()
        if url.startswith("www."):
            url = "http://" + url

        oldTimeout = socket.getdefaulttimeout()
        newTimeout = 5      # Otherwise the pause is too long
        socket.setdefaulttimeout(newTimeout)
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))

        try:
            response = urllib.request.urlopen(url)
            content = decodeURLContent(response.read())

            # The content has been read sucessfully
            mainWindow = GlobalData().mainWindow
            editorsManager = mainWindow.editorsManagerWidget.editorsManager
            editorsManager.newTabClicked(content, os.path.basename(url))
        except Exception as exc:
            logging.error("Error downloading '" + url + "'\n" + str(exc))

        QApplication.restoreOverrideCursor()
        socket.setdefaulttimeout(oldTimeout)

    def __onPluginMenuAdded(self, menu, count):
        """Triggered when a new menu was added"""
        self._menu.addMenu(menu)
        self.__pluginMenuSeparator.setVisible(True)

    def __onPluginMenuRemoved(self, menu, count):
        """Triggered when a menu was deleted"""
        self._menu.removeAction(menu.menuAction())
        self.__pluginMenuSeparator.setVisible(count != 0)

    def openAsFileAvailable(self):
        """True if there is something to try to open as a file"""
        importLine, line = isImportLine(self)
        if importLine:
            return False
        selectedText = self.selectedText().strip()
        if selectedText:
            return '\n' not in selectedText and \
                   '\r' not in selectedText

        currentWord = self.getCurrentWord().strip()
        return currentWord != ""

    def downloadAndShowAvailable(self):
        """True if download and show available"""
        importLine, line = isImportLine(self)
        if importLine:
            return False
        selectedText = self.selectedText().strip()
        if not selectedText:
            return False

        if '\n' in selectedText or '\r' in selectedText:
            # Not a single line selection
            return False

        return selectedText.startswith('http://') or \
               selectedText.startswith('www.')
