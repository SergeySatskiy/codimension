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


import os.path
from cdmpyparser import getBriefModuleInfoFromMemory
from ui.qt import QMenu, QActionGroup, QApplication, QMessageBox
from utils.pixmapcache import getIcon
from utils.globals import GlobalData
from utils.encoding import (SUPPORTED_CODECS,
                            getNormalizedEncoding,
                            detectEncodingOnClearExplicit,
                            detectNewFileWriteEncoding)
from utils.diskvaluesrelay import getFileEncoding, setFileEncoding
from autocomplete.bufferutils import getContext
from analysis.disasm import (OPT_NO_OPTIMIZATION, OPT_OPTIMIZE_ASSERT,
                             OPT_OPTIMIZE_DOCSTRINGS)


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
        self.toolsMenu = QMenu('Python too&ls')
        self.runAct = self.toolsMenu.addAction(
            getIcon('run.png'), 'Run script', self._parent.onRunScript)
        self.runParamAct = self.toolsMenu.addAction(
            getIcon('paramsmenu.png'), 'Set parameters and run',
            self._parent.onRunScriptDlg)
        self.toolsMenu.addSeparator()
        self.profileAct = self.toolsMenu.addAction(
            getIcon('profile.png'), 'Profile script',
            self._parent.onProfileScript)
        self.profileParamAct = self.toolsMenu.addAction(
            getIcon('paramsmenu.png'), 'Set parameters and profile',
            self._parent.onProfileScriptDlg)
        self.toolsMenu.addSeparator()
        self.disasmMenu = QMenu('Disassembly')
        self.disasmMenu.setIcon(getIcon('disassembly.png'))
        self.disasmAct0 = self.disasmMenu.addAction(
            getIcon(''), 'Disassembly (no optimization)',
            self._onDisasm0)
        self.disasmAct1 = self.disasmMenu.addAction(
            getIcon(''), 'Disassembly (optimization level 1)',
            self._onDisasm1)
        self.disasmAct2 = self.disasmMenu.addAction(
            getIcon(''), 'Disassembly (optimization level 2)',
            self._onDisasm2)
        self.toolsMenu.addMenu(self.disasmMenu)
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

        self.toolsMenu.setEnabled(isPython)
        if isPython:
            runEnabled = self._parent.runScriptButton.isEnabled()
            self.runAct.setEnabled(runEnabled)
            self.runParamAct.setEnabled(runEnabled)
            self.profileAct.setEnabled(runEnabled)
            self.profileParamAct.setEnabled(runEnabled)

        if absFileName:
            self.__menuClearEncoding.setEnabled(
                getFileEncoding(fileName) is not None)
        else:
            self.__menuClearEncoding.setEnabled(
                self.explicitUserEncoding is not None)

        # Check the proper encoding in the menu
        encoding = 'undefined'
        if absFileName:
            enc = getFileEncoding(fileName)
            if enc:
                encoding = enc
        else:
            if self.explicitUserEncoding:
                encoding = self.explicitUserEncoding
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
            if not self.explicitUserEncoding:
                return False
            return getNormalizedEncoding(enc) == getNormalizedEncoding(
                self.explicitUserEncoding)

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

        # fileName = self._parent.getFileName()
        # absFileName = os.path.isabs(fileName)
        self.document().setModified(True)
        self.explicitUserEncoding = encoding
        self.__updateMainWindowStatusBar()

    def __onClearEncoding(self):
        """Clears the explicitly set encoding"""
        self.explicitUserEncoding = None
        fileName = self._parent.getFileName()
        absFileName = os.path.isabs(fileName)
        if absFileName:
            setFileEncoding(fileName, None)
            self.encoding = detectEncodingOnClearExplicit(fileName, self.text)
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

    def __onPluginMenuAdded(self, menu, count):
        """Triggered when a new menu was added"""
        del count   # unused argument
        self._menu.addMenu(menu)
        self.__pluginMenuSeparator.setVisible(True)

    def __onDisasm(self, optimization):
        """Common implementation"""
        if self.isPythonBuffer():
            if os.path.isabs(self._parent.getFileName()):
                if not self._parent.isModified():
                    GlobalData().mainWindow.showFileDisassembly(
                        self._parent.getFileName(), optimization)
                    return
            fileName = self._parent.getFileName()
            if not fileName:
                fileName = self._parent.getShortName()
            encoding = self.encoding
            if not encoding:
                encoding = detectNewFileWriteEncoding(self, fileName)
            GlobalData().mainWindow.showBufferDisassembly(
                self.text, encoding, fileName, optimization)

    def _onDisasm0(self):
        """Triggered to disassemble the buffer without optimization"""
        self.__onDisasm(OPT_NO_OPTIMIZATION)

    def _onDisasm1(self):
        """Triggered to disassemble the buffer with optimization level 1"""
        self.__onDisasm(OPT_OPTIMIZE_ASSERT)

    def _onDisasm2(self):
        """Triggered to disassemble the buffer with optimization level 2"""
        self.__onDisasm(OPT_OPTIMIZE_DOCSTRINGS)

    def __onPluginMenuRemoved(self, menu, count):
        """Triggered when a menu was deleted"""
        self._menu.removeAction(menu.menuAction())
        self.__pluginMenuSeparator.setVisible(count != 0)

    def highlightInOutline(self):
        """Triggered when highlight in outline browser is requested"""
        if self.isPythonBuffer():
            info = getBriefModuleInfoFromMemory(self.text)
            context = getContext(self, info, True, False)
            line, _ = self.cursorPosition
            GlobalData().mainWindow.highlightInOutline(context, int(line) + 1)
            self.setFocus()

    @staticmethod
    def __updateMainWindowStatusBar():
        """Updates the main window status bar"""
        mainWindow = GlobalData().mainWindow
        editorsManager = mainWindow.editorsManagerWidget.editorsManager
        editorsManager.updateStatusBar()

    @staticmethod
    def __updateFilePosition():
        """Updates the position in a file"""
        mainWindow = GlobalData().mainWindow
        editorsManager = mainWindow.editorsManagerWidget.editorsManager
        editorsManager.updateFilePosition(None)

    @staticmethod
    def __restoreFilePosition():
        """Restores the position in a file"""
        mainWindow = GlobalData().mainWindow
        editorsManager = mainWindow.editorsManagerWidget.editorsManager
        editorsManager.restoreFilePosition(None)
