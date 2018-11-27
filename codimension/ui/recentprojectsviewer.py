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

"""list viewer base class for classes/func etc list viewers"""

import os.path
import logging
from utils.pixmapcache import getIcon
from utils.settings import Settings
from utils.project import CodimensionProject, getProjectFileTooltip
from utils.globals import GlobalData
from utils.colorfont import getLabelStyle, HEADER_HEIGHT, HEADER_BUTTON
from utils.fileutils import (getFileProperties, isPythonMime,
                             isCDMProjectMime, isImageViewable)
from utils.diskvaluesrelay import removeRecentFile, getRecentFiles
from .qt import (Qt, QSize, QTreeWidget, QTreeWidgetItem, QHeaderView, QMenu,
                 QToolButton, QWidget, QAction, QDialog, QSpacerItem,
                 QVBoxLayout, QSizePolicy, QToolBar, QApplication, QFrame,
                 QLabel, QHBoxLayout, QSplitter, QCursor)
from .projectproperties import ProjectPropertiesDialog
from .itemdelegates import NoOutlineHeightDelegate


class RecentProjectViewItem(QTreeWidgetItem):

    """Single recent projects view item data structure"""

    def __init__(self, fileName):
        # full file name is expected
        projectName = os.path.basename(fileName .replace('.cdm3', ''))
        QTreeWidgetItem.__init__(self, ["", projectName + "   ", fileName])

        self.__isValid = True
        self.__isCurrent = False
        self.updateTooltip()

    def updateTooltip(self):
        """Updates the item tooltip"""
        fileName = self.getFilename()

        # Check that the file exists
        if not os.path.exists(fileName):
            self.__isValid = False
            self.setToolTip(0, 'Project file does not exist')
            self.setToolTip(1, 'Project file does not exist')
            self.__markBroken()
        else:
            # Get the project properties
            try:
                tooltip = getProjectFileTooltip(fileName)
                if Settings()['recentTooltips']:
                    self.setToolTip(1, tooltip)
                else:
                    self.setToolTip(1, "")
                self.setText(0, "")
                if fileName == GlobalData().project.fileName:
                    self.__markCurrent()
            except:
                # Cannot get project properties. Mark broken.
                self.__isValid = False
                self.setToolTip(0, 'Broken project file')
                self.setToolTip(1, 'Broken project file')
                self.__markBroken()
        self.setToolTip(2, self.getFilename())

    def __markBroken(self):
        """Mark the broken project with an icon"""
        self.setIcon(0, getIcon('brokenproject.png'))

    def __markCurrent(self):
        """Mark the current project with an icon"""
        self.setIcon(0, getIcon('currentproject.png'))
        self.__isCurrent = True

    def getFilename(self):
        """Provides the full project filename"""
        return str(self.text(2))

    def isValid(self):
        """True if the project is valid"""
        return self.__isValid

    def isCurrent(self):
        """True if the project is current"""
        return self.__isCurrent


