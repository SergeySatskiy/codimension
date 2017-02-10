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
from ui.qt import (QMenu, QActionGroup, QApplication, Qt, QCursor,
                   QDesktopServices, QUrl, QMessageBox)
from utils.pixmapcache import getIcon
from utils.globals import GlobalData
from utils.encoding import (SUPPORTED_CODECS, decodeURLContent,
                            getNormalizedEncoding,
                            detectExistingFileWriteEncoding)
from utils.diskvaluesrelay import getFileEncoding, setFileEncoding
from autocomplete.bufferutils import isImportLine


class EditorContextMenuMixin:

    """Encapsulates the context menu handling"""

    def __init__(self):
        self.encodingReloadMenu = QMenu("Set &encoding and reload")
        self.encodingReloadActGrp = QActionGroup(self)
        self.encodingWriteMenu = QMenu("Set encodin&g")
        self.encodingWriteActGrp = QActionGroup(self)

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

        self.__initReloadEncodingMenu()
        self.encodingReloadMenu.setIcon(getIcon('textencoding.png'))
        self._menu.addMenu(self.encodingReloadMenu)
        self.__initWriteEncodingMenu()
        self.encodingWriteMenu.setIcon(getIcon('textencoding.png'))
        menu = self._menu.addMenu(self.encodingWriteMenu)
        self.__menuClearEncoding = self._menu.addAction(
            getIcon('clearmenu.png'), 'Clear explicit encoding',
            self.__onClearEncoding)
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

    def __initReloadEncodingMenu(self):
        """Creates the encoding menu for reloading the existing file"""
        for encoding in sorted(SUPPORTED_CODECS):
            act = self.encodingReloadMenu.addAction(encoding)
            act.setCheckable(True)
            act.setData(encoding)
            self.encodingReloadActGrp.addAction(act)
        self.encodingReloadMenu.triggered.connect(self.__onReloadWithEncoding)

    def __initWriteEncodingMenu(self):
        """Creates the encoding menu for further read/write operations"""
        for encoding in sorted(SUPPORTED_CODECS):
            act = self.encodingWriteMenu.addAction(encoding)
            act.setCheckable(True)
            act.setData(encoding)
            self.encodingWriteActGrp.addAction(act)
        self.encodingWriteMenu.triggered.connect(self.__onReadWriteEncoding)

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

    def contextMenuEvent(self, event):
        """Called just before showing a context menu"""
        # Accepting needs to suppress the native menu
        event.accept()

        isPython = self.isPythonBuffer()
        readOnly = self.isReadOnly()
        self.__menuUndo.setEnabled(self.document().isUndoAvailable())
        self.__menuRedo.setEnabled(self.document().isRedoAvailable())
        self.__menuCut.setEnabled(not readOnly)
        self.__menuPaste.setEnabled(QApplication.clipboard().text() != ""
                                    and not readOnly)

        fileName = self._parent.getFileName()
        absFileName = os.path.isabs(fileName)
        self.__menuOpenAsFile.setEnabled(self.openAsFileAvailable())
        self.__menuDownloadAndShow.setEnabled(self.downloadAndShowAvailable())
        self.__menuOpenInBrowser.setEnabled(self.downloadAndShowAvailable())
        self.__menuHighlightInPrj.setEnabled(
            absFileName and GlobalData().project.isProjectFile(fileName))
        self.__menuHighlightInFS.setEnabled(absFileName)
        self._menuHighlightInOutline.setEnabled(isPython)
        self._menuHighlightInOutline.setEnabled(isPython)

        runEnabled = self._parent.runScriptButton.isEnabled()
        self.toolsMenu.setEnabled(runEnabled)

        if absFileName:
            self.__menuClearEncoding.setEnabled(
                getFileEncoding(fileName) is not None)
        else:
            self.__menuClearEncoding.setEnabled(
                self.newFileUserEncoding is not None)

        # Check the proper encoding in the menu
        encoding = 'undefined'
        if absFileName:
            enc = getFileEncoding(fileName)
            if enc:
                encoding = enc
        else:
            if self.newFileUserEncoding:
                encoding = self.newFileUserEncoding
        encoding = getNormalizedEncoding(encoding, False)
        if absFileName:
            for act in self.encodingReloadActGrp.actions():
                act.setChecked(encoding == getNormalizedEncoding(act.data()))
        else:
            self.encodingReloadMenu.setEnabled(False)
        for act in self.encodingWriteActGrp.actions():
            act.setChecked(encoding == getNormalizedEncoding(act.data()))

        # Show the menu
        self._menu.popup(event.globalPos())

    def __isSameEncodingAsCurrent(self, enc):
        """True if the same encoding has already been set"""
        fileName = self._parent.getFileName()
        if not os.path.isabs(fileName):
            # New unsaved yet file
            if not self.newFileUserEncoding:
                return False
            return getNormalizedEncoding(enc) == getNormalizedEncoding(
                self.newFileUserEncoding)

        # Existed before or just saved new file
        currentEnc = getFileEncoding(fileName)
        if not currentEnc:
            return False
        return getNormalizedEncoding(currentEnc) == getNormalizedEncoding(enc)

    def __onReloadWithEncoding(self, act):
        """Triggered when encoding is selected"""
        # The method is called only for the existing disk files
        encoding = act.data()
        if self.__isSameEncodingAsCurrent(encoding):
            return

        if self.document().isModified():
            res = QMessageBox.warning(
                self, 'Continue loosing changes',
                '<p>The buffer has unsaved changes. Are you sure to continue '
                'reloading the content using ' + encoding + ' encoding and '
                'loosing the changes?</p>',
                QMessageBox.StandardButtons(QMessageBox.Cancel |
                                            QMessageBox.Yes),
                QMessageBox.Cancel)
            if res == QMessageBox.Cancel:
                return

        # Do the reload
        fileName = self._parent.getFileName()
        setFileEncoding(fileName, encoding)
        self.__updateFilePosition()
        self.readFile(fileName)
        self.__restoreFilePosition()
        self.__updateMainWindowStatusBar()

    def __onReadWriteEncoding(self, act):
        """Sets explicit encoding for further read/write ops"""
        encoding = act.data()
        if self.__isSameEncodingAsCurrent(encoding):
            return

        fileName = self._parent.getFileName()
        absFileName = os.path.isabs(fileName)
        if absFileName:
            self.encoding = encoding
            setFileEncoding(fileName, encoding)
        else:
            self.newFileUserEncoding = encoding
        self.setModified(True)
        self.__updateMainWindowStatusBar()

    def __onClearEncoding(self):
        """Clears the explicitly set encoding"""
        fileName = self._parent.getFileName()
        absFileName = os.path.isabs(fileName)
        if absFileName:
            setFileEncoding(fileName, None)
            print("User encoding: " + str(getFileEncoding(fileName)))
            self.encoding = None
            self.encoding = detectExistingFileWriteEncoding(self, fileName)
            print("Saving encoding: " + str(self.encoding))
        else:
            self.newFileUserEncoding = None
        self.__updateMainWindowStatusBar()

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
        if self.selectedText:
            QApplication.clipboard().setText(self.selectedText)
            self.selectedText = ''
        else:
            line, _ = self.cursorPosition
            if self.lines[line]:
                QApplication.clipboard().setText(self.lines[line])
                self.lines[line] = ''

    def onCtrlC(self):
        """Handles copying"""
        if self.selectedText:
            QApplication.clipboard().setText(self.selectedText)
        else:
            line, _ = self.cursorPosition
            if self.lines[line]:
                QApplication.clipboard().setText(self.lines[line])

    def openAsFile(self):
        """Opens a selection or a current tag as a file"""
        path = self.selectedText.strip()
        if path == "" or '\n' in path or '\r' in path:
            return

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
        url = self.selectedText.strip()
        if url.lower().startswith("www."):
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
        importLine, _ = isImportLine(self)
        if not importLine:
            selectedText = self.selectedText.strip()
            if selectedText:
                return '\n' not in selectedText and \
                       '\r' not in selectedText
        return False

    def downloadAndShowAvailable(self):
        """True if download and show available"""
        importLine, _ = isImportLine(self)
        if not importLine:
            selectedText = self.selectedText.strip()
            if '\n' not in selectedText and '\r' not in selectedText:
                return selectedText.lower().startswith('http://') or \
                       selectedText.lower().startswith('www.')
        return False

    def openInBrowser(self):
        """Triggered when a selected URL should be opened in a browser"""
        url = self.selectedText.strip()
        if url.lower().startswith("www."):
            url = "http://" + url
        QDesktopServices.openUrl(QUrl(url))

    @staticmethod
    def __updateMainWindowStatusBar():
        mainWindow = GlobalData().mainWindow
        editorsManager = mainWindow.editorsManagerWidget.editorsManager
        editorsManager.updateStatusBar()

    @staticmethod
    def __updateFilePosition():
        mainWindow = GlobalData().mainWindow
        editorsManager = mainWindow.editorsManagerWidget.editorsManager
        editorsManager.updateFilePosition(None)

    @staticmethod
    def __restoreFilePosition():
        mainWindow = GlobalData().mainWindow
        editorsManager = mainWindow.editorsManagerWidget.editorsManager
        editorsManager.restoreFilePosition(None)
