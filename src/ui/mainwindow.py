# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2016  Sergey Satskiy <sergey.satskiy@gmail.com>
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

"""Codimension main window"""

import os.path
import sys
import logging
import gc
from utils.globals import GlobalData
from utils.project import CodimensionProject
from utils.misc import (getDefaultTemplate, getIDETemplateFile,
                        getProjectTemplateFile, extendInstance)
from utils.pixmapcache import getIcon
from utils.settings import THIRDPARTY_DIR
from utils.fileutils import (getFileProperties, isImageViewable, isImageFile,
                             isFileSearchable, isCDMProjectFile, isPythonMime)
from utils.diskvaluesrelay import getRunParameters, addRunParams
from diagram.importsdgm import (ImportsDiagramDialog, ImportsDiagramProgress,
                                ImportDiagramOptions)
from utils.run import (getWorkingDir,
                       parseCommandLineArguments, getNoArgsEnvironment,
                       TERM_AUTO, TERM_KONSOLE, TERM_GNOME, TERM_XTERM,
                       TERM_REDIRECT)
from debugger.context import DebuggerContext
from debugger.modifiedunsaved import ModifiedUnsavedDialog
from debugger.server import CodimensionDebugger
from debugger.excpt import DebuggerExceptions
from debugger.bpwp import DebuggerBreakWatchPoints
from thirdparty.diff2html.diff2html import parse_from_memory
from analysis.notused import NotUsedAnalysisProgress
from autocomplete.completelists import getOccurrences
from profiling.profui import ProfilingProgressDialog
from profiling.disasm import getDisassembled
from debugger.bputils import clearValidBreakpointLinesCache
from utils.colorfont import getMonospaceFontList
from plugins.manager.pluginmanagerdlg import PluginsDialog
from plugins.vcssupport.vcsmanager import VCSManager
from editor.redirectedioconsole import IOConsoleTabWidget
from utils.skin import getThemesList
from utils.config import CONFIG_DIR
from .qt import (Qt, QSize, QTimer, QDir, QUrl, pyqtSignal, QLabel,
                 QToolBar, QWidget, QMessageBox, QVBoxLayout, QSplitter,
                 QSizePolicy, QAction, QMainWindow, QShortcut, QFrame,
                 QApplication, QMenu, QToolButton, QToolTip, QFileDialog,
                 QDialog, QStyleFactory, QActionGroup, QFont, QCursor,
                 QPalette, QColor, QDesktopServices)
from .about import AboutDialog
from .runmanager import RunManager
from .fitlabel import FitPathLabel
from .sidebar import SideBar
from .logviewer import LogViewer
from .taghelpviewer import TagHelpViewer
from .redirector import Redirector
from .functionsviewer import FunctionsViewer
from .globalsviewer import GlobalsViewer
from .classesviewer import ClassesViewer
from .recentprojectsviewer import RecentProjectsViewer
from .projectviewer import ProjectViewer
from .outline import FileOutlineViewer
from .pyflakesviewer import PyflakesViewer
from .editorsmanager import EditorsManager
from .linecounter import LineCounterDialog
from .projectproperties import ProjectPropertiesDialog
from .findreplacewidget import FindWidget, ReplaceWidget
from .gotolinewidget import GotoLineWidget
from .diffviewer import DiffViewer
from .findinfiles import FindInFilesDialog, ItemToSearchIn, getSearchItemIndex
from .findinfilesviewer import FindInFilesViewer, hideSearchTooltip
from .findname import FindNameDialog
from .findfile import FindFileDialog
from .mainwindowtabwidgetbase import MainWindowTabWidgetBase
from .runparams import RunDialog
from .mainstatusbar import MainWindowStatusBarMixin


class EditorsManagerWidget(QWidget):

    """Tab widget which has tabs with editors and viewers"""

    def __init__(self, parent, debugger):

        QWidget.__init__(self, parent)

        self.editorsManager = EditorsManager(parent, debugger)
        self.findWidget = FindWidget(self.editorsManager)
        self.replaceWidget = ReplaceWidget(self.editorsManager)
        self.gotoLineWidget = GotoLineWidget(self.editorsManager)
        self.editorsManager.registerAuxWidgets(self.findWidget,
                                               self.replaceWidget,
                                               self.gotoLineWidget)

        self.editorsManager.setSizePolicy(QSizePolicy.Preferred,
                                          QSizePolicy.Expanding)
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(1, 1, 1, 1)

        self.layout.addWidget(self.editorsManager)
        self.layout.addWidget(self.findWidget)
        self.layout.addWidget(self.replaceWidget)
        self.layout.addWidget(self.gotoLineWidget)

        self.setLayout(self.layout)


