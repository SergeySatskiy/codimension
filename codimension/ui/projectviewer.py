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

"""project viewer implementation"""


import os
import os.path
import logging
import shutil
from utils.pixmapcache import getIcon
from utils.globals import GlobalData
from utils.settings import Settings
from utils.project import CodimensionProject
from utils.fileutils import isPythonMime, isPythonFile, isPythonCompiledFile
from utils.colorfont import getLabelStyle, HEADER_HEIGHT, HEADER_BUTTON
from diagram.importsdgm import (ImportsDiagramDialog, ImportDiagramOptions,
                                ImportsDiagramProgress)
from analysis.disasm import (OPT_NO_OPTIMIZATION, OPT_OPTIMIZE_ASSERT,
                             OPT_OPTIMIZE_DOCSTRINGS)
from .qt import (QSize, Qt, QWidget, QVBoxLayout, QSplitter,
                 QToolBar, QAction, QToolButton, QHBoxLayout, QLabel,
                 QSpacerItem, QSizePolicy, QDialog, QMenu, QFrame,
                 QMessageBox, QCursor, pyqtSignal)
from .projectproperties import ProjectPropertiesDialog
from .filesystembrowser import FileSystemBrowser
from .projectbrowser import ProjectBrowser
from .viewitems import (NoItemType, DirectoryItemType, SysPathItemType,
                        FileItemType, GlobalsItemType, ImportsItemType,
                        FunctionsItemType, ClassesItemType,
                        StaticAttributesItemType, InstanceAttributesItemType,
                        CodingItemType, ImportItemType, FunctionItemType,
                        ClassItemType, DecoratorItemType, AttributeItemType,
                        GlobalItemType, ImportWhatItemType)
from .newnesteddir import NewProjectDirDialog