class RecentFileViewItem(QTreeWidgetItem):

    """Single recent file view item data structure"""

    def __init__(self, fileName):
        # full file name is expected
        basename = os.path.basename(fileName)
        QTreeWidgetItem.__init__(self, ["", basename + "   ", fileName])

        self.__isValid = True
        self.updateIconAndTooltip()

    def updateIconAndTooltip(self):
        """Updates the item icon and tooltip if required"""
        if not os.path.exists(self.getFilename()):
            self.__markBroken()
        else:
            self.__markOK()

    def __markBroken(self):
        """Mark the file as broken"""
        self.__isValid = False
        self.setToolTip(0, 'File does not exist')
        self.setToolTip(1, 'File does not exist')
        self.setToolTip(2, self.getFilename())
        self.setIcon(0, getIcon('brokenproject.png'))

    def __markOK(self):
        """Mark the file as OK"""
        self.__isValid = True
        fileName = self.getFilename()
        mime, icon, _ = getFileProperties(fileName)
        if isPythonMime(mime):
            # The tooltip could be the file docstring
            info = GlobalData().briefModinfoCache.get(fileName)
            if info.docstring and Settings()['recentTooltips']:
                self.setToolTip(1, info.docstring.text)
            else:
                self.setToolTip(1, "")
            if info.isOK:
                self.setIcon(0, getIcon('filepython.png'))
            else:
                self.setIcon(0, getIcon('filepythonbroken.png'))
            self.setToolTip(0, "")
        elif isCDMProjectMime(mime):
            # Get the project properties
            try:
                self.setToolTip(0, "")
                tooltip = getProjectFileTooltip(fileName)
                if Settings()['recentTooltips']:
                    self.setToolTip(1, tooltip)
                else:
                    self.setToolTip(1, "")
                self.setText(0, "")
            except:
                # cannot get project properties. Mark broken.
                self.__isValid = False
                self.setToolTip(0, 'Broken project file')
                self.setToolTip(1, 'Broken project file')
            self.setIcon(0, icon)
        else:
            # Get the other file type icon
            self.setIcon(0, icon)

        self.setToolTip(2, self.getFilename())

    def getFilename(self):
        """Provides the full file name"""
        return str(self.text(2))

    def isValid(self):
        """True if the file is still valid"""
        return self.__isValid


