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

"""Text editor tab widget"""


import os.path
import logging
from ui.qt import (Qt, QFileInfo, QSize, pyqtSignal, QToolBar, QHBoxLayout,
                   QWidget, QAction, QMenu, QToolButton, QDialog,
                   QVBoxLayout, QSplitter)
from ui.mainwindowtabwidgetbase import MainWindowTabWidgetBase
from ui.importlist import ImportListWidget
from ui.outsidechanges import OutsideChangeWidget
from ui.spacers import ToolBarExpandingSpacer, ToolBarVSpacer
from utils.pixmapcache import getIcon
from utils.globals import GlobalData
from utils.settings import Settings
from utils.misc import extendInstance
from utils.fileutils import isPythonMime
from utils.importutils import getImportsList, resolveImports
from diagram.importsdgm import (ImportsDiagramDialog, ImportDiagramOptions,
                                ImportsDiagramProgress)
from .flowuiwidget import FlowUIWidget
from .mdwidget import MDWidget
from .navbar import NavigationBar
from .texteditor import TextEditor


class TextEditorTabWidget(QWidget):

    """Plain text editor tab widget"""

    sigReloadRequest = pyqtSignal()
    reloadAllNonModifiedRequest = pyqtSignal()
    sigTabRunChanged = pyqtSignal(bool)

    def __init__(self, parent, debugger):
        QWidget.__init__(self, parent)

        extendInstance(self, MainWindowTabWidgetBase)
        MainWindowTabWidgetBase.__init__(self)

        self.__navigationBar = None
        self.__editor = TextEditor(self, debugger)
        self.__fileName = ""
        self.__shortName = ""

        self.__createLayout()

        self.__editor.redoAvailable.connect(self.__redoAvailable)
        self.__editor.undoAvailable.connect(self.__undoAvailable)
        self.__editor.modificationChanged.connect(self.modificationChanged)
        self.__editor.sigCFlowSyncRequested.connect(self.cflowSyncRequested)
        self.__editor.languageChanged.connect(self.__languageChanged)

        self.__diskModTime = None
        self.__diskSize = None
        self.__reloadDlgShown = False

        self.__debugMode = False

        self.__vcsStatus = None

    def onTextZoomChanged(self):
        """Triggered when a text zoom is changed"""
        self.__editor.onTextZoomChanged()

    def onFlowZoomChanged(self):
        """Triggered when a flow zoom is changed"""
        self.__flowUI.onFlowZoomChanged()

    def getNavigationBar(self):
        """Provides a reference to the navigation bar"""
        return self.__navigationBar

    def shouldAcceptFocus(self):
        """True if it can accept the focus"""
        return self.__outsideChangesBar.isHidden()

    def readFile(self, fileName):
        """Reads the text from a file"""
        self.__editor.readFile(fileName)
        self.setFileName(fileName)
        self.__editor.restoreBreakpoints()

        # Memorize the modification date
        path = os.path.realpath(fileName)
        self.__diskModTime = os.path.getmtime(path)
        self.__diskSize = os.path.getsize(path)

    def writeFile(self, fileName):
        """Writes the text to a file"""
        if self.__editor.writeFile(fileName):
            # Memorize the modification date
            path = os.path.realpath(fileName)
            self.__diskModTime = os.path.getmtime(path)
            self.__diskSize = os.path.getsize(path)
            self.setFileName(fileName)
            self.__editor.restoreBreakpoints()
            return True
        return False

    def __createLayout(self):
        """Creates the toolbar and layout"""
        # The toolbar
        self.toolbar = QToolBar(self)
        self.toolbar.setOrientation(Qt.Vertical)
        self.toolbar.setMovable(False)
        self.toolbar.setAllowedAreas(Qt.RightToolBarArea)
        self.toolbar.setIconSize(QSize(16, 16))
        self.toolbar.setFixedWidth(30)
        self.toolbar.setContentsMargins(0, 0, 0, 0)

        # Buttons
        printButton = QAction(getIcon('printer.png'), 'Print (Ctrl+P)',
                              self.toolbar)
        printButton.triggered.connect(self.__onPrint)
        printButton.setObjectName('printButton')

        printPreviewButton = QAction(getIcon('printpreview.png'),
                                     'Print preview', self.toolbar)
        printPreviewButton.triggered.connect(self.__onPrintPreview)
        printPreviewButton.setEnabled(False)
        printPreviewButton.setVisible(False)
        printPreviewButton.setObjectName('printPreviewButton')

        printSpacer = ToolBarVSpacer(self.toolbar, 8)
        printSpacer.setObjectName('printSpacer')

        # Imports diagram and its menu
        importsMenu = QMenu(self)
        self.importsDlgAct = importsMenu.addAction(
            getIcon('detailsdlg.png'), 'Fine tuned imports diagram')
        self.importsDlgAct.triggered.connect(self.onImportDgmTuned)
        self.importsDiagramButton = QToolButton(self.toolbar)
        self.importsDiagramButton.setIcon(getIcon('importsdiagram.png'))
        self.importsDiagramButton.setToolTip('Generate imports diagram')
        self.importsDiagramButton.setPopupMode(QToolButton.DelayedPopup)
        self.importsDiagramButton.setMenu(importsMenu)
        self.importsDiagramButton.setFocusPolicy(Qt.NoFocus)
        self.importsDiagramButton.clicked.connect(self.onImportDgm)
        self.importsDiagramButton.setEnabled(False)
        self.importsDiagramButton.setObjectName('importsDiagramButton')

        # Run script and its menu
        runScriptMenu = QMenu(self)
        self.runScriptDlgAct = runScriptMenu.addAction(
            getIcon('detailsdlg.png'), 'Set run/debug parameters')
        self.runScriptDlgAct.triggered.connect(self.onRunScriptDlg)
        self.runScriptButton = QToolButton(self.toolbar)
        self.runScriptButton.setIcon(getIcon('run.png'))
        self.runScriptButton.setToolTip('Run script')
        self.runScriptButton.setPopupMode(QToolButton.DelayedPopup)
        self.runScriptButton.setMenu(runScriptMenu)
        self.runScriptButton.setFocusPolicy(Qt.NoFocus)
        self.runScriptButton.clicked.connect(self.onRunScript)
        self.runScriptButton.setEnabled(False)
        self.runScriptButton.setObjectName('runScriptButton')

        # Profile script and its menu
        profileScriptMenu = QMenu(self)
        self.profileScriptDlgAct = profileScriptMenu.addAction(
            getIcon('detailsdlg.png'), 'Set profile parameters')
        self.profileScriptDlgAct.triggered.connect(self.onProfileScriptDlg)
        self.profileScriptButton = QToolButton(self.toolbar)
        self.profileScriptButton.setIcon(getIcon('profile.png'))
        self.profileScriptButton.setToolTip('Profile script')
        self.profileScriptButton.setPopupMode(QToolButton.DelayedPopup)
        self.profileScriptButton.setMenu(profileScriptMenu)
        self.profileScriptButton.setFocusPolicy(Qt.NoFocus)
        self.profileScriptButton.clicked.connect(self.onProfileScript)
        self.profileScriptButton.setEnabled(False)
        self.profileScriptButton.setObjectName('profileScriptButton')

        # Debug script and its menu
        debugScriptMenu = QMenu(self)
        self.debugScriptDlgAct = debugScriptMenu.addAction(
            getIcon('detailsdlg.png'), 'Set run/debug parameters')
        self.debugScriptDlgAct.triggered.connect(self.onDebugScriptDlg)
        self.debugScriptButton = QToolButton(self.toolbar)
        self.debugScriptButton.setIcon(getIcon('debugger.png'))
        self.debugScriptButton.setToolTip('Debug script')
        self.debugScriptButton.setPopupMode(QToolButton.DelayedPopup)
        self.debugScriptButton.setMenu(debugScriptMenu)
        self.debugScriptButton.setFocusPolicy(Qt.NoFocus)
        self.debugScriptButton.clicked.connect(self.onDebugScript)
        self.debugScriptButton.setEnabled(False)
        self.debugScriptButton.setObjectName('debugScriptButton')

        # Disassembling
        disasmScriptMenu = QMenu(self)
        disasmScriptMenu.addAction(
            getIcon(''), 'Disassembly (no optimization)',
            self.__editor._onDisasm0)
        disasmScriptMenu.addAction(
            getIcon(''), 'Disassembly (optimization level 1)',
            self.__editor._onDisasm1)
        disasmScriptMenu.addAction(
            getIcon(''), 'Disassembly (optimization level 2)',
            self.__editor._onDisasm2)
        self.disasmScriptButton = QToolButton(self.toolbar)
        self.disasmScriptButton.setIcon(getIcon('disassembly.png'))
        self.disasmScriptButton.setToolTip('Disassembly script')
        self.disasmScriptButton.setPopupMode(QToolButton.DelayedPopup)
        self.disasmScriptButton.setMenu(disasmScriptMenu)
        self.disasmScriptButton.setFocusPolicy(Qt.NoFocus)
        self.disasmScriptButton.clicked.connect(self.__editor._onDisasm0)
        self.disasmScriptButton.setEnabled(False)
        self.disasmScriptButton.setObjectName('disasmScriptButton')

        # Dead code
        self.deadCodeScriptButton = QAction(getIcon('deadcode.png'),
                                            'Find dead code', self.toolbar)
        self.deadCodeScriptButton.triggered.connect(self.__onDeadCode)
        self.deadCodeScriptButton.setEnabled(False)
        self.deadCodeScriptButton.setObjectName('deadCodeScriptButton')

        undoSpacer = ToolBarVSpacer(self.toolbar, 8)
        undoSpacer.setObjectName('undoSpacer')

        self.__undoButton = QAction(getIcon('undo.png'), 'Undo (Ctrl+Z)',
                                    self.toolbar)
        self.__undoButton.setShortcut('Ctrl+Z')
        self.__undoButton.triggered.connect(self.__editor.onUndo)
        self.__undoButton.setEnabled(False)
        self.__undoButton.setObjectName('undoButton')

        self.__redoButton = QAction(getIcon('redo.png'), 'Redo (Ctrl+Y)',
                                    self.toolbar)
        self.__redoButton.setShortcut('Ctrl+Y')
        self.__redoButton.triggered.connect(self.__editor.onRedo)
        self.__redoButton.setEnabled(False)
        self.__redoButton.setObjectName('redoButton')

        spacer = ToolBarExpandingSpacer(self.toolbar)
        spacer.setObjectName('spacer')

        self.removeTrailingSpacesButton = QAction(
            getIcon('trailingws.png'), 'Remove trailing spaces', self.toolbar)
        self.removeTrailingSpacesButton.triggered.connect(
            self.onRemoveTrailingWS)
        self.removeTrailingSpacesButton.setObjectName(
            'removeTrailingSpacesButton')
        self.expandTabsButton = QAction(
            getIcon('expandtabs.png'), 'Expand tabs (4 spaces)', self.toolbar)
        self.expandTabsButton.triggered.connect(self.onExpandTabs)
        self.expandTabsButton.setObjectName('expandTabsButton')

        # Add items to the toolbar
        self.toolbar.addAction(printPreviewButton)
        self.toolbar.addAction(printButton)
        self.toolbar.addWidget(printSpacer)
        self.toolbar.addWidget(self.importsDiagramButton)
        self.toolbar.addWidget(self.runScriptButton)
        self.toolbar.addWidget(self.profileScriptButton)
        self.toolbar.addWidget(self.debugScriptButton)
        self.toolbar.addWidget(self.disasmScriptButton)
        self.toolbar.addAction(self.deadCodeScriptButton)
        self.toolbar.addWidget(undoSpacer)
        self.toolbar.addAction(self.__undoButton)
        self.toolbar.addAction(self.__redoButton)
        self.toolbar.addWidget(spacer)
        self.toolbar.addAction(self.removeTrailingSpacesButton)
        self.toolbar.addAction(self.expandTabsButton)

        self.importsBar = ImportListWidget(self.__editor)
        self.importsBar.hide()

        self.__outsideChangesBar = OutsideChangeWidget(self.__editor)
        self.__outsideChangesBar.sigReloadRequest.connect(self.__onReload)
        self.__outsideChangesBar.reloadAllNonModifiedRequest.connect(
            self.reloadAllNonModified)
        self.__outsideChangesBar.hide()

        hLayout = QHBoxLayout()
        hLayout.setContentsMargins(0, 0, 0, 0)
        hLayout.setSpacing(0)

        vLayout = QVBoxLayout()
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.setSpacing(0)

        self.__navigationBar = NavigationBar(self.__editor, self)
        vLayout.addWidget(self.__navigationBar)
        vLayout.addWidget(self.__editor)

        hLayout.addLayout(vLayout)
        hLayout.addWidget(self.toolbar)
        widget = QWidget(self)
        widget.setLayout(hLayout)

        self.__splitter = QSplitter(Qt.Horizontal, self)

        self.__flowUI = FlowUIWidget(self.__editor, self)
        self.__mdView = MDWidget(self.__editor, self)

        self.__renderLayout = QVBoxLayout()
        self.__renderLayout.setContentsMargins(0, 0, 0, 0)
        self.__renderLayout.setSpacing(0)
        self.__renderLayout.addWidget(self.__flowUI)
        self.__renderLayout.addWidget(self.__mdView)
        self.__renderWidget = QWidget(self)
        self.__renderWidget.setLayout(self.__renderLayout)

        self.__splitter.addWidget(widget)
        self.__splitter.addWidget(self.__renderWidget)

        containerLayout = QHBoxLayout()
        containerLayout.setContentsMargins(0, 0, 0, 0)
        containerLayout.setSpacing(0)
        containerLayout.addWidget(self.__splitter)
        self.setLayout(containerLayout)

        self.__renderWidget.setVisible(False)

        self.__splitter.setSizes(Settings()['flowSplitterSizes'])
        self.__splitter.splitterMoved.connect(self.flowSplitterMoved)
        Settings().sigFlowSplitterChanged.connect(self.otherFlowSplitterMoved)

    def flowSplitterMoved(self, pos, index):
        """Splitter has been moved"""
        del pos     # unused argument
        del index   # unused argument
        Settings()['flowSplitterSizes'] = list(self.__splitter.sizes())

    def otherFlowSplitterMoved(self):
        """Other window has changed the splitter position"""
        self.__splitter.setSizes(Settings()['flowSplitterSizes'])

    def updateStatus(self):
        """Updates the toolbar buttons status"""
        self.__updateRunDebugButtons()
        isPythonFile = isPythonMime(self.__editor.mime)
        self.importsDiagramButton.setEnabled(
            isPythonFile and GlobalData().graphvizAvailable)
        self.__editor.diagramsMenu.setEnabled(
            self.importsDiagramButton.isEnabled())
        self.__editor.toolsMenu.setEnabled(self.runScriptButton.isEnabled())

    def onNavigationBar(self):
        """Triggered when navigation bar focus is requested"""
        if self.__navigationBar.isVisible():
            self.__navigationBar.setFocusToLastCombo()
        return True

    def __onPrint(self):
        """Triggered when the print button is pressed"""
        self.__editor._onShortcutPrint()

    def __onPrintPreview(self):
        """Triggered when the print preview button is pressed"""
        pass

    def __onDeadCode(self):
        """Triggered when vulture analysis is requested"""
        GlobalData().mainWindow.tabDeadCodeClicked()

    def __redoAvailable(self, available):
        """Reports redo ops available"""
        self.__redoButton.setEnabled(available)

    def __undoAvailable(self, available):
        """Reports undo ops available"""
        self.__undoButton.setEnabled(available)

    def __languageChanged(self, _=None):
        """Language changed"""
        isPython = self.__editor.isPythonBuffer()
        isMarkdown = self.__editor.isMarkdownBuffer()
        self.disasmScriptButton.setEnabled(isPython)
        self.__renderWidget.setVisible(not Settings()['floatingRenderer'] and
                                       (isPython or isMarkdown))

    # Arguments: modified
    def modificationChanged(self, _=None):
        """Triggered when the content is changed"""
        self.__updateRunDebugButtons()

    def __updateRunDebugButtons(self):
        """Enables/disables the run and debug buttons as required"""
        enable = isPythonMime(self.__editor.mime) and \
                 not self.isModified() and \
                 not self.__debugMode and \
                 os.path.isabs(self.__fileName)

        if enable != self.runScriptButton.isEnabled():
            self.runScriptButton.setEnabled(enable)
            self.profileScriptButton.setEnabled(enable)
            self.debugScriptButton.setEnabled(enable)
            self.deadCodeScriptButton.setEnabled(enable)
            self.sigTabRunChanged.emit(enable)

    def isTabRunEnabled(self):
        """Tells the status of run-like buttons"""
        return self.runScriptButton.isEnabled()

    def replaceAll(self, newText):
        """Replaces the current buffer content with a new text"""
        # Unfortunately, the setText() clears the undo history so it cannot be
        # used. The selectAll() and replacing selected text do not suite
        # because after undo the cursor does not jump to the previous position.
        # So, there is an ugly select -> replace manipulation below...
        with self.__editor:
            origLine, origPos = self.__editor.cursorPosition
            self.__editor.setSelection(0, 0, origLine, origPos)
            self.__editor.removeSelectedText()
            self.__editor.insert(newText)
            self.__editor.setCurrentPosition(len(newText))
            line, pos = self.__editor.cursorPosition
            lastLine = self.__editor.lines()
            self.__editor.setSelection(line, pos,
                                       lastLine - 1,
                                       len(self.__editor.text(lastLine - 1)))
            self.__editor.removeSelectedText()
            self.__editor.cursorPosition = origLine, origPos

            # These two for the proper cursor positioning after redo
            self.__editor.insert("s")
            self.__editor.cursorPosition = origLine, origPos + 1
            self.__editor.deleteBack()
            self.__editor.cursorPosition = origLine, origPos

    def onRemoveTrailingWS(self):
        """Triggers when the trailing spaces should be wiped out"""
        self.__editor.removeTrailingWhitespaces()

    def onExpandTabs(self):
        """Expands tabs if there are any"""
        self.__editor.expandTabs(4)

    def setFocus(self):
        """Overridden setFocus"""
        if self.__outsideChangesBar.isHidden():
            self.__editor.setFocus()
        else:
            self.__outsideChangesBar.setFocus()

    def onImportDgmTuned(self):
        """Runs the settings dialog first"""
        if self.isModified():
            what = ImportsDiagramDialog.SingleBuffer
            if not os.path.isabs(self.getFileName()):
                logging.warning("Imports diagram can only be generated for "
                                "a file. Save the editor buffer "
                                "and try again.")
                return
        else:
            what = ImportsDiagramDialog.SingleFile
        dlg = ImportsDiagramDialog(what, self.getFileName(), self)
        if dlg.exec_() == QDialog.Accepted:
            # Should proceed with the diagram generation
            self.__generateImportDiagram(what, dlg.options)

    # Arguments: action
    def onImportDgm(self, _=None):
        """Runs the generation process with default options"""
        if self.isModified():
            what = ImportsDiagramDialog.SingleBuffer
            if not os.path.isabs(self.getFileName()):
                logging.warning("Imports diagram can only be generated for "
                                "a file. Save the editor buffer "
                                "and try again.")
                return
        else:
            what = ImportsDiagramDialog.SingleFile
        self.__generateImportDiagram(what, ImportDiagramOptions())

    def __generateImportDiagram(self, what, options):
        """Show the generation progress and display the diagram"""
        if self.isModified():
            progressDlg = ImportsDiagramProgress(what, options,
                                                 self.getFileName(),
                                                 self.__editor.text)
            tooltip = "Generated for modified buffer (" + \
                      self.getFileName() + ")"
        else:
            progressDlg = ImportsDiagramProgress(what, options,
                                                 self.getFileName())
            tooltip = "Generated for file " + self.getFileName()
        if progressDlg.exec_() == QDialog.Accepted:
            GlobalData().mainWindow.openDiagram(progressDlg.scene,
                                                tooltip)

    def onOpenImport(self):
        """Triggered when Ctrl+I is received"""
        if isPythonMime(self.__editor.mime):
            # Take all the file imports and resolve them
            fileImports = getImportsList(self.__editor.text)
            if not fileImports:
                GlobalData().mainWindow.showStatusBarMessage(
                    "There are no imports")
            else:
                self.__onImportList(self.__fileName, fileImports)

    def __onImportList(self, fileName, imports):
        """Works with a list of imports"""
        # It has already been checked that the file is a Python one
        resolvedList, errors = resolveImports(fileName, imports)
        del errors  # errors are OK here
        if resolvedList:
            # Display the import selection widget
            self.importsBar.showResolvedImports(resolvedList)
        else:
            GlobalData().mainWindow.showStatusBarMessage(
                "Could not resolve any imports")

    def resizeEvent(self, event):
        """Resizes the import selection dialogue if necessary"""
        self.__editor.hideCompleter()
        QWidget.resizeEvent(self, event)
        self.resizeBars()

    def resizeBars(self):
        """Resize the bars if they are shown"""
        if not self.importsBar.isHidden():
            self.importsBar.resize()
        if not self.__outsideChangesBar.isHidden():
            self.__outsideChangesBar.resize()
        self.__editor.resizeCalltip()

    def showOutsideChangesBar(self, allEnabled):
        """Shows the bar for the editor for the user to choose the action"""
        self.setReloadDialogShown(True)
        self.__outsideChangesBar.showChoice(self.isModified(),
                                            allEnabled)

    def __onReload(self):
        """Triggered when a request to reload the file is received"""
        self.sigReloadRequest.emit()

    def reload(self):
        """Called (from the editors manager) to reload the file"""
        # Re-read the file with updating the file timestamp
        self.readFile(self.__fileName)

        # Hide the bars, just in case both of them
        if not self.importsBar.isHidden():
            self.importsBar.hide()
        if not self.__outsideChangesBar.isHidden():
            self.__outsideChangesBar.hide()

        # Set the shown flag
        self.setReloadDialogShown(False)

    def reloadAllNonModified(self):
        """Request to reload all the non-modified files"""
        self.reloadAllNonModifiedRequest.emit()

    @staticmethod
    def onRunScript(action=None):
        """Runs the script"""
        del action  # unused argument
        GlobalData().mainWindow.onRunTab()

    @staticmethod
    def onRunScriptDlg():
        """Shows the run parameters dialogue"""
        GlobalData().mainWindow.onRunTabDlg()

    @staticmethod
    def onProfileScript(action=None):
        """Profiles the script"""
        del action  # unused argument
        GlobalData().mainWindow.onProfileTab()

    @staticmethod
    def onProfileScriptDlg():
        """Shows the profile parameters dialogue"""
        GlobalData().mainWindow.onProfileTabDlg()

    @staticmethod
    def onDebugScript(action=None):
        """Starts debugging"""
        del action  # unused argument
        GlobalData().mainWindow.onDebugTab()

    @staticmethod
    def onDebugScriptDlg():
        """Shows the debug parameters dialogue"""
        GlobalData().mainWindow.onDebugTabDlg()

    def getCFEditor(self):
        """Provides a reference to the control flow widget"""
        return self.__flowUI

    def cflowSyncRequested(self, absPos, line, pos):
        """Highlight the item closest to the absPos"""
        self.__flowUI.highlightAtAbsPos(absPos, line, pos)

    def passFocusToFlow(self):
        """Sets the focus to the graphics part"""
        if isPythonMime(self.__editor.mime):
            self.__flowUI.setFocus()
            return True
        return False

    def getMDView(self):
        """Provides a reference to the MD rendered view"""
        return self.__mdView

    def terminate(self):
        """Called just before the tab is closed"""
        self.__splitter.splitterMoved.disconnect(self.flowSplitterMoved)
        Settings().sigFlowSplitterChanged.disconnect(
            self.otherFlowSplitterMoved)
        self.__cleanupLayout()

        self.__navigationBar.terminate()
        self.__navigationBar.deleteLater()

        self.__mdView.terminate()
        self.__mdView.deleteLater()

        self.__flowUI.terminate()
        self.__flowUI.deleteLater()

        self.__editor.terminate()
        self.__editor.deleteLater()

    def __cleanupLayout(self):
        """Disconnects QT widget signals and destroys the UI items"""
        self.__editor.redoAvailable.disconnect(self.__redoAvailable)
        self.__editor.undoAvailable.disconnect(self.__undoAvailable)
        self.__editor.modificationChanged.disconnect(self.modificationChanged)
        self.__editor.sigCFlowSyncRequested.disconnect(self.cflowSyncRequested)
        self.__editor.languageChanged.disconnect(self.__languageChanged)

        printButton = self.toolbar.findChild(QAction, 'printButton')
        printButton.triggered.disconnect(self.__onPrint)
        printButton.deleteLater()

        printPreviewButton = self.toolbar.findChild(QAction, 'printPreviewButton')
        printPreviewButton.triggered.connect(self.__onPrintPreview)
        printPreviewButton.deleteLater()

        self.importsDlgAct.triggered.disconnect(self.onImportDgmTuned)
        self.importsDlgAct.deleteLater()
        self.importsDiagramButton.menu().deleteLater()
        self.importsDiagramButton.clicked.disconnect(self.onImportDgm)
        self.importsDiagramButton.deleteLater()

        self.runScriptDlgAct.triggered.disconnect(self.onRunScriptDlg)
        self.runScriptDlgAct.deleteLater()
        self.runScriptButton.menu().deleteLater()
        self.runScriptButton.clicked.disconnect(self.onRunScript)
        self.runScriptButton.deleteLater()

        self.profileScriptDlgAct.triggered.disconnect(self.onProfileScriptDlg)
        self.profileScriptDlgAct.deleteLater()
        self.profileScriptButton.menu().deleteLater()
        self.profileScriptButton.clicked.disconnect(self.onProfileScript)
        self.profileScriptButton.deleteLater()

        self.debugScriptDlgAct.triggered.disconnect(self.onDebugScriptDlg)
        self.debugScriptDlgAct.deleteLater()
        self.debugScriptButton.menu().deleteLater()
        self.debugScriptButton.clicked.disconnect(self.onDebugScript)
        self.debugScriptButton.deleteLater()

        self.disasmScriptButton.clicked.disconnect(self.__editor._onDisasm0)
        self.disasmScriptButton.menu().deleteLater()
        self.disasmScriptButton.deleteLater()

        self.deadCodeScriptButton.triggered.disconnect(self.__onDeadCode)
        self.deadCodeScriptButton.deleteLater()

        self.__undoButton.triggered.disconnect(self.__editor.onUndo)
        self.__undoButton.deleteLater()

        self.__redoButton.triggered.disconnect(self.__editor.onRedo)
        self.__redoButton.deleteLater()

        self.removeTrailingSpacesButton.triggered.disconnect(
            self.onRemoveTrailingWS)
        self.removeTrailingSpacesButton.deleteLater()

        self.expandTabsButton.triggered.disconnect(self.onExpandTabs)
        self.expandTabsButton.deleteLater()

        self.__renderWidget.deleteLater()

        self.importsBar.deleteLater()
        self.toolbar.deleteLater()


    # Mandatory interface part is below

    def getEditor(self):
        """Provides the editor widget"""
        return self.__editor

    def isModified(self):
        """Tells if the file is modified"""
        return self.__editor.document().isModified()

    def getRWMode(self):
        """Tells if the file is read only"""
        if not os.path.exists(self.__fileName):
            return None
        return 'RW' if QFileInfo(self.__fileName).isWritable() else 'RO'

    def getMime(self):
        """Provides the buffer mime"""
        return self.__editor.mime

    @staticmethod
    def getType():
        """Tells the widget type"""
        return MainWindowTabWidgetBase.PlainTextEditor

    def getLanguage(self):
        """Tells the content language"""
        editorLanguage = self.__editor.language()
        if editorLanguage:
            return editorLanguage
        return self.__editor.mime if self.__editor.mime else 'n/a'

    def getFileName(self):
        """Tells what file name of the widget content"""
        return self.__fileName

    def setFileName(self, name):
        """Sets the file name"""
        self.__fileName = name
        self.__shortName = os.path.basename(name)

    def getEol(self):
        """Tells the EOL style"""
        return self.__editor.getEolIndicator()

    def getLine(self):
        """Tells the cursor line"""
        line, _ = self.__editor.cursorPosition
        return line

    def getPos(self):
        """Tells the cursor column"""
        _, pos = self.__editor.cursorPosition
        return pos

    def getEncoding(self):
        """Tells the content encoding"""
        if self.__editor.explicitUserEncoding:
            return self.__editor.explicitUserEncoding
        return self.__editor.encoding

    def getShortName(self):
        """Tells the display name"""
        return self.__shortName

    def setShortName(self, name):
        """Sets the display name"""
        self.__shortName = name

    def isDiskFileModified(self):
        """Return True if the loaded file is modified"""
        if not os.path.isabs(self.__fileName):
            return False
        if not os.path.exists(self.__fileName):
            return True
        path = os.path.realpath(self.__fileName)
        return self.__diskModTime != os.path.getmtime(path) or \
               self.__diskSize != os.path.getsize(path)

    def doesFileExist(self):
        """Returns True if the loaded file still exists"""
        return os.path.exists(self.__fileName)

    def setReloadDialogShown(self, value=True):
        """Memorizes if the reloading dialogue has already been displayed"""
        self.__reloadDlgShown = value

    def getReloadDialogShown(self):
        """Tells if the reload dialog has already been shown"""
        return self.__reloadDlgShown and \
            not self.__outsideChangesBar.isVisible()

    def updateModificationTime(self, fileName):
        """Updates the modification time"""
        path = os.path.realpath(fileName)
        self.__diskModTime = os.path.getmtime(path)
        self.__diskSize = os.path.getsize(path)

    def setDebugMode(self, debugOn, disableEditing):
        """Called to switch debug/development"""
        self.__debugMode = debugOn
        self.__editor.setDebugMode(debugOn, disableEditing)

        if debugOn:
            if disableEditing:
                # Undo/redo
                self.__undoButton.setEnabled(False)
                self.__redoButton.setEnabled(False)

                # Spaces/tabs/line
                self.removeTrailingSpacesButton.setEnabled(False)
                self.expandTabsButton.setEnabled(False)
        else:
            # Undo/redo
            self.__undoButton.setEnabled(
                self.__editor.document().isUndoAvailable())
            self.__redoButton.setEnabled(
                self.__editor.document().isRedoAvailable())

            # Spaces/tabs
            self.removeTrailingSpacesButton.setEnabled(True)
            self.expandTabsButton.setEnabled(True)

        # Run/debug buttons
        self.__updateRunDebugButtons()

    def isLineBreakable(self, line=None, enforceRecalc=False,
                        enforceSure=False):
        """True if a breakpoint could be placed on the current line"""
        return self.__editor.isLineBreakable()

    def getVCSStatus(self):
        """Provides the VCS status"""
        return self.__vcsStatus

    def setVCSStatus(self, newStatus):
        """Sets the new VCS status"""
        self.__vcsStatus = newStatus

    # Floating renderer support
    def popRenderingWidgets(self):
        """Pops the rendering widgets"""
        self.__renderLayout.removeWidget(self.__flowUI)
        self.__renderLayout.removeWidget(self.__mdView)
        self.__renderWidget.setVisible(False)
        return [self.__flowUI, self.__mdView]

    def pushRenderingWidgets(self, widgets):
        """Returns back the rendering widgets"""
        for widget in widgets:
            self.__renderLayout.addWidget(widget)
        self.__languageChanged()    # Sets the widget visibility
