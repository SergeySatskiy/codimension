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

"""Codimension main window"""

import os.path
import sys
import logging
import gc
from utils.globals import GlobalData
from utils.settings import Settings
from utils.project import CodimensionProject
from utils.misc import (getDefaultTemplate, getIDETemplateFile,
                        getProjectTemplateFile, extendInstance)
from utils.pixmapcache import getIcon
from utils.fileutils import (getFileProperties, isImageViewable, isImageFile,
                             isFileSearchable, isCDMProjectFile)
from utils.diskvaluesrelay import getRunParameters, addRunParams
from diagram.importsdgm import (ImportsDiagramDialog, ImportsDiagramProgress,
                                ImportDiagramOptions)
from utils.run import (getWorkingDir,
                       parseCommandLineArguments, getNoArgsEnvironment,
                       TERM_AUTO, TERM_KONSOLE, TERM_GNOME, TERM_XTERM,
                       TERM_REDIRECT)
from utils.fileutils import isPythonMime
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
from plugins.manager.pluginmanagerdlg import PluginsDialog
from plugins.vcssupport.vcsmanager import VCSManager
from editor.redirectedioconsole import IOConsoleTabWidget
from .qt import (Qt, QSize, QTimer, QDir, QUrl, pyqtSignal, QToolBar, QWidget,
                 QMessageBox, QVBoxLayout, QSplitter, QSizePolicy, QAction,
                 QMainWindow, QShortcut, QApplication, QCursor, QToolButton,
                 QToolTip, QFileDialog, QDialog, QMenu, QDesktopServices)
from .about import AboutDialog
from .runmanager import RunManager
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
from .findreplacewidget import FindReplaceWidget
from .gotolinewidget import GotoLineWidget
from .diffviewer import DiffViewer
from .findinfiles import FindInFilesDialog, ItemToSearchIn, getSearchItemIndex
from .findinfilesviewer import FindInFilesViewer, hideSearchTooltip
from .findname import FindNameDialog
from .findfile import FindFileDialog
from .mainwindowtabwidgetbase import MainWindowTabWidgetBase
from .runparams import RunDialog
from .mainstatusbar import MainWindowStatusBarMixin
from .mainmenu import MainWindowMenuMixin