class RecentProjectsViewer(QWidget):

    """Recent projects viewer implementation"""

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

        self.__projectContextItem = None
        self.__fileContextItem = None

        self.__minH = None
        self.__maxH = None

        self.upper = self.__createRecentFilesLayout()
        self.lower = self.__createRecentProjectsLayout()
        self.__createProjectPopupMenu()
        self.__createFilePopupMenu()

        layout = QVBoxLayout()
        layout.setContentsMargins(1, 1, 1, 1)
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.upper)
        splitter.addWidget(self.lower)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)

        layout.addWidget(splitter)
        self.setLayout(layout)

        self.__populateProjects()
        self.__populateFiles()
        self.__updateProjectToolbarButtons()
        self.__updateFileToolbarButtons()

        # Debugging mode support
        self.__debugMode = False
        parent.debugModeChanged.connect(self.__onDebugMode)

    def setTooltips(self, _):
        """Switches the tooltips mode; _: switchOn"""
        for index in range(0, self.recentFilesView.topLevelItemCount()):
            self.recentFilesView.topLevelItem(index).updateIconAndTooltip()
        for index in range(0, self.projectsView.topLevelItemCount()):
            self.projectsView.topLevelItem(index).updateTooltip()

    def __createFilePopupMenu(self):
        """create the recent files popup menu"""
        self.__fileMenu = QMenu(self.recentFilesView)
        self.__openMenuItem = self.__fileMenu.addAction(
            getIcon('openitem.png'), 'Open', self.__openFile)
        self.__copyPathFileMenuItem = self.__fileMenu.addAction(
            getIcon('copymenu.png'),
            'Copy path to clipboard', self.__filePathToClipboard)
        self.__fileMenu.addSeparator()
        self.__delFileMenuItem = self.__fileMenu.addAction(
            getIcon('trash.png'), 'Delete from recent', self.__deleteFile)
        self.recentFilesView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.recentFilesView.customContextMenuRequested.connect(
            self.__handleShowFileContextMenu)

        GlobalData().project.sigRecentFilesChanged.connect(self.__populateFiles)
        Settings().sigRecentFilesChanged.connect(self.__populateFiles)

    def __createProjectPopupMenu(self):
        """Creates the recent project popup menu"""
        self.__projectMenu = QMenu(self.projectsView)
        self.__prjLoadMenuItem = self.__projectMenu.addAction(
            getIcon('load.png'), 'Load', self.__loadProject)
        self.__projectMenu.addSeparator()
        self.__propsMenuItem = self.__projectMenu.addAction(
            getIcon('smalli.png'), 'Properties', self.__viewProperties)
        self.__prjCopyPathMenuItem = self.__projectMenu.addAction(
            getIcon('copymenu.png'),
            'Copy path to clipboard', self.__prjPathToClipboard)
        self.__projectMenu.addSeparator()
        self.__delPrjMenuItem = self.__projectMenu.addAction(
            getIcon('trash.png'), 'Delete from recent', self.__deleteProject)
        self.projectsView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.projectsView.customContextMenuRequested.connect(
            self.__handleShowPrjContextMenu)

        Settings().sigRecentListChanged.connect(self.__populateProjects)
        GlobalData().project.sigProjectChanged.connect(self.__projectChanged)

    def __createRecentFilesLayout(self):
        """Creates the upper part - recent files"""
        headerFrame = QFrame()
        headerFrame.setObjectName('fheader')
        headerFrame.setStyleSheet('QFrame#fheader {' +
                                  getLabelStyle(self) + '}')
        headerFrame.setFixedHeight(HEADER_HEIGHT)

        recentFilesLabel = QLabel()
        recentFilesLabel.setText("Recent files")

        headerLayout = QHBoxLayout()
        headerLayout.setContentsMargins(3, 0, 0, 0)
        headerLayout.addWidget(recentFilesLabel)
        headerFrame.setLayout(headerLayout)

        self.recentFilesView = QTreeWidget()
        self.recentFilesView.setAlternatingRowColors(True)
        self.recentFilesView.setRootIsDecorated(False)
        self.recentFilesView.setItemsExpandable(False)
        self.recentFilesView.setSortingEnabled(True)
        self.recentFilesView.setItemDelegate(NoOutlineHeightDelegate(4))
        self.recentFilesView.setUniformRowHeights(True)

        self.__filesHeaderItem = QTreeWidgetItem(["", "File",
                                                  "Absolute path"])
        self.recentFilesView.setHeaderItem(self.__filesHeaderItem)
        self.recentFilesView.header().setSortIndicator(1, Qt.AscendingOrder)

        self.recentFilesView.itemSelectionChanged.connect(
            self.__fileSelectionChanged)
        self.recentFilesView.itemActivated.connect(self.__fileActivated)

        # Toolbar part - buttons
        self.openFileButton = QAction(getIcon('openitem.png'),
                                      'Open the highlighted file', self)
        self.openFileButton.triggered.connect(self.__openFile)
        self.copyFilePathButton = QAction(getIcon('copymenu.png'),
                                          'Copy path to clipboard', self)
        self.copyFilePathButton.triggered.connect(self.__filePathToClipboard)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.trashFileButton = QAction(getIcon('delitem.png'),
                                       'Remove selected (not from the disk)',
                                       self)
        self.trashFileButton.triggered.connect(self.__deleteFile)

        self.upperToolbar = QToolBar()
        self.upperToolbar.setMovable(False)
        self.upperToolbar.setAllowedAreas(Qt.TopToolBarArea)
        self.upperToolbar.setIconSize(QSize(16, 16))
        self.upperToolbar.setFixedHeight(28)
        self.upperToolbar.setContentsMargins(0, 0, 0, 0)
        self.upperToolbar.addAction(self.openFileButton)
        self.upperToolbar.addAction(self.copyFilePathButton)
        self.upperToolbar.addWidget(spacer)
        self.upperToolbar.addAction(self.trashFileButton)

        recentFilesLayout = QVBoxLayout()
        recentFilesLayout.setContentsMargins(0, 0, 0, 0)
        recentFilesLayout.setSpacing(0)
        recentFilesLayout.addWidget(headerFrame)
        recentFilesLayout.addWidget(self.upperToolbar)
        recentFilesLayout.addWidget(self.recentFilesView)

        upperContainer = QWidget()
        upperContainer.setContentsMargins(0, 0, 0, 0)
        upperContainer.setLayout(recentFilesLayout)
        return upperContainer

    def getRecentFilesToolbar(self):
        """Provides a reference to the recent files toolbar"""
        return self.upperToolbar

    def __createRecentProjectsLayout(self):
        """Creates the bottom layout"""
        self.headerFrame = QFrame()
        self.headerFrame.setObjectName('pheader')
        self.headerFrame.setStyleSheet('QFrame#pheader {' +
                                       getLabelStyle(self) + '}')
        self.headerFrame.setFixedHeight(HEADER_HEIGHT)

        recentProjectsLabel = QLabel()
        recentProjectsLabel.setText("Recent projects")

        expandingSpacer = QSpacerItem(10, 10, QSizePolicy.Expanding)

        self.__showHideButton = QToolButton()
        self.__showHideButton.setAutoRaise(True)
        self.__showHideButton.setIcon(getIcon('less.png'))
        self.__showHideButton.setFixedSize(HEADER_BUTTON, HEADER_BUTTON)
        self.__showHideButton.setToolTip("Hide recent projects list")
        self.__showHideButton.setFocusPolicy(Qt.NoFocus)
        self.__showHideButton.clicked.connect(self.__onShowHide)

        headerLayout = QHBoxLayout()
        headerLayout.setContentsMargins(3, 0, 0, 0)
        headerLayout.addWidget(recentProjectsLabel)
        headerLayout.addSpacerItem(expandingSpacer)
        headerLayout.addWidget(self.__showHideButton)
        self.headerFrame.setLayout(headerLayout)

        # Toolbar part - buttons
        self.loadButton = QAction(getIcon('load.png'),
                                  'Load the highlighted project', self)
        self.loadButton.triggered.connect(self.__loadProject)
        self.propertiesButton = QAction(getIcon('smalli.png'),
                                        'Show the highlighted project '
                                        'properties', self)
        self.propertiesButton.triggered.connect(self.__viewProperties)
        self.copyPrjPathButton = QAction(getIcon('copymenu.png'),
                                         'Copy path to clipboard', self)
        self.copyPrjPathButton.triggered.connect(self.__prjPathToClipboard)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.trashButton = QAction(getIcon('delitem.png'),
                                   'Remove selected (not from the disk)', self)
        self.trashButton.triggered.connect(self.__deleteProject)

        self.lowerToolbar = QToolBar()
        self.lowerToolbar.setMovable(False)
        self.lowerToolbar.setAllowedAreas(Qt.TopToolBarArea)
        self.lowerToolbar.setIconSize(QSize(16, 16))
        self.lowerToolbar.setFixedHeight(28)
        self.lowerToolbar.setContentsMargins(0, 0, 0, 0)
        self.lowerToolbar.addAction(self.loadButton)
        self.lowerToolbar.addAction(self.propertiesButton)
        self.lowerToolbar.addAction(self.copyPrjPathButton)
        self.lowerToolbar.addWidget(spacer)
        self.lowerToolbar.addAction(self.trashButton)

        self.projectsView = QTreeWidget()
        self.projectsView.setAlternatingRowColors(True)
        self.projectsView.setRootIsDecorated(False)
        self.projectsView.setItemsExpandable(False)
        self.projectsView.setSortingEnabled(True)
        self.projectsView.setItemDelegate(NoOutlineHeightDelegate(4))
        self.projectsView.setUniformRowHeights(True)

        self.__projectsHeaderItem = QTreeWidgetItem(
            ["", "Project", "Absolute path"])
        self.projectsView.setHeaderItem(self.__projectsHeaderItem)

        self.projectsView.header().setSortIndicator(1, Qt.AscendingOrder)
        self.projectsView.itemActivated.connect(self.__projectActivated)
        self.projectsView.itemSelectionChanged.connect(
            self.__projectSelectionChanged)

        recentProjectsLayout = QVBoxLayout()
        recentProjectsLayout.setContentsMargins(0, 0, 0, 0)
        recentProjectsLayout.setSpacing(0)
        recentProjectsLayout.addWidget(self.headerFrame)
        recentProjectsLayout.addWidget(self.lowerToolbar)
        recentProjectsLayout.addWidget(self.projectsView)

        lowerContainer = QWidget()
        lowerContainer.setContentsMargins(0, 0, 0, 0)
        lowerContainer.setLayout(recentProjectsLayout)
        return lowerContainer

    def getRecentProjectsToolbar(self):
        """Provides a reference to the projects toolbar"""
        return self.lowerToolbar

    def __projectSelectionChanged(self):
        """Handles the projects changed selection"""
        selected = list(self.projectsView.selectedItems())

        if selected:
            self.__projectContextItem = selected[0]
        else:
            self.__projectContextItem = None

        self.__updateProjectToolbarButtons()

    def __fileSelectionChanged(self):
        """Handles the files changed selection"""
        selected = list(self.recentFilesView.selectedItems())

        if selected:
            self.__fileContextItem = selected[0]
        else:
            self.__fileContextItem = None
        self.__updateFileToolbarButtons()

    def __updateProjectToolbarButtons(self):
        """Updates the toolbar buttons depending on the __projectContextItem"""
        if self.__projectContextItem is None:
            self.loadButton.setEnabled(False)
            self.propertiesButton.setEnabled(False)
            self.copyPrjPathButton.setEnabled(False)
            self.trashButton.setEnabled(False)
        else:
            enabled = self.__projectContextItem.isValid()
            isCurrentProject = self.__projectContextItem.isCurrent()

            self.propertiesButton.setEnabled(enabled)
            self.copyPrjPathButton.setEnabled(True)
            self.loadButton.setEnabled(enabled and
                                       not isCurrentProject and
                                       not self.__debugMode)
            self.trashButton.setEnabled(not isCurrentProject)

    def __updateFileToolbarButtons(self):
        """Updates the toolbar buttons depending on the __fileContextItem"""
        enabled = self.__fileContextItem is not None
        self.openFileButton.setEnabled(enabled)
        self.copyFilePathButton.setEnabled(enabled)
        self.trashFileButton.setEnabled(enabled)

    def __handleShowPrjContextMenu(self, coord):
        """Show the project item context menu"""
        self.__projectContextItem = self.projectsView.itemAt(coord)
        if self.__projectContextItem is None:
            return

        enabled = self.__projectContextItem.isValid()
        isCurrentProject = self.__projectContextItem.isCurrent()

        self.__propsMenuItem.setEnabled(enabled)
        self.__delPrjMenuItem.setEnabled(not isCurrentProject)
        # fName = self.__projectContextItem.getFilename()
        self.__prjLoadMenuItem.setEnabled(enabled and
                                          not isCurrentProject and
                                          not self.__debugMode)

        self.__projectMenu.popup(QCursor.pos())

    def __sortProjects(self):
        """Sort the project items"""
        self.projectsView.sortItems(
            self.projectsView.sortColumn(),
            self.projectsView.header().sortIndicatorOrder())

    def __sortFiles(self):
        """Sort the file items"""
        self.recentFilesView.sortItems(
            self.recentFilesView.sortColumn(),
            self.recentFilesView.header().sortIndicatorOrder())

    def __resizeProjectColumns(self):
        """Resize the projects list columns"""
        self.projectsView.header().setStretchLastSection(True)
        self.projectsView.header().resizeSections(
            QHeaderView.ResizeToContents)
        self.projectsView.header().resizeSection(0, 22)
        self.projectsView.header().setSectionResizeMode(
            0, QHeaderView.Fixed)

    def __resizeFileColumns(self):
        """Resize the files list columns"""
        self.recentFilesView.header().setStretchLastSection(True)
        self.recentFilesView.header().resizeSections(
            QHeaderView.ResizeToContents)
        self.recentFilesView.header().resizeSection(0, 22)
        self.recentFilesView.header().setSectionResizeMode(
            0, QHeaderView.Fixed)

    def __projectActivated(self, item, _):
        """Handles the double click (or Enter) on the item"""
        self.__projectContextItem = item
        self.__loadProject()

    def __fileActivated(self, item, _):
        """Handles the double click (or Enter) on a file item"""
        self.__fileContextItem = item
        self.__openFile()

    def __viewProperties(self):
        """Handles the 'view properties' context menu item"""
        if self.__projectContextItem is None:
            return
        if not self.__projectContextItem.isValid():
            return

        if self.__projectContextItem.isCurrent():
            # This is the current project - it can be edited
            project = GlobalData().project
            dlg = ProjectPropertiesDialog(project, self)
            if dlg.exec_() == QDialog.Accepted:
                importDirs = []
                for index in range(dlg.importDirList.count()):
                    importDirs.append(dlg.importDirList.item(index).text())

                scriptName = dlg.scriptEdit.text().strip()
                relativePath = os.path.relpath(scriptName,
                                               project.getProjectDir())
                if not relativePath.startswith('..'):
                    scriptName = relativePath

                mdDocFile = dlg.mdDocEdit.text().strip()
                relativePath = os.path.relpath(mdDocFile,
                                               project.getProjectDir())
                if not relativePath.startswith('..'):
                    mdDocFile = relativePath

                project.updateProperties(
                    {'scriptname': scriptName,
                     'mddocfile': mdDocFile,
                     'creationdate': dlg.creationDateEdit.text().strip(),
                     'author': dlg.authorEdit.text().strip(),
                     'license': dlg.licenseEdit.text().strip(),
                     'copyright': dlg.copyrightEdit.text().strip(),
                     'version': dlg.versionEdit.text().strip(),
                     'email': dlg.emailEdit.text().strip(),
                     'description': dlg.descriptionEdit.toPlainText().strip(),
                     'uuid': dlg.uuidEdit.text().strip(),
                     'importdirs': importDirs,
                     'encoding': dlg.encodingCombo.currentText().strip()})
        else:
            # This is not the current project - it can be viewed
            fName = self.__projectContextItem.getFilename()
            dlg = ProjectPropertiesDialog(fName, self)
            dlg.exec_()

    def __deleteProject(self):
        """Handles the 'delete from recent' context menu item"""
        if self.__projectContextItem is None:
            return

        # Removal from the visible list is done via a signal which comes back
        # from settings
        fName = self.__projectContextItem.getFilename()
        Settings().deleteRecentProject(fName)

    def __loadProject(self):
        """handles 'Load' context menu item"""
        if self.__projectContextItem is None:
            return
        if not self.__projectContextItem.isValid():
            return
        if self.__debugMode:
            return

        projectFileName = self.__projectContextItem.getFilename()

        if self.__projectContextItem.isCurrent():
            GlobalData().mainWindow.openFile(projectFileName, -1)
            return  # This is the current project, open for text editing

        QApplication.processEvents()
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        if os.path.exists(projectFileName):
            mainWin = GlobalData().mainWindow
            editorsManager = mainWin.editorsManagerWidget.editorsManager
            if editorsManager.closeRequest():
                prj = GlobalData().project
                prj.tabsStatus = editorsManager.getTabsStatus()
                editorsManager.closeAll()
                prj.loadProject(projectFileName)
                mainWin.activateProjectTab()
        else:
            logging.error("The project " +
                          os.path.basename(projectFileName) +
                          " disappeared from the file system.")
            self.__populateProjects()
        QApplication.restoreOverrideCursor()

    def __populateProjects(self):
        """Populates the recent projects"""
        self.projectsView.clear()
        for item in Settings()['recentProjects']:
            self.projectsView.addTopLevelItem(RecentProjectViewItem(item))

        self.__sortProjects()
        self.__resizeProjectColumns()
        self.__updateProjectToolbarButtons()

    def __populateFiles(self):
        """Populates the recent files"""
        self.recentFilesView.clear()
        for path in getRecentFiles():
            self.recentFilesView.addTopLevelItem(RecentFileViewItem(path))

        self.__sortFiles()
        self.__resizeFileColumns()
        self.__updateFileToolbarButtons()

    def __projectChanged(self, what):
        """Triggered when the current project is changed"""
        if what == CodimensionProject.CompleteProject:
            self.__populateProjects()
            self.__populateFiles()
            return

        if what == CodimensionProject.Properties:
            # Update the corresponding tooltip
            items = self.projectsView.findItems(GlobalData().project.fileName,
                                                Qt.MatchExactly, 2)
            if len(items) != 1:
                logging.error("Unexpected number of matched projects: " +
                              str(len(items)))
                return

            items[0].updateTooltip()

    def __openFile(self):
        """Handles 'open' file menu item"""
        self.__fileContextItem.updateIconAndTooltip()
        fName = self.__fileContextItem.getFilename()

        if not self.__fileContextItem.isValid():
            logging.warning("Cannot open " + fName)
            return

        mime, _, _ = getFileProperties(fName)
        if isImageViewable(mime):
            GlobalData().mainWindow.openPixmapFile(fName)
        else:
            GlobalData().mainWindow.openFile(fName, -1)

    def __deleteFile(self):
        """Handles 'delete from recent' file menu item"""
        self.removeRecentFile(self.__fileContextItem.getFilename())

    def __handleShowFileContextMenu(self, coord):
        """File context menu"""
        self.__fileContextItem = self.recentFilesView.itemAt(coord)
        if self.__fileContextItem is not None:
            self.__fileMenu.popup(QCursor.pos())

    def __filePathToClipboard(self):
        """Copies the file item path to the clipboard"""
        if self.__fileContextItem is not None:
            QApplication.clipboard().setText(
                self.__fileContextItem.getFilename())

    def __prjPathToClipboard(self):
        """Copies the project item path to the clipboard"""
        if self.__projectContextItem is not None:
            QApplication.clipboard().setText(
                self.__projectContextItem.getFilename())

    def onFileUpdated(self, fileName, _):
        """Triggered when the file is updated: python or project; _: uuid"""
        realPath = os.path.realpath(fileName)

        count = self.recentFilesView.topLevelItemCount()
        for index in range(0, count):
            item = self.recentFilesView.topLevelItem(index)

            itemRealPath = os.path.realpath(item.getFilename())
            if realPath == itemRealPath:
                item.updateIconAndTooltip()
                break

        for index in range(0, self.projectsView.topLevelItemCount()):
            item = self.projectsView.topLevelItem(index)

            itemRealPath = os.path.realpath(item.getFilename())
            if realPath == itemRealPath:
                item.updateTooltip()
                break

    def __onShowHide(self):
        """Triggered when show/hide button is clicked"""
        if self.projectsView.isVisible():
            self.projectsView.setVisible(False)
            self.lowerToolbar.setVisible(False)
            self.__showHideButton.setIcon(getIcon('more.png'))
            self.__showHideButton.setToolTip("Show recent projects list")

            self.__minH = self.lower.minimumHeight()
            self.__maxH = self.lower.maximumHeight()

            self.lower.setMinimumHeight(self.headerFrame.height())
            self.lower.setMaximumHeight(self.headerFrame.height())
        else:
            self.projectsView.setVisible(True)
            self.lowerToolbar.setVisible(True)
            self.__showHideButton.setIcon(getIcon('less.png'))
            self.__showHideButton.setToolTip("Hide recent projects list")

            self.lower.setMinimumHeight(self.__minH)
            self.lower.setMaximumHeight(self.__maxH)

    def __onDebugMode(self, newState):
        """Triggered when debug mode has changed"""
        self.__debugMode = newState

        # Disable the load project button
        self.__updateProjectToolbarButtons()

    def removeRecentFile(self, fName):
        """Removes a single file from the recent files list"""
        removeRecentFile(fName)

        for index in range(self.recentFilesView.topLevelItemCount()):
            candidate = self.recentFilesView.topLevelItem(index)
            if candidate.getFilename() == fName:
                self.recentFilesView.takeTopLevelItem(index)
                return