class CodimensionMainWindow(QMainWindow):

    """Main application window"""

    DEBUG_ACTION_GO = 1
    DEBUG_ACTION_NEXT = 2
    DEBUG_ACTION_STEP_INTO = 3
    DEBUG_ACTION_RUN_TO_LINE = 4
    DEBUG_ACTION_STEP_OUT = 5

    debugModeChanged = pyqtSignal(bool)

    def __init__(self, splash, settings):
        QMainWindow.__init__(self)

        self.settings = settings

        extendInstance(self, MainWindowStatusBarMixin)
        MainWindowStatusBarMixin.__init__(self)

        self.debugMode = False
        # Last position the IDE received control from the debugger
        self.__lastDebugFileName = None
        self.__lastDebugLineNumber = None
        self.__lastDebugAsException = None
        self.__lastDebugAction = None
        self.__newRunIndex = -1
        self.__newProfileIndex = -1

        self.vcsManager = VCSManager()

        self.__debugger = CodimensionDebugger(self)
        self.__debugger.sigDebuggerStateChanged.connect(
            self.__onDebuggerStateChanged)
        self.__debugger.sigClientLine.connect(self.__onDebuggerCurrentLine)
        self.__debugger.sigClientException.connect(
            self.__onDebuggerClientException)
        self.__debugger.sigClientSyntaxError.connect(
            self.__onDebuggerClientSyntaxError)
        self.__debugger.sigClientIDEMessage.connect(
            self.__onDebuggerClientIDEMessage)
        self.__debugger.sigEvalOK.connect(self.__onEvalOK)
        self.__debugger.sigEvalError.connect(self.__onEvalError)
        self.__debugger.sigExecOK.connect(self.__onExecOK)
        self.__debugger.sigExecError.connect(self.__onExecError)
        self.__debugger.sigClientStdout.connect(self.__onClientStdout)
        self.__debugger.sigClientStderr.connect(self.__onClientStderr)
        self.__debugger.sigClientRawInput.connect(self.__onClientRawInput)
        self.__debugger.getBreakPointModel().sigBreakpoinsChanged.connect(
            self.__onBreakpointsModelChanged)

        self.__initialisation = True

        # This prevents context menu on the main window toolbar.
        # I don't really know why but it is what I need
        self.setContextMenuPolicy(Qt.NoContextMenu)

        # The size restore is done twice to avoid huge flickering
        # This one is approximate, the one in restoreWindowPosition()
        # is precise
        screenSize = GlobalData().application.desktop().screenGeometry()
        if screenSize.width() != settings['screenwidth'] or \
           screenSize.height() != settings['screenheight']:
            # The screen resolution has been changed, use the default pos
            defXPos, defYpos, \
            defWidth, defHeight = settings.getDefaultGeometry()
            self.resize(defWidth, defHeight)
            self.move(defXPos, defYpos)
        else:
            # No changes in the screen resolution
            self.resize(settings['width'], settings['height'])
            self.move(settings['xpos'] + settings['xdelta'],
                      settings['ypos'] + settings['ydelta'])

        splash.showMessage("Creating toolbar...")
        self.__createToolBar()

        splash.showMessage("Creating layout...")
        self.__leftSideBar = None
        self.__bottomSideBar = None
        self.__rightSideBar = None

        # Setup output redirectors
        sys.stdout = Redirector(True)
        sys.stderr = Redirector(False)

        self.__horizontalSplitter = None
        self.__verticalSplitter = None
        self.__horizontalSplitterSizes = settings['hSplitterSizes']
        self.__verticalSplitterSizes = settings['vSplitterSizes']

        self.logViewer = None
        self.redirectedIOConsole = None
        self.__createLayout()

        splash.showMessage("Initializing main menu bar...")
        self.__initPluginSupport()
        self.__initMainMenu()

        self.updateWindowTitle()
        self.__printThirdPartyAvailability()

        findNextAction = QShortcut('F3', self)
        findNextAction.activated.connect(
            self.editorsManagerWidget.editorsManager.findNext)
        findPrevAction = QShortcut('Shift+F3', self)
        findPrevAction.activated.connect(
            self.editorsManagerWidget.editorsManager.findPrev)

        self.__runManager = RunManager(self)

    def restoreWindowPosition(self):
        """Makes sure that the window frame delta is proper"""
        screenSize = GlobalData().application.desktop().screenGeometry()
        if screenSize.width() != self.settings['screenwidth'] or \
           screenSize.height() != self.settings['screenheight']:
            # The screen resolution has been changed, save the new values
            self.settings['screenwidth'] = screenSize.width()
            self.settings['screenheight'] = screenSize.height()
            self.settings['xdelta'] = self.settings['xpos'] - self.x()
            self.settings['ydelta'] = self.settings['ypos'] - self.y()
            self.settings['xpos'] = self.x()
            self.settings['ypos'] = self.y()
        else:
            # Screen resolution is the same as before
            if self.settings['xpos'] != self.x() or \
               self.settings['ypos'] != self.y():
                # The saved delta is incorrect, update it
                self.settings['xdelta'] = self.settings['xpos'] - self.x() + \
                                          self.settings['xdelta']
                self.settings['ydelta'] = self.settings['ypos'] - self.y() + \
                                          self.settings['ydelta']
                self.settings['xpos'] = self.x()
                self.settings['ypos'] = self.y()
        self.__initialisation = False

    def __onMaximizeEditor(self):
        """Triggered when F11 is pressed"""
        self.__leftSideBar.shrink()
        self.__bottomSideBar.shrink()
        self.__rightSideBar.shrink()

    def __createLayout(self):
        """Creates the UI layout"""
        self.editorsManagerWidget = EditorsManagerWidget(self, self.__debugger)
        self.editorsManagerWidget.editorsManager.sigTabRunChanged.connect(
            self.setDebugTabAvailable)

        self.editorsManagerWidget.findWidget.hide()
        self.editorsManagerWidget.replaceWidget.hide()
        self.editorsManagerWidget.gotoLineWidget.hide()

        # The layout is a sidebar-style one
        self.__bottomSideBar = SideBar(SideBar.South, self)
        self.__leftSideBar = SideBar(SideBar.West, self)
        self.__rightSideBar = SideBar(SideBar.East, self)

        # Create tabs on bars
        self.logViewer = LogViewer()
        self.__bottomSideBar.addTab(self.logViewer, getIcon('logviewer.png'),
                                    'Log', 'log', 0)
        sys.stdout.appendToStdout.connect(self.toStdout)
        sys.stderr.appendToStderr.connect(self.toStderr)

        # replace logging streamer to self.stdout
        logging.root.handlers = []
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("%(levelname) -10s %(asctime)s %(message)s",
            None))
        logging.root.addHandler(handler)

        self.projectViewer = ProjectViewer(self)
        self.__leftSideBar.addTab(self.projectViewer, getIcon(''),
                                  'Project', 'project', 0)
        self.editorsManagerWidget.editorsManager.sigFileUpdated.connect(
            self.projectViewer.onFileUpdated)
        self.recentProjectsViewer = RecentProjectsViewer(self)
        self.__leftSideBar.addTab(self.recentProjectsViewer, getIcon(''),
                                  "Recent", 'recent', 1)
        self.editorsManagerWidget.editorsManager.sigFileUpdated.connect(
            self.recentProjectsViewer.onFileUpdated)
        self.editorsManagerWidget.editorsManager.sigBufferSavedAs.connect(
            self.recentProjectsViewer.onFileUpdated)
        self.projectViewer.sigFileUpdated.connect(
            self.recentProjectsViewer.onFileUpdated)

        self.classesViewer = ClassesViewer()
        self.editorsManagerWidget.editorsManager.sigFileUpdated.connect(
            self.classesViewer.onFileUpdated)
        self.__leftSideBar.addTab(self.classesViewer, getIcon(''),
                                  'Classes', 'classes', 2)
        self.functionsViewer = FunctionsViewer()
        self.editorsManagerWidget.editorsManager.sigFileUpdated.connect(
            self.functionsViewer.onFileUpdated)
        self.__leftSideBar.addTab(self.functionsViewer, getIcon(''),
                                  'Functions', 'functions', 3)
        self.globalsViewer = GlobalsViewer()
        self.editorsManagerWidget.editorsManager.sigFileUpdated.connect(
            self.globalsViewer.onFileUpdated)
        self.__leftSideBar.addTab(self.globalsViewer, getIcon(''),
                                  'Globals', 'globals', 4)

        # Create search results viewer
        self.findInFilesViewer = FindInFilesViewer()
        self.__bottomSideBar.addTab(self.findInFilesViewer,
            getIcon('findindir.png'), 'Search results', 'search', 1)

        # Create tag help viewer
        self.tagHelpViewer = TagHelpViewer()
        self.__bottomSideBar.addTab(self.tagHelpViewer,
            getIcon('helpviewer.png'), 'Context help', 'contexthelp', 2)
        self.__bottomSideBar.setTabToolTip('contexthelp',
                                           "Ctrl+F1 in python file")

        # Create diff viewer
        self.diffViewer = DiffViewer()
        self.__bottomSideBar.addTab(self.diffViewer,
            getIcon('diffviewer.png'), 'Diff viewer', 'diff', 3)
        self.__bottomSideBar.setTabToolTip('diff', 'No diff shown')

        # Create outline viewer
        self.outlineViewer = FileOutlineViewer(
            self.editorsManagerWidget.editorsManager, self)
        self.__rightSideBar.addTab(self.outlineViewer,
            getIcon(''), 'File outline', 'fileoutline', 0)

        # Create the pyflakes viewer
        self.__pyflakesViewer = PyflakesViewer(
            self.editorsManagerWidget.editorsManager,
            self.sbPyflakes, self)

        self.debuggerContext = DebuggerContext(self.__debugger)
        self.__rightSideBar.addTab(self.debuggerContext,
            getIcon(''), 'Debugger', 'debugger', 1)
        self.__rightSideBar.setTabEnabled('debugger', False)

        self.debuggerExceptions = DebuggerExceptions()
        self.__rightSideBar.addTab(self.debuggerExceptions,
            getIcon(''), 'Exceptions', 'exceptions', 2)
        self.debuggerExceptions.sigClientExceptionsCleared.connect(
            self.__onClientExceptionsCleared)

        self.debuggerBreakWatchPoints = DebuggerBreakWatchPoints(
            self, self.__debugger)
        self.__rightSideBar.addTab(self.debuggerBreakWatchPoints,
            getIcon(''), 'Breakpoints', 'breakpoints', 3)

        # Create splitters
        self.__horizontalSplitter = QSplitter(Qt.Horizontal)
        self.__verticalSplitter = QSplitter(Qt.Vertical)

        self.__horizontalSplitter.addWidget(self.__leftSideBar)
        self.__horizontalSplitter.addWidget(self.editorsManagerWidget)
        self.__horizontalSplitter.addWidget(self.__rightSideBar)

        # This prevents changing the size of the side panels
        self.__horizontalSplitter.setCollapsible(0, False)
        self.__horizontalSplitter.setCollapsible(2, False)
        self.__horizontalSplitter.setStretchFactor(0, 0)
        self.__horizontalSplitter.setStretchFactor(1, 1)
        self.__horizontalSplitter.setStretchFactor(2, 0)

        self.__verticalSplitter.addWidget(self.__horizontalSplitter)
        self.__verticalSplitter.addWidget(self.__bottomSideBar)
        # This prevents changing the size of the side panels
        self.__verticalSplitter.setCollapsible(1, False)
        self.__verticalSplitter.setStretchFactor(0, 1)
        self.__verticalSplitter.setStretchFactor(1, 1)

        self.setCentralWidget(self.__verticalSplitter)

        self.__leftSideBar.setSplitter(self.__horizontalSplitter)
        self.__bottomSideBar.setSplitter(self.__verticalSplitter)
        self.__rightSideBar.setSplitter(self.__horizontalSplitter)

    def restoreSplitterSizes(self):
        """Restore the side bar state"""
        self.__horizontalSplitter.setSizes(self.settings['hSplitterSizes'])
        self.__verticalSplitter.setSizes(self.settings['vSplitterSizes'])
        if self.settings['leftBarMinimized']:
            self.__leftSideBar.shrink()
        if self.settings['bottomBarMinimized']:
            self.__bottomSideBar.shrink()
        if self.settings['rightBarMinimized']:
            self.__rightSideBar.shrink()

        # Setup splitters movement handlers
        self.__verticalSplitter.splitterMoved.connect(self.vSplitterMoved)
        self.__horizontalSplitter.splitterMoved.connect(self.hSplitterMoved)

    @staticmethod
    def __printThirdPartyAvailability():
        """Prints third party tools availability"""
        globalData = GlobalData()
        if globalData.graphvizAvailable:
            logging.debug("The 'graphviz' utility is available")
        else:
            logging.warning("The 'graphviz' utility is not found. "
                            "Some functionality will not be available.")

    def vSplitterMoved(self, pos, index):
        """Vertical splitter moved handler"""
        newSizes = list(self.__verticalSplitter.sizes())

        if not self.__bottomSideBar.isMinimized():
            self.__verticalSplitterSizes[0] = newSizes[0]

        self.__verticalSplitterSizes[1] = sum(newSizes) - \
            self.__verticalSplitterSizes[0]

    def hSplitterMoved(self, pos, index):
        """Horizontal splitter moved handler"""
        newSizes = list(self.__horizontalSplitter.sizes())

        if not self.__leftSideBar.isMinimized():
            self.__horizontalSplitterSizes[0] = newSizes[0]
        if not self.__rightSideBar.isMinimized():
            self.__horizontalSplitterSizes[2] = newSizes[2]

        self.__horizontalSplitterSizes[1] = sum(newSizes) - \
            self.__horizontalSplitterSizes[0] - \
            self.__horizontalSplitterSizes[2]

    def __initMainMenu(self):
        """Initializes the main menu bar"""
        editorsManager = self.editorsManagerWidget.editorsManager

        # The Project menu
        self.__projectMenu = QMenu("&Project", self)
        self.__projectMenu.aboutToShow.connect(self.__prjAboutToShow)
        self.__projectMenu.aboutToHide.connect(self.__prjAboutToHide)
        self.__newProjectAct = self.__projectMenu.addAction(
            getIcon('createproject.png'), "&New project",
            self.__createNewProject, 'Ctrl+Shift+N')
        self.__openProjectAct = self.__projectMenu.addAction(
            getIcon('project.png'), '&Open project',
            self.__openProject, 'Ctrl+Shift+O')
        self.__unloadProjectAct = self.__projectMenu.addAction(
            getIcon('unloadproject.png'), '&Unload project',
            self.projectViewer.unloadProject)
        self.__projectPropsAct = self.__projectMenu.addAction(
            getIcon('smalli.png'), '&Properties',
            self.projectViewer.projectProperties)
        self.__projectMenu.addSeparator()
        self.__prjTemplateMenu = QMenu("Project-specific &template", self)
        self.__createPrjTemplateAct = self.__prjTemplateMenu.addAction(
            getIcon('generate.png'), '&Create')
        self.__createPrjTemplateAct.triggered.connect(
            self.__onCreatePrjTemplate)
        self.__editPrjTemplateAct = self.__prjTemplateMenu.addAction(
            getIcon('edit.png'), '&Edit')
        self.__editPrjTemplateAct.triggered.connect(self.__onEditPrjTemplate)
        self.__prjTemplateMenu.addSeparator()
        self.__delPrjTemplateAct = self.__prjTemplateMenu.addAction(
            getIcon('trash.png'), '&Delete')
        self.__delPrjTemplateAct.triggered.connect(self.__onDelPrjTemplate)
        self.__projectMenu.addMenu(self.__prjTemplateMenu)
        self.__projectMenu.addSeparator()
        self.__recentPrjMenu = QMenu("&Recent projects", self)
        self.__recentPrjMenu.triggered.connect(self.__onRecentPrj)
        self.__projectMenu.addMenu(self.__recentPrjMenu)
        self.__projectMenu.addSeparator()
        self.__quitAct = self.__projectMenu.addAction(
            getIcon('exitmenu.png'), "E&xit codimension",
            QApplication.closeAllWindows, "Ctrl+Q")

        # The Tab menu
        self.__tabMenu = QMenu("&Tab", self)
        self.__tabMenu.aboutToShow.connect(self.__tabAboutToShow)
        self.__tabMenu.aboutToHide.connect(self.__tabAboutToHide)
        self.__newTabAct = self.__tabMenu.addAction(
            getIcon('filemenu.png'), "&New tab",
            editorsManager.newTabClicked, 'Ctrl+N')
        self.__openFileAct = self.__tabMenu.addAction(
            getIcon('filemenu.png'), '&Open file', self.__openFile, 'Ctrl+O')
        self.__cloneTabAct = self.__tabMenu.addAction(
            getIcon('clonetabmenu.png'), '&Clone tab', editorsManager.onClone)
        self.__closeOtherTabsAct = self.__tabMenu.addAction(
            getIcon(''), 'Close oth&er tabs', editorsManager.onCloseOther)
        self.__closeTabAct = self.__tabMenu.addAction(
            getIcon('closetabmenu.png'), 'Close &tab',
            editorsManager.onCloseTab)
        self.__tabMenu.addSeparator()
        self.__saveFileAct = self.__tabMenu.addAction(
            getIcon('savemenu.png'), '&Save', editorsManager.onSave, 'Ctrl+S')
        self.__saveFileAsAct = self.__tabMenu.addAction(
            getIcon('saveasmenu.png'),
            'Save &as...', editorsManager.onSaveAs, "Ctrl+Shift+S")
        self.__tabJumpToDefAct = self.__tabMenu.addAction(
            getIcon('definition.png'), "&Jump to definition",
            self.__onTabJumpToDef)
        self.__calltipAct = self.__tabMenu.addAction(
            getIcon('calltip.png'), 'Show &calltip', self.__onShowCalltip)
        self.__tabJumpToScopeBeginAct = self.__tabMenu.addAction(
            getIcon('jumpupscopemenu.png'),
            'Jump to scope &begin', self.__onTabJumpToScopeBegin)
        self.__tabOpenImportAct = self.__tabMenu.addAction(
            getIcon('imports.png'), 'Open &import(s)', self.__onTabOpenImport)
        self.__openAsFileAct = self.__tabMenu.addAction(
            getIcon('filemenu.png'), 'O&pen as file', self.__onOpenAsFile)
        self.__downloadAndShowAct = self.__tabMenu.addAction(
            getIcon('filemenu.png'), 'Download and show',
            self.__onDownloadAndShow)
        self.__openInBrowserAct = self.__tabMenu.addAction(
            getIcon('homepagemenu.png'), 'Open in browser',
            self.__onOpenInBrowser)
        self.__tabMenu.addSeparator()
        self.__highlightInPrjAct = self.__tabMenu.addAction(
            getIcon('highlightmenu.png'), 'Highlight in project browser',
            editorsManager.onHighlightInPrj)
        self.__highlightInFSAct = self.__tabMenu.addAction(
            getIcon('highlightmenu.png'), 'Highlight in file system browser',
            editorsManager.onHighlightInFS)
        self.__highlightInOutlineAct = self.__tabMenu.addAction(
            getIcon('highlightmenu.png'), 'Highlight in outline browser',
            self.__onHighlightInOutline)
        self.__tabMenu.addSeparator()
        self.__recentFilesMenu = QMenu("&Recent files", self)
        self.__recentFilesMenu.triggered.connect(self.__onRecentFile)
        self.__tabMenu.addMenu(self.__recentFilesMenu)

        # The Edit menu
        self.__editMenu = QMenu("&Edit", self)
        self.__editMenu.aboutToShow.connect(self.__editAboutToShow)
        self.__editMenu.aboutToHide.connect(self.__editAboutToHide)
        self.__undoAct = self.__editMenu.addAction(
            getIcon('undo.png'), '&Undo', self.__onUndo)
        self.__redoAct = self.__editMenu.addAction(
            getIcon('redo.png'), '&Redo', self.__onRedo)
        self.__editMenu.addSeparator()
        self.__cutAct = self.__editMenu.addAction(
            getIcon('cutmenu.png'), 'Cu&t', self.__onCut)
        self.__copyAct = self.__editMenu.addAction(
            getIcon('copymenu.png'), '&Copy', editorsManager.onCopy)
        self.__pasteAct = self.__editMenu.addAction(
            getIcon('pastemenu.png'), '&Paste', self.__onPaste)
        self.__selectAllAct = self.__editMenu.addAction(
            getIcon('selectallmenu.png'), 'Select &all', self.__onSelectAll)
        self.__editMenu.addSeparator()
        self.__commentAct = self.__editMenu.addAction(
            getIcon('commentmenu.png'), 'C&omment/uncomment', self.__onComment)
        self.__duplicateAct = self.__editMenu.addAction(
            getIcon('duplicatemenu.png'), '&Duplicate line',
            self.__onDuplicate)
        self.__autocompleteAct = self.__editMenu.addAction(
            getIcon('autocompletemenu.png'), 'Autoco&mplete',
            self.__onAutocomplete)
        self.__expandTabsAct = self.__editMenu.addAction(
            getIcon('expandtabs.png'), 'Expand tabs (&4 spaces)',
            self.__onExpandTabs)
        self.__trailingSpacesAct = self.__editMenu.addAction(
            getIcon('trailingws.png'), 'Remove trailing &spaces',
            self.__onRemoveTrailingSpaces)

        # The Search menu
        self.__searchMenu = QMenu("&Search", self)
        self.__searchMenu.aboutToShow.connect(self.__searchAboutToShow)
        self.__searchMenu.aboutToHide.connect(self.__searchAboutToHide)
        self.__searchInFilesAct = self.__searchMenu.addAction(
            getIcon('findindir.png'), "Find in file&s",
            self.findInFilesClicked, "Ctrl+Shift+F")
        self.__searchMenu.addSeparator()
        self.__findNameMenuAct = self.__searchMenu.addAction(
            getIcon('findname.png'), 'Find &name in project',
            self.findNameClicked, 'Alt+Shift+S')
        self.__fileProjectFileAct = self.__searchMenu.addAction(
            getIcon('findfile.png'), 'Find &project file',
            self.findFileClicked, 'Alt+Shift+O')
        self.__searchMenu.addSeparator()
        self.__findOccurencesAct = self.__searchMenu.addAction(
            getIcon('findindir.png'), 'Find &occurrences',
            self.__onFindOccurences)
        self.__findAct = self.__searchMenu.addAction(
            getIcon('findindir.png'), '&Find...', self.__onFind)
        self.__findCurrentAct = self.__searchMenu.addAction(
            getIcon('find.png'), 'Find current &word', self.__onFindCurrent)
        self.__findNextAct = self.__searchMenu.addAction(
            getIcon('1rightarrow.png'), "Find &next", self.__onFindNext)
        self.__findPrevAct = self.__searchMenu.addAction(
            getIcon('1leftarrow.png'), "Find pre&vious", self.__onFindPrevious)
        self.__replaceAct = self.__searchMenu.addAction(
            getIcon('replace.png'), '&Replace...', self.__onReplace)
        self.__goToLineAct = self.__searchMenu.addAction(
            getIcon('gotoline.png'), '&Go to line...', self.__onGoToLine)

        # The Tools menu
        self.__toolsMenu = QMenu("T&ools", self)
        self.__toolsMenu.aboutToShow.connect(self.__toolsAboutToShow)
        self.__toolsMenu.aboutToHide.connect(self.__toolsAboutToHide)
        self.__toolsMenu.addSeparator()
        self.__toolsMenu.addSeparator()
        self.__prjLineCounterAct = self.__toolsMenu.addAction(
            getIcon('linecounter.png'), "&Line counter for project",
            self.linecounterButtonClicked)
        self.__tabLineCounterAct = self.__toolsMenu.addAction(
            getIcon('linecounter.png'), "L&ine counter for tab",
            self.__onTabLineCounter)
        self.__toolsMenu.addSeparator()
        self.__unusedClassesAct = self.__toolsMenu.addAction(
            getIcon('notused.png'), 'Unused class analysis',
            self.onNotUsedClasses)
        self.__unusedFunctionsAct = self.__toolsMenu.addAction(
            getIcon('notused.png'), 'Unused function analysis',
            self.onNotUsedFunctions)
        self.__unusedGlobalsAct = self.__toolsMenu.addAction(
            getIcon('notused.png'), 'Unused global variable analysis',
            self.onNotUsedGlobals)

        # The Run menu
        self.__runMenu = QMenu("&Run", self)
        self.__runMenu.aboutToShow.connect(self.__runAboutToShow)
        self.__prjRunAct = self.__runMenu.addAction(
            getIcon('run.png'), 'Run &project main script',
            self.__onRunProject)
        self.__prjRunDlgAct = self.__runMenu.addAction(
            getIcon('detailsdlg.png'), 'Run p&roject main script...',
            self.__onRunProjectSettings)
        self.__tabRunAct = self.__runMenu.addAction(
            getIcon('run.png'), 'Run &tab script', self.onRunTab)
        self.__tabRunDlgAct = self.__runMenu.addAction(
            getIcon('detailsdlg.png'), 'Run t&ab script...', self.onRunTabDlg)
        self.__runMenu.addSeparator()
        self.__prjProfileAct = self.__runMenu.addAction(
            getIcon('profile.png'), 'Profile project main script',
            self.__onProfileProject)
        self.__prjProfileDlgAct = self.__runMenu.addAction(
            getIcon('profile.png'), 'Profile project main script...',
            self.__onProfileProjectSettings)
        self.__tabProfileAct = self.__runMenu.addAction(
            getIcon('profile.png'), 'Profile tab script', self.__onProfileTab)
        self.__tabProfileDlgAct = self.__runMenu.addAction(
            getIcon('profile.png'), 'Profile tab script...',
            self.__onProfileTabDlg)

        # The Debug menu
        self.__debugMenu = QMenu("Debu&g", self)
        self.__debugMenu.aboutToShow.connect(self.__debugAboutToShow)
        self.__prjDebugAct = self.__debugMenu.addAction(
            getIcon('debugger.png'), 'Debug &project main script',
            self.__onDebugProject, "Shift+F5")
        self.__prjDebugDlgAct = self.__debugMenu.addAction(
            getIcon('detailsdlg.png'), 'Debug p&roject main script...',
            self.__onDebugProjectSettings, "Ctrl+Shift+F5")
        self.__tabDebugAct = self.__debugMenu.addAction(
            getIcon('debugger.png'), 'Debug &tab script',
            self.__onDebugTab, "F5")
        self.__tabDebugDlgAct = self.__debugMenu.addAction(
            getIcon('detailsdlg.png'), 'Debug t&ab script...',
            self.__onDebugTabDlg, "Ctrl+F5")
        self.__debugMenu.addSeparator()
        self.__debugStopBrutalAct = self.__debugMenu.addAction(
            getIcon('dbgstopbrutal.png'), 'Stop session and kill console',
            self.__onBrutalStopDbgSession, "Ctrl+F10")
        self.__debugStopBrutalAct.setEnabled(False)
        self.__debugStopAct = self.__debugMenu.addAction(
            getIcon('dbgstop.png'), 'Stop session and keep console if so',
            self.__onStopDbgSession, "F10")
        self.__debugStopAct.setEnabled(False)
        self.__debugRestartAct = self.__debugMenu.addAction(
            getIcon('dbgrestart.png'), 'Restart session',
            self.__onRestartDbgSession, "F4")
        self.__debugRestartAct.setEnabled(False)
        self.__debugMenu.addSeparator()
        self.__debugContinueAct = self.__debugMenu.addAction(
            getIcon('dbggo.png'), 'Continue', self.__onDbgGo, "F6")
        self.__debugContinueAct.setEnabled(False)
        self.__debugStepInAct = self.__debugMenu.addAction(
            getIcon('dbgstepinto.png'), 'Step in', self.__onDbgStepInto, "F7")
        self.__debugStepInAct.setEnabled(False)
        self.__debugStepOverAct = self.__debugMenu.addAction(
            getIcon('dbgnext.png'), 'Step over', self.__onDbgNext, "F8")
        self.__debugStepOverAct.setEnabled(False)
        self.__debugStepOutAct = self.__debugMenu.addAction(
            getIcon('dbgreturn.png'), 'Step out', self.__onDbgReturn, "F9")
        self.__debugStepOutAct.setEnabled(False)
        self.__debugRunToCursorAct = self.__debugMenu.addAction(
            getIcon('dbgruntoline.png'), 'Run to cursor',
            self.__onDbgRunToLine, "Shift+F6")
        self.__debugRunToCursorAct.setEnabled(False)
        self.__debugJumpToCurrentAct = self.__debugMenu.addAction(
            getIcon('dbgtocurrent.png'), 'Show current line',
            self.__onDbgJumpToCurrent, "Ctrl+W")
        self.__debugJumpToCurrentAct.setEnabled(False)
        self.__debugMenu.addSeparator()

        self.__dumpDbgSettingsMenu = QMenu("Dump debug settings", self)
        self.__debugMenu.addMenu(self.__dumpDbgSettingsMenu)
        self.__debugDumpSettingsAct = self.__dumpDbgSettingsMenu.addAction(
            getIcon('dbgsettings.png'), 'Debug session settings',
            self.__onDumpDebugSettings)
        self.__debugDumpSettingsAct.setEnabled(False)
        self.__debugDumpSettingsEnvAct = self.__dumpDbgSettingsMenu.addAction(
            getIcon('detailsdlg.png'),
            'Session settings with complete environment',
            self.__onDumpFullDebugSettings)
        self.__debugDumpSettingsEnvAct.setEnabled(False)
        self.__dumpDbgSettingsMenu.addSeparator()
        self.__debugDumpScriptSettingsAct = \
            self.__dumpDbgSettingsMenu.addAction(
                getIcon('dbgsettings.png'), 'Current script settings',
                self.__onDumpScriptDebugSettings)
        self.__debugDumpScriptSettingsAct.setEnabled(False)
        self.__debugDumpScriptSettingsEnvAct = \
            self.__dumpDbgSettingsMenu.addAction(
                getIcon('detailsdlg.png'),
                'Current script settings with complete environment',
                self.__onDumpScriptFullDebugSettings)
        self.__debugDumpScriptSettingsEnvAct.setEnabled(False)
        self.__dumpDbgSettingsMenu.addSeparator()
        self.__debugDumpProjectSettingsAct = \
            self.__dumpDbgSettingsMenu.addAction(
                getIcon('dbgsettings.png'), 'Project main script settings',
                self.__onDumpProjectDebugSettings)
        self.__debugDumpProjectSettingsAct.setEnabled(False)
        self.__debugDumpProjectSettingsEnvAct = \
            self.__dumpDbgSettingsMenu.addAction(
                getIcon('detailsdlg.png'),
                'Project script settings with complete environment',
                self.__onDumpProjectFullDebugSettings)
        self.__debugDumpProjectSettingsEnvAct.setEnabled(False)
        self.__dumpDbgSettingsMenu.aboutToShow.connect(
            self.__onDumpDbgSettingsAboutToShow)

        # The Diagrams menu
        self.__diagramsMenu = QMenu("&Diagrams", self)
        self.__diagramsMenu.aboutToShow.connect(self.__diagramsAboutToShow)
        self.__prjImportDgmAct = self.__diagramsMenu.addAction(
            getIcon('importsdiagram.png'), '&Project imports diagram',
            self.__onImportDgm)
        self.__prjImportsDgmDlgAct = self.__diagramsMenu.addAction(
            getIcon('detailsdlg.png'), 'P&roject imports diagram...',
            self.__onImportDgmTuned)
        self.__tabImportDgmAct = self.__diagramsMenu.addAction(
            getIcon('importsdiagram.png'), '&Tab imports diagram',
            self.__onTabImportDgm)
        self.__tabImportDgmDlgAct = self.__diagramsMenu.addAction(
            getIcon('detailsdlg.png'), 'T&ab imports diagram...',
            self.__onTabImportDgmTuned)

        # The View menu
        self.__viewMenu = QMenu("&View", self)
        self.__viewMenu.aboutToShow.connect(self.__viewAboutToShow)
        self.__viewMenu.aboutToHide.connect(self.__viewAboutToHide)
        self.__shrinkBarsAct = self.__viewMenu.addAction(
            getIcon('shrinkmenu.png'), "&Hide sidebars",
            self.__onMaximizeEditor, 'F11')
        self.__leftSideBarMenu = QMenu("&Left sidebar", self)
        self.__leftSideBarMenu.triggered.connect(self.__activateSideTab)
        self.__prjBarAct = self.__leftSideBarMenu.addAction(
            getIcon('project.png'), 'Activate &project tab')
        self.__prjBarAct.setData('project')
        self.__recentBarAct = self.__leftSideBarMenu.addAction(
            getIcon('project.png'), 'Activate &recent tab')
        self.__recentBarAct.setData('recent')
        self.__classesBarAct = self.__leftSideBarMenu.addAction(
            getIcon('class.png'), 'Activate &classes tab')
        self.__classesBarAct.setData('classes')
        self.__funcsBarAct = self.__leftSideBarMenu.addAction(
            getIcon('fx.png'), 'Activate &functions tab')
        self.__funcsBarAct.setData('functions')
        self.__globsBarAct = self.__leftSideBarMenu.addAction(
            getIcon('globalvar.png'), 'Activate &globals tab')
        self.__globsBarAct.setData('globals')
        self.__leftSideBarMenu.addSeparator()
        self.__hideLeftSideBarAct = self.__leftSideBarMenu.addAction(
            getIcon(""), '&Hide left sidebar', self.__leftSideBar.shrink)
        self.__viewMenu.addMenu(self.__leftSideBarMenu)

        self.__rightSideBarMenu = QMenu("&Right sidebar", self)
        self.__rightSideBarMenu.triggered.connect(self.__activateSideTab)
        self.__outlineBarAct = self.__rightSideBarMenu.addAction(
            getIcon('filepython.png'), 'Activate &outline tab')
        self.__outlineBarAct.setData('fileoutline')
        self.__debugBarAct = self.__rightSideBarMenu.addAction(
            getIcon(''), 'Activate &debug tab')
        self.__debugBarAct.setData('debugger')
        self.__excptBarAct = self.__rightSideBarMenu.addAction(
            getIcon(''), 'Activate &exceptions tab')
        self.__excptBarAct.setData('excptions')
        self.__bpointBarAct = self.__rightSideBarMenu.addAction(
            getIcon(''), 'Activate &breakpoints tab')
        self.__bpointBarAct.setData('breakpoints')
        self.__rightSideBarMenu.addSeparator()
        self.__hideRightSideBarAct = self.__rightSideBarMenu.addAction(
            getIcon(""), '&Hide right sidebar', self.__rightSideBar.shrink)
        self.__viewMenu.addMenu(self.__rightSideBarMenu)

        self.__bottomSideBarMenu = QMenu("&Bottom sidebar", self)
        self.__bottomSideBarMenu.triggered.connect(self.__activateSideTab)
        self.__logBarAct = self.__bottomSideBarMenu.addAction(
            getIcon('logviewer.png'), 'Activate &log tab')
        self.__logBarAct.setData('log')
        self.__searchBarAct = self.__bottomSideBarMenu.addAction(
            getIcon('findindir.png'), 'Activate &search tab')
        self.__searchBarAct.setData('search')
        self.__contextHelpBarAct = self.__bottomSideBarMenu.addAction(
            getIcon('helpviewer.png'), 'Activate context &help tab')
        self.__contextHelpBarAct.setData('contexthelp')
        self.__diffBarAct = self.__bottomSideBarMenu.addAction(
            getIcon('diffviewer.png'), 'Activate &diff tab')
        self.__diffBarAct.setData('diff')
        self.__bottomSideBarMenu.addSeparator()
        self.__hideBottomSideBarAct = self.__bottomSideBarMenu.addAction(
            getIcon(""), '&Hide bottom sidebar', self.__bottomSideBar.shrink)
        self.__viewMenu.addMenu(self.__bottomSideBarMenu)
        self.__viewMenu.addSeparator()
        self.__zoomInAct = self.__viewMenu.addAction(
            getIcon('zoomin.png'), 'Zoom &in', self.__onZoomIn)
        self.__zoomOutAct = self.__viewMenu.addAction(
            getIcon('zoomout.png'), 'Zoom &out', self.__onZoomOut)
        self.__zoom11Act = self.__viewMenu.addAction(
            getIcon('zoomreset.png'), 'Zoom r&eset', self.__onZoomReset)

        # Options menu
        self.__optionsMenu = QMenu("Optio&ns", self)
        self.__optionsMenu.aboutToShow.connect(self.__optionsAboutToShow)

        self.__ideTemplateMenu = QMenu("IDE-wide &template", self)
        self.__ideCreateTemplateAct = self.__ideTemplateMenu.addAction(
            getIcon('generate.png'), '&Create')
        self.__ideCreateTemplateAct.triggered.connect(
            self.__onCreateIDETemplate)
        self.__ideEditTemplateAct = self.__ideTemplateMenu.addAction(
            getIcon('edit.png'), '&Edit')
        self.__ideEditTemplateAct.triggered.connect(self.__onEditIDETemplate)
        self.__ideTemplateMenu.addSeparator()
        self.__ideDelTemplateAct = self.__ideTemplateMenu.addAction(
            getIcon('trash.png'), '&Delete')
        self.__ideDelTemplateAct.triggered.connect(self.__onDelIDETemplate)
        self.__optionsMenu.addMenu(self.__ideTemplateMenu)

        self.__optionsMenu.addSeparator()

        verticalEdgeAct = self.__optionsMenu.addAction('Show vertical edge')
        verticalEdgeAct.setCheckable(True)
        verticalEdgeAct.setChecked(self.settings['verticalEdge'])
        verticalEdgeAct.changed.connect(self.__verticalEdgeChanged)
        showSpacesAct = self.__optionsMenu.addAction('Show whitespaces')
        showSpacesAct.setCheckable(True)
        showSpacesAct.setChecked(self.settings['showSpaces'])
        showSpacesAct.changed.connect(self.__showSpacesChanged)
        lineWrapAct = self.__optionsMenu.addAction('Wrap long lines')
        lineWrapAct.setCheckable(True)
        lineWrapAct.setChecked(self.settings['lineWrap'])
        lineWrapAct.changed.connect(self.__lineWrapChanged)
        showEOLAct = self.__optionsMenu.addAction('Show EOL')
        showEOLAct.setCheckable(True)
        showEOLAct.setChecked(self.settings['showEOL'])
        showEOLAct.changed.connect(self.__showEOLChanged)
        showBraceMatchAct = self.__optionsMenu.addAction(
            'Show brace matching')
        showBraceMatchAct.setCheckable(True)
        showBraceMatchAct.setChecked(self.settings['showBraceMatch'])
        showBraceMatchAct.changed.connect(self.__showBraceMatchChanged)
        autoIndentAct = self.__optionsMenu.addAction('Auto indent')
        autoIndentAct.setCheckable(True)
        autoIndentAct.setChecked(self.settings['autoIndent'])
        autoIndentAct.changed.connect(self.__autoIndentChanged)
        backspaceUnindentAct = self.__optionsMenu.addAction(
            'Backspace unindent')
        backspaceUnindentAct.setCheckable(True)
        backspaceUnindentAct.setChecked(self.settings['backspaceUnindent'])
        backspaceUnindentAct.changed.connect(self.__backspaceUnindentChanged)
        tabIndentsAct = self.__optionsMenu.addAction('TAB indents')
        tabIndentsAct.setCheckable(True)
        tabIndentsAct.setChecked(self.settings['tabIndents'])
        tabIndentsAct.changed.connect(self.__tabIndentsChanged)
        indentationGuidesAct = self.__optionsMenu.addAction(
            'Show indentation guides')
        indentationGuidesAct.setCheckable(True)
        indentationGuidesAct.setChecked(self.settings['indentationGuides'])
        indentationGuidesAct.changed.connect(self.__indentationGuidesChanged)
        currentLineVisibleAct = self.__optionsMenu.addAction(
            'Highlight current line')
        currentLineVisibleAct.setCheckable(True)
        currentLineVisibleAct.setChecked(self.settings['currentLineVisible'])
        currentLineVisibleAct.changed.connect(self.__currentLineVisibleChanged)
        jumpToFirstNonSpaceAct = self.__optionsMenu.addAction(
            'HOME to first non-space')
        jumpToFirstNonSpaceAct.setCheckable(True)
        jumpToFirstNonSpaceAct.setChecked(self.settings['jumpToFirstNonSpace'])
        jumpToFirstNonSpaceAct.changed.connect(
            self.__homeToFirstNonSpaceChanged)
        removeTrailingOnSpaceAct = self.__optionsMenu.addAction(
            'Auto remove trailing spaces on save')
        removeTrailingOnSpaceAct.setCheckable(True)
        removeTrailingOnSpaceAct.setChecked(
            self.settings['removeTrailingOnSave'])
        removeTrailingOnSpaceAct.changed.connect(self.__removeTrailingChanged)
        editorCalltipsAct = self.__optionsMenu.addAction('Editor calltips')
        editorCalltipsAct.setCheckable(True)
        editorCalltipsAct.setChecked(self.settings['editorCalltips'])
        editorCalltipsAct.changed.connect(self.__editorCalltipsChanged)
        clearDebugIOAct = self.__optionsMenu.addAction(
            'Clear debug IO console on new session')
        clearDebugIOAct.setCheckable(True)
        clearDebugIOAct.setChecked(self.settings['clearDebugIO'])
        clearDebugIOAct.changed.connect(self.__clearDebugIOChanged)
        showNavBarAct = self.__optionsMenu.addAction('Show navigation bar')
        showNavBarAct.setCheckable(True)
        showNavBarAct.setChecked(self.settings['showNavigationBar'])
        showNavBarAct.changed.connect(self.__showNavBarChanged)
        showCFNavBarAct = self.__optionsMenu.addAction(
            'Show control flow navigation bar')
        showCFNavBarAct.setCheckable(True)
        showCFNavBarAct.setChecked(self.settings['showCFNavigationBar'])
        showCFNavBarAct.changed.connect(self.__showCFNavBarChanged)
        showMainToolBarAct = self.__optionsMenu.addAction('Show main toolbar')
        showMainToolBarAct.setCheckable(True)
        showMainToolBarAct.setChecked(self.settings['showMainToolBar'])
        showMainToolBarAct.changed.connect(self.__showMainToolbarChanged)
        self.__optionsMenu.addSeparator()
        tooltipsMenu = self.__optionsMenu.addMenu("Tooltips")
        projectTooltipsAct = tooltipsMenu.addAction("&Project tab")
        projectTooltipsAct.setCheckable(True)
        projectTooltipsAct.setChecked(self.settings['projectTooltips'])
        projectTooltipsAct.changed.connect(self.__projectTooltipsChanged)
        recentTooltipsAct = tooltipsMenu.addAction("&Recent tab")
        recentTooltipsAct.setCheckable(True)
        recentTooltipsAct.setChecked(self.settings['recentTooltips'])
        recentTooltipsAct.changed.connect(self.__recentTooltipsChanged)
        classesTooltipsAct = tooltipsMenu.addAction("&Classes tab")
        classesTooltipsAct.setCheckable(True)
        classesTooltipsAct.setChecked(self.settings['classesTooltips'])
        classesTooltipsAct.changed.connect(self.__classesTooltipsChanged)
        functionsTooltipsAct = tooltipsMenu.addAction("&Functions tab")
        functionsTooltipsAct.setCheckable(True)
        functionsTooltipsAct.setChecked(self.settings['functionsTooltips'])
        functionsTooltipsAct.changed.connect(self.__functionsTooltipsChanged)
        outlineTooltipsAct = tooltipsMenu.addAction("&Outline tab")
        outlineTooltipsAct.setCheckable(True)
        outlineTooltipsAct.setChecked(self.settings['outlineTooltips'])
        outlineTooltipsAct.changed.connect(self.__outlineTooltipsChanged)
        findNameTooltipsAct = tooltipsMenu.addAction("Find &name dialog")
        findNameTooltipsAct.setCheckable(True)
        findNameTooltipsAct.setChecked(self.settings['findNameTooltips'])
        findNameTooltipsAct.changed.connect(self.__findNameTooltipsChanged)
        findFileTooltipsAct = tooltipsMenu.addAction("Find fi&le dialog")
        findFileTooltipsAct.setCheckable(True)
        findFileTooltipsAct.setChecked(self.settings['findFileTooltips'])
        findFileTooltipsAct.changed.connect(self.__findFileTooltipsChanged)
        editorTooltipsAct = tooltipsMenu.addAction("&Editor tabs")
        editorTooltipsAct.setCheckable(True)
        editorTooltipsAct.setChecked(self.settings['editorTooltips'])
        editorTooltipsAct.changed.connect(self.__editorTooltipsChanged)

        openTabsMenu = self.__optionsMenu.addMenu("Open tabs button")
        self.__navigationSortGroup = QActionGroup(self)
        self.__alphasort = openTabsMenu.addAction("Sort alphabetically")
        self.__alphasort.setCheckable(True)
        self.__alphasort.setData(-1)
        self.__alphasort.setActionGroup(self.__navigationSortGroup)
        self.__tabsort = openTabsMenu.addAction("Tab order sort")
        self.__tabsort.setCheckable(True)
        self.__tabsort.setData(-2)
        self.__tabsort.setActionGroup(self.__navigationSortGroup)
        if self.settings['tablistsortalpha']:
            self.__alphasort.setChecked(True)
        else:
            self.__tabsort.setChecked(True)
        openTabsMenu.addSeparator()
        tabOrderPreservedAct = openTabsMenu.addAction(
            "Tab order preserved on selection")
        tabOrderPreservedAct.setCheckable(True)
        tabOrderPreservedAct.setData(0)
        tabOrderPreservedAct.setChecked(self.settings['taborderpreserved'])
        tabOrderPreservedAct.changed.connect(self.__tabOrderPreservedChanged)
        openTabsMenu.triggered.connect(self.__openTabsMenuTriggered)

        self.__optionsMenu.addSeparator()
        themesMenu = self.__optionsMenu.addMenu("Themes")
        availableThemes = self.__buildThemesList()
        for theme in availableThemes:
            themeAct = themesMenu.addAction(theme[1])
            themeAct.setData(theme[0])
            if theme[0] == self.settings['skin']:
                font = themeAct.font()
                font.setBold(True)
                themeAct.setFont(font)
        themesMenu.triggered.connect(self.__onTheme)

        styleMenu = self.__optionsMenu.addMenu("Styles")
        availableStyles = QStyleFactory.keys()
        self.__styles = []
        for style in availableStyles:
            styleAct = styleMenu.addAction(style)
            styleAct.setData(style)
            self.__styles.append((str(style), styleAct))
        styleMenu.triggered.connect(self.__onStyle)
        styleMenu.aboutToShow.connect(self.__styleAboutToShow)

        fontFaceMenu = self.__optionsMenu.addMenu("Mono font face")
        for fontFace in getMonospaceFontList():
            faceAct = fontFaceMenu.addAction(fontFace)
            faceAct.setData(fontFace)
            f = faceAct.font()
            f.setFamily(fontFace)
            faceAct.setFont(f)
        fontFaceMenu.triggered.connect(self.__onMonoFont)

        # The plugins menu
        self.__pluginsMenu = QMenu("P&lugins", self)
        self.__recomposePluginMenu()

        # The Help menu
        self.__helpMenu = QMenu("&Help", self)
        self.__helpMenu.aboutToShow.connect(self.__helpAboutToShow)
        self.__helpMenu.aboutToHide.connect(self.__helpAboutToHide)
        self.__shortcutsAct = self.__helpMenu.addAction(
            getIcon('shortcutsmenu.png'),
            '&Major shortcuts', editorsManager.onHelp, 'F1')
        self.__contextHelpAct = self.__helpMenu.addAction(
            getIcon('helpviewer.png'),
            'Current &word help', self.__onContextHelp)
        self.__callHelpAct = self.__helpMenu.addAction(
            getIcon('helpviewer.png'),
            '&Current call help', self.__onCallHelp)
        self.__helpMenu.addSeparator()
        self.__allShotcutsAct = self.__helpMenu.addAction(
            getIcon('allshortcutsmenu.png'),
            '&All shortcuts (web page)', self.__onAllShortcurs)
        self.__homePageAct = self.__helpMenu.addAction(
            getIcon('homepagemenu.png'),
            'Codimension &home page', self.__onHomePage)
        self.__helpMenu.addSeparator()
        self.__aboutAct = self.__helpMenu.addAction(
            getIcon("logo.png"),
            "A&bout codimension", self.__onAbout)

        menuBar = self.menuBar()
        menuBar.addMenu(self.__projectMenu)
        menuBar.addMenu(self.__tabMenu)
        menuBar.addMenu(self.__editMenu)
        menuBar.addMenu(self.__searchMenu)
        menuBar.addMenu(self.__runMenu)
        menuBar.addMenu(self.__debugMenu)
        menuBar.addMenu(self.__toolsMenu)
        menuBar.addMenu(self.__diagramsMenu)
        menuBar.addMenu(self.__viewMenu)
        menuBar.addMenu(self.__optionsMenu)
        menuBar.addMenu(self.__pluginsMenu)
        menuBar.addMenu(self.__helpMenu)

    def __createToolBar(self):
        """creates the buttons bar"""
        # Imports diagram button and its menu
        importsMenu = QMenu(self)
        importsDlgAct = importsMenu.addAction(
            getIcon('detailsdlg.png'), 'Fine tuned imports diagram')
        importsDlgAct.triggered.connect(self.__onImportDgmTuned)
        self.importsDiagramButton = QToolButton(self)
        self.importsDiagramButton.setIcon(getIcon('importsdiagram.png'))
        self.importsDiagramButton.setToolTip('Generate imports diagram')
        self.importsDiagramButton.setPopupMode(QToolButton.DelayedPopup)
        self.importsDiagramButton.setMenu(importsMenu)
        self.importsDiagramButton.setFocusPolicy(Qt.NoFocus)
        self.importsDiagramButton.clicked.connect(self.__onImportDgm)

        # Run project button and its menu
        runProjectMenu = QMenu(self)
        runProjectAct = runProjectMenu.addAction(
            getIcon('detailsdlg.png'), 'Set run parameters')
        runProjectAct.triggered.connect(self.__onRunProjectSettings)
        self.runProjectButton = QToolButton(self)
        self.runProjectButton.setIcon(getIcon('run.png'))
        self.runProjectButton.setToolTip('Project is not loaded')
        self.runProjectButton.setPopupMode(QToolButton.DelayedPopup)
        self.runProjectButton.setMenu(runProjectMenu)
        self.runProjectButton.setFocusPolicy(Qt.NoFocus)
        self.runProjectButton.clicked.connect(self.__onRunProject)

        # profile project button and its menu
        profileProjectMenu = QMenu(self)
        profileProjectAct = profileProjectMenu.addAction(
            getIcon('detailsdlg.png'), 'Set profile parameters')
        profileProjectAct.triggered.connect(self.__onProfileProjectSettings)
        self.profileProjectButton = QToolButton(self)
        self.profileProjectButton.setIcon(getIcon('profile.png'))
        self.profileProjectButton.setToolTip('Project is not loaded')
        self.profileProjectButton.setPopupMode(QToolButton.DelayedPopup)
        self.profileProjectButton.setMenu(profileProjectMenu)
        self.profileProjectButton.setFocusPolicy(Qt.NoFocus)
        self.profileProjectButton.clicked.connect(self.__onProfileProject)

        # Debug project button and its menu
        debugProjectMenu = QMenu(self)
        debugProjectAct = debugProjectMenu.addAction(
            getIcon('detailsdlg.png'), 'Set debug parameters')
        debugProjectAct.triggered.connect(self.__onDebugProjectSettings)
        self.debugProjectButton = QToolButton(self)
        self.debugProjectButton.setIcon(getIcon('debugger.png'))
        self.debugProjectButton.setToolTip('Project is not loaded')
        self.debugProjectButton.setPopupMode(QToolButton.DelayedPopup)
        self.debugProjectButton.setMenu(debugProjectMenu)
        self.debugProjectButton.setFocusPolicy(Qt.NoFocus)
        self.debugProjectButton.clicked.connect(self.__onDebugProject)
        self.debugProjectButton.setVisible(True)

        packageDiagramButton = QAction(
            getIcon('packagediagram.png'), 'Generate package diagram', self)
        packageDiagramButton.setEnabled(False)
        packageDiagramButton.setVisible(False)
        applicationDiagramButton = QAction(
            getIcon('applicationdiagram.png'), 'Generate application diagram',
            self)
        applicationDiagramButton.setEnabled(False)
        applicationDiagramButton.setVisible(False)
        neverUsedButton = QAction(
            getIcon('neverused.png'),
            'Analysis for never used variables, functions, classes', self)
        neverUsedButton.setEnabled(False)
        neverUsedButton.setVisible(False)

        self.linecounterButton = QAction(getIcon('linecounter.png'),
                                         'Project line counter', self)
        self.linecounterButton.triggered.connect(self.linecounterButtonClicked)
        self.__findInFilesButton = QAction(
            getIcon('findindir.png'), 'Find in files (Ctrl+Shift+F)', self)
        self.__findInFilesButton.triggered.connect(self.findInFilesClicked)
        self.__findNameButton = QAction(
            getIcon('findname.png'), 'Find name in project (Alt+Shift+S)',
            self)
        self.__findNameButton.triggered.connect(self.findNameClicked)
        self.__findFileButton = QAction(
            getIcon('findfile.png'), 'Find project file (Alt+Shift+O)', self)
        self.__findFileButton.triggered.connect(self.findFileClicked)

        # Debugger buttons
        self.__dbgStopBrutal = QAction(
            getIcon('dbgstopbrutal.png'), 'Stop debugging session and '
            'kill console (Ctrl+F10)', self)
        self.__dbgStopBrutal.triggered.connect(self.__onBrutalStopDbgSession)
        self.__dbgStopBrutal.setVisible(False)
        self.__dbgStopAndClearIO = QAction(
            getIcon('dbgstopcleario.png'),
            'Stop debugging session and clear IO console', self)
        self.__dbgStopAndClearIO.triggered.connect(
            self.__onBrutalStopDbgSession)
        self.__dbgStopAndClearIO.setVisible(False)
        self.__dbgStop = QAction(
            getIcon('dbgstop.png'),
            'Stop debugging session and keep console if so (F10)', self)
        self.__dbgStop.triggered.connect(self.__onStopDbgSession)
        self.__dbgStop.setVisible(False)
        self.__dbgRestart = QAction(
            getIcon('dbgrestart.png'), 'Restart debugging section (F4)', self)
        self.__dbgRestart.triggered.connect(self.__onRestartDbgSession)
        self.__dbgRestart.setVisible(False)
        self.__dbgGo = QAction(getIcon('dbggo.png'), 'Continue (F6)', self)
        self.__dbgGo.triggered.connect(self.__onDbgGo)
        self.__dbgGo.setVisible(False)
        self.__dbgNext = QAction(
            getIcon('dbgnext.png'), 'Step over (F8)', self)
        self.__dbgNext.triggered.connect(self.__onDbgNext)
        self.__dbgNext.setVisible(False)
        self.__dbgStepInto = QAction(
            getIcon('dbgstepinto.png'), 'Step into (F7)', self)
        self.__dbgStepInto.triggered.connect(self.__onDbgStepInto)
        self.__dbgStepInto.setVisible(False)
        self.__dbgRunToLine = QAction(
            getIcon('dbgruntoline.png'), 'Run to cursor (Shift+F6)', self)
        self.__dbgRunToLine.triggered.connect(self.__onDbgRunToLine)
        self.__dbgRunToLine.setVisible(False)
        self.__dbgReturn = QAction(
            getIcon('dbgreturn.png'), 'Step out (F9)', self)
        self.__dbgReturn.triggered.connect(self.__onDbgReturn)
        self.__dbgReturn.setVisible(False)
        self.__dbgJumpToCurrent = QAction(
            getIcon('dbgtocurrent.png'),
            'Show current debugger line (Ctrl+W)', self)
        self.__dbgJumpToCurrent.triggered.connect(self.__onDbgJumpToCurrent)
        self.__dbgJumpToCurrent.setVisible(False)

        dumpDebugSettingsMenu = QMenu(self)
        dumpDebugSettingsAct = dumpDebugSettingsMenu.addAction(
            getIcon('detailsdlg.png'),
            'Dump settings with complete environment')
        dumpDebugSettingsAct.triggered.connect(self.__onDumpFullDebugSettings)
        self.__dbgDumpSettingsButton = QToolButton(self)
        self.__dbgDumpSettingsButton.setIcon(getIcon('dbgsettings.png'))
        self.__dbgDumpSettingsButton.setToolTip('Dump debug session settings')
        self.__dbgDumpSettingsButton.setPopupMode(QToolButton.DelayedPopup)
        self.__dbgDumpSettingsButton.setMenu(dumpDebugSettingsMenu)
        self.__dbgDumpSettingsButton.setFocusPolicy(Qt.NoFocus)
        self.__dbgDumpSettingsButton.clicked.connect(
            self.__onDumpDebugSettings)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.__toolbar = QToolBar()
        self.__toolbar.setMovable(False)
        self.__toolbar.setAllowedAreas(Qt.TopToolBarArea)
        self.__toolbar.setIconSize(QSize(26, 26))
        self.__toolbar.addAction(packageDiagramButton)
        self.__toolbar.addWidget(self.importsDiagramButton)
        self.__toolbar.addSeparator()
        self.__toolbar.addWidget(self.runProjectButton)
        self.__toolbar.addWidget(self.debugProjectButton)
        self.__toolbar.addWidget(self.profileProjectButton)
        self.__toolbar.addAction(applicationDiagramButton)
        self.__toolbar.addSeparator()
        self.__toolbar.addAction(neverUsedButton)
        self.__toolbar.addAction(self.linecounterButton)
        self.__toolbar.addSeparator()
        self.__toolbar.addAction(self.__findInFilesButton)
        self.__toolbar.addAction(self.__findNameButton)
        self.__toolbar.addAction(self.__findFileButton)

        # Debugger part begin
        dbgSpacer = QWidget()
        dbgSpacer.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        dbgSpacer.setFixedWidth(40)
        self.__toolbar.addWidget(dbgSpacer)
        self.__toolbar.addAction(self.__dbgStopBrutal)
        self.__toolbar.addAction(self.__dbgStopAndClearIO)
        self.__toolbar.addAction(self.__dbgStop)
        self.__toolbar.addAction(self.__dbgRestart)
        self.__toolbar.addAction(self.__dbgGo)
        self.__toolbar.addAction(self.__dbgStepInto)
        self.__toolbar.addAction(self.__dbgNext)
        self.__toolbar.addAction(self.__dbgRunToLine)
        self.__toolbar.addAction(self.__dbgReturn)
        self.__toolbar.addAction(self.__dbgJumpToCurrent)
        self.__dbgDumpSettingsAct = self.__toolbar.addWidget(
            self.__dbgDumpSettingsButton)

        # Heck! The only QAction can be hidden
        self.__dbgDumpSettingsAct.setVisible(False)
        # Debugger part end

        self.__toolbar.setVisible(False)
        self.addToolBar(self.__toolbar)

    def getToolbar(self):
        """Provides the top toolbar reference"""
        return self.__toolbar

    def __guessMaximized(self):
        """True if the window is maximized"""
        # Ugly but I don't see any better way.
        # It is impossible to catch the case when the main window is maximized.
        # Especially when networked XServer is used (like xming)
        # So, make a wild guess instead and do not save the status is
        # maximized.
        availGeom = GlobalData().application.desktop().availableGeometry()
        if self.width() + abs(self.settings['xdelta']) > availGeom.width() or \
           self.height() + abs(self.settings['ydelta']) > availGeom.height():
            return True
        return False

    def resizeEvent(self, resizeEv):
        """Triggered when the window is resized"""
        QTimer.singleShot(1, self.__resizeEventdelayed)

    def __resizeEventdelayed(self):
        """Memorizes the new window size"""
        if self.__initialisation:
            return
        if self.__guessMaximized():
            return

        self.settings['width'] = self.width()
        self.settings['height'] = self.height()
        self.vSplitterMoved(0, 0)
        self.hSplitterMoved(0, 0)

    def moveEvent(self, moveEv):
        """Triggered when the window is moved"""
        QTimer.singleShot(1, self.__moveEventDelayed)

    def __moveEventDelayed(self):
        """Memorizes the new window position"""
        if not self.__initialisation and not self.__guessMaximized():
            self.settings['xpos'] = self.x()
            self.settings['ypos'] = self.y()

    def onProjectChanged(self, what):
        """Slot to receive sigProjectChanged signal"""
        if what == CodimensionProject.CompleteProject:
            self.closeAllIOConsoles()
            self.updateToolbarStatus()
            self.updateWindowTitle()

            projectLoaded = GlobalData().project.isLoaded()
            self.__unloadProjectAct.setEnabled(projectLoaded)
            self.__projectPropsAct.setEnabled(projectLoaded)
            self.__prjTemplateMenu.setEnabled(projectLoaded)
            self.__findNameMenuAct.setEnabled(projectLoaded)
            self.__fileProjectFileAct.setEnabled(projectLoaded)
            self.__prjLineCounterAct.setEnabled(projectLoaded)
            self.__prjImportDgmAct.setEnabled(projectLoaded)
            self.__prjImportsDgmDlgAct.setEnabled(projectLoaded)

            self.settings['projectLoaded'] = projectLoaded
            if projectLoaded:
                # The editor tabs must be loaded after a VCS plugin has a
                # chance to receive sigProjectChanged signal where it reads
                # the plugin configuration
                QTimer.singleShot(1, self.__delayedEditorsTabRestore)
        self.updateRunDebugButtons()

    def __delayedEditorsTabRestore(self):
        """Delayed restore editor tabs"""
        editorsManager = self.editorsManagerWidget.editorsManager
        editorsManager.restoreTabs(GlobalData().project.tabStatus)

    def updateWindowTitle(self):
        """Updates the main window title with the current so file"""
        if GlobalData().project.isLoaded():
            self.setWindowTitle('Codimension for Python 3: ' +
                                os.path.basename(
                                   GlobalData().project.fileName))
        else:
            self.setWindowTitle(
                'Codimension for Python 3: no project selected')

    def updateToolbarStatus(self):
        " Enables/disables the toolbar buttons "
        projectLoaded = GlobalData().project.isLoaded()
        self.linecounterButton.setEnabled(projectLoaded)
        self.importsDiagramButton.setEnabled(projectLoaded and
                                             GlobalData().graphvizAvailable)
        self.__findNameButton.setEnabled(projectLoaded)
        self.__findFileButton.setEnabled(projectLoaded)

    def updateRunDebugButtons(self):
        """Updates the run/debug buttons statuses"""
        if self.debugMode:
            self.runProjectButton.setEnabled(False)
            self.runProjectButton.setToolTip("Cannot run project - "
                                             "debug in progress")
            self.debugProjectButton.setEnabled(False)
            self.debugProjectButton.setToolTip("Cannot debug project - "
                                               "debug in progress")
            self.__prjDebugAct.setEnabled(False)
            self.__prjDebugDlgAct.setEnabled(False)
            self.__tabDebugAct.setEnabled(False)
            self.__tabDebugDlgAct.setEnabled(False)
            self.profileProjectButton.setEnabled(False)
            self.profileProjectButton.setToolTip("Cannot profile project - "
                                                 "debug in progress")
            return

        if not GlobalData().project.isLoaded():
            self.runProjectButton.setEnabled(False)
            self.runProjectButton.setToolTip("Run project")
            self.debugProjectButton.setEnabled(False)
            self.debugProjectButton.setToolTip("Debug project")
            self.__prjDebugAct.setEnabled(False)
            self.__prjDebugDlgAct.setEnabled(False)
            self.profileProjectButton.setEnabled(False)
            self.profileProjectButton.setToolTip("Profile project")
            return

        if not GlobalData().isProjectScriptValid():
            self.runProjectButton.setEnabled(False)
            self.runProjectButton.setToolTip(
                "Cannot run project - script is not specified or invalid")
            self.debugProjectButton.setEnabled(False)
            self.debugProjectButton.setToolTip(
                "Cannot debug project - script is not specified or invalid")
            self.__prjDebugAct.setEnabled(False)
            self.__prjDebugDlgAct.setEnabled(False)
            self.profileProjectButton.setEnabled(False)
            self.profileProjectButton.setToolTip(
                "Cannot profile project - script is not specified or invalid")
            return

        self.runProjectButton.setEnabled(True)
        self.runProjectButton.setToolTip("Run project")
        self.debugProjectButton.setEnabled(True)
        self.debugProjectButton.setToolTip("Debug project")
        self.__prjDebugAct.setEnabled(True)
        self.__prjDebugDlgAct.setEnabled(True)
        self.profileProjectButton.setEnabled(True)
        self.profileProjectButton.setToolTip("Profile project")

    @staticmethod
    def linecounterButtonClicked():
        """Triggered when the line counter button is clicked"""
        LineCounterDialog().exec_()

    def findInFilesClicked(self):
        """Triggered when the find in files button is clicked"""
        searchText = ""
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        if currentWidget.getType() in \
           [MainWindowTabWidgetBase.PlainTextEditor]:
            searchText = currentWidget.getEditor().getSearchText()

        dlg = FindInFilesDialog(FindInFilesDialog.inProject, searchText,
                                "", [], self)
        dlg.exec_()
        if dlg.searchResults:
            self.displayFindInFiles(dlg.searchRegexp, dlg.searchResults)

    def toStdout(self, txt):
        """Triggered when a new message comes"""
        self.showLogTab()
        self.logViewer.append(str(txt))

    def toStderr(self, txt):
        """Triggered when a new message comes"""
        self.showLogTab()
        self.logViewer.appendError(str(txt))

    def showLogTab(self):
        """Makes sure that the log tab is visible"""
        self.__activateSideTab('log')

    def openFile(self, path, lineNo, pos=0):
        """User double clicked on a file or an item in a file"""
        self.editorsManagerWidget.editorsManager.openFile(path, lineNo, pos)

    def gotoInBuffer(self, uuid, lineNo):
        """Usually needs when an item is clicked in the file outline browser"""
        self.editorsManagerWidget.editorsManager.gotoInBuffer(uuid, lineNo)

    def jumpToLine(self, lineNo):
        """Usually needs when rope provided definition
           in the current unsaved buffer
        """
        self.editorsManagerWidget.editorsManager.jumpToLine(lineNo)

    def openPixmapFile(self, path):
        """User double clicked on a file"""
        self.editorsManagerWidget.editorsManager.openPixmapFile(path)

    def openDiagram(self, scene, tooltip):
        """Show a generated diagram"""
        self.editorsManagerWidget.editorsManager.openDiagram(scene, tooltip)

    def detectTypeAndOpenFile(self, path, lineNo=-1):
        """Detects the file type and opens the corresponding editor / browser"""
        self.openFileByType(detectFileType(path), path, lineNo)

    def openFileByType(self, mime, path, lineNo=-1):
        """Opens editor/browser suitable for the file type"""
        path = os.path.abspath(path)
        if not os.path.exists(path):
            logging.error("Cannot open " + path + ", does not exist")
            return
        if os.path.islink(path):
            path = os.path.realpath(path)
            if not os.path.exists(path):
                logging.error("Cannot open " + path + ", does not exist")
                return
            # The type may differ...
            mime, _, _ = getFileProperties(path)
        else:
            # The intermediate directory could be a link, so use the real path
            path = os.path.realpath(path)

        if not os.access(path, os.R_OK):
            logging.error("No read permissions to open " + path)
            return

        if not os.path.isfile(path):
            logging.error(path + " is not a file")
            return

        if isImageViewable(mime):
            self.openPixmapFile(path)
            return
        if not isFileSearchable(path):
            logging.error("Cannot open non-text file for editing")
            return

        self.openFile(path, lineNo)

    def __createNewProject(self):
        """Create new action"""
        editorsManager = self.editorsManagerWidget.editorsManager
        if not editorsManager.closeRequest():
            return

        dialog = ProjectPropertiesDialog(None, self)
        if dialog.exec_() != QDialog.Accepted:
            return

        # Request accepted
        baseDir = os.path.dirname(dialog.absProjectFileName) + os.path.sep
        importDirs = []
        index = 0
        while index < dialog.importDirList.count():
            dirName = dialog.importDirList.item(index).text()
            if dirName.startswith(baseDir):
                # Replace paths with relative if needed
                dirName = dirName[len(baseDir):]
                if dirName == "":
                    dirName = "."
            importDirs.append(dirName)
            index += 1

        QApplication.processEvents()
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))

        prj = GlobalData().project
        prj.tabxsStatus = editorsManager.getTabsStatus()
        editorsManager.closeAll()

        GlobalData().project.createNew(
            dialog.absProjectFileName,
            {'scriptname': dialog.scriptEdit.text().strip(),
             'creationdate': dialog.creationDateEdit.text().strip(),
             'author': dialog.authorEdit.text().strip(),
             'license': dialog.licenseEdit.text().strip(),
             'copyright': dialog.copyrightEdit.text().strip(),
             'version': dialog.versionEdit.text().strip(),
             'email': dialog.emailEdit.text().strip(),
             'description': dialog.descriptionEdit.toPlainText().strip(),
             'encoding': dialog.encodingCombo.currentText().strip(),
             'importdirs': importDirs})

        QApplication.restoreOverrideCursor()
        self.settings.addRecentProject(dialog.absProjectFileName)

    def notImplementedYet(self):
        """Shows a dummy window"""
        QMessageBox.about(self, 'Not implemented yet',
                          'This function has not been implemented yet')

    def closeEvent(self, event):
        """Triggered when the IDE is closed"""
        # Save the side bars status
        self.settings['vSplitterSizes'] = self.__verticalSplitterSizes
        self.settings['hSplitterSizes'] = self.__horizontalSplitterSizes
        self.settings['bottomBarMinimized'] = self.__bottomSideBar.isMinimized()
        self.settings['leftBarMinimized'] = self.__leftSideBar.isMinimized()
        self.settings['rightBarMinimized'] = self.__rightSideBar.isMinimized()

        # Ask the editors manager to close all the editors
        editorsManager = self.editorsManagerWidget.editorsManager
        if editorsManager.getUnsavedCount() == 0:
            project = GlobalData().project
            if project.isLoaded():
                project.tabsStatus = editorsManager.getTabsStatus()
                self.settings.tabsStatus = []
            else:
                self.settings.tabsStatus = editorsManager.getTabsStatus()

        if editorsManager.closeEvent(event):
            # The IDE is going to be closed just now
            if self.debugMode:
                self.__onBrutalStopDbgSession()

            project = GlobalData().project
            project.fsBrowserExpandedDirs = self.getProjectExpandedPaths()
            project.unloadProject(False)

            # Stop the VCS manager threads
            self.vcsManager.dismissAllPlugins()

            # Kill all the non-detached processes
            self.__runManager.killAll()

            # On ubuntu codimension produces core dumps coming from QT when:
            # - a new project is created
            # - the IDE is closed via Alt+F4
            # It seems that python GC conflicts with QT at finishing. Explicit
            # call of GC resolves the problem.
            while gc.collect():
                pass

    def dismissVCSPlugin(self, plugin):
        """Dismisses the given VCS plugin"""
        self.vcsManager.dismissPlugin(plugin)

    def getProjectExpandedPaths(self):
        """Provides a list of expanded project directories"""
        project = GlobalData().project
        if project.isLoaded():
            return self.projectViewer.projectTreeView.getExpanded()
        return []

    def __calltipDisplayable(self, calltip):
        """True if calltip is displayable"""
        if calltip is None:
            return False
        if calltip.strip() == "":
            return False
        return True

    def __docstringDisplayable(self, docstring):
        """True if docstring is displayable"""
        if docstring is None:
            return False
        if isinstance(docstring, dict):
            if docstring["docstring"].strip() == "":
                return False
            return True
        if docstring.strip() == "":
            return False
        return True

    def showTagHelp(self, calltip, docstring):
        """Shows a tag help"""
        if not self.__calltipDisplayable(calltip) and \
           not self.__docstringDisplayable(docstring):
            return

        self.__bottomSideBar.show()
        self.__bottomSideBar.setCurrentTab('contexthelp')
        self.__bottomSideBar.raise_()

        self.tagHelpViewer.display(calltip, docstring)

    def showDiff(self, diff, tooltip):
        """Shows the diff"""
        self.__bottomSideBar.show()
        self.__bottomSideBar.setCurrentTab('diff')
        self.__bottomSideBar.raise_()

        try:
            self.__bottomSideBar.setTabToolTip('diff', tooltip)
            self.diffViewer.setHTML(parse_from_memory(diff, False, True),
                                    tooltip)
        except Exception as exc:
            logging.error("Error showing diff: " + str(exc))

    def showDiffInMainArea(self, content, tooltip):
        """Shows the given diff in the main editing area"""
        self.editorsManagerWidget.editorsManager.showDiff(content, tooltip)

    def zoomDiff(self, zoomValue):
        """Zooms the diff view at the bottom"""
        self.diffViewer.zoomTo(zoomValue)

    def zoomIOconsole(self, zoomValue):
        """Zooms the IO console"""
        # Handle run/profile IO consoles and the debug IO console
        index = self.__bottomSideBar.count - 1
        while index >= 0:
            widget = self.__bottomSideBar.widget(index)
            if hasattr(widget, "getType"):
                if widget.getType() == MainWindowTabWidgetBase.IOConsole:
                    widget.zoomTo(zoomValue)
            index -= 1

    def onIOConsoleSettingUpdated(self):
        """Initiates updating all the IO consoles settings"""
        index = self.__bottomSideBar.count() - 1
        while index >= 0:
            widget = self.__bottomSideBar.widget(index)
            if hasattr(widget, "getType"):
                if widget.getType() == MainWindowTabWidgetBase.IOConsole:
                    widget.consoleSettingsUpdated()
            index -= 1

    def showProfileReport(self, widget, tooltip):
        """Shows the given profile report"""
        self.editorsManagerWidget.editorsManager.showProfileReport(widget,
                                                                   tooltip)

    def getWidgetByUUID(self, uuid):
        """Provides the widget found by the given UUID"""
        return self.editorsManagerWidget.editorsManager.getWidgetByUUID(uuid)

    def getWidgetForFileName(self, fname):
        """Provides the widget found by the given file name"""
        editorsManager = self.editorsManagerWidget.editorsManager
        return editorsManager.getWidgetForFileName(fname)

    def editorsManager(self):
        """Provides the editors manager"""
        return self.editorsManagerWidget.editorsManager

    @staticmethod
    def __buildPythonFilesList():
        """Builds the list of python project files"""
        QApplication.processEvents()
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        filesToProcess = []
        for item in GlobalData().project.filesList:
            if isPythonFile(item):
                filesToProcess.append(item)
        QApplication.restoreOverrideCursor()
        QApplication.processEvents()
        return filesToProcess

    def __onCreatePrjTemplate(self):
        """Triggered when project template should be created"""
        self.createTemplateFile(getProjectTemplateFile())

    def __onEditPrjTemplate(self):
        """Triggered when project template should be edited"""
        self.editTemplateFile(getProjectTemplateFile())

    @staticmethod
    def __onDelPrjTemplate():
        """Triggered when project template should be deleted"""
        fileName = getProjectTemplateFile()
        if fileName is not None:
            if os.path.exists(fileName):
                os.unlink(fileName)
                logging.info("Project new file template deleted")

    def __onCreateIDETemplate(self):
        """Triggered to create IDE template"""
        self.createTemplateFile(getIDETemplateFile())

    def createTemplateFile(self, fileName):
        """Creates a template file"""
        try:
            f = open(fileName, "w")
            f.write(getDefaultTemplate())
            f.close()
        except Exception as exc:
            logging.error("Error creating a template file: " + str(exc))
            return
        self.openFile(fileName, -1)

    def __onEditIDETemplate(self):
        """Triggered to edit IDE template"""
        self.editTemplateFile(getIDETemplateFile())

    def editTemplateFile(self, fileName):
        """Edits the timepale file"""
        if fileName is not None:
            if not os.path.exists(fileName):
                logging.error("The template file " + fileName +
                              " disappeared from the file system.")
                return
            self.openFile(fileName, -1)

    @staticmethod
    def __onDelIDETemplate():
        """Triggered to del IDE template"""
        fileName = getIDETemplateFile()
        if fileName is not None:
            if os.path.exists(fileName):
                os.unlink(fileName)
                logging.info("IDE new file template deleted")

    def displayFindInFiles(self, searchRegexp, searchResults):
        """Displays the results on a tab"""
        self.findInFilesViewer.showReport(searchRegexp, searchResults)

        if self.__bottomSideBar.height() == 0:
            # It was hidden completely, so need to move the slider
            splitterSizes = self.settings.vSplitterSizes
            splitterSizes[0] -= 200
            splitterSizes[1] += 200
            self.__verticalSplitter.setSizes(splitterSizes)

        self.__bottomSideBar.show()
        self.__bottomSideBar.setCurrentTab('search')
        self.__bottomSideBar.raise_()

    def findNameClicked(self):
        """Find name dialog should come up"""
        try:
            FindNameDialog("", self).exec_()
        except Exception as exc:
            logging.error(str(exc))

    def findFileClicked(self):
        """Find file dialog should come up"""
        try:
            FindFileDialog(self).exec_()
        except Exception as exc:
            logging.error(str(exc))

    @staticmethod
    def hideTooltips():
        """Hides all the tooltips"""
        QToolTip.hideText()
        hideSearchTooltip()

    def __onImportDgmTuned(self):
        """Runs the settings dialog first"""
        dlg = ImportsDiagramDialog(ImportsDiagramDialog.ProjectFiles,
                                   "", self)
        if dlg.exec_() == QDialog.Accepted:
            self.__generateImportDiagram(dlg.options)

    def __onImportDgm(self, action=False):
        """Runs the generation process"""
        self.__generateImportDiagram(ImportDiagramOptions())

    def __generateImportDiagram(self, options):
        """Show the generation progress and display the diagram"""
        progressDlg = ImportsDiagramProgress(ImportsDiagramDialog.ProjectFiles,
                                             options)
        if progressDlg.exec_() == QDialog.Accepted:
            self.openDiagram(progressDlg.scene, "Generated for the project")

    def __onRunProjectSettings(self):
        """Brings up the dialog with run script settings"""
        if self.__checkProjectScriptValidity():
            fileName = GlobalData().project.getProjectScript()
            self.__runManager.run(fileName, True)

    def __onProfileProjectSettings(self):
        """Brings up the dialog with profile script settings"""
        if self.__checkProjectScriptValidity():
            fileName = GlobalData().project.getProjectScript()
            params = getRunParameters(fileName)
            termType = self.settings.terminalType
            profilerParams = self.settings.getProfilerSettings()
            debuggerParams = self.settings.getDebuggerSettings()
            dlg = RunDialog(fileName, params, termType,
                            profilerParams, debuggerParams, "Profile")
            if dlg.exec_() == QDialog.Accepted:
                addRunParams(fileName, dlg.runParams)
                if dlg.termType != termType:
                    self.settings.terminalType = dlg.termType
                if dlg.profilerParams != profilerParams:
                    self.settings.setProfilerSettings(dlg.profilerParams)
                self.__onProfileProject()

    def __onDebugProjectSettings(self):
        """Brings up the dialog with debug script settings"""
        if self.__checkDebugPrerequisites():
            fileName = GlobalData().project.getProjectScript()
            params = getRunParameters(fileName)
            termType = self.settings.terminalType
            profilerParams = self.settings.getProfilerSettings()
            debuggerParams = self.settings.getDebuggerSettings()
            dlg = RunDialog(fileName, params, termType,
                            profilerParams, debuggerParams, "Debug")
            if dlg.exec_() == QDialog.Accepted:
                addRunParams(fileName, dlg.runParams)
                if dlg.termType != termType:
                    self.settings.terminalType = dlg.termType
                if dlg.debuggerParams != debuggerParams:
                    self.settings.setDebuggerSettings(dlg.debuggerParams)
                self.__onDebugProject()

    def __onRunProject(self, action=False):
        """Runs the project with saved sattings"""
        if self.__checkProjectScriptValidity():
            fileName = GlobalData().project.getProjectScript()
            self.__runManager.run(fileName, False)

    def __onProfileProject(self, action=False):
        """Profiles the project with saved settings"""
        if self.__checkProjectScriptValidity():
            try:
                dlg = ProfilingProgressDialog(
                    GlobalData().project.getProjectScript(), self)
                dlg.exec_()
            except Exception as exc:
                logging.error(str(exc))

    def __onDebugProject(self, action=False):
        """Debugging is requested"""
        if not self.debugMode:
            if self.__checkDebugPrerequisites():
                self.debugScript(GlobalData().project.getProjectScript())

    def debugScript(self, fileName):
        """Runs a script to debug"""
        if not self.debugMode:
            self.__debugger.startDebugging(fileName)

    def __checkDebugPrerequisites(self):
        """Returns True if should continue"""
        if not self.__checkProjectScriptValidity():
            return False

        editorsManager = self.editorsManagerWidget.editorsManager
        modifiedFiles = editorsManager.getModifiedList(True)
        if len(modifiedFiles) == 0:
            return True

        dlg = ModifiedUnsavedDialog(modifiedFiles, "Save and debug")
        if dlg.exec_() != QDialog.Accepted:
            # Selected to cancel
            return False

        # Need to save the modified project files
        return editorsManager.saveModified(True)

    def __checkProjectScriptValidity(self):
        """Checks and logs error message if so. Returns True if all is OK"""
        if not GlobalData().isProjectScriptValid():
            self.updateRunDebugButtons()
            logging.error("Invalid project script. "
                          "Use project properties dialog to "
                          "select existing python script.")
            return False
        return True

    def __verticalEdgeChanged(self):
        """Editor setting changed"""
        self.settings['verticalEdge'] = not self.settings['verticalEdge']
        self.editorsManagerWidget.editorsManager.updateEditorsSettings()

    def __showSpacesChanged(self):
        """Editor setting changed"""
        self.settings['showSpaces'] = not self.settings['showSpaces']
        self.editorsManagerWidget.editorsManager.updateEditorsSettings()

    def __lineWrapChanged(self):
        """Editor setting changed"""
        self.settings['lineWrap'] = not self.settings['lineWrap']
        self.editorsManagerWidget.editorsManager.updateEditorsSettings()

    def __showEOLChanged(self):
        """Editor setting changed"""
        self.settings['showEOL'] = not self.settings['showEOL']
        self.editorsManagerWidget.editorsManager.updateEditorsSettings()

    def __showBraceMatchChanged(self):
        """Editor setting changed"""
        self.settings['showBraceMatch'] = not self.settings['showBraceMatch']
        self.editorsManagerWidget.editorsManager.updateEditorsSettings()

    def __autoIndentChanged(self):
        """Editor setting changed"""
        self.settings['autoIndent'] = not self.settings['autoIndent']
        self.editorsManagerWidget.editorsManager.updateEditorsSettings()

    def __backspaceUnindentChanged(self):
        """Editor setting changed"""
        self.settings['backspaceUnindent'] = \
            not self.settings['backspaceUnindent']
        self.editorsManagerWidget.editorsManager.updateEditorsSettings()

    def __tabIndentsChanged(self):
        """Editor setting changed"""
        self.settings['tabIndents'] = not self.settings['tabIndents']
        self.editorsManagerWidget.editorsManager.updateEditorsSettings()

    def __indentationGuidesChanged(self):
        """Editor setting changed"""
        self.settings['indentationGuides'] = \
            not self.settings['indentationGuides']
        self.editorsManagerWidget.editorsManager.updateEditorsSettings()

    def __currentLineVisibleChanged(self):
        """Editor setting changed"""
        self.settings['currentLineVisible'] = \
            not self.settings['currentLineVisible']
        self.editorsManagerWidget.editorsManager.updateEditorsSettings()

    def __homeToFirstNonSpaceChanged(self):
        """Editor setting changed"""
        self.settings['jumpToFirstNonSpace'] = \
            not self.settings['jumpToFirstNonSpace']
        self.editorsManagerWidget.editorsManager.updateEditorsSettings()

    def __removeTrailingChanged(self):
        """Editor setting changed"""
        self.settings['removeTrailingOnSave'] = \
            not self.settings['removeTrailingOnSave']

    def __editorCalltipsChanged(self):
        """Editor calltips changed"""
        self.settings['editorCalltips'] = not self.settings['editorCalltips']

    def __clearDebugIOChanged(self):
        """Clear debug IO console before a new session changed"""
        self.settings['clearDebugIO'] = not self.settings['clearDebugIO']

    def __showNavBarChanged(self):
        """Editor setting changed"""
        self.settings['showNavigationBar'] = \
            not self.settings['showNavigationBar']
        self.editorsManagerWidget.editorsManager.updateEditorsSettings()

    def __showCFNavBarChanged(self):
        """Control flow toolbar visibility changed"""
        self.settings['showCFNavigationBar'] = \
            not self.settings['showCFNavigationBar']
        self.editorsManagerWidget.editorsManager.updateCFEditorsSettings()

    def __showMainToolbarChanged(self):
        """Main toolbar visibility changed"""
        self.settings['showMainToolBar'] = \
            not self.settings['showMainToolBar']
        self.__toolbar.setVisible(self.settings['showMainToolBar'])

    def __projectTooltipsChanged(self):
        """Tooltips setting changed"""
        self.settings['projectTooltips'] = \
            not self.settings['projectTooltips']
        self.projectViewer.setTooltips(self.settings['projectTooltips'])

    def __recentTooltipsChanged(self):
        """Tooltips setting changed"""
        self.settings['recentTooltips'] = \
            not self.settings['recentTooltips']
        self.recentProjectsViewer.setTooltips(self.settings['recentTooltips'])

    def __classesTooltipsChanged(self):
        """Tooltips setting changed"""
        self.settings['classesTooltips'] = \
            not self.settings['classesTooltips']
        self.classesViewer.setTooltips(self.settings['classesTooltips'])

    def __functionsTooltipsChanged(self):
        """Tooltips setting changed"""
        self.settings['functionsTooltips'] = \
            not self.settings['functionsTooltips']
        self.functionsViewer.setTooltips(self.settings['functionsTooltips'])

    def __outlineTooltipsChanged(self):
        """Tooltips setting changed"""
        self.settings.outlineTooltips = \
            not self.settings['outlineTooltips']
        self.outlineViewer.setTooltips(self.settings['outlineTooltips'])

    def __findNameTooltipsChanged(self):
        """Tooltips setting changed"""
        self.settings['findNameTooltips'] = \
            not self.settings['findNameTooltips']

    def __findFileTooltipsChanged(self):
        """Tooltips setting changed"""
        self.settings['findFileTooltips'] = \
            not self.settings['findFileTooltips']

    def __editorTooltipsChanged(self):
        """Tooltips setting changed"""
        self.settings['editorTooltips'] = \
            not self.settings['editorTooltips']
        self.editorsManagerWidget.editorsManager.setTooltips(
            self.settings['editorTooltips'])

    def __tabOrderPreservedChanged(self):
        """Tab order preserved option changed"""
        self.settings['taborderpreserved'] = \
            not self.settings['taborderpreserved']

    def __openTabsMenuTriggered(self, act):
        """Tab list settings menu triggered"""
        if act == -1:
            self.settings.tablistsortalpha = True
            self.__alphasort.setChecked(True)
            self.__tabsort.setChecked(False)
        elif act == -2:
            self.settings.tablistsortalpha = False
            self.__alphasort.setChecked(False)
            self.__tabsort.setChecked(True)

    @staticmethod
    def __buildThemesList():
        """Builds a list of themes - system wide and the user local"""
        localSkinsDir = os.path.normpath(str(QDir.homePath())) + \
                        os.path.sep + CONFIG_DIR + os.path.sep + "skins" + \
                        os.path.sep
        return getThemesList(localSkinsDir)

    def __onTheme(self, skinSubdir):
        """Triggers when a theme is selected"""
        if self.settings['skin'] == skinSubdir.data():
            return

        logging.info("Please restart codimension to apply the new theme")
        self.settings['skin'] = skinSubdir.data()

    def __styleAboutToShow(self):
        """Style menu is about to show"""
        currentStyle = self.settings['style'].lower()
        for item in self.__styles:
            font = item[1].font()
            if item[0].lower() == currentStyle:
                font.setBold(True)
            else:
                font.setBold(False)
            item[1].setFont(font)

    def __onStyle(self, styleName):
        """Sets the selected style"""
        QApplication.setStyle(styleName)
        self.settings.style = styleName.lower()

    def __onMonoFont(self, fintFace):
        """Sets the new mono font"""
        try:
            font = QFont()
            font.setFamily(fontFace)
            GlobalData().skin.setMainEditorFont(font)
            GlobalData().skin.setBaseMonoFontFace(fontFace)
        except Exception as exc:
            logging.error(str(exc))
            return

        logging.info("Please restart codimension to apply the new font")

    def checkOutsideFileChanges(self):
        """Checks if there are changes in the files
           currently loaded by codimension"""
        self.editorsManagerWidget.editorsManager.checkOutsideFileChanges()

    def switchDebugMode(self, newState):
        """Switches the debug mode to the desired"""
        if self.debugMode == newState:
            return

        self.debugMode = newState
        self.__removeCurrenDebugLineHighlight()
        clearValidBreakpointLinesCache()

        # Satatus bar
        self.sbDebugState.setVisible(newState)
        self.sbLanguage.setVisible(not newState)
        self.sbEncoding.setVisible(not newState)
        self.sbEol.setVisible(not newState)

        # Toolbar buttons
        self.__dbgStopBrutal.setVisible(
            newState and self.settings.terminalType != TERM_REDIRECT)
        self.__dbgStopAndClearIO.setVisible(
            newState and self.settings.terminalType == TERM_REDIRECT)
        self.__dbgStop.setVisible(newState)
        self.__dbgRestart.setVisible(newState)
        self.__dbgGo.setVisible(newState)
        self.__dbgNext.setVisible(newState)
        self.__dbgStepInto.setVisible(newState)
        self.__dbgRunToLine.setVisible(newState)
        self.__dbgReturn.setVisible(newState)
        self.__dbgJumpToCurrent.setVisible(newState)
        self.__dbgDumpSettingsAct.setVisible(newState)

        if not newState:
            self.__debugStopBrutalAct.setEnabled(False)
            self.__debugStopAct.setEnabled(False)
            self.__debugRestartAct.setEnabled(False)
            self.__debugContinueAct.setEnabled(False)
            self.__debugStepOverAct.setEnabled(False)
            self.__debugStepInAct.setEnabled(False)
            self.__debugStepOutAct.setEnabled(False)
            self.__debugRunToCursorAct.setEnabled(False)
            self.__debugJumpToCurrentAct.setEnabled(False)
            self.__debugDumpSettingsAct.setEnabled(False)
            self.__debugDumpSettingsEnvAct.setEnabled(False)

        self.updateRunDebugButtons()

        # Tabs at the right
        if newState:
            self.__rightSideBar.setTabEnabled(1, True)    # vars etc.
            self.debuggerContext.clear()
            self.debuggerExceptions.clear()
            self.__rightSideBar.setTabText(2, "Exceptions")
            self.__rightSideBar.show()
            self.__rightSideBar.setCurrentTab('debugger')
            self.__rightSideBar.raise_()
            self.__lastDebugAction = None
            self.__debugDumpSettingsAct.setEnabled(True)
            self.__debugDumpSettingsEnvAct.setEnabled(True)
        else:
            if not self.__rightSideBar.isMinimized():
                if self.__rightSideBar.currentIndex() == 1:
                    self.__rightSideBar.setCurrentTab('fileoutline')
            self.__rightSideBar.setTabEnabled(1, False)    # vars etc.

        self.debugModeChanged.emit(newState)

    def __onDebuggerStateChanged(self, newState):
        """Triggered when the debugger reported its state changed"""
        if newState != CodimensionDebugger.STATE_IN_IDE:
            self.__removeCurrenDebugLineHighlight()
            self.debuggerContext.switchControl(False)
        else:
            self.debuggerContext.switchControl(True)

        if newState == CodimensionDebugger.STATE_STOPPED:
            self.__dbgStopBrutal.setEnabled(False)
            self.__dbgStopAndClearIO.setEnabled(False)
            self.__debugStopBrutalAct.setEnabled(False)
            self.__dbgStop.setEnabled(False)
            self.__debugStopAct.setEnabled(False)
            self.__dbgRestart.setEnabled(False)
            self.__debugRestartAct.setEnabled(False)
            self.__setDebugControlFlowButtonsState(False)
            self.sbDebugState.setText("Debugger: stopped")
            self.redirectedIOConsole.sessionStopped()
        elif newState == CodimensionDebugger.STATE_PROLOGUE:
            self.__dbgStopBrutal.setEnabled(True)
            self.__dbgStopAndClearIO.setEnabled(True)
            self.__debugStopBrutalAct.setEnabled(
                self.settings.terminalType != TERM_REDIRECT)
            self.__dbgStop.setEnabled(False)
            self.__debugStopAct.setEnabled(False)
            self.__dbgRestart.setEnabled(False)
            self.__debugRestartAct.setEnabled(False)
            self.__setDebugControlFlowButtonsState(False)
            self.sbDebugState.setText("Debugger: prologue")
        elif newState == CodimensionDebugger.STATE_IN_IDE:
            self.__dbgStopBrutal.setEnabled(True)
            self.__dbgStopAndClearIO.setEnabled(True)
            self.__debugStopBrutalAct.setEnabled(
                self.settings.terminalType != TERM_REDIRECT)
            self.__dbgStop.setEnabled(True)
            self.__debugStopAct.setEnabled(True)
            self.__dbgRestart.setEnabled(True)
            self.__debugRestartAct.setEnabled(True)
            self.__setDebugControlFlowButtonsState(True)
            self.sbDebugState.setText("Debugger: idle")
        elif newState == CodimensionDebugger.STATE_IN_CLIENT:
            self.__dbgStopBrutal.setEnabled(True)
            self.__dbgStopAndClearIO.setEnabled(True)
            self.__debugStopBrutalAct.setEnabled(
                self.settings.terminalType != TERM_REDIRECT)
            self.__dbgStop.setEnabled(True)
            self.__debugStopAct.setEnabled(True)
            self.__dbgRestart.setEnabled(True)
            self.__debugRestartAct.setEnabled(True)
            self.__setDebugControlFlowButtonsState(False)
            self.sbDebugState.setText("Debugger: running")
        elif newState == CodimensionDebugger.STATE_FINISHING:
            self.__dbgStopBrutal.setEnabled(True)
            self.__dbgStopAndClearIO.setEnabled(True)
            self.__debugStopBrutalAct.setEnabled(
                self.settings.terminalType != TERM_REDIRECT)
            self.__dbgStop.setEnabled(False)
            self.__debugStopAct.setEnabled(False)
            self.__dbgRestart.setEnabled(False)
            self.__debugRestartAct.setEnabled(False)
            self.__setDebugControlFlowButtonsState(False)
            self.sbDebugState.setText("Debugger: finishing")
        elif newState == CodimensionDebugger.STATE_BRUTAL_FINISHING:
            self.__dbgStopBrutal.setEnabled(False)
            self.__dbgStopAndClearIO.setEnabled(False)
            self.__debugStopBrutalAct.setEnabled(False)
            self.__dbgStop.setEnabled(False)
            self.__dbgStop.setEnabled(False)
            self.__dbgRestart.setEnabled(False)
            self.__debugRestartAct.setEnabled(False)
            self.__setDebugControlFlowButtonsState(False)
            self.sbDebugState.setText("Debugger: force finishing")
        QApplication.processEvents()

    def __onDebuggerCurrentLine(self, fileName, lineNumber,
                                isStack, asException=False):
        "Triggered when the client reported a new line"""
        self.__removeCurrenDebugLineHighlight()

        self.__lastDebugFileName = fileName
        self.__lastDebugLineNumber = lineNumber
        self.__lastDebugAsException = asException
        self.__onDbgJumpToCurrent()

    def __onDebuggerClientException(self, excType, excMessage, excStackTrace):
        """Debugged program exception handler"""
        self.debuggerExceptions.addException(excType, excMessage,
                                             excStackTrace)
        count = self.debuggerExceptions.getTotalClientExceptionCount()
        self.__rightSideBar.setTabText(2, "Exceptions (" + str(count) + ")")

        # The information about the exception is stored in the exception window
        # regardless whether there is a stack trace or not. So, there is no
        # need to show the exception info in the closing dialog (if this dialog
        # is required).

        if excType is None or excType.startswith("unhandled") or not excStackTrace:
            self.__rightSideBar.show()
            self.__rightSideBar.setCurrentTab('exceptions')
            self.__rightSideBar.raise_()

            if not excStackTrace:
                message = "An exception did not report the stack trace.\n" \
                          "The debugging session will be closed."
            else:
                message = "An unhandled exception occured.\n" \
                          "The debugging session will be closed."

            dlg = QMessageBox(QMessageBox.Critical, "Debugging session",
                              message)
            dlg.addButton(QMessageBox.Ok)
            dlg.addButton(QMessageBox.Cancel)

            btn1 = dlg.button(QMessageBox.Ok)
            btn1.setText("&Close debug console")
            btn1.setIcon(getIcon(''))

            btn2 = dlg.button(QMessageBox.Cancel)
            btn2.setText("&Keep debug console")
            btn2.setIcon(getIcon(''))

            dlg.setDefaultButton(QMessageBox.Ok)
            res = dlg.exec_()

            if res == QMessageBox.Cancel:
                QTimer.singleShot(0, self.__onStopDbgSession)
            else:
                QTimer.singleShot(0, self.__onBrutalStopDbgSession)
            self.debuggerExceptions.setFocus()
            return

        if self.debuggerExceptions.isIgnored(str(excType)):
            # Continue the last action
            if self.__lastDebugAction is None:
                self.__debugger.remoteContinue()
            elif self.__lastDebugAction == self.DEBUG_ACTION_GO:
                self.__debugger.remoteContinue()
            elif self.__lastDebugAction == self.DEBUG_ACTION_NEXT:
                self.__debugger.remoteStepOver()
            elif self.__lastDebugAction == self.DEBUG_ACTION_STEP_INTO:
                self.__debugger.remoteStep()
            elif self.__lastDebugAction == self.DEBUG_ACTION_RUN_TO_LINE:
                self.__debugger.remoteContinue()
            elif self.__lastDebugAction == self.DEBUG_ACTION_STEP_OUT:
                self.__debugger.remoteStepOut()
            return

        # Should stop at the exception
        self.__rightSideBar.show()
        self.__rightSideBar.setCurrentTab('exceptions')
        self.__rightSideBar.raise_()

        fileName = excStackTrace[0][0]
        lineNumber = excStackTrace[0][1]
        self.__onDebuggerCurrentLine(fileName, lineNumber, False, True)
        self.__debugger.remoteThreadList()

        # If a stack is explicitly requested then the only deepest frame
        # is reported. It is better to stick with the exception stack
        # for the time beeing.
        self.debuggerContext.onClientStack(excStackTrace)

        self.__debugger.remoteClientVariables(1, 0) # globals
        self.__debugger.remoteClientVariables(0, 0) # locals
        self.debuggerExceptions.setFocus()

    def __onDebuggerClientSyntaxError(self, errMessage, fileName,
                                      lineNo, charNo):
        """Triggered when the client reported a syntax error"""
        if errMessage is None:
            message = "The program being debugged contains an unspecified " \
                      "syntax error.\nDebugging session will be closed."
        else:
            # Jump to the source code
            editorsManager = self.editorsManagerWidget.editorsManager
            editorsManager.openFile(fileName, lineNo)
            editor = editorsManager.currentWidget().getEditor()
            editor.gotoLine(lineNo, charNo)

            message = "The file " + fileName + " contains syntax error: '" + \
                errMessage + "' at line " + str(lineNo) + ", position " + \
                str(charNo) + ".\nDebugging session will be closed."

        dlg = QMessageBox(QMessageBox.Critical, "Debugging session", message)

        if self.settings.terminalType == TERM_REDIRECT:
            dlg.addButton(QMessageBox.Ok)
        else:
            dlg.addButton(QMessageBox.Ok)
            dlg.addButton(QMessageBox.Cancel)

            btn1 = dlg.button(QMessageBox.Ok)
            btn1.setText("&Close debug console")
            btn1.setIcon(getIcon(''))

            btn2 = dlg.button(QMessageBox.Cancel)
            btn2.setText("&Keep debug console")
            btn2.setIcon(getIcon(''))

        dlg.setDefaultButton(QMessageBox.Ok)
        res = dlg.exec_()

        if res == QMessageBox.Cancel or \
           self.settings.terminalType == TERM_REDIRECT:
            QTimer.singleShot(0, self.__onStopDbgSession)
        else:
            QTimer.singleShot(0, self.__onBrutalStopDbgSession)

    def __onDebuggerClientIDEMessage(self, message):
        """Triggered when the debug server has something to report"""
        if self.settings.terminalType == TERM_REDIRECT:
            self.__ioconsoleIDEMessage(str(message))
        else:
            logging.info(str(message))

    def __removeCurrenDebugLineHighlight(self):
        """Removes the current debug line highlight"""
        if self.__lastDebugFileName is not None:
            editorsManager = self.editorsManagerWidget.editorsManager
            widget = editorsManager.getWidgetForFileName(
                self.__lastDebugFileName)
            if widget is not None:
                widget.getEditor().clearCurrentDebuggerLine()
            self.__lastDebugFileName = None
            self.__lastDebugLineNumber = None
            self.__lastDebugAsException = None

    def __setDebugControlFlowButtonsState(self, enabled):
        """Sets the control flow debug buttons state"""
        self.__dbgGo.setEnabled(enabled)
        self.__debugContinueAct.setEnabled(enabled)
        self.__dbgNext.setEnabled(enabled)
        self.__debugStepOverAct.setEnabled(enabled)
        self.__dbgStepInto.setEnabled(enabled)
        self.__debugStepInAct.setEnabled(enabled)
        self.__dbgReturn.setEnabled(enabled)
        self.__debugStepOutAct.setEnabled(enabled)
        self.__dbgJumpToCurrent.setEnabled(enabled)
        self.__debugJumpToCurrentAct.setEnabled(enabled)

        if enabled:
            self.setRunToLineButtonState()
        else:
            self.__dbgRunToLine.setEnabled(False)
            self.__debugRunToCursorAct.setEnabled(False)

    def setRunToLineButtonState(self):
        """Sets the Run To Line button state"""
        # Separate story:
        # - no run to unbreakable line
        # - no run for non-python file
        if not self.debugMode:
            self.__dbgRunToLine.setEnabled(False)
            self.__debugRunToCursorAct.setEnabled(False)
            return
        if not self.__isPythonBuffer():
            self.__dbgRunToLine.setEnabled(False)
            self.__debugRunToCursorAct.setEnabled(False)
            return

        # That's for sure a python buffer, so the widget exists
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        if currentWidget.getType() in [MainWindowTabWidgetBase.VCSAnnotateViewer]:
            self.__dbgRunToLine.setEnabled(False)
            self.__debugRunToCursorAct.setEnabled(False)
            return

        enabled = currentWidget.isLineBreakable()
        self.__dbgRunToLine.setEnabled(enabled)
        self.__debugRunToCursorAct.setEnabled(enabled)

    def __onBrutalStopDbgSession(self):
        """Stop debugging brutally"""
        self.__debugger.stopDebugging(True)
        if self.settings.terminalType == TERM_REDIRECT:
            self.redirectedIOConsole.clear()

    def __onStopDbgSession(self):
        """Debugger stop debugging clicked"""
        self.__debugger.stopDebugging(False)

    def __onRestartDbgSession(self):
        """Debugger restart session clicked"""
        fileName = self.__debugger.getScriptPath()
        self.__onBrutalStopDbgSession()
        self.__debugger.startDebugging(fileName)

    def __onDbgGo(self):
        """Debugger continue clicked"""
        self.__lastDebugAction = self.DEBUG_ACTION_GO
        self.__debugger.remoteContinue()

    def __onDbgNext(self):
        """Debugger step over clicked"""
        self.__lastDebugAction = self.DEBUG_ACTION_NEXT
        self.__debugger.remoteStepOver()

    def __onDbgStepInto(self):
        """Debugger step into clicked"""
        self.__lastDebugAction = self.DEBUG_ACTION_STEP_INTO
        self.__debugger.remoteStep()

    def __onDbgRunToLine(self):
        """Debugger run to cursor clicked"""
        # The run-to-line button state is set approprietly
        if not self.__dbgRunToLine.isEnabled():
            return

        self.__lastDebugAction = self.DEBUG_ACTION_RUN_TO_LINE
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()

        self.__debugger.remoteBreakpoint(currentWidget.getFileName(),
                                         currentWidget.getLine() + 1,
                                         True, None, True)
        self.__debugger.remoteContinue()

    def __onDbgReturn(self):
        """Debugger step out clicked"""
        self.__lastDebugAction = self.DEBUG_ACTION_STEP_OUT
        self.__debugger.remoteStepOut()

    def __onDbgJumpToCurrent(self):
        """Jump to the current debug line"""
        if self.__lastDebugFileName is None or \
           self.__lastDebugLineNumber is None or \
           self.__lastDebugAsException is None:
            return

        editorsManager = self.editorsManagerWidget.editorsManager
        editorsManager.openFile(self.__lastDebugFileName,
                                self.__lastDebugLineNumber)

        editor = editorsManager.currentWidget().getEditor()
        editor.gotoLine(self.__lastDebugLineNumber)
        editor.highlightCurrentDebuggerLine(self.__lastDebugLineNumber,
                                            self.__lastDebugAsException)
        editorsManager.currentWidget().setFocus()

    def __openProject(self):
        """Shows up a dialog to open a project"""
        if self.debugMode:
            return
        dialog = QFileDialog(self, 'Open project')
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setNameFilter("Codimension project files (*.cdm3)")
        urls = []
        for dname in QDir.drives():
            urls.append(QUrl.fromLocalFile(dname.absoluteFilePath()))
        urls.append(QUrl.fromLocalFile(QDir.homePath()))
        dialog.setDirectory(QDir.homePath())
        dialog.setSidebarUrls(urls)

        if dialog.exec_() != QDialog.Accepted:
            return

        fileNames = dialog.selectedFiles()
        fileName = os.path.realpath(str(fileNames[0]))
        if fileName == GlobalData().project.fileName:
            logging.warning("The selected project to load is "
                            "the currently loaded one.")
            return

        if not isCDMProjectFile(fileName):
            logging.warning("Codimension project file "
                            "must have .cdm3 extension")
            return

        self.__loadProject(fileName)

    def __loadProject(self, projectFile):
        """Loads the given project"""
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        editorsManager = self.editorsManagerWidget.editorsManager
        if editorsManager.closeRequest():
            prj = GlobalData().project
            prj.tabsStatus = editorsManager.getTabsStatus()
            editorsManager.closeAll()
            prj.loadProject(projectFile)
            if not self.__leftSideBar.isMinimized():
                self.activateProjectTab()
        QApplication.restoreOverrideCursor()

    def __openFile(self):
        """Triggers when Ctrl+O is pressed"""
        dialog = QFileDialog(self, 'Open file')
        dialog.setFileMode(QFileDialog.ExistingFiles)
        urls = []
        for dname in QDir.drives():
            urls.append(QUrl.fromLocalFile(dname.absoluteFilePath()))
        urls.append(QUrl.fromLocalFile(QDir.homePath()))

        editorsManager = self.editorsManagerWidget.editorsManager
        try:
            fileName = editorsManager.currentWidget().getFileName()
            if os.path.isabs(fileName):
                dirName = os.path.dirname(fileName)
                url = QUrl.fromLocalFile(dirName)
                if url not in urls:
                    urls.append(url)
        except:
            pass

        project = GlobalData().project
        if project.isLoaded():
            dialog.setDirectory(project.getProjectDir())
            urls.append(QUrl.fromLocalFile(project.getProjectDir()))
        else:
            # There is no project loaded
            dialog.setDirectory(QDir.homePath())
        dialog.setSidebarUrls(urls)

        if dialog.exec_() != QDialog.Accepted:
            return

        for fileName in dialog.selectedFiles():
            try:
                self.detectTypeAndOpenFile(os.path.realpath(str(fileName)))
            except Exception as exc:
                logging.error(str(exc))

    def __isPlainTextBuffer(self):
        """Provides if saving is enabled"""
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        if currentWidget is None:
            return False
        return currentWidget.getType() in \
            [MainWindowTabWidgetBase.PlainTextEditor,
             MainWindowTabWidgetBase.VCSAnnotateViewer]

    def __isTemporaryBuffer(self):
        """True if it is a temporary text buffer"""
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        if currentWidget is None:
            return False
        return currentWidget.getType() in \
            [MainWindowTabWidgetBase.VCSAnnotateViewer]

    def __isPythonBuffer(self):
        """True if the current tab is a python buffer"""
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        if currentWidget is None:
            return False
        return currentWidget.getType() in \
            [MainWindowTabWidgetBase.PlainTextEditor,
             MainWindowTabWidgetBase.VCSAnnotateViewer] and \
            isPythonMime(currentWidget.getMime())

    def __isGraphicsBuffer(self):
        """True if is pictures viewer"""
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        if currentWidget is None:
            return False
        return currentWidget.getType() == MainWindowTabWidgetBase.PictureViewer

    def __isGeneratedDiagram(self):
        """True if this is a generated diagram"""
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        if currentWidget is None:
            return False
        if currentWidget.getType() == MainWindowTabWidgetBase.GeneratedDiagram:
            return True
        if currentWidget.getType() == MainWindowTabWidgetBase.ProfileViewer:
            if currentWidget.isDiagramActive():
                return True
        return False

    def __isProfileViewer(self):
        """True if this is a profile viewer"""
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        if currentWidget is None:
            return False
        return currentWidget.getType() == MainWindowTabWidgetBase.ProfileViewer

    def __isDiffViewer(self):
        """True if this is a diff viewer"""
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        if currentWidget is None:
            return False
        return currentWidget.getType() == MainWindowTabWidgetBase.DiffViewer

    def __onTabImportDgm(self):
        """Triggered when tab imports diagram is requested"""
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.onImportDgm()

    def __onTabImportDgmTuned(self):
        """Triggered when tuned tab imports diagram is requested"""
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.onImportDgmTuned()

    def onRunTab(self):
        """Triggered when run tab script is requested"""
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        self.__runManager.run(currentWidget.getFileName(), False)

    def __onDebugTab(self):
        """Triggered when debug tab is requested"""
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.onDebugScript()

    def __onProfileTab(self):
        """Triggered when profile script is requested"""
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.onProfileScript()

    def onRunTabDlg(self):
        """Triggered when run tab script dialog is requested"""
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        self.__runManager.run(currentWidget.getFileName(), True)

    def __onDebugTabDlg(self):
        """Triggered when debug tab script dialog is requested"""
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.onDebugScriptSettings()

    def __onProfileTabDlg(self):
        """Triggered when profile tab script dialog is requested"""
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.onProfileScriptSettings()

    def __onPluginManager(self):
        """Triggered when a plugin manager dialog is requested"""
        dlg = PluginsDialog(GlobalData().pluginManager, self)
        dlg.exec_()

    def __onContextHelp(self):
        """Triggered when Ctrl+F1 is clicked"""
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.getEditor().onTagHelp()

    def __onCallHelp(self):
        """Triggered when a context help for the current call is requested"""
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.getEditor().onCallHelp()

    @staticmethod
    def __onHomePage():
        """Triggered when opening the home page is requested"""
        QDesktopServices.openUrl(QUrl("http://codimension.org"))

    @staticmethod
    def __onAllShortcurs():
        """Triggered when opening key bindings page is requested"""
        QDesktopServices.openUrl(
            QUrl("http://codimension.org/documentation/cheatsheet.html"))

    def __onAbout(self):
        """Triggered when 'About' info is requested"""
        dlg = AboutDialog(self)
        dlg.exec_()

    def __activateSideTab(self, act):
        """Triggered when a side bar should be activated"""
        if isinstance(act, str):
            name = act
        else:
            name = act.data()
        if name in ["project", "recent", "classes", "functions", "globals"]:
            self.__leftSideBar.show()
            self.__leftSideBar.setCurrentTab(name)
            self.__leftSideBar.raise_()
        elif name in ['fileoutline', 'debugger', 'exceptions', 'breakpoints']:
            self.__rightSideBar.show()
            self.__rightSideBar.setCurrentTab(name)
            self.__rightSideBar.raise_()
        elif name in ['log', 'search', 'contexthelp', 'diff']:
            self.__bottomSideBar.show()
            self.__bottomSideBar.setCurrentTab(name)
            self.__bottomSideBar.raise_()

    def __onTabLineCounter(self):
        """Triggered when line counter for the current buffer is requested"""
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.onLineCounter()

    def __onTabJumpToDef(self):
        """Triggered when jump to defenition is requested"""
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.getEditor().onGotoDefinition()

    def __onTabJumpToScopeBegin(self):
        """Triggered when jump to the beginning
           of the current scope is requested
        """
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.getEditor().onScopeBegin()

    def __onFindOccurences(self):
        """Triggered when search for occurences is requested"""
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.getEditor().onOccurences()

    def findWhereUsed(self, fileName, item):
        """Find occurences for c/f/g browsers"""
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))

        # False for no exceptions
        locations = getOccurrences(fileName, item.absPosition, False)
        if len(locations) == 0:
            QApplication.restoreOverrideCursor()
            self.showStatusBarMessage("No occurrences of " +
                                      item.name + " found.", 0)
            return

        # Process locations for find results window
        result = []
        for loc in locations:
            index = getSearchItemIndex(result, loc[0])
            if index < 0:
                widget = self.getWidgetForFileName(loc[0])
                if widget is None:
                    uuid = ""
                else:
                    uuid = widget.getUUID()
                newItem = ItemToSearchIn(loc[0], uuid)
                result.append(newItem)
                index = len(result) - 1
            result[index].addMatch(item.name, loc[1])

        QApplication.restoreOverrideCursor()

        self.displayFindInFiles("", result)

    def __onTabOpenImport(self):
        """Triggered when open import is requested"""
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.onOpenImport()

    def __onShowCalltip(self):
        """Triggered when show calltip is requested"""
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.getEditor().onShowCalltip()

    def __onOpenAsFile(self):
        """Triggered when open as file is requested"""
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.getEditor().openAsFile()

    def __onDownloadAndShow(self):
        """Triggered when a selected string should be treated as URL"""
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.getEditor().downloadAndShow()

    def __onOpenInBrowser(self):
        """Triggered when a selected url should be opened in a browser"""
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.getEditor().openInBrowser()

    def __onHighlightInOutline(self):
        """Triggered to highlight the current context in the outline browser"""
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.getEditor().highlightInOutline()

    def __onUndo(self):
        """Triggered when undo action is requested"""
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.getEditor().onUndo()

    def __onRedo(self):
        """Triggered when redo action is requested"""
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.getEditor().onRedo()

    def __onZoomIn(self):
        """Triggered when zoom in is requested"""
        editorsManager = self.editorsManagerWidget.editorsManager
        editorsManager.zoomIn()

    def __onZoomOut(self):
        """Triggered when zoom out is requested"""
        editorsManager = self.editorsManagerWidget.editorsManager
        editorsManager.zoomOut()

    def __onZoomReset(self):
        """Triggered when zoom 1:1 is requested"""
        editorsManager = self.editorsManagerWidget.editorsManager
        editorsManager.zoomReset()

    def __onGoToLine(self):
        """Triggered when go to line is requested"""
        editorsManager = self.editorsManagerWidget.editorsManager
        editorsManager.onGoto()

    def __getEditor(self):
        """Provides reference to the editor"""
        editorsManager = self.editorsManagerWidget.editorsManager
        return editorsManager.currentWidget().getEditor()

    def __onCut(self):
        """Triggered when cut is requested"""
        self.__getEditor().onShiftDel()

    def __onPaste(self):
        """Triggered when paste is requested"""
        self.__getEditor().paste()

    def __onSelectAll(self):
        """Triggered when select all is requested"""
        self.__getEditor().selectAll()

    def __onComment(self):
        """Triggered when comment/uncomment is requested"""
        self.__getEditor().onCommentUncomment()

    def __onDuplicate(self):
        """Triggered when duplicate line is requested"""
        self.__getEditor().duplicateLine()

    def __onAutocomplete(self):
        """Triggered when autocomplete is requested"""
        self.__getEditor().onAutoComplete()

    def __onFind(self):
        """Triggered when find is requested"""
        editorsManager = self.editorsManagerWidget.editorsManager
        editorsManager.onFind()

    def __onFindCurrent(self):
        """Triggered when find of the current identifier is requested"""
        editorsManager = self.editorsManagerWidget.editorsManager
        editorsManager.onHiddenFind()

    def __onReplace(self):
        """Triggered when replace is requested"""
        editorsManager = self.editorsManagerWidget.editorsManager
        editorsManager.onReplace()

    def __onFindNext(self):
        """Triggered when find next is requested"""
        editorsManager = self.editorsManagerWidget.editorsManager
        editorsManager.findNext()

    def __onFindPrevious(self):
        """Triggered when find previous is requested"""
        editorsManager = self.editorsManagerWidget.editorsManager
        editorsManager.findPrev()

    def __onExpandTabs(self):
        """Triggered when tabs expansion is requested"""
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.onExpandTabs()

    def __onRemoveTrailingSpaces(self):
        """Triggered when trailing spaces removal is requested"""
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        currentWidget.onRemoveTrailingWS()

    def __editAboutToShow(self):
        """Triggered when edit menu is about to show"""
        isPlainBuffer = self.__isPlainTextBuffer()
        isPythonBuffer = self.__isPythonBuffer()
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        if isPlainBuffer:
            editor = currentWidget.getEditor()

        self.__undoAct.setShortcut("Ctrl+Z")
        self.__undoAct.setEnabled(isPlainBuffer and
                                  editor.document().isUndoAvailable())
        self.__redoAct.setShortcut("Ctrl+Y")
        self.__redoAct.setEnabled(isPlainBuffer and
                                  editor.document().isRedoAvailable())
        self.__cutAct.setShortcut("Ctrl+X")
        self.__cutAct.setEnabled(isPlainBuffer and not editor.isReadOnly())
        self.__copyAct.setShortcut("Ctrl+C")
        self.__copyAct.setEnabled(editorsManager.isCopyAvailable())
        self.__pasteAct.setShortcut("Ctrl+V")
        self.__pasteAct.setEnabled(isPlainBuffer and
                                   QApplication.clipboard().text() != "" and
                                   not editor.isReadOnly())
        self.__selectAllAct.setShortcut("Ctrl+A")
        self.__selectAllAct.setEnabled(isPlainBuffer)
        self.__commentAct.setShortcut("Ctrl+M")
        self.__commentAct.setEnabled(isPythonBuffer and
                                     not editor.isReadOnly())
        self.__duplicateAct.setShortcut("Ctrl+D")
        self.__duplicateAct.setEnabled(isPlainBuffer and
                                       not editor.isReadOnly())
        self.__autocompleteAct.setShortcut("Ctrl+Space")
        self.__autocompleteAct.setEnabled(isPlainBuffer and
                                          not editor.isReadOnly())
        self.__expandTabsAct.setEnabled(isPlainBuffer and
                                        not editor.isReadOnly())
        self.__trailingSpacesAct.setEnabled(isPlainBuffer and
                                            not editor.isReadOnly())

    def __tabAboutToShow(self):
        """Triggered when tab menu is about to show"""
        plainTextBuffer = self.__isPlainTextBuffer()
        isPythonBuffer = self.__isPythonBuffer()
        isGeneratedDiagram = self.__isGeneratedDiagram()
        isProfileViewer = self.__isProfileViewer()
        editorsManager = self.editorsManagerWidget.editorsManager

        self.__cloneTabAct.setEnabled(plainTextBuffer)
        self.__closeOtherTabsAct.setEnabled(
            editorsManager.closeOtherAvailable())
        self.__saveFileAct.setEnabled(plainTextBuffer or isGeneratedDiagram or
                                      isProfileViewer)
        self.__saveFileAsAct.setEnabled(plainTextBuffer or isGeneratedDiagram or
                                        isProfileViewer)
        self.__closeTabAct.setEnabled(editorsManager.isTabClosable())
        self.__tabJumpToDefAct.setEnabled(isPythonBuffer)
        self.__calltipAct.setEnabled(isPythonBuffer)
        self.__tabJumpToScopeBeginAct.setEnabled(isPythonBuffer)
        self.__tabOpenImportAct.setEnabled(isPythonBuffer)
        if plainTextBuffer:
            widget = editorsManager.currentWidget()
            editor = widget.getEditor()
            self.__openAsFileAct.setEnabled(
                editor.openAsFileAvailable())
            self.__downloadAndShowAct.setEnabled(
                editor.downloadAndShowAvailable())
            self.__openInBrowserAct.setEnabled(
                editor.downloadAndShowAvailable())
        else:
            self.__openAsFileAct.setEnabled(False)
            self.__downloadAndShowAct.setEnabled(False)
            self.__openInBrowserAct.setEnabled(False)

        self.__highlightInPrjAct.setEnabled(
            editorsManager.isHighlightInPrjAvailable())
        self.__highlightInFSAct.setEnabled(
            editorsManager.isHighlightInFSAvailable())
        self.__highlightInOutlineAct.setEnabled(isPythonBuffer)

        self.__closeTabAct.setShortcut("Ctrl+F4")
        self.__tabJumpToDefAct.setShortcut("Ctrl+\\")
        self.__calltipAct.setShortcut("Ctrl+/")
        self.__tabJumpToScopeBeginAct.setShortcut("Alt+U")
        self.__tabOpenImportAct.setShortcut("Ctrl+I")
        self.__highlightInOutlineAct.setShortcut("Ctrl+B")

        self.__recentFilesMenu.clear()
        addedCount = 0

        for item in GlobalData().project.recentFiles:
            addedCount += 1
            act = self.__recentFilesMenu.addAction(
                self.__getAccelerator(addedCount) + item)
            act.setData(item)
            act.setEnabled(os.path.exists(item))

        self.__recentFilesMenu.setEnabled(addedCount > 0)

    def __searchAboutToShow(self):
        """Triggered when search menu is about to show"""
        isPlainTextBuffer = self.__isPlainTextBuffer()
        isPythonBuffer = self.__isPythonBuffer()
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()

        self.__findOccurencesAct.setEnabled(isPythonBuffer and
                                            os.path.isabs(currentWidget.getFileName()))
        self.__goToLineAct.setEnabled(isPlainTextBuffer)
        self.__findAct.setEnabled(isPlainTextBuffer)
        self.__findCurrentAct.setEnabled(isPlainTextBuffer)
        self.__replaceAct.setEnabled(isPlainTextBuffer and
                                     currentWidget.getType() != MainWindowTabWidgetBase.VCSAnnotateViewer)
        self.__findNextAct.setEnabled(isPlainTextBuffer)
        self.__findPrevAct.setEnabled(isPlainTextBuffer)

        self.__findOccurencesAct.setShortcut("Ctrl+]")
        self.__goToLineAct.setShortcut("Ctrl+G")
        self.__findAct.setShortcut("Ctrl+F")
        self.__findCurrentAct.setShortcut("Ctrl+F3")
        self.__replaceAct.setShortcut("Ctrl+R")
        self.__findNextAct.setShortcut("F3")
        self.__findPrevAct.setShortcut("Shift+F3")

    def __diagramsAboutToShow(self):
        """Triggered when the diagrams menu is about to show"""
        isPythonBuffer = self.__isPythonBuffer()
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()

        enabled = isPythonBuffer and \
            currentWidget.getType() != MainWindowTabWidgetBase.VCSAnnotateViewer
        self.__tabImportDgmAct.setEnabled(enabled)
        self.__tabImportDgmDlgAct.setEnabled(enabled)

    def __runAboutToShow(self):
        """Triggered when the run menu is about to show"""
        projectLoaded = GlobalData().project.isLoaded()
        prjScriptValid = GlobalData().isProjectScriptValid()

        enabled = projectLoaded and prjScriptValid and not self.debugMode
        self.__prjRunAct.setEnabled(enabled)
        self.__prjRunDlgAct.setEnabled(enabled)

        self.__prjProfileAct.setEnabled(enabled)
        self.__prjProfileDlgAct.setEnabled(enabled)

    def __debugAboutToShow(self):
        """Triggered when the debug menu is about to show"""
        projectLoaded = GlobalData().project.isLoaded()
        prjScriptValid = GlobalData().isProjectScriptValid()

        enabled = projectLoaded and prjScriptValid and not self.debugMode
        self.__prjDebugAct.setEnabled(enabled)
        self.__prjDebugDlgAct.setEnabled(enabled)

    def __toolsAboutToShow(self):
        """Triggered when tools menu is about to show"""
        isPythonBuffer = self.__isPythonBuffer()
        projectLoaded = GlobalData().project.isLoaded()
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()

        pythonBufferNonAnnotate = isPythonBuffer and \
            currentWidget.getType() != MainWindowTabWidgetBase.VCSAnnotateViewer
        self.__tabLineCounterAct.setEnabled(isPythonBuffer)

        if projectLoaded:
            self.__unusedClassesAct.setEnabled(
                self.classesViewer.getItemCount() > 0)
            self.__unusedFunctionsAct.setEnabled(
                self.functionsViewer.getItemCount() > 0)
            self.__unusedGlobalsAct.setEnabled(
                self.globalsViewer.getItemCount() > 0)
        else:
            self.__unusedClassesAct.setEnabled(False)
            self.__unusedFunctionsAct.setEnabled(False)
            self.__unusedGlobalsAct.setEnabled(False)

    def __viewAboutToShow(self):
        """Triggered when view menu is about to show"""
        isPlainTextBuffer = self.__isPlainTextBuffer()
        isGraphicsBuffer = self.__isGraphicsBuffer()
        isGeneratedDiagram = self.__isGeneratedDiagram()
        isProfileViewer = self.__isProfileViewer()
        isDiffViewer = self.__isDiffViewer()
        zoomEnabled = isPlainTextBuffer or isGraphicsBuffer or \
                      isGeneratedDiagram or isDiffViewer
        if not zoomEnabled and isProfileViewer:
            editorsManager = self.editorsManagerWidget.editorsManager
            currentWidget = editorsManager.currentWidget()
            zoomEnabled = currentWidget.isZoomApplicable()
        self.__zoomInAct.setEnabled(zoomEnabled)
        self.__zoomOutAct.setEnabled(zoomEnabled)
        self.__zoom11Act.setEnabled(zoomEnabled)

        self.__zoomInAct.setShortcut("Ctrl+=")
        self.__zoomOutAct.setShortcut("Ctrl+-")
        self.__zoom11Act.setShortcut("Ctrl+0")

        self.__debugBarAct.setEnabled(self.debugMode)

    def __optionsAboutToShow(self):
        """Triggered when the options menu is about to show"""
        exists = os.path.exists(getIDETemplateFile())
        self.__ideCreateTemplateAct.setEnabled(not exists)
        self.__ideEditTemplateAct.setEnabled(exists)
        self.__ideDelTemplateAct.setEnabled(exists)

    def __helpAboutToShow(self):
        """Triggered when help menu is about to show"""
        isPythonBuffer = self.__isPythonBuffer()
        self.__contextHelpAct.setEnabled(isPythonBuffer)
        self.__callHelpAct.setEnabled(isPythonBuffer)

        self.__contextHelpAct.setShortcut("Ctrl+F1")
        self.__callHelpAct.setShortcut("Ctrl+Shift+F1")

    def __editAboutToHide(self):
        """Triggered when edit menu is about to hide"""
        self.__undoAct.setShortcut("")
        self.__redoAct.setShortcut("")
        self.__cutAct.setShortcut("")
        self.__copyAct.setShortcut("")
        self.__pasteAct.setShortcut("")
        self.__selectAllAct.setShortcut("")
        self.__commentAct.setShortcut("")
        self.__duplicateAct.setShortcut("")
        self.__autocompleteAct.setShortcut("")

    def __prjAboutToHide(self):
        self.__newProjectAct.setEnabled(True)
        self.__openProjectAct.setEnabled(True)

    def __tabAboutToHide(self):
        """Triggered when tab menu is about to hide"""
        self.__closeTabAct.setShortcut("")
        self.__tabJumpToDefAct.setShortcut("")
        self.__calltipAct.setShortcut("")
        self.__tabJumpToScopeBeginAct.setShortcut("")
        self.__tabOpenImportAct.setShortcut("")
        self.__highlightInOutlineAct.setShortcut("")

        self.__saveFileAct.setEnabled(True)
        self.__saveFileAsAct.setEnabled(True)

    def __searchAboutToHide(self):
        """Triggered when search menu is about to hide"""
        self.__findOccurencesAct.setShortcut("")
        self.__goToLineAct.setShortcut("")
        self.__findAct.setShortcut("")
        self.__findCurrentAct.setShortcut("")
        self.__replaceAct.setShortcut("")
        self.__findNextAct.setShortcut("")
        self.__findPrevAct.setShortcut("")

    def __toolsAboutToHide(self):
        """Triggered when tools menu is about to hide"""
        pass

    def __viewAboutToHide(self):
        """Triggered when view menu is about to hide"""
        self.__zoomInAct.setShortcut("")
        self.__zoomOutAct.setShortcut("")
        self.__zoom11Act.setShortcut("")

    def __helpAboutToHide(self):
        """Triggered when help menu is about to hide"""
        self.__contextHelpAct.setShortcut("")
        self.__callHelpAct.setShortcut("")

    @staticmethod
    def __getAccelerator(count):
        """Provides an accelerator text for a menu item"""
        if count < 10:
            return "&" + str(count) + ".  "
        return "&" + chr(count - 10 + ord('a')) + ".  "

    def __prjAboutToShow(self):
        """Triggered when project menu is about to show"""
        self.__newProjectAct.setEnabled(not self.debugMode)
        self.__openProjectAct.setEnabled(not self.debugMode)
        self.__unloadProjectAct.setEnabled(not self.debugMode)

        # Recent projects part
        self.__recentPrjMenu.clear()
        addedCount = 0
        currentPrj = GlobalData().project.fileName
        for item in self.settings['recentProjects']:
            if item == currentPrj:
                continue
            addedCount += 1
            act = self.__recentPrjMenu.addAction(
                                self.__getAccelerator(addedCount) +
                                os.path.basename(item).replace(".cdm3", ""))
            act.setData(item)
            act.setEnabled(not self.debugMode and os.path.exists(item))

        self.__recentPrjMenu.setEnabled(addedCount > 0)

        if GlobalData().project.isLoaded():
            # Template part
            exists = os.path.exists(getProjectTemplateFile())
            self.__prjTemplateMenu.setEnabled(True)
            self.__createPrjTemplateAct.setEnabled(not exists)
            self.__editPrjTemplateAct.setEnabled(exists)
            self.__delPrjTemplateAct.setEnabled(exists)
        else:
            self.__prjTemplateMenu.setEnabled(False)

    def __onRecentPrj(self, path):
        """Triggered when a recent project is requested to be loaded"""
        path = path.data()
        if not os.path.exists(path):
            logging.error("Could not find project file: " + path)
        else:
            self.__loadProject(path)

    def __onRecentFile(self, path):
        """Triggered when a recent file is requested to be loaded"""
        if isImageFile(path):
            self.openPixmapFile(path)
        else:
            self.openFile(path, -1)

    def onNotUsedFunctions(self):
        """Triggered when not used functions analysis requested"""
        dlg = NotUsedAnalysisProgress(
            NotUsedAnalysisProgress.Functions,
            self.functionsViewer.funcViewer.model().sourceModel(), self)
        dlg.exec_()

    def onNotUsedGlobals(self):
        """Triggered when not used global vars analysis requested"""
        dlg = NotUsedAnalysisProgress(
            NotUsedAnalysisProgress.Globals,
            self.globalsViewer.globalsViewer.model().sourceModel(), self)
        dlg.exec_()

    def onNotUsedClasses(self):
        """Triggered when not used classes analysis requested"""
        dlg = NotUsedAnalysisProgress(
            NotUsedAnalysisProgress.Classes,
            self.classesViewer.clViewer.model().sourceModel(), self)
        dlg.exec_()

    def showDisassembler(self, scriptPath, name):
        """Triggered when a disassembler should be shown"""
        try:
            code = getDisassembled(scriptPath, name)
            editorsManager = self.editorsManagerWidget.editorsManager
            editorsManager.showDisassembler(scriptPath, name, code)
        except:
            logging.error("Could not get '" + name + "' from " +
                          scriptPath + " disassembled.")

    def highlightInPrj(self, path):
        """Triggered when the file is to be highlighted in a project tree"""
        if not GlobalData().project.isLoaded():
            return
        if not os.path.isabs(path):
            return
        if not GlobalData().project.isProjectFile(path):
            return
        if self.projectViewer.highlightPrjItem(path):
            self.activateProjectTab()

    def highlightInFS(self, path):
        """Triggered when the file is to be highlighted in the FS tree"""
        if not os.path.isabs(path):
            return
        if self.projectViewer.highlightFSItem(path):
            self.activateProjectTab()

    def highlightInOutline(self, context, line):
        """Triggered when the given context should be highlighted in outline"""
        if self.outlineViewer.highlightContextItem(context, line):
            self.activateOutlineTab()

    def getLogViewerContent(self):
        """Provides the log viewer window content as a plain text"""
        return self.logViewer.getText()

    def getCurrentFrameNumber(self):
        """Provides the current stack frame number"""
        return self.debuggerContext.getCurrentFrameNumber()

    def __onClientExceptionsCleared(self):
        """Triggered when the user cleared the client exceptions"""
        self.__rightSideBar.setTabText(2, "Exceptions")

    def __onBreakpointsModelChanged(self):
        " Triggered when something is changed in the breakpoints list "
        enabledCount, disabledCount = self.__debugger.getBreakPointModel().getCounts()
        total = enabledCount + disabledCount
        if total == 0:
            self.__rightSideBar.setTabText(3, "Breakpoints")
        else:
            self.__rightSideBar.setTabText(3, "Breakpoints (" + str(total) + ")")

    def __onEvalOK(self, message):
        """Triggered when Eval completed successfully"""
        logging.info("Eval succeeded:\n" + message)

    def __onEvalError(self, message):
        """Triggered when Eval failed"""
        logging.error("Eval failed:\n" + message)

    def __onExecOK(self, message):
        """Triggered when Exec completed successfully"""
        if message:
            logging.info("Exec succeeded:\n" + message)

    def __onExecError(self, message):
        """Triggered when Eval failed"""
        logging.error("Exec failed:\n" + message)

    def setDebugTabAvailable(self, enabled):
        """Sets a new status when a tab is changed
           or a content has been changed
        """
        self.__tabDebugAct.setEnabled(enabled)
        self.__tabDebugDlgAct.setEnabled(enabled)

        self.__tabRunAct.setEnabled(enabled)
        self.__tabRunDlgAct.setEnabled(enabled)

        self.__tabProfileAct.setEnabled(enabled)
        self.__tabProfileDlgAct.setEnabled(enabled)

    def __initPluginSupport(self):
        """Initializes the main window plugin support"""
        self.__pluginMenus = {}
        GlobalData().pluginManager.sigPluginActivated.connect(
            self.__onPluginActivated)
        GlobalData().pluginManager.sigPluginDeactivated.connect(
            self.__onPluginDeactivated)

    def __onPluginActivated(self, plugin):
        """Triggered when a plugin is activated"""
        pluginName = plugin.getName()
        try:
            pluginMenu = QMenu(pluginName, self)
            plugin.getObject().populateMainMenu(pluginMenu)
            if pluginMenu.isEmpty():
                pluginMenu = None
                return
            self.__pluginMenus[plugin.getPath()] = pluginMenu
            self.__recomposePluginMenu()
        except Exception as exc:
            logging.error("Error populating " + pluginName +
                          " plugin main menu: " +
                          str(exc) + ". Ignore and continue.")

    def __recomposePluginMenu(self):
        """Recomposes the plugin menu"""
        self.__pluginsMenu.clear()
        self.__pluginsMenu.addAction(getIcon('pluginmanagermenu.png'),
                                     'Plugin &manager', self.__onPluginManager)
        if self.__pluginMenus:
            self.__pluginsMenu.addSeparator()
        for path in self.__pluginMenus:
            self.__pluginsMenu.addMenu(self.__pluginMenus[path])

    def __onPluginDeactivated(self, plugin):
        """Triggered when a plugin is deactivated"""
        try:
            path = plugin.getPath()
            if path in self.__pluginMenus:
                del self.__pluginMenus[path]
                self.__recomposePluginMenu()
        except Exception as exc:
            pluginName = plugin.getName()
            logging.error("Error removing " + pluginName +
                          " plugin main menu: " +
                          str(exc) + ". Ignore and continue.")

    def activateProjectTab(self):
        """Activates the project tab"""
        self.__leftSideBar.show()
        self.__leftSideBar.setCurrentTab('project')
        self.__leftSideBar.raise_()

    def activateOutlineTab(self):
        """Activates the outline tab"""
        self.__rightSideBar.show()
        self.__rightSideBar.setCurrentTab('fileoutline')
        self.__rightSideBar.raise_()

    def __dumpDebugSettings(self, fileName, fullEnvironment):
        """Provides common settings except the environment"""
        runParameters = getRunParameters(fileName)
        debugSettings = self.settings.getDebuggerSettings()
        workingDir = getWorkingDir(fileName, runParameters)
        arguments = parseCommandLineArguments(runParameters.arguments)
        environment = getNoArgsEnvironment(runParameters)

        env = "Environment: "
        if runParameters.envType == runParameters.InheritParentEnv:
            env += "inherit parent"
        elif runParameters.envType == runParameters.InheritParentEnvPlus:
            env += "inherit parent and add/modify"
        else:
            env += "specific"

        pathVariables = []
        container = None
        if fullEnvironment:
            container = environment
            keys = environment.keys()
            keys.sort()
            for key in keys:
                env += "\n    " + key + " = " + environment[key]
                if 'PATH' in key:
                    pathVariables.append(key)
        else:
            if runParameters.envType == runParameters.InheritParentEnvPlus:
                container = runParameters.additionToParentEnv
                keys = runParameters.additionToParentEnv.keys()
                keys.sort()
                for key in keys:
                    env += "\n    " + key + " = " + runParameters.additionToParentEnv[key]
                    if 'PATH' in key:
                        pathVariables.append(key)
            elif runParameters.envType == runParameters.SpecificEnvironment:
                container = runParameters.specificEnv
                keys = runParameters.specificEnv.keys()
                keys.sort()
                for key in keys():
                    env += "\n    " + key + " = " + runParameters.specificEnv[key]
                    if 'PATH' in key:
                        pathVariables.append(key)

        if pathVariables:
            env += "\nDetected PATH-containing variables:"
            for key in pathVariables:
                env += "\n    " + key
                for item in container[key].split(':'):
                    env += "\n        " + item

        terminal = "Terminal to run in: "
        if self.settings.terminalType == TERM_AUTO:
            terminal += "auto detection"
        elif self.settings.terminalType == TERM_KONSOLE:
            terminal += "default KDE konsole"
        elif self.settings.terminalType == TERM_GNOME:
            terminal += "gnome-terminal"
        elif self.settings.terminalType == TERM_XTERM:
            terminal += "xterm"
        elif self.settings.terminalType == TERM_REDIRECT:
            terminal += "redirect to IDE"

        logging.info("\n".join(
            ["Current debug session settings",
             "Script: " + fileName,
             "Arguments: " + " ".join(arguments),
             "Working directory: " + workingDir,
             env, terminal,
             "Report exceptions: " + str(debugSettings.reportExceptions),
             "Trace interpreter libs: " + str(debugSettings.traceInterpreter),
             "Stop at first line: " + str(debugSettings.stopAtFirstLine),
             "Fork without asking: " + str(debugSettings.autofork),
             "Debug child process: " + str(debugSettings.followChild),
             "Close terminal upon successfull completion: " + str(runParameters.closeTerminal)]))

    def __onDumpDebugSettings(self, action=None):
        """Triggered when dumping visible settings was requested"""
        self.__dumpDebugSettings(self.__debugger.getScriptPath(), False)

    def __onDumpFullDebugSettings(self):
        """Triggered when dumping complete settings is requested"""
        self.__dumpDebugSettings(self.__debugger.getScriptPath(), True)

    def __onDumpScriptDebugSettings(self):
        """Triggered when dumping current script settings is requested"""
        if self.__dumpScriptDbgSettingsAvailable():
            editorsManager = self.editorsManagerWidget.editorsManager
            currentWidget = editorsManager.currentWidget()
            self.__dumpDebugSettings(currentWidget.getFileName(), False)

    def __onDumpScriptFullDebugSettings(self):
        """Triggered when dumping current script complete settings is requested"""
        if self.__dumpScriptDbgSettingsAvailable():
            editorsManager = self.editorsManagerWidget.editorsManager
            currentWidget = editorsManager.currentWidget()
            self.__dumpDebugSettings(currentWidget.getFileName(), True)

    def __onDumpProjectDebugSettings(self):
        """Triggered when dumping project script settings is requested"""
        if self.__dumpProjectDbgSettingsAvailable():
            project = GlobalData().project
            self.__dumpDebugSettings(project.getProjectScript(), False)

    def __onDumpProjectFullDebugSettings(self):
        """Triggered when dumping project script complete settings is requested"""
        if self.__dumpProjectDbgSettingsAvailable():
            project = GlobalData().project
            self.__dumpDebugSettings(project.getProjectScript(), True)

    def __dumpScriptDbgSettingsAvailable(self):
        """True if dumping dbg session settings for the script is available"""
        if not self.__isPythonBuffer():
            return False
        editorsManager = self.editorsManagerWidget.editorsManager
        currentWidget = editorsManager.currentWidget()
        if currentWidget is None:
            return False
        fileName = currentWidget.getFileName()
        if os.path.isabs(fileName) and os.path.exists(fileName):
            return True
        return False

    def __dumpProjectDbgSettingsAvailable(self):
        """True if dumping dbg session settings for the project is available"""
        project = GlobalData().project
        if not project.isLoaded():
            return False
        fileName = project.getProjectScript()
        if os.path.exists(fileName) and os.path.isabs(fileName):
            return True
        return False

    def __onDumpDbgSettingsAboutToShow(self):
        """Dump debug settings is about to show"""
        scriptAvailable = self.__dumpScriptDbgSettingsAvailable()
        self.__debugDumpScriptSettingsAct.setEnabled(scriptAvailable)
        self.__debugDumpScriptSettingsEnvAct.setEnabled(scriptAvailable)

        projectAvailable = self.__dumpProjectDbgSettingsAvailable()
        self.__debugDumpProjectSettingsAct.setEnabled(projectAvailable)
        self.__debugDumpProjectSettingsEnvAct.setEnabled(projectAvailable)

    def installRedirectedIOConsole(self):
        """Create redirected IO console"""
        self.redirectedIOConsole = IOConsoleTabWidget(self)
        self.redirectedIOConsole.sigUserInput.connect(self.__onUserInput)
        self.redirectedIOConsole.sigTextEditorZoom.connect(
            self.editorsManagerWidget.editorsManager.onZoom)
        self.redirectedIOConsole.sigSettingUpdated.connect(
            self.onIOConsoleSettingUpdated)
        self.__bottomSideBar.addTab(
            self.redirectedIOConsole, getIcon('ioconsole.png'),
            'IO console', 'ioredirect', None)
        self.__bottomSideBar.setTabToolTip('ioredirect',
                                           'Redirected IO debug console')

    def clearDebugIOConsole(self):
        """Clears the content of the debug IO console"""
        if self.redirectedIOConsole:
            self.redirectedIOConsole.clear()

    def __onClientStdout(self, data):
        """Triggered when the client reports stdout"""
        self.__bottomSideBar.show()
        self.__bottomSideBar.setCurrentTab('ioredirect')
        self.__bottomSideBar.raise_()
        self.redirectedIOConsole.appendStdoutMessage(data)

    def __onClientStderr(self, data):
        """Triggered when the client reports stderr"""
        self.__bottomSideBar.show()
        self.__bottomSideBar.setCurrentTab('ioredirect')
        self.__bottomSideBar.raise_()
        self.redirectedIOConsole.appendStderrMessage(data)

    def __ioconsoleIDEMessage(self, message):
        """Sends an IDE message to the IO console"""
        self.__bottomSideBar.show()
        self.__bottomSideBar.setCurrentTab('ioredirect')
        self.__bottomSideBar.raise_()
        self.redirectedIOConsole.appendIDEMessage(message)

    def __onClientRawInput(self, prompt, echo):
        """Triggered when the client input is requested"""
        self.__bottomSideBar.show()
        self.__bottomSideBar.setCurrentTab('ioredirect')
        self.__bottomSideBar.raise_()
        self.redirectedIOConsole.rawInput(prompt, echo)
        self.redirectedIOConsole.setFocus()

    def __onUserInput(self, userInput):
        """Triggered when the user finished input in the redirected IO tab"""
        self.__debugger.remoteRawInput(userInput)

    def __getNewRunIndex(self):
        """Provides the new run index"""
        self.__newRunIndex += 1
        return self.__newRunIndex

    def __getNewProfileIndex(self):
        """Provides the new profile index"""
        self.__newProfileIndex += 1
        return self.__newProfileIndex

    def installIOConsole(self, widget, isProfile=False):
        """Installs a new widget at the bottom"""
        if isProfile:
            index = str(self.__getNewProfileIndex())
            caption = "Profiling #" + index
            name = 'profiling#' + index
            tooltip = "Redirected IO profile console #" + index + " (running)"
        else:
            index = str(self.__getNewRunIndex())
            caption = "Run #" + index
            name = 'running#' + index
            tooltip = "Redirected IO run console #" + index + " (running)"

        widget.CloseIOConsole.connect(self.__onCloseIOConsole)
        widget.KillIOConsoleProcess.connect(self.__onKillIOConsoleProcess)
        widget.textEditorZoom.connect(
            self.editorsManagerWidget.editorsManager.onZoom)
        widget.settingUpdated.connect(self.onIOConsoleSettingUpdated)

        self.__bottomSideBar.addTab(
            widget, getIcon('ioconsole.png'), caption, name)
        self.__bottomSideBar.setTabToolTip(name, tooltip)
        self.__bottomSideBar.show()
        self.__bottomSideBar.setCurrentTab(name)
        self.__bottomSideBar.raise_()
        widget.setFocus()

    def updateIOConsoleTooltip(self, threadID, msg):
        """Updates the IO console tooltip"""
        index = self.__getIOConsoleIndex(threadID)
        if index is not None:
            tooltip = self.__bottomSideBar.tabToolTip(index)
            tooltip = tooltip.replace("(running)", "(" + msg + ")")
            self.__bottomSideBar.setTabToolTip(index, tooltip)

    def __getIOConsoleIndex(self, threadID):
        """Provides the IO console index by the thread ID"""
        index = self.__bottomSideBar.count() - 1
        while index >= 0:
            widget = self.__bottomSideBar.widget(index)
            if hasattr(widget, "threadID"):
                if widget.threadID() == threadID:
                    return index
            index -= 1
        return None

    def __onCloseIOConsole(self, threadID):
        """Closes the tab with the corresponding widget"""
        index = self.__getIOConsoleIndex(threadID)
        if index is not None:
            self.__bottomSideBar.removeTab(index)

    def __onKillIOConsoleProcess(self, threadID):
        """Kills the process linked to the IO console"""
        self.__runManager.kill(threadID)

    def closeAllIOConsoles(self):
        """Closes all IO run/profile tabs and clears the debug IO console"""
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        index = self.__bottomSideBar.count - 1
        while index >= 0:
            widget = self.__bottomSideBar.widget(index)
            if hasattr(widget, "getType"):
                if widget.getType() == MainWindowTabWidgetBase.IOConsole:
                    if hasattr(widget, "stopAndClose"):
                        widget.stopAndClose()
            index -= 1

        self.clearDebugIOConsole()
        QApplication.restoreOverrideCursor()

    def passFocusToEditor(self):
        """Passes the focus to the text editor if it is there"""
        return self.editorsManagerWidget.editorsManager.passFocusToEditor()

    def passFocusToFlow(self):
        """Passes the focus to the flow UI if it is there"""
        return self.editorsManagerWidget.editorsManager.passFocusToFlow()