class ProjectViewer(QWidget):

    """Project viewer widget"""

    sigFileUpdated = pyqtSignal(str, str)

    def __init__(self, parent):
        QWidget.__init__(self, parent)

        self.__mainWindow = parent

        self.__fsContextItem = None
        self.__prjContextItem = None

        self.upper = self.__createProjectPartLayout()
        self.lower = self.__createFilesystemPartLayout()
        self.__createFilesystemPopupMenu()
        self.__createProjectPopupMenu()

        layout = QVBoxLayout()
        layout.setContentsMargins(1, 1, 1, 1)
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.upper)
        splitter.addWidget(self.lower)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)

        layout.addWidget(splitter)
        self.setLayout(layout)

        self.__updateFSToolbarButtons()
        self.__updatePrjToolbarButtons()

        GlobalData().project.sigProjectChanged.connect(
            self.__onProjectChanged)
        GlobalData().project.sigRestoreProjectExpandedDirs.connect(
            self.__onRestorePrjExpandedDirs)

        # Support switching to debug and back
        self.__mainWindow.debugModeChanged.connect(
            self.projectTreeView.onDebugMode)
        self.__mainWindow.debugModeChanged.connect(
            self.filesystemView.onDebugMode)
        self.__mainWindow.debugModeChanged.connect(self.onDebugMode)

        # Plugin context menu support
        self.__pluginFileMenus = {}
        self.__pluginDirMenus = {}
        GlobalData().pluginManager.sigPluginActivated.connect(
            self.__onPluginActivated)
        GlobalData().pluginManager.sigPluginDeactivated.connect(
            self.__onPluginDeactivated)

        # Keep the min and max height of the FS part initialized
        self.__minH = self.lower.minimumHeight()
        self.__maxH = self.lower.maximumHeight()

        # At the beginning the FS viewer is shown, so hide it if needed
        if not Settings()['showFSViewer']:
            self.__onShowHide(True)

    def setTooltips(self, switchOn):
        """Triggers the tooltips mode"""
        self.projectTreeView.model().sourceModel().setTooltips(switchOn)
        self.filesystemView.model().sourceModel().setTooltips(switchOn)

    def __createProjectPartLayout(self):
        """Creates the upper part of the project viewer"""
        self.projectTreeView = ProjectBrowser(self.__mainWindow)

        # Header part: label + i-button
        headerFrame = QFrame()
        headerFrame.setObjectName('prjheader')
        headerFrame.setStyleSheet('QFrame#prjheader {' +
                                  getLabelStyle(self) + '}')
        headerFrame.setFixedHeight(HEADER_HEIGHT)

        self.projectLabel = QLabel()
        self.projectLabel.setText("Project: none")

        expandingSpacer = QSpacerItem(10, 10, QSizePolicy.Expanding)
        fixedSpacer = QSpacerItem(3, 3)

        self.propertiesButton = QToolButton()
        self.propertiesButton.setAutoRaise(True)
        self.propertiesButton.setIcon(getIcon('smalli.png'))
        self.propertiesButton.setFixedSize(HEADER_BUTTON, HEADER_BUTTON)
        self.propertiesButton.setToolTip("Project properties")
        self.propertiesButton.setEnabled(False)
        self.propertiesButton.setFocusPolicy(Qt.NoFocus)
        self.propertiesButton.clicked.connect(self.projectProperties)

        self.unloadButton = QToolButton()
        self.unloadButton.setAutoRaise(True)
        self.unloadButton.setIcon(getIcon('unloadproject.png'))
        self.unloadButton.setFixedSize(HEADER_BUTTON, HEADER_BUTTON)
        self.unloadButton.setToolTip("Unload project")
        self.unloadButton.setEnabled(False)
        self.unloadButton.setFocusPolicy(Qt.NoFocus)
        self.unloadButton.clicked.connect(self.unloadProject)

        headerLayout = QHBoxLayout()
        headerLayout.setContentsMargins(0, 0, 0, 0)
        headerLayout.addWidget(self.unloadButton)
        headerLayout.addSpacerItem(fixedSpacer)
        headerLayout.addWidget(self.projectLabel)
        headerLayout.addSpacerItem(expandingSpacer)
        headerLayout.addWidget(self.propertiesButton)
        headerFrame.setLayout(headerLayout)

        # Toolbar part - buttons
        self.prjFindWhereUsedButton = QAction(
            getIcon('findusage.png'),
            'Find where the highlighted item is used', self)
        self.prjFindWhereUsedButton.triggered.connect(self.__findWhereUsed)
        self.prjFindInDirButton = QAction(
            getIcon('findindir.png'), 'Find in highlighted directory', self)
        self.prjFindInDirButton.triggered.connect(
            self.projectTreeView.findInDirectory)
        self.prjShowParsingErrorsButton = QAction(
            getIcon('showparsingerrors.png'), 'Show lexer/parser errors', self)
        self.prjShowParsingErrorsButton.triggered.connect(
            self.showPrjParserError)
        self.prjNewDirButton = QAction(
            getIcon('newdir.png'), 'Create sub directory', self)
        self.prjNewDirButton.triggered.connect(self.__createDir)
        self.prjCopyToClipboardButton = QAction(
            getIcon('copymenu.png'), 'Copy path to clipboard', self)
        self.prjCopyToClipboardButton.triggered.connect(
            self.projectTreeView.copyToClipboard)

        self.upperToolbar = QToolBar()
        self.upperToolbar.setMovable(False)
        self.upperToolbar.setAllowedAreas(Qt.TopToolBarArea)
        self.upperToolbar.setIconSize(QSize(16, 16))
        self.upperToolbar.setFixedHeight(28)
        self.upperToolbar.setContentsMargins(0, 0, 0, 0)
        self.upperToolbar.addAction(self.prjFindWhereUsedButton)
        self.upperToolbar.addAction(self.prjFindInDirButton)
        self.upperToolbar.addAction(self.prjShowParsingErrorsButton)
        self.upperToolbar.addAction(self.prjNewDirButton)
        self.upperToolbar.addAction(self.prjCopyToClipboardButton)

        self.projectTreeView.sigFirstSelectedItem.connect(
            self.__prjSelectionChanged)

        self.projectTreeView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.projectTreeView.customContextMenuRequested.connect(
            self.__prjContextMenuRequested)
        pLayout = QVBoxLayout()
        pLayout.setContentsMargins(0, 0, 0, 0)
        pLayout.setSpacing(0)
        pLayout.addWidget(headerFrame)
        pLayout.addWidget(self.upperToolbar)
        pLayout.addWidget(self.projectTreeView)

        upperContainer = QWidget()
        upperContainer.setContentsMargins(0, 0, 0, 0)
        upperContainer.setLayout(pLayout)
        return upperContainer

    def getProjectToolbar(self):
        """Provides a reference to the project toolbar"""
        return self.upperToolbar

    def __createProjectPopupMenu(self):
        """Generates the various popup menus for the project browser"""
        # popup menu for python files content
        self.prjPythonMenu = QMenu(self)
        self.prjUsageAct = self.prjPythonMenu.addAction(
            getIcon('findusage.png'), 'Find occurences', self.__findWhereUsed)
        self.prjPythonMenu.addSeparator()
        self.prjCopyAct = self.prjPythonMenu.addAction(
            getIcon('copymenu.png'),
            'Copy path to clipboard', self.projectTreeView.copyToClipboard)

        # popup menu for directories
        self.prjDirMenu = QMenu(self)
        self.prjDirMenu.aboutToShow.connect(self.__updatePluginMenuData)
        self.prjDirImportDgmAct = self.prjDirMenu.addAction(
            getIcon('importsdiagram.png'),
            "Imports diagram", self.__onImportDiagram)
        self.prjDirImportDgmTunedAct = self.prjDirMenu.addAction(
            getIcon('detailsdlg.png'),
            'Fine tuned imports diagram', self.__onImportDgmTuned)
        self.prjDirMenu.addSeparator()
        self.prjDirNewDirAct = self.prjDirMenu.addAction(
            getIcon('newdir.png'), 'Create nested directory', self.__createDir)
        self.prjDirMenu.addSeparator()
        self.prjDirFindAct = self.prjDirMenu.addAction(
            getIcon('findindir.png'),
            'Find in this directory', self.projectTreeView.findInDirectory)
        self.prjDirCopyPathAct = self.prjDirMenu.addAction(
            getIcon('copymenu.png'),
            'Copy path to clipboard', self.projectTreeView.copyToClipboard)
        self.prjDirMenu.addSeparator()
        self.prjDirRemoveFromDiskAct = self.prjDirMenu.addAction(
            getIcon('trash.png'),
            'Remove directory from the disk recursively', self.__removePrj)
        self.__prjDirPluginSeparator = self.prjDirMenu.addSeparator()
        self.__prjDirPluginSeparator.setVisible(False)

        # popup menu for files
        self.prjFileMenu = QMenu(self)
        self.prjFileMenu.aboutToShow.connect(self.__updatePluginMenuData)
        self.prjFileImportDgmAct = self.prjFileMenu.addAction(
            getIcon('importsdiagram.png'),
            "Imports diagram", self.__onImportDiagram)
        self.prjFileImportDgmTunedAct = self.prjFileMenu.addAction(
            getIcon('detailsdlg.png'),
            'Fine tuned imports diagram', self.__onImportDgmTuned)
        self.prjFileMenu.addSeparator()
        self.prjFileCopyPathAct = self.prjFileMenu.addAction(
            getIcon('copymenu.png'),
            'Copy path to clipboard', self.projectTreeView.copyToClipboard)
        self.prjFileShowErrorsAct = self.prjFileMenu.addAction(
            getIcon('showparsingerrors.png'),
            'Show lexer/parser errors', self.showPrjParserError)
        self.prjDisasmMenu = self.prjFileMenu.addMenu(
            getIcon('disassembly.png'), 'Disassembly')
        self.prjDisasmAct0 = self.prjDisasmMenu.addAction(
            getIcon(''), 'Disassembly (no optimization)',
            self.onPrjDisasm0)
        self.prjDisasmAct1 = self.prjDisasmMenu.addAction(
            getIcon(''), 'Disassembly (optimization level 1)',
            self.onPrjDisasm1)
        self.prjDisasmAct2 = self.prjDisasmMenu.addAction(
            getIcon(''), 'Disassembly (optimization level 2)',
            self.onPrjDisasm2)
        self.prjFileMenu.addMenu(self.prjDisasmMenu)
        self.prjDisasmPycAct = self.prjFileMenu.addAction(
            getIcon('disassembly.png'), 'Disassembly .pyc',
            self.onPrjDisasm0)
        self.prjFileMenu.addSeparator()
        self.prjFileRemoveFromDiskAct = self.prjFileMenu.addAction(
            getIcon('trash.png'),
            'Remove file from the disk', self.__removePrj)
        self.__prjFilePluginSeparator = self.prjFileMenu.addSeparator()
        self.__prjFilePluginSeparator.setVisible(False)

        # Popup menu for broken symlinks
        self.prjBrokenLinkMenu = QMenu(self)
        self.prjBrokenLinkMenu.addAction(
            getIcon('trash.png'),
            'Remove broken link from the disk', self.__removePrj)

    def __createFilesystemPartLayout(self):
        """Creates the lower part of the project viewer"""
        # Header part: label + show/hide button
        self.headerFrame = QFrame()
        self.headerFrame.setObjectName('fsheader')
        self.headerFrame.setStyleSheet('QFrame#fsheader {' +
                                       getLabelStyle(self) + '}')
        self.headerFrame.setFixedHeight(HEADER_HEIGHT)

        projectLabel = QLabel()
        projectLabel.setText("File system")

        expandingSpacer = QSpacerItem(10, 10, QSizePolicy.Expanding)

        self.__showHideButton = QToolButton()
        self.__showHideButton.setAutoRaise(True)
        self.__showHideButton.setIcon(getIcon('less.png'))
        self.__showHideButton.setFixedSize(HEADER_BUTTON, HEADER_BUTTON)
        self.__showHideButton.setToolTip("Hide file system tree")
        self.__showHideButton.setFocusPolicy(Qt.NoFocus)
        self.__showHideButton.clicked.connect(self.__onShowHide)

        headerLayout = QHBoxLayout()
        headerLayout.setContentsMargins(3, 0, 0, 0)
        headerLayout.addWidget(projectLabel)
        headerLayout.addSpacerItem(expandingSpacer)
        headerLayout.addWidget(self.__showHideButton)
        self.headerFrame.setLayout(headerLayout)

        # Tree view part
        self.filesystemView = FileSystemBrowser()
        self.filesystemView.sigFirstSelectedItem.connect(
            self.__fsSelectionChanged)
        self.filesystemView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.filesystemView.customContextMenuRequested.connect(
            self.__fsContextMenuRequested)

        # Toolbar part - buttons
        self.fsFindInDirButton = QAction(
            getIcon('findindir.png'), 'Find in highlighted directory', self)
        self.fsFindInDirButton.triggered.connect(
            self.filesystemView.findInDirectory)
        self.fsAddTopLevelDirButton = QAction(
            getIcon('addtopleveldir.png'),
            'Add as a top level directory', self)
        self.fsAddTopLevelDirButton.triggered.connect(self.addToplevelDir)
        self.fsRemoveTopLevelDirButton = QAction(
            getIcon('removetopleveldir.png'),
            'Remove from the top level directories', self)
        self.fsRemoveTopLevelDirButton.triggered.connect(
            self.removeToplevelDir)
        self.fsShowParsingErrorsButton = QAction(
            getIcon('showparsingerrors.png'), 'Show lexer/parser errors', self)
        self.fsShowParsingErrorsButton.triggered.connect(
            self.showFsParserError)
        self.fsCopyToClipboardButton = QAction(
            getIcon('copymenu.png'), 'Copy path to clipboard', self)
        self.fsCopyToClipboardButton.triggered.connect(
            self.filesystemView.copyToClipboard)
        self.fsReloadButton = QAction(getIcon('reload.png'),
                                      'Re-read the file system tree', self)
        self.fsReloadButton.triggered.connect(self.filesystemView.reload)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.lowerToolbar = QToolBar()
        self.lowerToolbar.setMovable(False)
        self.lowerToolbar.setAllowedAreas(Qt.TopToolBarArea)
        self.lowerToolbar.setIconSize(QSize(16, 16))
        self.lowerToolbar.setFixedHeight(28)
        self.lowerToolbar.setContentsMargins(0, 0, 0, 0)
        self.lowerToolbar.addAction(self.fsFindInDirButton)
        self.lowerToolbar.addAction(self.fsAddTopLevelDirButton)
        self.lowerToolbar.addAction(self.fsRemoveTopLevelDirButton)
        self.lowerToolbar.addAction(self.fsCopyToClipboardButton)
        self.lowerToolbar.addAction(self.fsShowParsingErrorsButton)
        self.lowerToolbar.addWidget(spacer)
        self.lowerToolbar.addAction(self.fsReloadButton)


        fsLayout = QVBoxLayout()
        fsLayout.setContentsMargins(0, 0, 0, 0)
        fsLayout.setSpacing(0)
        fsLayout.addWidget(self.headerFrame)
        fsLayout.addWidget(self.lowerToolbar)
        fsLayout.addWidget(self.filesystemView)

        lowerContainer = QWidget()
        lowerContainer.setContentsMargins(0, 0, 0, 0)
        lowerContainer.setLayout(fsLayout)
        return lowerContainer

    def getFileSystemToolbar(self):
        """Provides a reference to the file system part toolbar"""
        return self.lowerToolbar

    def __createFilesystemPopupMenu(self):
        """Generates the various popup menus for the FS browser"""
        # create the popup menu for files
        self.fsFileMenu = QMenu(self)
        self.fsFileMenu.aboutToShow.connect(self.__updatePluginMenuData)
        self.fsFileCopyPathAct = self.fsFileMenu.addAction(
            getIcon('copymenu.png'),
            'Copy path to clipboard', self.filesystemView.copyToClipboard)
        self.fsFileShowErrorsAct = self.fsFileMenu.addAction(
            getIcon('showparsingerrors.png'),
            'Show lexer/parser errors', self.showFsParserError)
        self.fsDisasmMenu = self.fsFileMenu.addMenu(
            getIcon('disassembly.png'), 'Disassembly')
        self.fsDisasmAct0 = self.fsDisasmMenu.addAction(
            getIcon(''), 'Disassembly (no optimization)',
            self.onFsDisasm0)
        self.fsDisasmAct1 = self.fsDisasmMenu.addAction(
            getIcon(''), 'Disassembly (optimization level 1)',
            self.onFsDisasm1)
        self.fsDisasmAct2 = self.fsDisasmMenu.addAction(
            getIcon(''), 'Disassembly (optimization level 2)',
            self.onFsDisasm2)
        self.fsFileMenu.addMenu(self.fsDisasmMenu)
        self.fsDisasmPycAct = self.fsFileMenu.addAction(
            getIcon('disassembly.png'), 'Disassembly .pyc',
            self.onFsDisasm0)
        self.fsFileMenu.addSeparator()
        self.fsFileRemoveAct = self.fsFileMenu.addAction(
            getIcon('trash.png'), 'Remove file from the disk', self.__removeFs)
        self.__fsFilePluginSeparator = self.fsFileMenu.addSeparator()
        self.__fsFilePluginSeparator.setVisible(False)

        # create the directory menu
        self.fsDirMenu = QMenu(self)
        self.fsDirMenu.aboutToShow.connect(self.__updatePluginMenuData)
        self.fsDirAddAsTopLevelAct = self.fsDirMenu.addAction(
            getIcon('addtopleveldir.png'),
            'Add as top level directory', self.addToplevelDir)
        self.fsDirRemoveFromToplevelAct = self.fsDirMenu.addAction(
            getIcon('removetopleveldir.png'),
            'Remove from top level', self.removeToplevelDir)
        self.fsDirMenu.addSeparator()
        self.fsDirFindAct = self.fsDirMenu.addAction(
            getIcon('findindir.png'),
            'Find in this directory', self.filesystemView.findInDirectory)
        self.fsDirCopyPathAct = self.fsDirMenu.addAction(
            getIcon('copymenu.png'),
            'Copy path to clipboard', self.filesystemView.copyToClipboard)
        self.fsDirMenu.addSeparator()
        self.fsDirRemoveAct = self.fsDirMenu.addAction(
            getIcon('trash.png'),
            'Remove directory from the disk recursively', self.__removeFs)
        self.__fsDirPluginSeparator = self.fsDirMenu.addSeparator()
        self.__fsDirPluginSeparator.setVisible(False)

        # create menu for broken symlink
        self.fsBrokenLinkMenu = QMenu(self)
        self.fsBrokenLinkMenu.addAction(
            getIcon('trash.png'),
            'Remove broken link from the disk', self.__removeFs)

        # popup menu for python files content
        self.fsPythonMenu = QMenu(self)
        self.fsUsageAct = self.fsPythonMenu.addAction(
            getIcon('findusage.png'),
            'Find occurences', self.__fsFindWhereUsed)
        self.fsCopyAct = self.fsPythonMenu.addAction(
            getIcon('copymenu.png'),
            'Copy path to clipboard', self.filesystemView.copyToClipboard)

    @staticmethod
    def unloadProject():
        """Unloads the project"""
        # Check first if the project can be unloaded
        globalData = GlobalData()
        mainWindow = globalData.mainWindow
        editorsManager = mainWindow.editorsManagerWidget.editorsManager
        if editorsManager.closeRequest():
            globalData.project.tabsStatus = editorsManager.getTabsStatus()
            editorsManager.closeAll()
            globalData.project.fsBrowserExpandedDirs = \
                mainWindow.getProjectExpandedPaths()
            globalData.project.unloadProject()

    def __onRestorePrjExpandedDirs(self):
        """Triggered when a project tree should restore its previous state"""
        for path in GlobalData().project.fsBrowserExpandedDirs:
            self.projectTreeView.highlightItem(path)

    def __onProjectChanged(self, what):
        """Triggered when a signal comes"""
        if what != CodimensionProject.CompleteProject:
            return

        if GlobalData().project.isLoaded():
            self.projectLabel.setText(
                'Project: ' + os.path.basename(
                    GlobalData().project.fileName)[:-5])
            self.propertiesButton.setEnabled(True)
            self.unloadButton.setEnabled(True)
        else:
            self.projectLabel.setText('Project: none')
            self.propertiesButton.setEnabled(False)
            self.unloadButton.setEnabled(False)
        self.filesystemView.layoutDisplay()
        self.projectTreeView.layoutDisplay()

        self.__fsContextItem = None
        self.__prjContextItem = None

        self.__updateFSToolbarButtons()
        self.__updatePrjToolbarButtons()

    def projectProperties(self):
        """Triggered when the project properties button is clicked"""
        project = GlobalData().project
        dialog = ProjectPropertiesDialog(project, self)
        if dialog.exec_() == QDialog.Accepted:
            importDirs = []
            for index in range(dialog.importDirList.count()):
                importDirs.append(dialog.importDirList.item(index).text())

            scriptName = dialog.scriptEdit.text().strip()
            if scriptName != "":
                relativePath = os.path.relpath(scriptName,
                                               project.getProjectDir())
                if not relativePath.startswith('..'):
                    scriptName = relativePath

            mdDocFile = dialog.mdDocEdit.text().strip()
            if mdDocFile != '':
                relativePath = os.path.relpath(mdDocFile,
                                               project.getProjectDir())
                if not relativePath.startswith('..'):
                    mdDocFile = relativePath

            project.updateProperties(
                {'scriptname': scriptName,
                 'mddocfile': mdDocFile,
                 'creationdate': dialog.creationDateEdit.text().strip(),
                 'author': dialog.authorEdit.text().strip(),
                 'license': dialog.licenseEdit.text().strip(),
                 'copyright': dialog.copyrightEdit.text().strip(),
                 'version': dialog.versionEdit.text().strip(),
                 'email': dialog.emailEdit.text().strip(),
                 'description': dialog.descriptionEdit.toPlainText().strip(),
                 'uuid': dialog.uuidEdit.text().strip(),
                 'importdirs':  importDirs,
                 'encoding': dialog.encodingCombo.currentText().strip()})

            self.sigFileUpdated.emit(project.fileName, "")
            self.onFileUpdated(project.fileName, "")

    def __fsSelectionChanged(self, index):
        """Handles the changed selection in the FS browser"""
        if index.isValid():
            self.__fsContextItem = self.filesystemView.model().item(index)
        else:
            self.__fsContextItem = None
        self.__updateFSToolbarButtons()

    def __prjSelectionChanged(self, index):
        """Handles the changed selection in the project browser"""
        if index.isValid():
            self.__prjContextItem = self.projectTreeView.model().item(index)
        else:
            self.__prjContextItem = None
        self.__updatePrjToolbarButtons()

    def __updateFSToolbarButtons(self):
        """Updates the toolbar buttons depending on the __fsContextItem"""
        self.fsFindInDirButton.setEnabled(False)
        self.fsAddTopLevelDirButton.setEnabled(False)
        self.fsRemoveTopLevelDirButton.setEnabled(False)
        self.fsShowParsingErrorsButton.setEnabled(False)
        self.fsCopyToClipboardButton.setEnabled(False)

        if self.__fsContextItem is None:
            return

        if self.__fsContextItem.itemType not in \
           [NoItemType, SysPathItemType, GlobalsItemType,
            ImportsItemType, FunctionsItemType,
            ClassesItemType, StaticAttributesItemType,
            InstanceAttributesItemType]:
            self.fsCopyToClipboardButton.setEnabled(True)

        if self.__fsContextItem.itemType == DirectoryItemType:
            self.fsFindInDirButton.setEnabled(True)
            globalData = GlobalData()
            if globalData.project.isLoaded():
                if globalData.project.isTopLevelDir(
                        self.__fsContextItem.getPath()):
                    if self.__fsContextItem.parentItem.itemType == NoItemType:
                        self.fsRemoveTopLevelDirButton.setEnabled(True)
                else:
                    if self.__fsContextItem.parentItem.itemType != NoItemType:
                        self.fsAddTopLevelDirButton.setEnabled(True)

        if self.__fsContextItem.itemType == FileItemType:
            if isPythonMime(self.__fsContextItem.fileType) and \
               'broken-symlink' not in self.__fsContextItem.fileType:
                self.fsShowParsingErrorsButton.setEnabled(
                    self.__fsContextItem.parsingErrors)

    def __updatePrjToolbarButtons(self):
        """Updates the toolbar buttons depending on the __prjContextItem"""
        self.prjFindWhereUsedButton.setEnabled(False)
        self.prjFindInDirButton.setEnabled(False)
        self.prjShowParsingErrorsButton.setEnabled(False)
        self.prjNewDirButton.setEnabled(False)
        self.prjCopyToClipboardButton.setEnabled(False)