class EditorsManagerWidget(QWidget):

    """Tab widget which has tabs with editors and viewers"""

    def __init__(self, parent, debugger):

        QWidget.__init__(self, parent)

        self.editorsManager = EditorsManager(parent, debugger)
        self.findReplaceWidget = FindReplaceWidget(self.editorsManager)
        self.gotoLineWidget = GotoLineWidget(self.editorsManager)
        self.editorsManager.registerAuxWidgets(self.findReplaceWidget,
                                               self.gotoLineWidget)

        self.editorsManager.setSizePolicy(QSizePolicy.Preferred,
                                          QSizePolicy.Expanding)
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(1, 1, 1, 1)

        self.layout.addWidget(self.editorsManager)
        self.layout.addWidget(self.findReplaceWidget)
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

        extendInstance(self, MainWindowMenuMixin)
        MainWindowMenuMixin.__init__(self)

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
        self._leftSideBar = None
        self._bottomSideBar = None
        self._rightSideBar = None

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
        self._initMainMenu()

        self.updateWindowTitle()
        self.__printThirdPartyAvailability()

        self.__runManager = RunManager(self)

        Settings().sigTextZoomChanged.connect(self.onTextZoomChanged)

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

    def _onMaximizeEditor(self):
        """Triggered when F11 is pressed"""
        self._leftSideBar.shrink()
        self._bottomSideBar.shrink()
        self._rightSideBar.shrink()

    def __createLayout(self):
        """Creates the UI layout"""
        self.editorsManagerWidget = EditorsManagerWidget(self, self.__debugger)
        self.em = self.editorsManagerWidget.editorsManager
        self.em.sigTabRunChanged.connect(self.setDebugTabAvailable)

        self.editorsManagerWidget.findReplaceWidget.hide()
        self.editorsManagerWidget.gotoLineWidget.hide()

        # The layout is a sidebar-style one
        self._bottomSideBar = SideBar(SideBar.South, self)
        self._leftSideBar = SideBar(SideBar.West, self)
        self._rightSideBar = SideBar(SideBar.East, self)

        # Create tabs on bars
        self.logViewer = LogViewer()
        self._bottomSideBar.addTab(self.logViewer, getIcon('logviewer.png'),
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
        self._leftSideBar.addTab(self.projectViewer, getIcon(''),
                                 'Project', 'project', 0)
        self.em.sigFileUpdated.connect(self.projectViewer.onFileUpdated)
        self.recentProjectsViewer = RecentProjectsViewer(self)
        self._leftSideBar.addTab(self.recentProjectsViewer, getIcon(''),
                                 'Recent', 'recent', 1)
        self.em.sigFileUpdated.connect(self.recentProjectsViewer.onFileUpdated)
        self.em.sigBufferSavedAs.connect(
            self.recentProjectsViewer.onFileUpdated)
        self.projectViewer.sigFileUpdated.connect(
            self.recentProjectsViewer.onFileUpdated)

        self.classesViewer = ClassesViewer()
        self.em.sigFileUpdated.connect(self.classesViewer.onFileUpdated)
        self._leftSideBar.addTab(self.classesViewer, getIcon(''),
                                 'Classes', 'classes', 2)
        self.functionsViewer = FunctionsViewer()
        self.em.sigFileUpdated.connect(self.functionsViewer.onFileUpdated)
        self._leftSideBar.addTab(self.functionsViewer, getIcon(''),
                                 'Functions', 'functions', 3)
        self.globalsViewer = GlobalsViewer()
        self.em.sigFileUpdated.connect(self.globalsViewer.onFileUpdated)
        self._leftSideBar.addTab(self.globalsViewer, getIcon(''),
                                 'Globals', 'globals', 4)

        # Create search results viewer
        self.findInFilesViewer = FindInFilesViewer()
        self._bottomSideBar.addTab(self.findInFilesViewer,
            getIcon('findindir.png'), 'Search results', 'search', 1)

        # Create tag help viewer
        self.tagHelpViewer = TagHelpViewer()
        self._bottomSideBar.addTab(self.tagHelpViewer,
            getIcon('helpviewer.png'), 'Context help', 'contexthelp', 2)
        self._bottomSideBar.setTabToolTip('contexthelp',
                                           "Ctrl+F1 in python file")

        # Create diff viewer
        self.diffViewer = DiffViewer()
        self._bottomSideBar.addTab(self.diffViewer,
            getIcon('diffviewer.png'), 'Diff viewer', 'diff', 3)
        self._bottomSideBar.setTabToolTip('diff', 'No diff shown')

        # Create outline viewer
        self.outlineViewer = FileOutlineViewer(self.em, self)
        self._rightSideBar.addTab(self.outlineViewer, getIcon(''),
                                  'File outline', 'fileoutline', 0)

        # Create the pyflakes viewer
        self.__pyflakesViewer = PyflakesViewer(self.em, self.sbPyflakes, self)

        self.debuggerContext = DebuggerContext(self.__debugger)
        self._rightSideBar.addTab(self.debuggerContext,
            getIcon(''), 'Debugger', 'debugger', 1)
        self._rightSideBar.setTabEnabled('debugger', False)

        self.debuggerExceptions = DebuggerExceptions()
        self._rightSideBar.addTab(self.debuggerExceptions,
            getIcon(''), 'Exceptions', 'exceptions', 2)
        self.debuggerExceptions.sigClientExceptionsCleared.connect(
            self.__onClientExceptionsCleared)

        self.debuggerBreakWatchPoints = DebuggerBreakWatchPoints(
            self, self.__debugger)
        self._rightSideBar.addTab(self.debuggerBreakWatchPoints,
            getIcon(''), 'Breakpoints', 'breakpoints', 3)

        # Create splitters
        self.__horizontalSplitter = QSplitter(Qt.Horizontal)
        self.__verticalSplitter = QSplitter(Qt.Vertical)

        self.__horizontalSplitter.addWidget(self._leftSideBar)
        self.__horizontalSplitter.addWidget(self.editorsManagerWidget)
        self.__horizontalSplitter.addWidget(self._rightSideBar)

        # This prevents changing the size of the side panels
        self.__horizontalSplitter.setCollapsible(0, False)
        self.__horizontalSplitter.setCollapsible(2, False)
        self.__horizontalSplitter.setStretchFactor(0, 0)
        self.__horizontalSplitter.setStretchFactor(1, 1)
        self.__horizontalSplitter.setStretchFactor(2, 0)

        self.__verticalSplitter.addWidget(self.__horizontalSplitter)
        self.__verticalSplitter.addWidget(self._bottomSideBar)
        # This prevents changing the size of the side panels
        self.__verticalSplitter.setCollapsible(1, False)
        self.__verticalSplitter.setStretchFactor(0, 1)
        self.__verticalSplitter.setStretchFactor(1, 1)

        self.setCentralWidget(self.__verticalSplitter)

        self._leftSideBar.setSplitter(self.__horizontalSplitter)
        self._bottomSideBar.setSplitter(self.__verticalSplitter)
        self._rightSideBar.setSplitter(self.__horizontalSplitter)

    def restoreSplitterSizes(self):
        """Restore the side bar state"""
        self.__horizontalSplitter.setSizes(self.settings['hSplitterSizes'])
        self.__verticalSplitter.setSizes(self.settings['vSplitterSizes'])
        if self.settings['leftBarMinimized']:
            self._leftSideBar.shrink()
        if self.settings['bottomBarMinimized']:
            self._bottomSideBar.shrink()
        if self.settings['rightBarMinimized']:
            self._rightSideBar.shrink()

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

        if not self._bottomSideBar.isMinimized():
            self.__verticalSplitterSizes[0] = newSizes[0]

        self.__verticalSplitterSizes[1] = sum(newSizes) - \
            self.__verticalSplitterSizes[0]

    def hSplitterMoved(self, pos, index):
        """Horizontal splitter moved handler"""
        newSizes = list(self.__horizontalSplitter.sizes())

        if not self._leftSideBar.isMinimized():
            self.__horizontalSplitterSizes[0] = newSizes[0]
        if not self._rightSideBar.isMinimized():
            self.__horizontalSplitterSizes[2] = newSizes[2]

        self.__horizontalSplitterSizes[1] = sum(newSizes) - \
            self.__horizontalSplitterSizes[0] - \
            self.__horizontalSplitterSizes[2]

    def __createToolBar(self):
        """creates the buttons bar"""
        # Imports diagram button and its menu
        importsMenu = QMenu(self)
        importsDlgAct = importsMenu.addAction(
            getIcon('detailsdlg.png'), 'Fine tuned imports diagram')
        importsDlgAct.triggered.connect(self._onImportDgmTuned)
        self.importsDiagramButton = QToolButton(self)
        self.importsDiagramButton.setIcon(getIcon('importsdiagram.png'))
        self.importsDiagramButton.setToolTip('Generate imports diagram')
        self.importsDiagramButton.setPopupMode(QToolButton.DelayedPopup)
        self.importsDiagramButton.setMenu(importsMenu)
        self.importsDiagramButton.setFocusPolicy(Qt.NoFocus)
        self.importsDiagramButton.clicked.connect(self._onImportDgm)

        # Run project button and its menu
        runProjectMenu = QMenu(self)
        runProjectAct = runProjectMenu.addAction(
            getIcon('detailsdlg.png'), 'Set run parameters')
        runProjectAct.triggered.connect(self._onRunProjectSettings)
        self.runProjectButton = QToolButton(self)
        self.runProjectButton.setIcon(getIcon('run.png'))
        self.runProjectButton.setToolTip('Project is not loaded')
        self.runProjectButton.setPopupMode(QToolButton.DelayedPopup)
        self.runProjectButton.setMenu(runProjectMenu)
        self.runProjectButton.setFocusPolicy(Qt.NoFocus)
        self.runProjectButton.clicked.connect(self._onRunProject)

        # profile project button and its menu
        profileProjectMenu = QMenu(self)
        profileProjectAct = profileProjectMenu.addAction(
            getIcon('detailsdlg.png'), 'Set profile parameters')
        profileProjectAct.triggered.connect(self._onProfileProjectSettings)
        self.profileProjectButton = QToolButton(self)
        self.profileProjectButton.setIcon(getIcon('profile.png'))
        self.profileProjectButton.setToolTip('Project is not loaded')
        self.profileProjectButton.setPopupMode(QToolButton.DelayedPopup)
        self.profileProjectButton.setMenu(profileProjectMenu)
        self.profileProjectButton.setFocusPolicy(Qt.NoFocus)
        self.profileProjectButton.clicked.connect(self._onProfileProject)

        # Debug project button and its menu
        debugProjectMenu = QMenu(self)
        debugProjectAct = debugProjectMenu.addAction(
            getIcon('detailsdlg.png'), 'Set debug parameters')
        debugProjectAct.triggered.connect(self._onDebugProjectSettings)
        self.debugProjectButton = QToolButton(self)
        self.debugProjectButton.setIcon(getIcon('debugger.png'))
        self.debugProjectButton.setToolTip('Project is not loaded')
        self.debugProjectButton.setPopupMode(QToolButton.DelayedPopup)
        self.debugProjectButton.setMenu(debugProjectMenu)
        self.debugProjectButton.setFocusPolicy(Qt.NoFocus)
        self.debugProjectButton.clicked.connect(self._onDebugProject)
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
        self.__dbgStopBrutal.triggered.connect(self._onBrutalStopDbgSession)
        self.__dbgStopBrutal.setVisible(False)
        self.__dbgStopAndClearIO = QAction(
            getIcon('dbgstopcleario.png'),
            'Stop debugging session and clear IO console', self)
        self.__dbgStopAndClearIO.triggered.connect(
            self._onBrutalStopDbgSession)
        self.__dbgStopAndClearIO.setVisible(False)
        self.__dbgStop = QAction(
            getIcon('dbgstop.png'),
            'Stop debugging session and keep console if so (F10)', self)
        self.__dbgStop.triggered.connect(self._onStopDbgSession)
        self.__dbgStop.setVisible(False)
        self.__dbgRestart = QAction(
            getIcon('dbgrestart.png'), 'Restart debugging section (F4)', self)
        self.__dbgRestart.triggered.connect(self._onRestartDbgSession)
        self.__dbgRestart.setVisible(False)
        self.__dbgGo = QAction(getIcon('dbggo.png'), 'Continue (F6)', self)
        self.__dbgGo.triggered.connect(self._onDbgGo)
        self.__dbgGo.setVisible(False)
        self.__dbgNext = QAction(
            getIcon('dbgnext.png'), 'Step over (F8)', self)
        self.__dbgNext.triggered.connect(self._onDbgNext)
        self.__dbgNext.setVisible(False)
        self.__dbgStepInto = QAction(
            getIcon('dbgstepinto.png'), 'Step into (F7)', self)
        self.__dbgStepInto.triggered.connect(self._onDbgStepInto)
        self.__dbgStepInto.setVisible(False)
        self.__dbgRunToLine = QAction(
            getIcon('dbgruntoline.png'), 'Run to cursor (Shift+F6)', self)
        self.__dbgRunToLine.triggered.connect(self._onDbgRunToLine)
        self.__dbgRunToLine.setVisible(False)
        self.__dbgReturn = QAction(
            getIcon('dbgreturn.png'), 'Step out (F9)', self)
        self.__dbgReturn.triggered.connect(self._onDbgReturn)
        self.__dbgReturn.setVisible(False)
        self.__dbgJumpToCurrent = QAction(
            getIcon('dbgtocurrent.png'),
            'Show current debugger line (Ctrl+W)', self)
        self.__dbgJumpToCurrent.triggered.connect(self._onDbgJumpToCurrent)
        self.__dbgJumpToCurrent.setVisible(False)

        dumpDebugSettingsMenu = QMenu(self)
        dumpDebugSettingsAct = dumpDebugSettingsMenu.addAction(
            getIcon('detailsdlg.png'),
            'Dump settings with complete environment')
        dumpDebugSettingsAct.triggered.connect(self._onDumpFullDebugSettings)
        self.__dbgDumpSettingsButton = QToolButton(self)
        self.__dbgDumpSettingsButton.setIcon(getIcon('dbgsettings.png'))
        self.__dbgDumpSettingsButton.setToolTip('Dump debug session settings')
        self.__dbgDumpSettingsButton.setPopupMode(QToolButton.DelayedPopup)
        self.__dbgDumpSettingsButton.setMenu(dumpDebugSettingsMenu)
        self.__dbgDumpSettingsButton.setFocusPolicy(Qt.NoFocus)
        self.__dbgDumpSettingsButton.clicked.connect(
            self._onDumpDebugSettings)

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
            self._unloadProjectAct.setEnabled(projectLoaded)
            self._projectPropsAct.setEnabled(projectLoaded)
            self._prjTemplateMenu.setEnabled(projectLoaded)
            self._findNameMenuAct.setEnabled(projectLoaded)
            self._fileProjectFileAct.setEnabled(projectLoaded)
            self._prjLineCounterAct.setEnabled(projectLoaded)
            self._prjImportDgmAct.setEnabled(projectLoaded)
            self._prjImportsDgmDlgAct.setEnabled(projectLoaded)

            self.settings['projectLoaded'] = projectLoaded
            if projectLoaded:
                # The editor tabs must be loaded after a VCS plugin has a
                # chance to receive sigProjectChanged signal where it reads
                # the plugin configuration
                QTimer.singleShot(1, self.__delayedEditorsTabRestore)
        self.updateRunDebugButtons()

    def __delayedEditorsTabRestore(self):
        """Delayed restore editor tabs"""
        self.em.restoreTabs(GlobalData().project.tabStatus)

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
            self._prjDebugAct.setEnabled(False)
            self._prjDebugDlgAct.setEnabled(False)
            self._tabDebugAct.setEnabled(False)
            self._tabDebugDlgAct.setEnabled(False)
            self.profileProjectButton.setEnabled(False)
            self.profileProjectButton.setToolTip("Cannot profile project - "
                                                 "debug in progress")
            return

        if not GlobalData().project.isLoaded():
            self.runProjectButton.setEnabled(False)
            self.runProjectButton.setToolTip("Run project")
            self.debugProjectButton.setEnabled(False)
            self.debugProjectButton.setToolTip("Debug project")
            self._prjDebugAct.setEnabled(False)
            self._prjDebugDlgAct.setEnabled(False)
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
            self._prjDebugAct.setEnabled(False)
            self._prjDebugDlgAct.setEnabled(False)
            self.profileProjectButton.setEnabled(False)
            self.profileProjectButton.setToolTip(
                "Cannot profile project - script is not specified or invalid")
            return

        self.runProjectButton.setEnabled(True)
        self.runProjectButton.setToolTip("Run project")
        self.debugProjectButton.setEnabled(True)
        self.debugProjectButton.setToolTip("Debug project")
        self._prjDebugAct.setEnabled(True)
        self._prjDebugDlgAct.setEnabled(True)
        self.profileProjectButton.setEnabled(True)
        self.profileProjectButton.setToolTip("Profile project")

    @staticmethod
    def linecounterButtonClicked():
        """Triggered when the line counter button is clicked"""
        LineCounterDialog().exec_()

    def findInFilesClicked(self):
        """Triggered when the find in files button is clicked"""
        searchText = ""
        currentWidget = self.em.currentWidget()
        if currentWidget.getType() in \
           [MainWindowTabWidgetBase.PlainTextEditor]:
            searchText = currentWidget.getEditor().getSearchText()

        dlg = FindInFilesDialog(FindInFilesDialog.IN_PROJECT, searchText, "")
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
        self._activateSideTab('log')

    def openFile(self, path, lineNo, pos=0):
        """User double clicked on a file or an item in a file"""
        self.em.openFile(path, lineNo, pos)

    def gotoInBuffer(self, uuid, lineNo):
        """Usually needs when an item is clicked in the file outline browser"""
        self.em.gotoInBuffer(uuid, lineNo)

    def jumpToLine(self, lineNo):
        """Usually needs when rope provided definition
           in the current unsaved buffer
        """
        self.em.jumpToLine(lineNo)

    def openPixmapFile(self, path):
        """User double clicked on a file"""
        self.em.openPixmapFile(path)

    def openDiagram(self, scene, tooltip):
        """Show a generated diagram"""
        self.em.openDiagram(scene, tooltip)

    def detectTypeAndOpenFile(self, path, lineNo=-1):
        """Detects the file type and opens the corresponding editor/browser"""
        mime, _, _ = getFileProperties(path)
        self.openFileByType(mime, path, lineNo)

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

    def notImplementedYet(self):
        """Shows a dummy window"""
        QMessageBox.about(self, 'Not implemented yet',
                          'This function has not been implemented yet')

    def closeEvent(self, event):
        """Triggered when the IDE is closed"""
        # Save the side bars status
        self.settings['vSplitterSizes'] = self.__verticalSplitterSizes
        self.settings['hSplitterSizes'] = self.__horizontalSplitterSizes
        self.settings['bottomBarMinimized'] = self._bottomSideBar.isMinimized()
        self.settings['leftBarMinimized'] = self._leftSideBar.isMinimized()
        self.settings['rightBarMinimized'] = self._rightSideBar.isMinimized()

        # Ask the editors manager to close all the editors
        if self.em.getUnsavedCount() == 0:
            project = GlobalData().project
            if project.isLoaded():
                project.tabsStatus = self.em.getTabsStatus()
                self.settings.tabsStatus = []
            else:
                self.settings.tabsStatus = self.em.getTabsStatus()

        if self.em.closeEvent(event):
            # The IDE is going to be closed just now
            if self.debugMode:
                self._onBrutalStopDbgSession()

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

        self._bottomSideBar.show()
        self._bottomSideBar.setCurrentTab('contexthelp')
        self._bottomSideBar.raise_()

        self.tagHelpViewer.display(calltip, docstring)

    def showDiff(self, diff, tooltip):
        """Shows the diff"""
        self._bottomSideBar.show()
        self._bottomSideBar.setCurrentTab('diff')
        self._bottomSideBar.raise_()

        try:
            self._bottomSideBar.setTabToolTip('diff', tooltip)
            self.diffViewer.setHTML(parse_from_memory(diff, False, True),
                                    tooltip)
        except Exception as exc:
            logging.error("Error showing diff: " + str(exc))

    def showDiffInMainArea(self, content, tooltip):
        """Shows the given diff in the main editing area"""
        self.em.showDiff(content, tooltip)

    def onTextZoomChanged(self):
        """Triggered when a text zoom is changed"""
        self.logViewer.onTextZoomChanged()
        self.diffViewer.onTextZoomChanged()

        # Handle run/profile IO consoles and the debug IO console
        index = self._bottomSideBar.count - 1
        while index >= 0:
            widget = self._bottomSideBar.widget(index)
            if hasattr(widget, "getType"):
                if widget.getType() == MainWindowTabWidgetBase.IOConsole:
                    widget.onTextZoomChanged()
            index -= 1

    def onIOConsoleSettingUpdated(self):
        """Initiates updating all the IO consoles settings"""
        index = self._bottomSideBar.count() - 1
        while index >= 0:
            widget = self._bottomSideBar.widget(index)
            if hasattr(widget, "getType"):
                if widget.getType() == MainWindowTabWidgetBase.IOConsole:
                    widget.consoleSettingsUpdated()
            index -= 1

    def showProfileReport(self, widget, tooltip):
        """Shows the given profile report"""
        self.em.showProfileReport(widget, tooltip)

    def getWidgetByUUID(self, uuid):
        """Provides the widget found by the given UUID"""
        return self.em.getWidgetByUUID(uuid)

    def getWidgetForFileName(self, fname):
        """Provides the widget found by the given file name"""
        return self.em.getWidgetForFileName(fname)

    def editorsManager(self):
        """Provides the editors manager"""
        return self.em

    def _onCreateIDETemplate(self):
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

    def _onEditIDETemplate(self):
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
    def _onDelIDETemplate():
        """Triggered to del IDE template"""
        fileName = getIDETemplateFile()
        if fileName is not None:
            if os.path.exists(fileName):
                os.unlink(fileName)
                logging.info("IDE new file template deleted")

    def displayFindInFiles(self, searchRegexp, searchResults):
        """Displays the results on a tab"""
        self.findInFilesViewer.showReport(searchRegexp, searchResults)

        if self._bottomSideBar.height() == 0:
            # It was hidden completely, so need to move the slider
            splitterSizes = self.settings.vSplitterSizes
            splitterSizes[0] -= 200
            splitterSizes[1] += 200
            self.__verticalSplitter.setSizes(splitterSizes)

        self._bottomSideBar.show()
        self._bottomSideBar.setCurrentTab('search')
        self._bottomSideBar.raise_()

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

    def _onImportDgmTuned(self):
        """Runs the settings dialog first"""
        dlg = ImportsDiagramDialog(ImportsDiagramDialog.ProjectFiles,
                                   "", self)
        if dlg.exec_() == QDialog.Accepted:
            self.__generateImportDiagram(dlg.options)

    def _onImportDgm(self, action=False):
        """Runs the generation process"""
        self.__generateImportDiagram(ImportDiagramOptions())

    def __generateImportDiagram(self, options):
        """Show the generation progress and display the diagram"""
        progressDlg = ImportsDiagramProgress(ImportsDiagramDialog.ProjectFiles,
                                             options)
        if progressDlg.exec_() == QDialog.Accepted:
            self.openDiagram(progressDlg.scene, "Generated for the project")

    def _onRunProjectSettings(self):
        """Brings up the dialog with run script settings"""
        if self.__checkProjectScriptValidity():
            fileName = GlobalData().project.getProjectScript()
            self.__runManager.run(fileName, True)

    def _onProfileProjectSettings(self):
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
                self._onProfileProject()

    def _onDebugProjectSettings(self):
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
                self._onDebugProject()

    def _onRunProject(self, action=False):
        """Runs the project with saved sattings"""
        if self.__checkProjectScriptValidity():
            fileName = GlobalData().project.getProjectScript()
            self.__runManager.run(fileName, False)

    def _onProfileProject(self, action=False):
        """Profiles the project with saved settings"""
        if self.__checkProjectScriptValidity():
            try:
                dlg = ProfilingProgressDialog(
                    GlobalData().project.getProjectScript(), self)
                dlg.exec_()
            except Exception as exc:
                logging.error(str(exc))

    def _onDebugProject(self, action=False):
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

        modifiedFiles = self.em.getModifiedList(True)
        if len(modifiedFiles) == 0:
            return True

        dlg = ModifiedUnsavedDialog(modifiedFiles, "Save and debug")
        if dlg.exec_() != QDialog.Accepted:
            # Selected to cancel
            return False

        # Need to save the modified project files
        return self.em.saveModified(True)

    def __checkProjectScriptValidity(self):
        """Checks and logs error message if so. Returns True if all is OK"""
        if not GlobalData().isProjectScriptValid():
            self.updateRunDebugButtons()
            logging.error("Invalid project script. "
                          "Use project properties dialog to "
                          "select existing python script.")
            return False
        return True

    def _isPythonBuffer(self):
        """True if the current tab is a python buffer"""
        currentWidget = self.em.currentWidget()
        if currentWidget is None:
            return False
        return currentWidget.getType() in \
            [MainWindowTabWidgetBase.PlainTextEditor,
             MainWindowTabWidgetBase.VCSAnnotateViewer] and \
            isPythonMime(currentWidget.getMime())

    def _verticalEdgeChanged(self):
        """Editor setting changed"""
        self.settings['verticalEdge'] = not self.settings['verticalEdge']
        self.em.updateEditorsSettings()

    def _showSpacesChanged(self):
        """Editor setting changed"""
        self.settings['showSpaces'] = not self.settings['showSpaces']
        self.em.updateEditorsSettings()

    def _lineWrapChanged(self):
        """Editor setting changed"""
        self.settings['lineWrap'] = not self.settings['lineWrap']
        self.em.updateEditorsSettings()

    def _showEOLChanged(self):
        """Editor setting changed"""
        self.settings['showEOL'] = not self.settings['showEOL']
        self.em.updateEditorsSettings()

    def _showBraceMatchChanged(self):
        """Editor setting changed"""
        self.settings['showBraceMatch'] = not self.settings['showBraceMatch']
        self.em.updateEditorsSettings()

    def _autoIndentChanged(self):
        """Editor setting changed"""
        self.settings['autoIndent'] = not self.settings['autoIndent']
        self.em.updateEditorsSettings()

    def _backspaceUnindentChanged(self):
        """Editor setting changed"""
        self.settings['backspaceUnindent'] = \
            not self.settings['backspaceUnindent']
        self.em.updateEditorsSettings()

    def _tabIndentsChanged(self):
        """Editor setting changed"""
        self.settings['tabIndents'] = not self.settings['tabIndents']
        self.em.updateEditorsSettings()

    def _indentationGuidesChanged(self):
        """Editor setting changed"""
        self.settings['indentationGuides'] = \
            not self.settings['indentationGuides']
        self.em.updateEditorsSettings()

    def _currentLineVisibleChanged(self):
        """Editor setting changed"""
        self.settings['currentLineVisible'] = \
            not self.settings['currentLineVisible']
        self.em.updateEditorsSettings()

    def _homeToFirstNonSpaceChanged(self):
        """Editor setting changed"""
        self.settings['jumpToFirstNonSpace'] = \
            not self.settings['jumpToFirstNonSpace']
        self.em.updateEditorsSettings()

    def _removeTrailingChanged(self):
        """Editor setting changed"""
        self.settings['removeTrailingOnSave'] = \
            not self.settings['removeTrailingOnSave']

    def _editorCalltipsChanged(self):
        """Editor calltips changed"""
        self.settings['editorCalltips'] = not self.settings['editorCalltips']

    def _clearDebugIOChanged(self):
        """Clear debug IO console before a new session changed"""
        self.settings['clearDebugIO'] = not self.settings['clearDebugIO']

    def _showNavBarChanged(self):
        """Editor setting changed"""
        self.settings['showNavigationBar'] = \
            not self.settings['showNavigationBar']
        self.em.updateEditorsSettings()

    def _showCFNavBarChanged(self):
        """Control flow toolbar visibility changed"""
        self.settings['showCFNavigationBar'] = \
            not self.settings['showCFNavigationBar']
        self.em.updateCFEditorsSettings()

    def _showMainToolbarChanged(self):
        """Main toolbar visibility changed"""
        self.settings['showMainToolBar'] = \
            not self.settings['showMainToolBar']
        self.__toolbar.setVisible(self.settings['showMainToolBar'])

    def _projectTooltipsChanged(self):
        """Tooltips setting changed"""
        self.settings['projectTooltips'] = \
            not self.settings['projectTooltips']
        self.projectViewer.setTooltips(self.settings['projectTooltips'])

    def _recentTooltipsChanged(self):
        """Tooltips setting changed"""
        self.settings['recentTooltips'] = \
            not self.settings['recentTooltips']
        self.recentProjectsViewer.setTooltips(self.settings['recentTooltips'])

    def _classesTooltipsChanged(self):
        """Tooltips setting changed"""
        self.settings['classesTooltips'] = \
            not self.settings['classesTooltips']
        self.classesViewer.setTooltips(self.settings['classesTooltips'])

    def _functionsTooltipsChanged(self):
        """Tooltips setting changed"""
        self.settings['functionsTooltips'] = \
            not self.settings['functionsTooltips']
        self.functionsViewer.setTooltips(self.settings['functionsTooltips'])

    def _outlineTooltipsChanged(self):
        """Tooltips setting changed"""
        self.settings.outlineTooltips = \
            not self.settings['outlineTooltips']
        self.outlineViewer.setTooltips(self.settings['outlineTooltips'])

    def _findNameTooltipsChanged(self):
        """Tooltips setting changed"""
        self.settings['findNameTooltips'] = \
            not self.settings['findNameTooltips']

    def _findFileTooltipsChanged(self):
        """Tooltips setting changed"""
        self.settings['findFileTooltips'] = \
            not self.settings['findFileTooltips']

    def _editorTooltipsChanged(self):
        """Tooltips setting changed"""
        self.settings['editorTooltips'] = \
            not self.settings['editorTooltips']
        self.em.setTooltips(self.settings['editorTooltips'])

    def _tabOrderPreservedChanged(self):
        """Tab order preserved option changed"""
        self.settings['taborderpreserved'] = \
            not self.settings['taborderpreserved']

    def _openTabsMenuTriggered(self, act):
        """Tab list settings menu triggered"""
        if act == -1:
            self.settings.tablistsortalpha = True
            self.__alphasort.setChecked(True)
            self.__tabsort.setChecked(False)
        elif act == -2:
            self.settings.tablistsortalpha = False
            self.__alphasort.setChecked(False)
            self.__tabsort.setChecked(True)

    def _onTheme(self, skinSubdir):
        """Triggers when a theme is selected"""
        if self.settings['skin'] != skinSubdir.data():
            logging.info("Please restart codimension to apply the new theme")
            self.settings['skin'] = skinSubdir.data()

    def _onStyle(self, styleName):
        """Sets the selected style"""
        QApplication.setStyle(styleName.data())
        self.settings['style'] = styleName.data().lower()

    def _onMonoFont(self, fontFamily):
        """Sets the new mono font"""
        newFontFamily = fontFamily.data()
        if newFontFamily != GlobalData().skin['monoFont'].family():
            GlobalData().skin.setTextMonoFontFamily(newFontFamily)
            self.em.onTextZoomChanged()
            self.onTextZoomChanged()

    def _onFlowMonoFont(self, fontFamily):
        """Sets the new flow font"""
        newFontFamily = fontFamily.data()
        if newFontFamily != GlobalData().skin['cfMonoFont'].family():
            GlobalData().skin.setFlowMonoFontFamily(newFontFamily)
            self.em.onFlowZoomChanged()

    def checkOutsideFileChanges(self):
        """Checks if there are changes in the currently opened files"""
        self.em.checkOutsideFileChanges()

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
            self._rightSideBar.setTabEnabled(1, True)    # vars etc.
            self.debuggerContext.clear()
            self.debuggerExceptions.clear()
            self._rightSideBar.setTabText(2, "Exceptions")
            self._rightSideBar.show()
            self._rightSideBar.setCurrentTab('debugger')
            self._rightSideBar.raise_()
            self.__lastDebugAction = None
            self.__debugDumpSettingsAct.setEnabled(True)
            self.__debugDumpSettingsEnvAct.setEnabled(True)
        else:
            if not self._rightSideBar.isMinimized():
                if self._rightSideBar.currentIndex() == 1:
                    self._rightSideBar.setCurrentTab('fileoutline')
            self._rightSideBar.setTabEnabled(1, False)    # vars etc.

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
        self._onDbgJumpToCurrent()

    def __onDebuggerClientException(self, excType, excMessage, excStackTrace):
        """Debugged program exception handler"""
        self.debuggerExceptions.addException(excType, excMessage,
                                             excStackTrace)
        count = self.debuggerExceptions.getTotalClientExceptionCount()
        self._rightSideBar.setTabText(2, "Exceptions (" + str(count) + ")")

        # The information about the exception is stored in the exception window
        # regardless whether there is a stack trace or not. So, there is no
        # need to show the exception info in the closing dialog (if this dialog
        # is required).

        if excType is None or excType.startswith("unhandled") or not excStackTrace:
            self._rightSideBar.show()
            self._rightSideBar.setCurrentTab('exceptions')
            self._rightSideBar.raise_()

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
                QTimer.singleShot(0, self._onStopDbgSession)
            else:
                QTimer.singleShot(0, self._onBrutalStopDbgSession)
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
        self._rightSideBar.show()
        self._rightSideBar.setCurrentTab('exceptions')
        self._rightSideBar.raise_()

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
            self.em.openFile(fileName, lineNo)
            editor = self.em.currentWidget().getEditor()
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
            QTimer.singleShot(0, self._onStopDbgSession)
        else:
            QTimer.singleShot(0, self._onBrutalStopDbgSession)

    def __onDebuggerClientIDEMessage(self, message):
        """Triggered when the debug server has something to report"""
        if self.settings.terminalType == TERM_REDIRECT:
            self.__ioconsoleIDEMessage(str(message))
        else:
            logging.info(str(message))

    def __removeCurrenDebugLineHighlight(self):
        """Removes the current debug line highlight"""
        if self.__lastDebugFileName is not None:
            widget = self.em.getWidgetForFileName(self.__lastDebugFileName)
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
        if not self._isPythonBuffer():
            self.__dbgRunToLine.setEnabled(False)
            self.__debugRunToCursorAct.setEnabled(False)
            return

        # That's for sure a python buffer, so the widget exists
        currentWidget = self.em.currentWidget()
        if currentWidget.getType() in [MainWindowTabWidgetBase.VCSAnnotateViewer]:
            self.__dbgRunToLine.setEnabled(False)
            self.__debugRunToCursorAct.setEnabled(False)
            return

        enabled = currentWidget.isLineBreakable()
        self.__dbgRunToLine.setEnabled(enabled)
        self.__debugRunToCursorAct.setEnabled(enabled)

    def _onBrutalStopDbgSession(self):
        """Stop debugging brutally"""
        self.__debugger.stopDebugging(True)
        if self.settings.terminalType == TERM_REDIRECT:
            self.redirectedIOConsole.clear()

    def _onStopDbgSession(self):
        """Debugger stop debugging clicked"""
        self.__debugger.stopDebugging(False)

    def _onRestartDbgSession(self):
        """Debugger restart session clicked"""
        fileName = self.__debugger.getScriptPath()
        self._onBrutalStopDbgSession()
        self.__debugger.startDebugging(fileName)

    def _onDbgGo(self):
        """Debugger continue clicked"""
        self.__lastDebugAction = self.DEBUG_ACTION_GO
        self.__debugger.remoteContinue()

    def _onDbgNext(self):
        """Debugger step over clicked"""
        self.__lastDebugAction = self.DEBUG_ACTION_NEXT
        self.__debugger.remoteStepOver()

    def _onDbgStepInto(self):
        """Debugger step into clicked"""
        self.__lastDebugAction = self.DEBUG_ACTION_STEP_INTO
        self.__debugger.remoteStep()

    def _onDbgRunToLine(self):
        """Debugger run to cursor clicked"""
        # The run-to-line button state is set approprietly
        if not self.__dbgRunToLine.isEnabled():
            return

        self.__lastDebugAction = self.DEBUG_ACTION_RUN_TO_LINE
        currentWidget = self.em.currentWidget()

        self.__debugger.remoteBreakpoint(currentWidget.getFileName(),
                                         currentWidget.getLine() + 1,
                                         True, None, True)
        self.__debugger.remoteContinue()

    def _onDbgReturn(self):
        """Debugger step out clicked"""
        self.__lastDebugAction = self.DEBUG_ACTION_STEP_OUT
        self.__debugger.remoteStepOut()

    def _onDbgJumpToCurrent(self):
        """Jump to the current debug line"""
        if self.__lastDebugFileName is None or \
           self.__lastDebugLineNumber is None or \
           self.__lastDebugAsException is None:
            return

        self.em.openFile(self.__lastDebugFileName, self.__lastDebugLineNumber)

        editor = self.em.currentWidget().getEditor()
        editor.gotoLine(self.__lastDebugLineNumber)
        editor.highlightCurrentDebuggerLine(self.__lastDebugLineNumber,
                                            self.__lastDebugAsException)
        self.em.currentWidget().setFocus()

    def __loadProject(self, projectFile):
        """Loads the given project"""
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        if self.em.closeRequest():
            prj = GlobalData().project
            prj.tabsStatus = self.em.getTabsStatus()
            self.em.closeAll()
            prj.loadProject(projectFile)
            if not self._leftSideBar.isMinimized():
                self.activateProjectTab()
        QApplication.restoreOverrideCursor()

    def _openFile(self):
        """Triggers when Ctrl+O is pressed"""
        dialog = QFileDialog(self, 'Open file')
        dialog.setFileMode(QFileDialog.ExistingFiles)
        urls = []
        for dname in QDir.drives():
            urls.append(QUrl.fromLocalFile(dname.absoluteFilePath()))
        urls.append(QUrl.fromLocalFile(QDir.homePath()))

        try:
            fileName = self.em.currentWidget().getFileName()
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

    def _onTabImportDgm(self):
        """Triggered when tab imports diagram is requested"""
        self.em.currentWidget().onImportDgm()

    def _onTabImportDgmTuned(self):
        """Triggered when tuned tab imports diagram is requested"""
        self.em.currentWidget().onImportDgmTuned()

    def onRunTab(self):
        """Triggered when run tab script is requested"""
        currentWidget = self.em.currentWidget()
        self.__runManager.run(currentWidget.getFileName(), False)

    def _onDebugTab(self):
        """Triggered when debug tab is requested"""
        self.em.currentWidget().onDebugScript()

    def _onProfileTab(self):
        """Triggered when profile script is requested"""
        self.em.currentWidget().onProfileScript()

    def onRunTabDlg(self):
        """Triggered when run tab script dialog is requested"""
        currentWidget = self.em.currentWidget()
        self.__runManager.run(currentWidget.getFileName(), True)

    def _onDebugTabDlg(self):
        """Triggered when debug tab script dialog is requested"""
        self.em.currentWidget().onDebugScriptSettings()

    def _onProfileTabDlg(self):
        """Triggered when profile tab script dialog is requested"""
        self.em.currentWidget().onProfileScriptSettings()

    def _onPluginManager(self):
        """Triggered when a plugin manager dialog is requested"""
        dlg = PluginsDialog(GlobalData().pluginManager, self)
        dlg.exec_()

    def _onContextHelp(self):
        """Triggered when Ctrl+F1 is clicked"""
        self.em.currentWidget().getEditor().onTagHelp()

    def _onCallHelp(self):
        """Triggered when a context help for the current call is requested"""
        self.em.currentWidget().getEditor().onCallHelp()

    @staticmethod
    def _onHomePage():
        """Triggered when opening the home page is requested"""
        QDesktopServices.openUrl(QUrl("http://codimension.org"))

    @staticmethod
    def _onAllShortcurs():
        """Triggered when opening key bindings page is requested"""
        QDesktopServices.openUrl(
            QUrl("http://codimension.org/documentation/cheatsheet.html"))

    def _onAbout(self):
        """Triggered when 'About' info is requested"""
        dlg = AboutDialog(self)
        dlg.exec_()

    def _activateSideTab(self, act):
        """Triggered when a side bar should be activated"""
        if isinstance(act, str):
            name = act
        else:
            name = act.data()
        if name in ["project", "recent", "classes", "functions", "globals"]:
            self._leftSideBar.show()
            self._leftSideBar.setCurrentTab(name)
            self._leftSideBar.raise_()
        elif name in ['fileoutline', 'debugger', 'exceptions', 'breakpoints']:
            self._rightSideBar.show()
            self._rightSideBar.setCurrentTab(name)
            self._rightSideBar.raise_()
        elif name in ['log', 'search', 'contexthelp', 'diff']:
            self._bottomSideBar.show()
            self._bottomSideBar.setCurrentTab(name)
            self._bottomSideBar.raise_()

    def _onTabLineCounter(self):
        """Triggered when line counter for the current buffer is requested"""
        self.em.currentWidget().onLineCounter()

    def _onTabJumpToDef(self):
        """Triggered when jump to defenition is requested"""
        self.em.currentWidget().getEditor().onGotoDefinition()

    def _onTabJumpToScopeBegin(self):
        """Triggered when jump to the beginning
           of the current scope is requested
        """
        self.em.currentWidget().getEditor().onScopeBegin()

    def _onFindOccurences(self):
        """Triggered when search for occurences is requested"""
        self.em.currentWidget().getEditor().onOccurences()

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

    def _onTabOpenImport(self):
        """Triggered when open import is requested"""
        self.em.currentWidget().onOpenImport()

    def _onShowCalltip(self):
        """Triggered when show calltip is requested"""
        self.em.currentWidget().getEditor().onShowCalltip()

    def _onOpenAsFile(self):
        """Triggered when open as file is requested"""
        self.em.currentWidget().getEditor().openAsFile()

    def _onDownloadAndShow(self):
        """Triggered when a selected string should be treated as URL"""
        self.em.currentWidget().getEditor().downloadAndShow()

    def _onOpenInBrowser(self):
        """Triggered when a selected url should be opened in a browser"""
        self.em.currentWidget().getEditor().openInBrowser()

    def _onHighlightInOutline(self):
        """Triggered to highlight the current context in the outline browser"""
        self.em.currentWidget().getEditor().highlightInOutline()

    def _onUndo(self):
        """Triggered when undo action is requested"""
        self.em.currentWidget().getEditor().onUndo()

    def _onRedo(self):
        """Triggered when redo action is requested"""
        self.em.currentWidget().getEditor().onRedo()

    def _onGoToLine(self):
        """Triggered when go to line is requested"""
        self.em.onGoto()

    def __getEditor(self):
        """Provides reference to the editor"""
        return self.em.currentWidget().getEditor()

    def _onCut(self):
        """Triggered when cut is requested"""
        self.__getEditor().onShiftDel()

    def _onPaste(self):
        """Triggered when paste is requested"""
        self.__getEditor().paste()

    def _onSelectAll(self):
        """Triggered when select all is requested"""
        self.__getEditor().selectAll()

    def _onComment(self):
        """Triggered when comment/uncomment is requested"""
        self.__getEditor().onCommentUncomment()

    def _onDuplicate(self):
        """Triggered when duplicate line is requested"""
        self.__getEditor().duplicateLine()

    def _onAutocomplete(self):
        """Triggered when autocomplete is requested"""
        self.__getEditor().onAutoComplete()

    def _onFind(self):
        """Triggered when find is requested"""
        self.em.onFind()

    def _onReplace(self):
        """Triggered when replace is requested"""
        self.em.onReplace()

    def _onFindNext(self):
        """Triggered when find next is requested"""
        self.em.findNext()

    def _onFindPrevious(self):
        """Triggered when find previous is requested"""
        self.em.findPrev()

    def _onExpandTabs(self):
        """Triggered when tabs expansion is requested"""
        self.em.currentWidget().onExpandTabs()

    def _onRemoveTrailingSpaces(self):
        """Triggered when trailing spaces removal is requested"""
        self.em.currentWidget().onRemoveTrailingWS()

    def _onRecentFile(self, path):
        """Triggered when a recent file is requested to be loaded"""
        path = path.data()
        if isImageFile(path):
            self.openPixmapFile(path)
        else:
            self.openFile(path, -1)

    def _createNewProject(self):
        """Create new action"""
        if not self.em.closeRequest():
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
        prj.tabxsStatus = self.em.getTabsStatus()
        self.em.closeAll()

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

    def _openProject(self):
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

    def _onCreatePrjTemplate(self):
        """Triggered when project template should be created"""
        self.createTemplateFile(getProjectTemplateFile())

    def _onEditPrjTemplate(self):
        """Triggered when project template should be edited"""
        self.editTemplateFile(getProjectTemplateFile())

    @staticmethod
    def _onDelPrjTemplate():
        """Triggered when project template should be deleted"""
        fileName = getProjectTemplateFile()
        if fileName is not None:
            if os.path.exists(fileName):
                os.unlink(fileName)
                logging.info("Project new file template deleted")

    def _onRecentPrj(self, path):
        """Triggered when a recent project is requested to be loaded"""
        path = path.data()
        if not os.path.exists(path):
            logging.error("Could not find project file: " + path)
        else:
            self.__loadProject(path)

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
            self.em.showDisassembler(scriptPath, name, code)
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
        self._rightSideBar.setTabText(2, "Exceptions")

    def __onBreakpointsModelChanged(self):
        " Triggered when something is changed in the breakpoints list "
        enabledCount, disabledCount = self.__debugger.getBreakPointModel().getCounts()
        total = enabledCount + disabledCount
        if total == 0:
            self._rightSideBar.setTabText(3, "Breakpoints")
        else:
            self._rightSideBar.setTabText(3, "Breakpoints (" + str(total) + ")")

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
        self._tabDebugAct.setEnabled(enabled)
        self._tabDebugDlgAct.setEnabled(enabled)

        self._tabRunAct.setEnabled(enabled)
        self._tabRunDlgAct.setEnabled(enabled)

        self._tabProfileAct.setEnabled(enabled)
        self._tabProfileDlgAct.setEnabled(enabled)

    def __initPluginSupport(self):
        """Initializes the main window plugin support"""
        self._pluginMenus = {}
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
            self._pluginMenus[plugin.getPath()] = pluginMenu
            self._recomposePluginMenu()
        except Exception as exc:
            logging.error("Error populating " + pluginName +
                          " plugin main menu: " +
                          str(exc) + ". Ignore and continue.")

    def __onPluginDeactivated(self, plugin):
        """Triggered when a plugin is deactivated"""
        try:
            path = plugin.getPath()
            if path in self._pluginMenus:
                del self._pluginMenus[path]
                self._recomposePluginMenu()
        except Exception as exc:
            pluginName = plugin.getName()
            logging.error("Error removing " + pluginName +
                          " plugin main menu: " +
                          str(exc) + ". Ignore and continue.")

    def activateProjectTab(self):
        """Activates the project tab"""
        self._leftSideBar.show()
        self._leftSideBar.setCurrentTab('project')
        self._leftSideBar.raise_()

    def activateOutlineTab(self):
        """Activates the outline tab"""
        self._rightSideBar.show()
        self._rightSideBar.setCurrentTab('fileoutline')
        self._rightSideBar.raise_()

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

    def _onDumpDebugSettings(self, action=None):
        """Triggered when dumping visible settings was requested"""
        self.__dumpDebugSettings(self.__debugger.getScriptPath(), False)

    def _onDumpFullDebugSettings(self):
        """Triggered when dumping complete settings is requested"""
        self.__dumpDebugSettings(self.__debugger.getScriptPath(), True)

    def _onDumpScriptDebugSettings(self):
        """Triggered when dumping current script settings is requested"""
        if self._dumpScriptDbgSettingsAvailable():
            currentWidget = self.em.currentWidget()
            self.__dumpDebugSettings(currentWidget.getFileName(), False)

    def _onDumpScriptFullDebugSettings(self):
        """Triggered when dumping current script complete settings is requested"""
        if self._dumpScriptDbgSettingsAvailable():
            currentWidget = self.em.currentWidget()
            self.__dumpDebugSettings(currentWidget.getFileName(), True)

    def _onDumpProjectDebugSettings(self):
        """Triggered when dumping project script settings is requested"""
        if self.__dumpProjectDbgSettingsAvailable():
            project = GlobalData().project
            self.__dumpDebugSettings(project.getProjectScript(), False)

    def _onDumpProjectFullDebugSettings(self):
        """Triggered when dumping project script complete settings is requested"""
        if self.__dumpProjectDbgSettingsAvailable():
            project = GlobalData().project
            self.__dumpDebugSettings(project.getProjectScript(), True)

    def _dumpScriptDbgSettingsAvailable(self):
        """True if dumping dbg session settings for the script is available"""
        if not self._isPythonBuffer():
            return False
        currentWidget = self.em.currentWidget()
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

    def installRedirectedIOConsole(self):
        """Create redirected IO console"""
        self.redirectedIOConsole = IOConsoleTabWidget(self)
        self.redirectedIOConsole.sigUserInput.connect(self.__onUserInput)
        self.redirectedIOConsole.sigSettingUpdated.connect(
            self.onIOConsoleSettingUpdated)
        self._bottomSideBar.addTab(
            self.redirectedIOConsole, getIcon('ioconsole.png'),
            'IO console', 'ioredirect', None)
        self._bottomSideBar.setTabToolTip('ioredirect',
                                           'Redirected IO debug console')

    def clearDebugIOConsole(self):
        """Clears the content of the debug IO console"""
        if self.redirectedIOConsole:
            self.redirectedIOConsole.clear()

    def __onClientStdout(self, data):
        """Triggered when the client reports stdout"""
        self._bottomSideBar.show()
        self._bottomSideBar.setCurrentTab('ioredirect')
        self._bottomSideBar.raise_()
        self.redirectedIOConsole.appendStdoutMessage(data)

    def __onClientStderr(self, data):
        """Triggered when the client reports stderr"""
        self._bottomSideBar.show()
        self._bottomSideBar.setCurrentTab('ioredirect')
        self._bottomSideBar.raise_()
        self.redirectedIOConsole.appendStderrMessage(data)

    def __ioconsoleIDEMessage(self, message):
        """Sends an IDE message to the IO console"""
        self._bottomSideBar.show()
        self._bottomSideBar.setCurrentTab('ioredirect')
        self._bottomSideBar.raise_()
        self.redirectedIOConsole.appendIDEMessage(message)

    def __onClientRawInput(self, prompt, echo):
        """Triggered when the client input is requested"""
        self._bottomSideBar.show()
        self._bottomSideBar.setCurrentTab('ioredirect')
        self._bottomSideBar.raise_()
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
        widget.settingUpdated.connect(self.onIOConsoleSettingUpdated)

        self._bottomSideBar.addTab(
            widget, getIcon('ioconsole.png'), caption, name)
        self._bottomSideBar.setTabToolTip(name, tooltip)
        self._bottomSideBar.show()
        self._bottomSideBar.setCurrentTab(name)
        self._bottomSideBar.raise_()
        widget.setFocus()

    def updateIOConsoleTooltip(self, threadID, msg):
        """Updates the IO console tooltip"""
        index = self.__getIOConsoleIndex(threadID)
        if index is not None:
            tooltip = self._bottomSideBar.tabToolTip(index)
            tooltip = tooltip.replace("(running)", "(" + msg + ")")
            self._bottomSideBar.setTabToolTip(index, tooltip)

    def __getIOConsoleIndex(self, threadID):
        """Provides the IO console index by the thread ID"""
        index = self._bottomSideBar.count() - 1
        while index >= 0:
            widget = self._bottomSideBar.widget(index)
            if hasattr(widget, "threadID"):
                if widget.threadID() == threadID:
                    return index
            index -= 1
        return None

    def __onCloseIOConsole(self, threadID):
        """Closes the tab with the corresponding widget"""
        index = self.__getIOConsoleIndex(threadID)
        if index is not None:
            self._bottomSideBar.removeTab(index)

    def __onKillIOConsoleProcess(self, threadID):
        """Kills the process linked to the IO console"""
        self.__runManager.kill(threadID)

    def closeAllIOConsoles(self):
        """Closes all IO run/profile tabs and clears the debug IO console"""
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        index = self._bottomSideBar.count - 1
        while index >= 0:
            widget = self._bottomSideBar.widget(index)
            if hasattr(widget, "getType"):
                if widget.getType() == MainWindowTabWidgetBase.IOConsole:
                    if hasattr(widget, "stopAndClose"):
                        widget.stopAndClose()
            index -= 1

        self.clearDebugIOConsole()
        QApplication.restoreOverrideCursor()

    def passFocusToEditor(self):
        """Passes the focus to the text editor if it is there"""
        return self.em.passFocusToEditor()

    def passFocusToFlow(self):
        """Passes the focus to the flow UI if it is there"""
        return self.em.passFocusToFlow()