#        self.prjDelProjectDirButton.setEnabled(False)

        if self.__prjContextItem is None:
            return

        if self.__prjContextItem.itemType not in \
                    [NoItemType, SysPathItemType, GlobalsItemType,
                     ImportsItemType, FunctionsItemType,
                     ClassesItemType, StaticAttributesItemType,
                     InstanceAttributesItemType]:
            self.prjCopyToClipboardButton.setEnabled(True)

        if self.__prjContextItem.itemType == DirectoryItemType:
            self.prjFindInDirButton.setEnabled(True)
            self.prjNewDirButton.setEnabled(True)

            # if it is a top level and not the project file containing dir then
            # the del button should be enabled
            if self.__prjContextItem.parentItem.itemType == NoItemType:
                projectDir = os.path.dirname(GlobalData().project.fileName) + \
                             os.path.sep

        if self.__prjContextItem.itemType == FileItemType:
            if isPythonMime(self.__prjContextItem.fileType):
                self.prjShowParsingErrorsButton.setEnabled(
                    self.__prjContextItem.parsingErrors)

        if self.__prjContextItem.itemType in [FunctionItemType, ClassItemType,
                                              AttributeItemType,
                                              GlobalItemType]:
            self.prjFindWhereUsedButton.setEnabled(True)

    def __fsContextMenuRequested(self, coord):
        """Triggers when the filesystem menu is requested"""
        index = self.filesystemView.indexAt(coord)
        if not index.isValid():
            return

        # This will update the __fsContextItem
        self.__fsSelectionChanged(index)
        if self.__fsContextItem is None:
            return

        if self.__fsContextItem.itemType in [NoItemType, SysPathItemType,
                                             GlobalsItemType, ImportsItemType,
                                             FunctionsItemType,
                                             ClassesItemType,
                                             StaticAttributesItemType,
                                             InstanceAttributesItemType]:
            return
        if self.__fsContextItem.itemType == FileItemType:
            if 'broken-symlink' in self.__fsContextItem.fileType:
                self.fsBrokenLinkMenu.popup(QCursor.pos())
                return

        # Update the menu items status
        self.fsFileCopyPathAct.setEnabled(
            self.fsCopyToClipboardButton.isEnabled())
        self.fsCopyAct.setEnabled(
            self.fsCopyToClipboardButton.isEnabled())
        self.fsFileShowErrorsAct.setEnabled(
            self.fsShowParsingErrorsButton.isEnabled())

        self.fsDirAddAsTopLevelAct.setEnabled(
            self.fsAddTopLevelDirButton.isEnabled())
        self.fsDirRemoveFromToplevelAct.setEnabled(
            self.fsRemoveTopLevelDirButton.isEnabled())
        self.fsDirFindAct.setEnabled(
            self.fsFindInDirButton.isEnabled())
        self.fsDirCopyPathAct.setEnabled(
            self.fsCopyToClipboardButton.isEnabled())

        self.fsDisasmMenu.setEnabled(False)
        self.fsDisasmPycAct.setEnabled(False)
        if self.__fsContextItem.itemType == FileItemType:
            if isPythonMime(self.__fsContextItem.fileType):
                self.fsDisasmMenu.setEnabled(True)
            elif isPythonCompiledFile(self.__fsContextItem.getPath()):
                self.fsDisasmPycAct.setEnabled(True)

        # Add more conditions
        self.fsUsageAct.setEnabled(
            self.__fsContextItem.itemType in [FunctionItemType,
                                              ClassItemType,
                                              AttributeItemType,
                                              GlobalItemType] and \
                GlobalData().project.isProjectFile(
                    self.__fsContextItem.getPath()))

        if self.__fsContextItem.itemType == FileItemType:
            if self.__fsContextItem.isLink:
                self.fsFileRemoveAct.setText("Remove link from the disk")
            else:
                self.fsFileRemoveAct.setText("Remove file from the disk")
            self.fsFileRemoveAct.setEnabled(
                self.__canDeleteFile(self.__fsContextItem.getPath()))
            self.fsFileMenu.popup(QCursor.pos())
        elif self.__fsContextItem.itemType == DirectoryItemType:
            if self.__fsContextItem.isLink:
                self.fsDirRemoveAct.setText("Remove link from the disk")
            else:
                self.fsDirRemoveAct.setText("Remove directory from "
                                            "the disk recursively")
            self.fsDirRemoveAct.setEnabled(
                self.__canDeleteDir(self.__fsContextItem.getPath()))
            self.fsDirMenu.popup(QCursor.pos())
        elif self.__fsContextItem.itemType in [CodingItemType, ImportItemType,
                                               FunctionItemType,
                                               ClassItemType,
                                               DecoratorItemType,
                                               AttributeItemType,
                                               GlobalItemType,
                                               ImportWhatItemType]:
            self.fsPythonMenu.popup(QCursor.pos())

    def __prjContextMenuRequested(self, coord):
        """Triggered before the project context menu is shown"""
        index = self.projectTreeView.indexAt(coord)
        if not index.isValid():
            return

        # This will update the __prjContextItem
        self.__prjSelectionChanged(index)
        if self.__prjContextItem is None:
            return

        if self.__prjContextItem.itemType in [NoItemType, SysPathItemType,
                                              GlobalsItemType, ImportsItemType,
                                              FunctionsItemType,
                                              ClassesItemType,
                                              StaticAttributesItemType,
                                              InstanceAttributesItemType]:
            return
        if self.__prjContextItem.itemType == FileItemType:
            if 'broken-symlink' in self.__prjContextItem.fileType:
                self.prjBrokenLinkMenu.popup(QCursor.pos())
                return

        # Update the menu items status
        self.prjUsageAct.setEnabled(
            self.prjFindWhereUsedButton.isEnabled())
        self.prjCopyAct.setEnabled(
            self.prjCopyToClipboardButton.isEnabled())
        self.prjDirNewDirAct.setEnabled(
            self.prjNewDirButton.isEnabled())
        self.prjDirFindAct.setEnabled(
            self.prjFindInDirButton.isEnabled())
        self.prjDirCopyPathAct.setEnabled(
            self.prjCopyToClipboardButton.isEnabled())
        self.prjFileCopyPathAct.setEnabled(
            self.prjCopyToClipboardButton.isEnabled())
        self.prjFileShowErrorsAct.setEnabled(
            self.prjShowParsingErrorsButton.isEnabled())

        # Imports diagram menu
        enabled = False
        if self.__prjContextItem.itemType == DirectoryItemType:
            enabled = True
        if self.__prjContextItem.itemType == FileItemType:
            if isPythonMime(self.__prjContextItem.fileType):
                enabled = True
        if not GlobalData().graphvizAvailable:
            enabled = False
        self.prjFileImportDgmAct.setEnabled(enabled)
        self.prjFileImportDgmTunedAct.setEnabled(enabled)
        self.prjDirImportDgmAct.setEnabled(enabled)
        self.prjDirImportDgmTunedAct.setEnabled(enabled)

        # Disassembling menu
        self.prjDisasmMenu.setEnabled(False)
        self.prjDisasmPycAct.setEnabled(False)
        if self.__prjContextItem.itemType == FileItemType:
            if isPythonMime(self.__prjContextItem.fileType):
                self.prjDisasmMenu.setEnabled(True)
            elif isPythonCompiledFile(self.__prjContextItem.getPath()):
                self.prjDisasmPycAct.setEnabled(True)

        if self.__prjContextItem.itemType == FileItemType:
            if self.__prjContextItem.isLink:
                self.prjFileRemoveFromDiskAct.setText(
                    "Remove link from the disk")
            else:
                self.prjFileRemoveFromDiskAct.setText(
                    "Remove file from the disk")
            self.prjFileRemoveFromDiskAct.setEnabled(
                self.__canDeleteFile(self.__prjContextItem.getPath()))
            self.prjFileMenu.popup(QCursor.pos())
        elif self.__prjContextItem.itemType == DirectoryItemType:
            if self.__prjContextItem.isLink:
                self.prjDirRemoveFromDiskAct.setText(
                    "Remove link from the disk")
            else:
                self.prjDirRemoveFromDiskAct.setText("Remove directory from "
                                                     "the disk recursively")
            self.prjDirRemoveFromDiskAct.setEnabled(
                self.__canDeleteDir(self.__prjContextItem.getPath()))
            self.prjDirMenu.popup(QCursor.pos())
        elif self.__prjContextItem.itemType in [CodingItemType, ImportItemType,
                                                FunctionItemType,
                                                ClassItemType,
                                                DecoratorItemType,
                                                AttributeItemType,
                                                GlobalItemType,
                                                ImportWhatItemType]:
            self.prjPythonMenu.popup(QCursor.pos())

    def __findWhereUsed(self):
        """Triggers analysis where the highlighted item is used"""
        if self.__prjContextItem is not None:
            GlobalData().mainWindow.findWhereUsed(
                self.__prjContextItem.getPath(),
                self.__prjContextItem.sourceObj)

    def __fsFindWhereUsed(self):
        """Triggers analysis where the FS highlighted item is used"""
        if self.__fsContextItem is not None:
            GlobalData().mainWindow.findWhereUsed(
                self.__fsContextItem.getPath(),
                self.__fsContextItem.sourceObj)

    def __createDir(self):
        """Triggered when a new subdir should be created"""
        if self.__isValidPrjItem(DirectoryItemType):
            dlg = NewProjectDirDialog(self)
            if dlg.exec_() == QDialog.Accepted:
                try:
                    os.mkdir(self.__prjContextItem.getPath() +
                             dlg.getDirName())
                except Exception as exc:
                    logging.error(str(exc))

    def __isValidPrjItem(self, itemType):
        """True if it is a valid project item"""
        if self.__prjContextItem is None:
            return False
        return self.__prjContextItem.itemType == itemType

    def __isValidPrjPythonFile(self):
        """True if it is a valid project python file item"""
        if self.__isValidPrjItem(FileItemType):
            if isPythonMime(self.__prjContextItem.fileType):
                return True
        return False

    def showPrjParserError(self):
        """Triggered when parsing errors must be displayed"""
        if self.__isValidPrjPythonFile():
            self.projectTreeView.showParsingErrors(
                self.__prjContextItem.getPath())

    def onDisasm(self, path, opt):
        """Disassemble a file"""
        if path.endswith('.pyc') or path.endswith('.pyo'):
            GlobalData().mainWindow.showPycDisassembly(path)
        else:
            GlobalData().mainWindow.showFileDisassembly(path, opt)

    def onPrjDisasm0(self):
        """Disassemble without optimization"""
        # This one is also called for .pyc files
        if self.__isValidPrjItem(FileItemType):
            if isPythonMime(self.__prjContextItem.fileType) or \
               isPythonCompiledFile(self.__prjContextItem.getPath()):
                self.onDisasm(self.__prjContextItem.getPath(),
                              OPT_NO_OPTIMIZATION)

    def onPrjDisasm1(self):
        """Disassemble with optimization level 1"""
        if self.__isValidPrjPythonFile():
            self.onDisasm(self.__prjContextItem.getPath(), OPT_OPTIMIZE_ASSERT)

    def onPrjDisasm2(self):
        """Disassemble with optimization level 2"""
        if self.__isValidPrjPythonFile():
            self.onDisasm(self.__prjContextItem.getPath(),
                          OPT_OPTIMIZE_DOCSTRINGS)

    def __isValidFsItem(self, itemType):
        """True if it is a valid filesystem item"""
        if self.__fsContextItem is None:
            return False
        return self.__fsContextItem.itemType == itemType

    def __isValidFsPythonFile(self):
        """True if it is a valid filesystem python file item"""
        if self.__isValidFsItem(FileItemType):
            if isPythonMime(self.__fsContextItem.fileType):
                return True
        return False

    def onFsDisasm0(self):
        """Disassemble without optimization"""
        # This one is also called for .pyc files
        if self.__isValidFsItem(FileItemType):
            if isPythonMime(self.__fsContextItem.fileType) or \
               isPythonCompiledFile(self.__fsContextItem.getPath()):
                self.onDisasm(self.__fsContextItem.getPath(),
                              OPT_NO_OPTIMIZATION)

    def onFsDisasm1(self):
        """Disassemble with optimization level 1"""
        if self.__isValidFsPythonFile():
            self.onDisasm(self.__fsContextItem.getPath(), OPT_OPTIMIZE_ASSERT)

    def onFsDisasm2(self):
        """Disassemble with optimization level 2"""
        if self.__isValidFsPythonFile():
            self.onDisasm(self.__fsContextItem.getPath(),
                          OPT_OPTIMIZE_DOCSTRINGS)

    def showFsParserError(self):
        """Triggered when parsing errors must be displayed"""
        if self.__isValidFsPythonFile():
            self.filesystemView.showParsingErrors(
                self.__fsContextItem.getPath())

    def addToplevelDir(self):
        """Triggered for adding a new top level directory"""
        self.filesystemView.addToplevelDir()
        self.__updateFSToolbarButtons()

    def removeToplevelDir(self):
        """Triggered for removing a top level directory"""
        self.filesystemView.removeToplevelDir()
        self.__updateFSToolbarButtons()

    def __removePrj(self):
        """Remove the selected item"""
        if self.__prjContextItem is not None:
            fName = self.__prjContextItem.getPath()
            if self.__removeItem(fName):
                GlobalData().mainWindow.recentProjectsViewer.removeRecentFile(
                    fName)

    def __removeFs(self):
        """Remove the selected item"""
        if self.__fsContextItem is not None:
            fName = self.__fsContextItem.getPath()
            if self.__removeItem(fName):
                # The item has really been deleted. Update the view
                dirname, basename = self.filesystemView._splitPath(fName)
                self.filesystemView._delFromTree(self.__fsContextItem,
                                                 dirname, basename)
                GlobalData().mainWindow.recentProjectsViewer.removeRecentFile(
                    fName)

    def __removeItem(self, path):
        """Removes a link, a file or a directory"""
        path = os.path.abspath(path)
        if os.path.islink(path):
            header = "Deleting a link"
            text = "Are you sure you want to delete the " \
                   "symbolic link <b>" + path + "</b>?"
        elif os.path.isdir(path):
            header = "Deleting a directory"
            text = "Are you sure you want to delete the " \
                   "directory <b>" + path + "</b> recursively?"
        else:
            header = "Deleting a file"
            text = "Are you sure you want to delete the " \
                   "file <b>" + path + "</b>?"

        res = QMessageBox.warning(self, header, text,
                                  QMessageBox.StandardButtons(
                                      QMessageBox.Cancel | QMessageBox.Yes),
                                  QMessageBox.Cancel)
        if res == QMessageBox.Yes:
            try:
                # Unfortunately, remote file system may fail to report that
                # something has been deleted. So let's check that the
                # requested item still exists
                if os.path.exists(path):
                    if os.path.islink(path):
                        os.remove(path)
                    elif os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                else:
                    logging.info("Could not find " + path +
                                 " on the disk. Ignoring and "
                                 "deleting from the browser.")
            except Exception as exc:
                logging.error(str(exc))
                return False
            return True
        return False

    @staticmethod
    def __canDeleteFile(path):
        """Returns True if the file can be deleted"""
        return GlobalData().project.fileName != os.path.realpath(path)

    @staticmethod
    def __canDeleteDir(path):
        """Returns True if the dir can be deleted"""
        path = os.path.realpath(path)
        if not path.endswith(os.path.sep):
            path += os.path.sep
        return not GlobalData().project.fileName.startswith(path)

    @staticmethod
    def __areTherePythonFiles(path):
        """Tests if a directory has at least one python file"""
        for item in os.listdir(path):
            if os.path.isdir(path + item):
                if ProjectViewer.__areTherePythonFiles(path + item +
                                                       os.path.sep):
                    return True
                continue
            if isPythonFile(path + item):
                return True
        return False

    def __onImportDiagram(self):
        """Triggered when an import diagram is requested"""
        if self.__prjContextItem is None:
            return

        if self.__prjContextItem.itemType == DirectoryItemType:
            # Check first if there are python files in it
            if not self.__areTherePythonFiles(self.__prjContextItem.getPath()):
                logging.warning("There are no python files in " +
                                self.__prjContextItem.getPath())
                return
            projectDir = GlobalData().project.getProjectDir()
            if projectDir == self.__prjContextItem.getPath():
                what = ImportsDiagramDialog.ProjectFiles
                tooltip = "Generated for the project"
            else:
                what = ImportsDiagramDialog.DirectoryFiles
                tooltip = "Generated for directory " + \
                          self.__prjContextItem.getPath()
            self.__generateImportDiagram(what, ImportDiagramOptions(),
                                         tooltip)
        else:
            self.__generateImportDiagram(ImportsDiagramDialog.SingleFile,
                                         ImportDiagramOptions(),
                                         "Generated for file " +
                                         self.__prjContextItem.getPath())

    def __onImportDgmTuned(self):
        """Triggered when a tuned import diagram is requested"""
        if self.__prjContextItem is None:
            return

        if self.__prjContextItem.itemType == DirectoryItemType:
            # Check first if there are python files in it
            if not self.__areTherePythonFiles(self.__prjContextItem.getPath()):
                logging.warning("There are no python files in " +
                                self.__prjContextItem.getPath())
                return

        if self.__prjContextItem.itemType == DirectoryItemType:
            projectDir = GlobalData().project.getProjectDir()
            if projectDir == self.__prjContextItem.getPath():
                what = ImportsDiagramDialog.ProjectFiles
                dlg = ImportsDiagramDialog(what, "", self)
                tooltip = "Generated for the project"
            else:
                what = ImportsDiagramDialog.DirectoryFiles
                dlg = ImportsDiagramDialog(what,
                                           self.__prjContextItem.getPath(),
                                           self)
                tooltip = "Generated for directory " + \
                          self.__prjContextItem.getPath()
        else:
            what = ImportsDiagramDialog.SingleFile
            dlg = ImportsDiagramDialog(what,
                                       self.__prjContextItem.getPath(),
                                       self)
            tooltip = "Generated for file " + self.__prjContextItem.getPath()

        if dlg.exec_() == QDialog.Accepted:
            self.__generateImportDiagram(what, dlg.options, tooltip)

    def __generateImportDiagram(self, what, options, tooltip):
        """Show the generation progress and display the diagram"""
        progressDlg = ImportsDiagramProgress(what, options,
                                             self.__prjContextItem.getPath())
        if progressDlg.exec_() == QDialog.Accepted:
            GlobalData().mainWindow.openDiagram(progressDlg.scene,
                                                tooltip)

    def onFileUpdated(self, fileName, uuid):
        """Triggered when the file is updated"""
        self.projectTreeView.onFileUpdated(fileName, uuid)
        self.__updatePrjToolbarButtons()
        self.filesystemView.onFileUpdated(fileName, uuid)
        self.__updateFSToolbarButtons()

    def __onShowHide(self, startup=False):
        """Triggered when show/hide button is clicked"""
        if startup or self.filesystemView.isVisible():
            self.filesystemView.setVisible(False)
            self.lowerToolbar.setVisible(False)
            self.__showHideButton.setIcon(getIcon('more.png'))
            self.__showHideButton.setToolTip("Show file system tree")

            self.__minH = self.lower.minimumHeight()
            self.__maxH = self.lower.maximumHeight()

            self.lower.setMinimumHeight(self.headerFrame.height())
            self.lower.setMaximumHeight(self.headerFrame.height())

            Settings()['showFSViewer'] = False
        else:
            self.filesystemView.setVisible(True)
            self.lowerToolbar.setVisible(True)
            self.__showHideButton.setIcon(getIcon('less.png'))
            self.__showHideButton.setToolTip("Hide file system tree")

            self.lower.setMinimumHeight(self.__minH)
            self.lower.setMaximumHeight(self.__maxH)

            Settings()['showFSViewer'] = True

    def highlightPrjItem(self, path):
        """Triggered when the file is to be highlighted in a project tree"""
        return self.projectTreeView.highlightItem(path)

    def highlightFSItem(self, path):
        """Triggered when the file is to be highlighted in the FS tree"""
        result = self.filesystemView.highlightItem(path)
        if result:
            # Found, so check if the panel is shown
            if not self.filesystemView.isVisible():
                self.__onShowHide()
        return result

    def __onPluginActivated(self, plugin):
        """Triggered when a plugin is activated"""
        pluginName = plugin.getName()
        try:
            fMenu = QMenu(pluginName, self)
            plugin.getObject().populateFileContextMenu(fMenu)
            if fMenu.isEmpty():
                fMenu = None
            else:
                self.__pluginFileMenus[plugin.getPath()] = fMenu
                self.prjFileMenu.addMenu(fMenu)
                self.__prjFilePluginSeparator.setVisible(True)
                self.fsFileMenu.addMenu(fMenu)
                self.__fsFilePluginSeparator.setVisible(True)
        except Exception as exc:
            logging.error("Error populating " + pluginName +
                          " plugin file context menu: " +
                          str(exc) + ". Ignore and continue.")

        try:
            dMenu = QMenu(pluginName, self)
            plugin.getObject().populateDirectoryContextMenu(dMenu)
            if dMenu.isEmpty():
                dMenu = None
            else:
                self.__pluginDirMenus[plugin.getPath()] = dMenu
                self.prjDirMenu.addMenu(dMenu)
                self.__prjDirPluginSeparator.setVisible(True)
                self.fsDirMenu.addMenu(dMenu)
                self.__fsDirPluginSeparator.setVisible(True)
        except Exception as exc:
            logging.error("Error populating " + pluginName +
                          " plugin directory context menu: " +
                          str(exc) + ". Ignore and continue.")

    def __onPluginDeactivated(self, plugin):
        """Triggered when a plugin is deactivated"""
        try:
            path = plugin.getPath()
            if path in self.__pluginFileMenus:
                fMenu = self.__pluginFileMenus[path]
                del self.__pluginFileMenus[path]
                self.prjFileMenu.removeAction(fMenu.menuAction())
                pluginMenuCount = len(self.__pluginFileMenus)
                self.__prjFilePluginSeparator.setVisible(pluginMenuCount > 0)
                self.fsFileMenu.removeAction(fMenu.menuAction())
                self.__fsFilePluginSeparator.setVisible(pluginMenuCount > 0)
                fMenu = None
        except Exception as exc:
            pluginName = plugin.getName()
            logging.error("Error removing " + pluginName +
                          " plugin file context menu: " +
                          str(exc) + ". Ignore and continue.")

        try:
            path = plugin.getPath()
            if path in self.__pluginDirMenus:
                dMenu = self.__pluginDirMenus[path]
                del self.__pluginDirMenus[path]
                self.prjDirMenu.removeAction(dMenu.menuAction())
                dirMenuCount = len(self.__pluginDirMenus)
                self.__prjDirPluginSeparator.setVisible(dirMenuCount > 0)
                self.fsDirMenu.removeAction(dMenu.menuAction())
                self.__fsDirPluginSeparator.setVisible(dirMenuCount > 0)
                dMenu = None
        except Exception as exc:
            pluginName = plugin.getName()
            logging.error("Error removing " + pluginName +
                          " plugin directory context menu: " +
                          str(exc) + ". Ignore and continue.")

    def __updatePluginMenuData(self):
        """Triggered when a file or dir menu is about to show"""
        if self.projectTreeView.hasFocus():
            value = self.__prjContextItem.getPath()
        else:
            value = self.__fsContextItem.getPath()

        for path in self.__pluginFileMenus:
            menu = self.__pluginFileMenus[path]
            menu.menuAction().setData(value)
        for path in self.__pluginDirMenus:
            menu = self.__pluginDirMenus[path]
            menu.menuAction().setData(value)

    def onDebugMode(self, newState):
        """Triggered when a debug mode is changed"""
        self.unloadButton.setEnabled(GlobalData().project.isLoaded() and
                                     not newState)
