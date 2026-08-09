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

# pylint: disable=W0702
# pylint: disable=W0703

# cml 1 gb id=0 title="System imports"
import gc
import logging
import os.path
import sys

from analysis.disasm import getBufferDisassembled, getCompiledfileDisassembled, getFileDisassembled
from analysis.notused import NotUsedAnalysisProgress
from autocomplete.completelists import getJediProject, getOccurrences
from debugger.bpwp import DebuggerBreakWatchPoints
from debugger.calltraceviewer import CallTraceViewer
from debugger.context import DebuggerContext
from debugger.excpt import DebuggerExceptions
from debugger.server import CodimensionDebugger
from diagram.importsdgm import ImportDiagramOptions, ImportsDiagramDialog, ImportsDiagramProgress
from plugins.manager.pluginmanagerdlg import PluginsDialog
from plugins.vcssupport.vcsmanager import VCSManager
from profiling.profwidget import ProfileResultsWidget
from search.findinfilesdialog import FindInFilesDialog
from search.findinfilesprovider import FindInFilesSearchProvider
from search.occurrencesprovider import OccurrencesSearchProvider
from search.searchresultsviewer import SearchResultsViewer, hideSearchTooltip
from search.searchsupport import ItemToSearchIn, getSearchItemIndex
from search.vultureprovider import VultureSearchProvider
from utils.diskvaluesrelay import getRunParameters
from utils.fileutils import (
    getFileProperties,
    isCDMProjectFile,
    isFileSearchable,
    isImageFile,
    isImageViewable,
    isPythonMime,
)

# cml 1 ge id=0
# cml 1 gb id=1 title="Project imports"
from utils.globals import GlobalData
from utils.misc import getDefaultTemplate, getIDETemplateFile, getProjectTemplateFile
from utils.pixmapcache import getIcon
from utils.project import CodimensionProject
from utils.runmanager import RunManager

from .about import AboutDialog
from .classesviewer import ClassesViewer
from .editorsmanager import EditorsManager
from .findfile import FindFileDialog
from .findname import FindNameDialog
from .findreplacewidget import FindReplaceWidget
from .floatingrendererwindow import DetachedRendererWindow
from .functionsviewer import FunctionsViewer
from .globalsviewer import GlobalsViewer
from .gotolinewidget import GotoLineWidget
from .logviewer import LogViewer
from .mainmenu import MainWindowMenuMixin
from .mainredirectedio import MainWindowRedirectedIOMixin
from .mainstatusbar import MainWindowStatusBarMixin
from .mainwindow_debug import MainWindowDebuggerMixin
from .mainwindowtabwidgetbase import MainWindowTabWidgetBase
from .outline import FileOutlineViewer
from .projectproperties import ProjectPropertiesDialog
from .projectviewer import ProjectViewer
from .pyflakesviewer import PyflakesViewer
from .qt import (
    QAction,
    QApplication,
    QCursor,
    QDesktopServices,
    QDialog,
    QDir,
    QFileDialog,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSize,
    QSizePolicy,
    QSplitter,
    Qt,
    QTabBar,
    QTimer,
    QToolBar,
    QToolButton,
    QToolTip,
    QUrl,
    QVBoxLayout,
    QWidget,
    pyqtSignal,
)
from .recentprojectsviewer import RecentProjectsViewer
from .redirector import Redirector
from .sidebar import SideBar
from .spacers import ToolBarExpandingSpacer, ToolBarHSpacer

# cml 1 ge id=1


class EditorsManagerWidget(QWidget):
    """Tab widget which has tabs with editors and viewers"""

    def __init__(self, parent, debugger):

        QWidget.__init__(self, parent)

        self.editorsManager = EditorsManager(parent, debugger)
        self.findReplaceWidget = FindReplaceWidget(self.editorsManager)
        self.gotoLineWidget = GotoLineWidget(self.editorsManager)
        self.editorsManager.registerAuxWidgets(self.findReplaceWidget, self.gotoLineWidget)

        self.editorsManager.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(1, 1, 1, 1)

        self.layout.addWidget(self.editorsManager)
        self.layout.addWidget(self.findReplaceWidget)
        self.layout.addWidget(self.gotoLineWidget)

        self.setLayout(self.layout)


class CodimensionMainWindow(
    QMainWindow,
    MainWindowStatusBarMixin,
    MainWindowMenuMixin,
    MainWindowRedirectedIOMixin,
    MainWindowDebuggerMixin,
):
    """Main application window"""

    debugModeChanged = pyqtSignal(bool)

    def __init__(self, splash, settings):
        QMainWindow.__init__(self)

        self.settings = settings

        MainWindowStatusBarMixin.__init__(self)
        MainWindowMenuMixin.__init__(self)
        MainWindowRedirectedIOMixin.__init__(self)
        MainWindowDebuggerMixin.__init__(self)

        self.vcsManager = VCSManager()

        self._debugger = CodimensionDebugger(self)
        self._debugger.sigDebuggerStateChanged.connect(self._onDebuggerStateChanged)
        self._debugger.sigClientLine.connect(self._onDebuggerCurrentLine)
        self._debugger.sigClientException.connect(self._onDebuggerClientException)
        self._debugger.sigClientSyntaxError.connect(self._onDebuggerClientSyntaxError)
        self._debugger.getBreakPointModel().sigBreakpoinsChanged.connect(self._onBreakpointsModelChanged)

        self.__initialisation = True

        # This prevents context menu on the main window toolbar.
        # I don't really know why but it is what I need
        self.setContextMenuPolicy(Qt.NoContextMenu)

        # The size restore is done twice to avoid huge flickering
        # This one is approximate, the one in restoreWindowPosition()
        # is precise
        screenSize = GlobalData().application.desktop().screenGeometry()
        if screenSize.width() != settings["screenwidth"] or screenSize.height() != settings["screenheight"]:
            # The screen resolution has been changed, use the default pos
            defXPos, defYpos, defWidth, defHeight = settings.getDefaultGeometry()
            self.resize(defWidth, defHeight)
            self.move(defXPos, defYpos)
        else:
            # No changes in the screen resolution
            self.resize(settings["width"], settings["height"])
            self.move(settings["xpos"] + settings["xdelta"], settings["ypos"] + settings["ydelta"])

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
        self.__horizontalSplitterSizes = settings["hSplitterSizes"]
        self.__verticalSplitterSizes = settings["vSplitterSizes"]

        self.logViewer = None
        self.__createLayout()
        self._initRedirectedIO()

        splash.showMessage("Initializing main menu bar...")
        self.__initPluginSupport()
        self._initMainMenu()

        self.updateWindowTitle()
        self.__printThirdPartyAvailability()

        self._runManager = RunManager(self)
        self._runManager.sigProfilingResults.connect(self.onProfileResults)
        self._runManager.sigDebugSessionPrologueStarted.connect(self._debugger.onDebugSessionStarted)
        self._runManager.sigIncomingMessage.connect(self._debugger.onIncomingMessage)
        self._runManager.sigProcessFinished.connect(self._debugger.onProcessFinished)

        settings.sigTextZoomChanged.connect(self.onTextZoomChanged)

        # Flow UI/markdown renderer
        self.__detachedRenderer = DetachedRendererWindow(settings, self.em)
        if settings["floatingRenderer"]:
            self.__detachedRenderer.show()

        self.__registerSearchProviders()

    def restoreWindowPosition(self):
        """Makes sure that the window frame delta is proper"""
        screenSize = GlobalData().application.desktop().screenGeometry()
        if screenSize.width() != self.settings["screenwidth"] or screenSize.height() != self.settings["screenheight"]:
            # The screen resolution has been changed, save the new values
            self.settings["screenwidth"] = screenSize.width()
            self.settings["screenheight"] = screenSize.height()
            self.settings["xdelta"] = self.settings["xpos"] - self.x()
            self.settings["ydelta"] = self.settings["ypos"] - self.y()
            self.settings["xpos"] = self.x()
            self.settings["ypos"] = self.y()
        else:
            # Screen resolution is the same as before
            if self.settings["xpos"] != self.x() or self.settings["ypos"] != self.y():
                # The saved delta is incorrect, update it
                self.settings["xdelta"] = self.settings["xpos"] - self.x() + self.settings["xdelta"]
                self.settings["ydelta"] = self.settings["ypos"] - self.y() + self.settings["ydelta"]
                self.settings["xpos"] = self.x()
                self.settings["ypos"] = self.y()
        self.__initialisation = False

    def _onMaximizeEditor(self):
        """Triggered when F11 is pressed"""
        self._leftSideBar.shrink()
        self._bottomSideBar.shrink()
        self._rightSideBar.shrink()

    def __createLayout(self):
        """Creates the UI layout"""
        self.editorsManagerWidget = EditorsManagerWidget(self, self._debugger)
        self.em = self.editorsManagerWidget.editorsManager
        self.em.sigTabRunChanged.connect(self.setDebugTabAvailable)

        self.editorsManagerWidget.findReplaceWidget.hide()
        self.editorsManagerWidget.gotoLineWidget.hide()

        # The layout is a sidebar-style one
        self._bottomSideBar = SideBar(SideBar.South, self)
        self._bottomSideBar.setTabsClosable(True)
        self._leftSideBar = SideBar(SideBar.West, self)
        self._rightSideBar = SideBar(SideBar.East, self)

        # Create tabs on bars
        self.logViewer = LogViewer()
        self._bottomSideBar.addTab(self.logViewer, getIcon("logviewer.png"), "Log", "log", 0)
        self._bottomSideBar.tabButton("log", QTabBar.RightSide).resize(0, 0)
        sys.stdout.appendToStdout.connect(self.toStdout)
        sys.stderr.appendToStderr.connect(self.toStderr)

        # replace logging streamer to self.stdout
        logging.root.handlers = []
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(levelname) -10s %(asctime)s %(message)s", None))
        logging.root.addHandler(handler)

        self.projectViewer = ProjectViewer(self)
        self._leftSideBar.addTab(self.projectViewer, getIcon(""), "Project", "project", 0)
        self.em.sigFileUpdated.connect(self.projectViewer.onFileUpdated)
        self.em.sigFileTypeChanged.connect(self.projectViewer.onFileTypeChanged)
        self.recentProjectsViewer = RecentProjectsViewer(self)
        self._leftSideBar.addTab(self.recentProjectsViewer, getIcon(""), "Recent", "recent", 1)
        self.em.sigFileUpdated.connect(self.recentProjectsViewer.onFileUpdated)
        self.em.sigFileTypeChanged.connect(self.recentProjectsViewer.onFileTypeChanged)
        self.em.sigBufferSavedAs.connect(self.recentProjectsViewer.onFileUpdated)
        self.projectViewer.sigFileUpdated.connect(self.recentProjectsViewer.onFileUpdated)

        self.classesViewer = ClassesViewer()
        self.em.sigFileUpdated.connect(self.classesViewer.onFileUpdated)
        self._leftSideBar.addTab(self.classesViewer, getIcon(""), "Classes", "classes", 2)
        self.functionsViewer = FunctionsViewer()
        self.em.sigFileUpdated.connect(self.functionsViewer.onFileUpdated)
        self._leftSideBar.addTab(self.functionsViewer, getIcon(""), "Functions", "functions", 3)
        self.globalsViewer = GlobalsViewer()
        self.em.sigFileUpdated.connect(self.globalsViewer.onFileUpdated)
        self._leftSideBar.addTab(self.globalsViewer, getIcon(""), "Globals", "globals", 4)

        self._leftSideBar.sigCurrentTabChanged.connect(self.__onLeftSideBarTabChanged)

        # Create search results viewer
        self.searchResultsViewer = SearchResultsViewer()
        self._bottomSideBar.addTab(self.searchResultsViewer, getIcon("findindir.png"), "Search results", "search", 1)
        self._bottomSideBar.tabButton("search", QTabBar.RightSide).resize(0, 0)

        # Create outline viewer
        self.outlineViewer = FileOutlineViewer(self.em, self)
        self._rightSideBar.addTab(self.outlineViewer, getIcon(""), "File outline", "fileoutline", 0)

        # Create the pyflakes viewer
        self.__pyflakesViewer = PyflakesViewer(self.em, self.sbPyflakes, self.sbCC, self)

        self.debuggerContext = DebuggerContext(self._debugger)
        self._rightSideBar.addTab(self.debuggerContext, getIcon(""), "Debugger", "debugger", 1)
        self._rightSideBar.setTabEnabled("debugger", False)

        self.debuggerExceptions = DebuggerExceptions()
        self._rightSideBar.addTab(self.debuggerExceptions, getIcon(""), "Exceptions", "exceptions", 2)
        self.debuggerExceptions.sigClientExceptionsCleared.connect(self._onClientExceptionsCleared)

        self.debuggerBreakWatchPoints = DebuggerBreakWatchPoints(self, self._debugger)
        self._rightSideBar.addTab(self.debuggerBreakWatchPoints, getIcon(""), "Breakpoints", "breakpoints", 3)

        self.debuggerCallTrace = CallTraceViewer(self._debugger, self)
        self._rightSideBar.addTab(self.debuggerCallTrace, getIcon(""), "Call Trace", "calltrace", 4)

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
        self.__horizontalSplitter.setSizes(self.settings["hSplitterSizes"])
        self.__verticalSplitter.setSizes(self.settings["vSplitterSizes"])
        if self.settings["leftBarMinimized"]:
            self._leftSideBar.shrink()
        if self.settings["bottomBarMinimized"]:
            self._bottomSideBar.shrink()
        if self.settings["rightBarMinimized"]:
            self._rightSideBar.shrink()

        # Setup splitters movement handlers
        self.__verticalSplitter.splitterMoved.connect(self.vSplitterMoved)
        self.__horizontalSplitter.splitterMoved.connect(self.hSplitterMoved)

    @staticmethod
    def __printThirdPartyAvailability():
        """Prints third party tools availability"""
        globalData = GlobalData()
        if globalData.graphvizAvailable:
            logging.debug("The 'dot' utility is available")
        else:
            logging.warning("The 'dot' utility is not found. Some functionality will not be available.")
        if globalData.javaAvailable:
            logging.debug("java is available")
        else:
            logging.warning("java is not found. Some functionality will not be available.")

    def vSplitterMoved(self, pos, index):
        """Vertical splitter moved handler"""
        del pos  # unused argument
        del index  # unused argument

        newSizes = list(self.__verticalSplitter.sizes())

        if not self._bottomSideBar.isMinimized():
            self.__verticalSplitterSizes[0] = newSizes[0]

        self.__verticalSplitterSizes[1] = sum(newSizes) - self.__verticalSplitterSizes[0]

    def hSplitterMoved(self, pos, index):
        """Horizontal splitter moved handler"""
        del pos  # unused argument
        del index  # unused argument

        newSizes = list(self.__horizontalSplitter.sizes())

        if not self._leftSideBar.isMinimized():
            self.__horizontalSplitterSizes[0] = newSizes[0]
        if not self._rightSideBar.isMinimized():
            self.__horizontalSplitterSizes[2] = newSizes[2]

        self.__horizontalSplitterSizes[1] = (
            sum(newSizes) - self.__horizontalSplitterSizes[0] - self.__horizontalSplitterSizes[2]
        )

    def __onLeftSideBarTabChanged(self, index):
        """Lazy-load Classes/Functions/Globals when their tab is first shown."""
        self.__triggerLazyLoadForTabIndex(index)

    def __triggerLazyLoadForCurrentTab(self):
        """Triggers lazy load for the currently visible left sidebar tab."""
        self.__triggerLazyLoadForTabIndex(self._leftSideBar.currentIndex())

    def __triggerLazyLoadForTabIndex(self, index):
        """Populates the model for the given tab if it is Classes/Functions/Globals."""
        if index < 0:
            return
        tabName = self._leftSideBar.getTabName(index)
        if tabName == "classes":
            self.classesViewer.clViewer.model().sourceModel().populateIfNeeded()
        elif tabName == "functions":
            self.functionsViewer.funcViewer.model().sourceModel().populateIfNeeded()
        elif tabName == "globals":
            self.globalsViewer.globalsViewer.model().sourceModel().populateIfNeeded()

    def __createToolBar(self):
        """creates the buttons bar"""
        # Imports diagram button and its menu
        importsMenu = QMenu(self)
        importsDlgAct = importsMenu.addAction(getIcon("detailsdlg.png"), "Fine tuned imports diagram")
        importsDlgAct.triggered.connect(self._onImportDgmTuned)
        self.importsDiagramButton = QToolButton(self)
        self.importsDiagramButton.setIcon(getIcon("importsdiagram.png"))
        self.importsDiagramButton.setToolTip("Generate imports diagram")
        self.importsDiagramButton.setPopupMode(QToolButton.DelayedPopup)
        self.importsDiagramButton.setMenu(importsMenu)
        self.importsDiagramButton.setFocusPolicy(Qt.NoFocus)
        self.importsDiagramButton.clicked.connect(self._onImportDgm)

        # Run project button and its menu
        runProjectMenu = QMenu(self)
        runProjectAct = runProjectMenu.addAction(getIcon("detailsdlg.png"), "Set run parameters")
        runProjectAct.triggered.connect(self.onRunProjectDlg)
        self.runProjectButton = QToolButton(self)
        self.runProjectButton.setIcon(getIcon("run.png"))
        self.runProjectButton.setToolTip("Project is not loaded")
        self.runProjectButton.setPopupMode(QToolButton.DelayedPopup)
        self.runProjectButton.setMenu(runProjectMenu)
        self.runProjectButton.setFocusPolicy(Qt.NoFocus)
        self.runProjectButton.clicked.connect(self.onRunProject)

        # profile project button and its menu
        profileProjectMenu = QMenu(self)
        profileProjectAct = profileProjectMenu.addAction(getIcon("detailsdlg.png"), "Set profile parameters")
        profileProjectAct.triggered.connect(self.onProfileProjectDlg)
        self.profileProjectButton = QToolButton(self)
        self.profileProjectButton.setIcon(getIcon("profile.png"))
        self.profileProjectButton.setToolTip("Project is not loaded")
        self.profileProjectButton.setPopupMode(QToolButton.DelayedPopup)
        self.profileProjectButton.setMenu(profileProjectMenu)
        self.profileProjectButton.setFocusPolicy(Qt.NoFocus)
        self.profileProjectButton.clicked.connect(self.onProfileProject)

        # Debug project button and its menu
        debugProjectMenu = QMenu(self)
        debugProjectAct = debugProjectMenu.addAction(getIcon("detailsdlg.png"), "Set debug parameters")
        debugProjectAct.triggered.connect(self.onDebugProjectDlg)
        self.debugProjectButton = QToolButton(self)
        self.debugProjectButton.setIcon(getIcon("debugger.png"))
        self.debugProjectButton.setToolTip("Project is not loaded")
        self.debugProjectButton.setPopupMode(QToolButton.DelayedPopup)
        self.debugProjectButton.setMenu(debugProjectMenu)
        self.debugProjectButton.setFocusPolicy(Qt.NoFocus)
        self.debugProjectButton.clicked.connect(self.onDebugProject)
        self.debugProjectButton.setVisible(True)

        packageDiagramButton = QAction(getIcon("packagediagram.png"), "Generate package diagram", self)
        packageDiagramButton.setEnabled(False)
        packageDiagramButton.setVisible(False)
        applicationDiagramButton = QAction(getIcon("applicationdiagram.png"), "Generate application diagram", self)
        applicationDiagramButton.setEnabled(False)
        applicationDiagramButton.setVisible(False)

        self.__findInFilesButton = QAction(getIcon("findindir.png"), "Find in files (Ctrl+Shift+F)", self)
        self.__findInFilesButton.triggered.connect(self.findInFilesClicked)
        self.__findNameButton = QAction(getIcon("findname.png"), "Find name in project (Alt+Shift+S)", self)
        self.__findNameButton.triggered.connect(self.findNameClicked)
        self.__findFileButton = QAction(getIcon("findfile.png"), "Find project file (Alt+Shift+O)", self)
        self.__findFileButton.triggered.connect(self.findFileClicked)
        self.__deadCodeButton = QAction(getIcon("deadcode.png"), "Find project dead code (Alt+Shift+D)", self)
        self.__deadCodeButton.triggered.connect(self.projectDeadCodeClicked)
        self.__projectDocButton = QAction(getIcon("markdown.png"), "Project documentation", self)
        self.__projectDocButton.triggered.connect(self.projectDocClicked)

        # Debugger buttons
        self._dbgStop = QAction(getIcon("dbgstop.png"), "Stop debugging session (F10)", self)
        self._dbgStop.triggered.connect(self._onStopDbgSession)
        self._dbgStop.setVisible(False)
        self._dbgRestart = QAction(getIcon("dbgrestart.png"), "Restart debugging section (F4)", self)
        self._dbgRestart.triggered.connect(self._onRestartDbgSession)
        self._dbgRestart.setVisible(False)
        self._dbgGo = QAction(getIcon("dbggo.png"), "Continue (F6)", self)
        self._dbgGo.triggered.connect(self._onDbgGo)
        self._dbgGo.setVisible(False)
        self._dbgNext = QAction(getIcon("dbgnext.png"), "Step over (F8)", self)
        self._dbgNext.triggered.connect(self._onDbgNext)
        self._dbgNext.setVisible(False)
        self._dbgStepInto = QAction(getIcon("dbgstepinto.png"), "Step into (F7)", self)
        self._dbgStepInto.triggered.connect(self._onDbgStepInto)
        self._dbgStepInto.setVisible(False)
        self._dbgRunToLine = QAction(getIcon("dbgruntoline.png"), "Run to cursor (Shift+F6)", self)
        self._dbgRunToLine.triggered.connect(self._onDbgRunToLine)
        self._dbgRunToLine.setVisible(False)
        self._dbgReturn = QAction(getIcon("dbgreturn.png"), "Step out (F9)", self)
        self._dbgReturn.triggered.connect(self._onDbgReturn)
        self._dbgReturn.setVisible(False)
        self._dbgJumpToCurrent = QAction(getIcon("dbgtocurrent.png"), "Show current debugger line (Ctrl+W)", self)
        self._dbgJumpToCurrent.triggered.connect(self._onDbgJumpToCurrent)
        self._dbgJumpToCurrent.setVisible(False)

        dumpDebugSettingsMenu = QMenu(self)
        dumpDebugSettingsAct = dumpDebugSettingsMenu.addAction(
            getIcon("detailsdlg.png"), "Dump settings with complete environment"
        )
        dumpDebugSettingsAct.triggered.connect(self._onDumpFullDebugSettings)
        self._dbgDumpSettingsButton = QToolButton(self)
        self._dbgDumpSettingsButton.setIcon(getIcon("dbgsettings.png"))
        self._dbgDumpSettingsButton.setToolTip("Dump debug session settings")
        self._dbgDumpSettingsButton.setPopupMode(QToolButton.DelayedPopup)
        self._dbgDumpSettingsButton.setMenu(dumpDebugSettingsMenu)
        self._dbgDumpSettingsButton.setFocusPolicy(Qt.NoFocus)
        self._dbgDumpSettingsButton.clicked.connect(self._onDumpDebugSettings)

        self.floatingRendererButton = QToolButton(self)
        self.floatingRendererButton.setObjectName("floatingRendererButton")
        self.floatingRendererButton.setIcon(getIcon("floatingrenderer.png"))
        self.floatingRendererButton.setToolTip("Floating/embedded renderer")
        self.floatingRendererButton.setFocusPolicy(Qt.NoFocus)
        self.floatingRendererButton.setCheckable(True)
        self.floatingRendererButton.setChecked(self.settings["floatingRenderer"])
        self.floatingRendererButton.clicked.connect(self._onFloatingRenderer)

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
        self.__toolbar.addAction(self.__findInFilesButton)
        self.__toolbar.addAction(self.__findNameButton)
        self.__toolbar.addAction(self.__findFileButton)
        self.__toolbar.addSeparator()
        self.__toolbar.addAction(self.__deadCodeButton)
        self.__toolbar.addSeparator()
        self.__toolbar.addAction(self.__projectDocButton)

        # Debugger part begin
        self.__toolbar.addWidget(ToolBarHSpacer(self.__toolbar, 40)).setObjectName("debugSpacer")
        self.__toolbar.addAction(self._dbgStop)
        self.__toolbar.addAction(self._dbgRestart)
        self.__toolbar.addAction(self._dbgGo)
        self.__toolbar.addAction(self._dbgStepInto)
        self.__toolbar.addAction(self._dbgNext)
        self.__toolbar.addAction(self._dbgRunToLine)
        self.__toolbar.addAction(self._dbgReturn)
        self.__toolbar.addAction(self._dbgJumpToCurrent)
        self._dbgDumpSettingsAct = self.__toolbar.addWidget(self._dbgDumpSettingsButton)

        self.__toolbar.addWidget(ToolBarExpandingSpacer(self.__toolbar)).setObjectName("expandingSpacer")
        self.__toolbar.addWidget(self.floatingRendererButton)

        # Heck! The only QAction can be hidden
        self._dbgDumpSettingsAct.setVisible(False)
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
        # So, make a wild guess instead and do not save the status if
        # maximized.
        availGeom = GlobalData().application.desktop().availableGeometry()
        if (
            self.width() + abs(self.settings["xdelta"]) > availGeom.width()
            or self.height() + abs(self.settings["ydelta"]) > availGeom.height()
        ):
            return True
        return False

    def resizeEvent(self, resizeEv):
        """Triggered when the window is resized"""
        del resizeEv  # unused argument
        QTimer.singleShot(1, self.__resizeEventdelayed)

    def __resizeEventdelayed(self):
        """Memorizes the new window size"""
        if self.__initialisation:
            return
        if self.__guessMaximized():
            return

        self.settings["width"] = self.width()
        self.settings["height"] = self.height()
        self.vSplitterMoved(0, 0)
        self.hSplitterMoved(0, 0)

    def moveEvent(self, moveEv):
        """Triggered when the window is moved"""
        del moveEv  # unused argument
        QTimer.singleShot(1, self.__moveEventDelayed)

    def __moveEventDelayed(self):
        """Memorizes the new window position"""
        if not self.__initialisation and not self.__guessMaximized():
            self.settings["xpos"] = self.x()
            self.settings["ypos"] = self.y()

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
            self._deadCodeMenuAct.setEnabled(projectLoaded)
            self._findProjectFileAct.setEnabled(projectLoaded)
            self._prjImportDgmAct.setEnabled(projectLoaded)
            self._prjImportsDgmDlgAct.setEnabled(projectLoaded)

            self.settings["projectLoaded"] = projectLoaded
            if projectLoaded:
                # The editor tabs must be loaded after a VCS plugin has a
                # chance to receive sigProjectChanged signal where it reads
                # the plugin configuration
                QTimer.singleShot(1, self.__delayedEditorsTabRestore)
                # Lazy-load: if Classes/Functions/Globals tab is visible, populate it
                QTimer.singleShot(0, self.__triggerLazyLoadForCurrentTab)
        self.updateAnalysisEnvStatus()
        self.updateRunDebugButtons()

        # Updating of the jedi library project should happen regardless
        # whether the properties or the whole project is changed
        getJediProject(force=True)

    def __delayedEditorsTabRestore(self):
        """Delayed restore editor tabs"""
        self.em.restoreTabs(GlobalData().project.tabStatus)

    def updateWindowTitle(self):
        """Updates the main window title with the current so file"""
        if GlobalData().project.isLoaded():
            self.setWindowTitle("Codimension for Python 3: " + os.path.basename(GlobalData().project.fileName))
        else:
            self.setWindowTitle("Codimension for Python 3: no project selected")

    def updateToolbarStatus(self):
        """Enables/disables the toolbar buttons"""
        projectLoaded = GlobalData().project.isLoaded()
        self.importsDiagramButton.setEnabled(projectLoaded and GlobalData().graphvizAvailable)
        self.__findNameButton.setEnabled(projectLoaded)
        self.__findFileButton.setEnabled(projectLoaded)
        self.__deadCodeButton.setEnabled(projectLoaded)
        self.__projectDocButton.setEnabled(projectLoaded)

    def updateRunDebugButtons(self):
        """Updates the run/debug buttons statuses"""
        if self.debugMode:
            self.runProjectButton.setEnabled(False)
            self.runProjectButton.setToolTip("Cannot run project - debug in progress")
            self.debugProjectButton.setEnabled(False)
            self.debugProjectButton.setToolTip("Cannot debug project - debug in progress")
            self._prjDebugAct.setEnabled(False)
            self._prjDebugDlgAct.setEnabled(False)
            self._tabDebugAct.setEnabled(False)
            self._tabDebugDlgAct.setEnabled(False)
            self.profileProjectButton.setEnabled(False)
            self.profileProjectButton.setToolTip("Cannot profile project - debug in progress")
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
            self.runProjectButton.setToolTip("Cannot run project - script is not specified or invalid")
            self.debugProjectButton.setEnabled(False)
            self.debugProjectButton.setToolTip("Cannot debug project - script is not specified or invalid")
            self._prjDebugAct.setEnabled(False)
            self._prjDebugDlgAct.setEnabled(False)
            self.profileProjectButton.setEnabled(False)
            self.profileProjectButton.setToolTip("Cannot profile project - script is not specified or invalid")
            return

        self.runProjectButton.setEnabled(True)
        self.runProjectButton.setToolTip("Run project")
        self.debugProjectButton.setEnabled(True)
        self.debugProjectButton.setToolTip("Debug project")
        self._prjDebugAct.setEnabled(True)
        self._prjDebugDlgAct.setEnabled(True)
        self.profileProjectButton.setEnabled(True)
        self.profileProjectButton.setToolTip("Profile project")

    def findInFilesClicked(self):
        """Triggered when the find in files button is clicked"""
        txt = ""
        currentWidget = self.em.currentWidget()
        if currentWidget.getType() in [MainWindowTabWidgetBase.PlainTextEditor]:
            txt, _, _, _ = currentWidget.getEditor().getCurrentOrSelection()

        dlg = FindInFilesDialog(FindInFilesDialog.IN_PROJECT, txt, "")
        dlg.exec_()
        if dlg.searchResults:
            self.displayFindInFiles(FindInFilesSearchProvider().getName(), dlg.searchResults, dlg.getParameters())

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
        self._activateSideTab("log")

    def openFile(self, path, lineNo, pos=0):
        """User double clicked on a file or an item in a file"""
        return self.em.openFile(path, lineNo, pos)

    def gotoInBuffer(self, uuid, lineNo):
        """Usually needs when an item is clicked in the file outline browser"""
        self.em.gotoInBuffer(uuid, lineNo)

    def jumpToLine(self, lineNo):
        """Usually used when definition is in the current unsaved buffer"""
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
            logging.error("Cannot open %s, does not exist", path)
            return
        if os.path.islink(path):
            path = os.path.realpath(path)
            if not os.path.exists(path):
                logging.error("Cannot open %s, does not exist", path)
                return
            # The type may differ...
            mime, _, _ = getFileProperties(path)
        else:
            # The intermediate directory could be a link, so use the real path
            path = os.path.realpath(path)

        if not os.access(path, os.R_OK):
            logging.error("No read permissions to open %s", path)
            return

        if not os.path.isfile(path):
            logging.error("%s is not a file", path)
            return

        if isImageViewable(mime):
            self.openPixmapFile(path)
            return
        if mime != "inode/x-empty" and not isFileSearchable(path):
            logging.error("Cannot open non-text file for editing")
            return

        if path.lower().endswith("readme"):
            print(path)
            print(mime)
        self.openFile(path, lineNo)

    def closeEvent(self, event):
        """Triggered when the IDE is closed"""
        # Save the side bars status
        self.settings["vSplitterSizes"] = self.__verticalSplitterSizes
        self.settings["hSplitterSizes"] = self.__horizontalSplitterSizes
        self.settings["bottomBarMinimized"] = self._bottomSideBar.isMinimized()
        self.settings["leftBarMinimized"] = self._leftSideBar.isMinimized()
        self.settings["rightBarMinimized"] = self._rightSideBar.isMinimized()

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
                self._onStopDbgSession()

            project = GlobalData().project
            project.fsBrowserExpandedDirs = self.getProjectExpandedPaths()
            GlobalData().appServices.unload_project(emit_signal=False)

            # Stop the VCS manager threads
            self.vcsManager.dismissAllPlugins()

            # Kill all the non-detached processes
            self._runManager.killAll()

            # On ubuntu codimension produces core dumps coming from QT when:
            # - a new project is created
            # - the IDE is closed via Alt+F4
            # It seems that python GC conflicts with QT at finishing. Explicit
            # call of GC resolves the problem.
            while gc.collect():
                pass

            self.__detachedRenderer.close()

    def dismissVCSPlugin(self, plugin):
        """Dismisses the given VCS plugin"""
        self.vcsManager.dismissPlugin(plugin)

    def getProjectExpandedPaths(self):
        """Provides a list of expanded project directories"""
        project = GlobalData().project
        if project.isLoaded():
            return self.projectViewer.projectTreeView.getExpanded()
        return []

    @staticmethod
    def __calltipDisplayable(calltip):
        """True if calltip is displayable"""
        if calltip is None:
            return False
        if calltip.strip() == "":
            return False
        return True

    @staticmethod
    def __docstringDisplayable(docstring):
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

    def onTextZoomChanged(self):
        """Triggered when a text zoom is changed"""
        self.logViewer.onTextZoomChanged()

        # Handle run/profile IO consoles and the debug IO console
        index = self._bottomSideBar.count - 1
        while index >= 0:
            widget = self._bottomSideBar.widget(index)
            if hasattr(widget, "procuuid"):
                if hasattr(widget, "onTextZoomChanged"):
                    widget.onTextZoomChanged()
            index -= 1

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
            logging.error("Error creating a template file: %s", str(exc))
            return
        self.openFile(fileName, -1)

    def _onEditIDETemplate(self):
        """Triggered to edit IDE template"""
        self.editTemplateFile(getIDETemplateFile())

    def editTemplateFile(self, fileName):
        """Edits the timepale file"""
        if fileName is not None:
            if not os.path.exists(fileName):
                logging.error("The template file %s disappeared from the file system.", fileName)
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

    def displayFindInFiles(self, providerId, searchResults, parameters):
        """Displays the results on a tab"""
        self.searchResultsViewer.showReport(providerId, searchResults, parameters)
        self.activateBottomTab("search")

    def activateBottomTab(self, tabName):
        """Makes sure the bottom bar is visible and activates the required tab"""
        if self._bottomSideBar.height() == 0:
            # It was hidden completely, so need to move the slider
            splitterSizes = self.settings["vSplitterSizes"]
            splitterSizes[0] -= 200
            splitterSizes[1] += 200
            self.__verticalSplitter.setSizes(splitterSizes)

        self._bottomSideBar.show()
        self._bottomSideBar.setCurrentTab(tabName)
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

    def projectDeadCodeClicked(self):
        """Dead code analysis: vulture"""
        project = GlobalData().project
        if project.isLoaded():
            try:
                dlg = NotUsedAnalysisProgress(project.getProjectDir())
                dlg.exec_()
            except Exception as exc:
                logging.error(str(exc))

    def projectDocClicked(self):
        """Project documentation create/view/edit"""
        project = GlobalData().project
        if project.isLoaded():
            fName, error = project.findStartupMarkdownFile()
            if error:
                logging.error(error)
                return
            if fName:
                self.em.openMarkdownFullView(fName, readOnly=False)
                return

            # Not found, suggest the file
            fName = project.suggestStartupMarkdownFile()
            self.em.onDefaultProjectDoc(fName)

    def tabDeadCodeClicked(self):
        """Tab dead code analysis"""
        try:
            currentWidget = self.em.currentWidget()
            dlg = NotUsedAnalysisProgress(currentWidget.getFileName())
            dlg.exec_()
        except Exception as exc:
            logging.error(str(exc))

    @staticmethod
    def hideTooltips():
        """Hides all the tooltips"""
        QToolTip.hideText()
        hideSearchTooltip()

    def _onImportDgmTuned(self):
        """Runs the settings dialog first"""
        dlg = ImportsDiagramDialog(ImportsDiagramDialog.ProjectFiles, "", self)
        if dlg.exec_() == QDialog.Accepted:
            self.__generateImportDiagram(dlg.options)

    def _onImportDgm(self, action=False):
        """Runs the generation process"""
        del action  # unused argument
        self.__generateImportDiagram(ImportDiagramOptions())

    def __generateImportDiagram(self, options):
        """Show the generation progress and display the diagram"""
        progressDlg = ImportsDiagramProgress(ImportsDiagramDialog.ProjectFiles, options)
        if progressDlg.exec_() == QDialog.Accepted:
            self.openDiagram(progressDlg.scene, "Generated for the project")

    def onRunTab(self):
        """Triggered when run tab script is requested"""
        currentWidget = self.em.currentWidget()
        self._runManager.run(currentWidget.getFileName(), False)

    def onRunTabDlg(self):
        """Triggered when run tab script dialog is requested"""
        currentWidget = self.em.currentWidget()
        self._runManager.run(currentWidget.getFileName(), True)

    def onRunProject(self, _=None):
        """Runs the project with saved sattings"""
        if self._checkProjectScriptValidity():
            fileName = GlobalData().project.getProjectScript()
            self._runManager.run(fileName, False)

    def onRunProjectDlg(self):
        """Brings up the dialog with run script settings"""
        if self._checkProjectScriptValidity():
            fileName = GlobalData().project.getProjectScript()
            self._runManager.run(fileName, True)

    def onProfileTab(self):
        """Triggered when profile script is requested"""
        currentWidget = self.em.currentWidget()
        self._runManager.profile(currentWidget.getFileName(), False)

    def onProfileTabDlg(self):
        """Triggered when profile tab script dialog is requested"""
        currentWidget = self.em.currentWidget()
        self._runManager.profile(currentWidget.getFileName(), True)

    def onProfileProject(self, _=None):
        """Profiles the project with saved settings"""
        if self._checkProjectScriptValidity():
            fileName = GlobalData().project.getProjectScript()
            self._runManager.profile(fileName, False)

    def onProfileProjectDlg(self):
        """Brings up the dialog with profile script settings"""
        if self._checkProjectScriptValidity():
            fileName = GlobalData().project.getProjectScript()
            self._runManager.profile(fileName, True)

    def _checkProjectScriptValidity(self):
        """Checks and logs error message if so. Returns True if all is OK"""
        if not GlobalData().isProjectScriptValid():
            self.updateRunDebugButtons()
            logging.error("Invalid project script. Use project properties dialog to select existing python script.")
            return False
        return True

    def _isPythonBuffer(self):
        """True if the current tab is a python buffer"""
        currentWidget = self.em.currentWidget()
        if currentWidget is None:
            return False
        return currentWidget.getType() in [
            MainWindowTabWidgetBase.PlainTextEditor,
            MainWindowTabWidgetBase.VCSAnnotateViewer,
        ] and isPythonMime(currentWidget.getMime())

    def _verticalEdgeChanged(self):
        """Editor setting changed"""
        self.settings["verticalEdge"] = not self.settings["verticalEdge"]
        self.em.updateEditorsSettings()

    def _showSpacesChanged(self):
        """Editor setting changed"""
        self.settings["showSpaces"] = not self.settings["showSpaces"]
        self.em.updateEditorsSettings()

    def _lineWrapChanged(self):
        """Editor setting changed"""
        self.settings["lineWrap"] = not self.settings["lineWrap"]
        self.em.updateEditorsSettings()

    def _showBraceMatchChanged(self):
        """Editor setting changed"""
        self.settings["showBraceMatch"] = not self.settings["showBraceMatch"]
        self.em.updateEditorsSettings()

    def _indentationGuidesChanged(self):
        """Editor setting changed"""
        self.settings["indentationGuides"] = not self.settings["indentationGuides"]
        self.em.updateEditorsSettings()

    def _currentLineVisibleChanged(self):
        """Editor setting changed"""
        self.settings["currentLineVisible"] = not self.settings["currentLineVisible"]
        self.em.updateEditorsSettings()

    def _homeToFirstNonSpaceChanged(self):
        """Editor setting changed"""
        self.settings["jumpToFirstNonSpace"] = not self.settings["jumpToFirstNonSpace"]
        self.em.updateEditorsSettings()

    def _removeTrailingChanged(self):
        """Editor setting changed"""
        self.settings["removeTrailingOnSave"] = not self.settings["removeTrailingOnSave"]

    def _projectVenvPolicyChanged(self, act):
        """R176: Options → Project venv on open policy selector."""
        data = act.data()
        if data:
            self.settings["projectVenvPolicy"] = data

    def _aiUiEnabledTriggered(self, checked):
        """Options → AI → Enable AI (experimental)."""
        from core.ai_ui import ai_ui_env_override_active, set_ai_ui_enabled

        if ai_ui_env_override_active():
            return
        set_ai_ui_enabled(bool(checked))

    def _onAiSettings(self):
        """Options → AI → AI settings… (and editor context menu)."""
        from ui.aisettingsdlg import AiSettingsDialog

        dlg = AiSettingsDialog(self)
        dlg.exec_()

    def _editorCalltipsChanged(self):
        """Editor calltips changed"""
        self.settings["editorCalltips"] = not self.settings["editorCalltips"]

    def _showNavBarChanged(self):
        """Editor setting changed"""
        self.settings["showNavigationBar"] = not self.settings["showNavigationBar"]
        self.em.updateEditorsSettings()

    def _showCFNavBarChanged(self):
        """Control flow toolbar visibility changed"""
        self.settings["showCFNavigationBar"] = not self.settings["showCFNavigationBar"]
        self.em.updateCFEditorsSettings()

    def _showMainToolbarChanged(self):
        """Main toolbar visibility changed"""
        self.settings["showMainToolBar"] = not self.settings["showMainToolBar"]
        self.__toolbar.setVisible(self.settings["showMainToolBar"])

    def _projectTooltipsChanged(self):
        """Tooltips setting changed"""
        self.settings["projectTooltips"] = not self.settings["projectTooltips"]
        self.projectViewer.setTooltips(self.settings["projectTooltips"])

    def _recentTooltipsChanged(self):
        """Tooltips setting changed"""
        self.settings["recentTooltips"] = not self.settings["recentTooltips"]
        self.recentProjectsViewer.setTooltips(self.settings["recentTooltips"])

    def _classesTooltipsChanged(self):
        """Tooltips setting changed"""
        self.settings["classesTooltips"] = not self.settings["classesTooltips"]
        self.classesViewer.setTooltips(self.settings["classesTooltips"])

    def _functionsTooltipsChanged(self):
        """Tooltips setting changed"""
        self.settings["functionsTooltips"] = not self.settings["functionsTooltips"]
        self.functionsViewer.setTooltips(self.settings["functionsTooltips"])

    def _outlineTooltipsChanged(self):
        """Tooltips setting changed"""
        self.settings.outlineTooltips = not self.settings["outlineTooltips"]
        self.outlineViewer.setTooltips(self.settings["outlineTooltips"])

    def _findNameTooltipsChanged(self):
        """Tooltips setting changed"""
        self.settings["findNameTooltips"] = not self.settings["findNameTooltips"]

    def _findFileTooltipsChanged(self):
        """Tooltips setting changed"""
        self.settings["findFileTooltips"] = not self.settings["findFileTooltips"]

    def _editorTooltipsChanged(self):
        """Tooltips setting changed"""
        self.settings["editorTooltips"] = not self.settings["editorTooltips"]
        self.em.setTooltips(self.settings["editorTooltips"])

    def _tabOrderPreservedChanged(self):
        """Tab order preserved option changed"""
        self.settings["taborderpreserved"] = not self.settings["taborderpreserved"]

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

    def _onSkin(self, skinName):
        """Triggers when a skin is selected"""
        if self.settings["skin"] != skinName.data():
            logging.info("Please restart codimension to apply the new skin")
            self.settings["skin"] = skinName.data()

    def _onStyle(self, styleName):
        """Sets the selected style"""
        QApplication.setStyle(styleName.data())
        self.settings["style"] = styleName.data().lower()

    def checkOutsideFileChanges(self):
        """Checks if there are changes in the currently opened files"""
        self.em.checkOutsideFileChanges()

    def _loadProject(self, projectFile):
        """Loads the given project (public for mixins)."""
        self.__loadProject(projectFile)

    def __loadProject(self, projectFile):
        """Loads the given project via ApplicationServices (R102)."""
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        if self.em.closeRequest():
            globalData = GlobalData()
            prj = globalData.project
            prj.tabsStatus = self.em.getTabsStatus()
            self.em.closeAll()
            globalData.appServices.load_project(projectFile)
            if not self._leftSideBar.isMinimized():
                self.activateProjectTab()
        QApplication.restoreOverrideCursor()

    def _openFile(self):
        """Triggers when Ctrl+O is pressed"""
        dialog = QFileDialog(self, "Open file")
        dialog.setFileMode(QFileDialog.ExistingFiles)
        dialog.setOption(QFileDialog.DontUseNativeDialog, True)
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
        except Exception:
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

    def _onPluginManager(self):
        """Triggered when a plugin manager dialog is requested"""
        dlg = PluginsDialog(GlobalData().pluginManager, self)
        dlg.exec_()

    def _onContextHelp(self):
        """Triggered when Ctrl+F1 is clicked"""
        self.em.currentWidget().getEditor().onTagHelp()

    def _onEmbeddedHelp(self):
        """Triggered when embedded Codimension help is requested."""
        from utils.embedded_docs import resolve_product_help_index

        startMD = resolve_product_help_index()
        if not startMD:
            logging.error(
                "Product documentation is not found (expected doc/user/index.md next to the package)."
            )
        else:
            self.em.openMarkdownFullView(startMD, True)

    @staticmethod
    def _onHomePage():
        """Triggered when opening the home page is requested"""
        QDesktopServices.openUrl(QUrl("https://github.com/sesquicadaver/codimension"))

    @staticmethod
    def _onAllShortcurs():
        """Triggered when opening key bindings page is requested"""
        QDesktopServices.openUrl(
            QUrl(
                "https://github.com/sesquicadaver/codimension/blob/master/"
                "doc/www/codimension.org/documentation/cheatsheet.html"
            )
        )

    def _onCheckForUpdates(self):
        """R172/R173: check GitHub Releases; optional verified download to cache."""
        from utils.update_check import check_for_updates, format_update_message
        from utils.update_download import (
            default_update_cache_dir,
            download_and_verify,
            select_primary_artifact,
        )

        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        try:
            result = check_for_updates()
        finally:
            QApplication.restoreOverrideCursor()

        text = format_update_message(result)
        if result.status == "error":
            QMessageBox.warning(self, "Check for updates", text)
            return
        if result.status == "update_available" and result.latest is not None:
            latest = result.latest
            artifact = select_primary_artifact(latest.assets)
            url = latest.html_url
            if artifact is not None:
                answer = QMessageBox.question(
                    self,
                    "Check for updates",
                    text
                    + "\n\nDownload and verify the artifact into the local cache?"
                    + "\n(Requires a trusted SHA-256; apply/install is not done.)",
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                    QMessageBox.Yes,
                )
                if answer == QMessageBox.Yes:
                    QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
                    try:
                        dl = download_and_verify(latest, default_update_cache_dir())
                    finally:
                        QApplication.restoreOverrideCursor()
                    if dl.status == "ok":
                        QMessageBox.information(
                            self,
                            "Check for updates",
                            dl.message or f"Verified download:\n{dl.path}",
                        )
                    else:
                        QMessageBox.warning(
                            self,
                            "Check for updates",
                            (dl.message or "Download failed.") + (f"\n{dl.error}" if dl.error else ""),
                        )
                    return
                if answer == QMessageBox.No and url:
                    QDesktopServices.openUrl(QUrl(url))
                    return
                return
            if url:
                answer = QMessageBox.question(
                    self,
                    "Check for updates",
                    text + "\n\nOpen the release page in a browser?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes,
                )
                if answer == QMessageBox.Yes:
                    QDesktopServices.openUrl(QUrl(url))
                return
        QMessageBox.information(self, "Check for updates", text)

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
        elif name in ["fileoutline", "debugger", "exceptions", "breakpoints", "calltrace"]:
            self._rightSideBar.show()
            self._rightSideBar.setCurrentTab(name)
            self._rightSideBar.raise_()
        elif name in ["log", "search"]:
            self._bottomSideBar.show()
            self._bottomSideBar.setCurrentTab(name)
            self._bottomSideBar.raise_()

    def _onTabJumpToDef(self):
        """Triggered when jump to defenition is requested"""
        self.em.currentWidget().getEditor().onGotoDefinition()

    def _onTabJumpToScopeBegin(self):
        """Jumps to the beginning of the current scope"""
        self.em.currentWidget().getEditor().onScopeBegin()

    def _onFindOccurences(self):
        """Triggered when search for occurences is requested"""
        self.em.currentWidget().getEditor().onOccurences()

    def findWhereUsed(self, fileName, item):
        """Find occurences for c/f/g browsers"""
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        definitions = getOccurrences(None, fileName, item.line, item.pos)
        QApplication.restoreOverrideCursor()

        self.showStatusBarMessage("")
        result = []
        for definition in definitions:
            if definition.line is None or definition.module_path is None:
                continue

            fName = definition.module_path
            if not fName:
                fName = fileName
            lineno = definition.line
            index = getSearchItemIndex(result, fName)
            if index < 0:
                widget = self.getWidgetForFileName(fName)
                if widget is None:
                    uuid = ""
                else:
                    uuid = widget.getUUID()
                newItem = ItemToSearchIn(fName, uuid)
                result.append(newItem)
                index = len(result) - 1
            result[index].addMatch(item.name, lineno)

        if len(result) == 0:
            self.showStatusBarMessage("No occurrences found")
            return

        self.displayFindInFiles(
            OccurrencesSearchProvider().getName(),
            result,
            {"name": item.name, "filename": fileName, "line": item.line, "column": item.column},
        )

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
                dirName = dirName[len(baseDir) :]
                if dirName == "":
                    dirName = "."
            importDirs.append(dirName)
            index += 1

        QApplication.processEvents()
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))

        prj = GlobalData().project
        prj.tabsStatus = self.em.getTabsStatus()
        self.em.closeAll()

        GlobalData().project.createNew(
            dialog.absProjectFileName,
            {
                "scriptname": dialog.scriptEdit.text().strip(),
                "mddocfile": dialog.mdDocEdit.text().strip(),
                "creationdate": dialog.creationDateEdit.text().strip(),
                "author": dialog.authorEdit.text().strip(),
                "license": dialog.licenseEdit.text().strip(),
                "copyright": dialog.copyrightEdit.text().strip(),
                "version": dialog.versionEdit.text().strip(),
                "email": dialog.emailEdit.text().strip(),
                "description": dialog.descriptionEdit.toPlainText().strip(),
                "encoding": dialog.encodingCombo.currentText().strip(),
                "importdirs": importDirs,
                "pythoninterpreter": dialog.venvEdit.text().strip(),
            },
        )

        QApplication.restoreOverrideCursor()
        self.settings.addRecentProject(dialog.absProjectFileName)

    def _openProject(self):
        """Shows up a dialog to open a project"""
        if self.debugMode:
            return
        dialog = QFileDialog(self, "Open project")
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setOption(QFileDialog.DontUseNativeDialog, True)
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
            logging.warning("The selected project to load is the currently loaded one.")
            return

        if not isCDMProjectFile(fileName):
            logging.warning("Codimension project file must have .cdm3 extension")
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
            logging.error("Could not find project file: %s", path)
        else:
            self.__loadProject(path)

    def onDisasm0(self):
        """Disassemble without optimization"""
        self.em.currentWidget().getEditor()._onDisasm0()

    def onDisasm1(self):
        """Disassemble with optimization level 1"""
        self.em.currentWidget().getEditor()._onDisasm1()

    def onDisasm2(self):
        """Disassemble with optimization level 2"""
        self.em.currentWidget().getEditor()._onDisasm2()

    def showFileDisassembly(self, path, optimization):
        """Triggered when a disassembler should be shown"""
        try:
            code = getFileDisassembled(path, optimization)
            self.em.showDisassembly(path, code)
        except Exception as exc:
            logging.error("Cannot disassemble %s: %s", path, str(exc))

    def showBufferDisassembly(self, content, encoding, path, optimization):
        """Triggered when a disassembler for a buffer is requested"""
        try:
            code = getBufferDisassembled(content, encoding, path, optimization)
            self.em.showDisassembly(path, code)
        except Exception as exc:
            logging.error("Cannot disassemble buffer %s: %s", path, str(exc))

    def showPycDisassembly(self, path):
        """Triggered when a disassembly for a .pyc file is requested"""
        try:
            code = getCompiledfileDisassembled(path, os.path.basename(path).replace(".pyc", ".py"), None)
            self.em.showDisassembly(path, code)
        except Exception as exc:
            logging.error("Cannot disassemble pyc file: %s", str(exc))

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

    def __initPluginSupport(self):
        """Initializes the main window plugin support"""
        self._pluginMenus = {}
        GlobalData().pluginManager.sigPluginActivated.connect(self.__onPluginActivated)
        GlobalData().pluginManager.sigPluginDeactivated.connect(self.__onPluginDeactivated)

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
            logging.error("Error populating %s plugin main menu: %s. Ignore and continue.", pluginName, str(exc))

    def __onPluginDeactivated(self, plugin):
        """Triggered when a plugin is deactivated"""
        try:
            path = plugin.getPath()
            if path in self._pluginMenus:
                del self._pluginMenus[path]
                self._recomposePluginMenu()
        except Exception as exc:
            pluginName = plugin.getName()
            logging.error("Error removing %s plugin main menu: %s. Ignore and continue.", pluginName, str(exc))

    def activateProjectTab(self):
        """Activates the project tab"""
        self._leftSideBar.show()
        self._leftSideBar.setCurrentTab("project")
        self._leftSideBar.raise_()

    def activateRecentTab(self):
        """Activates the Recent Projects tab (for picking a project to load)"""
        self._leftSideBar.show()
        self._leftSideBar.setCurrentTab("recent")
        self._leftSideBar.raise_()

    def activateOutlineTab(self):
        """Activates the outline tab"""
        self._rightSideBar.show()
        self._rightSideBar.setCurrentTab("fileoutline")
        self._rightSideBar.raise_()

    def passFocusToEditor(self):
        """Passes the focus to the text editor if it is there"""
        return self.em.passFocusToEditor()

    def passFocusToFlow(self):
        """Passes the focus to the flow UI if it is there"""
        return self.em.passFocusToFlow()

    def onProfileResults(self, path, outfile, startTime, finishTime, redirected):
        """Triggered when profiling run finished"""
        del redirected  # unused argument
        del finishTime  # unused argument

        if not os.path.exists(outfile):
            logging.error("No profiling results found for %s", path)
            return

        try:
            QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
            widget = ProfileResultsWidget(path, getRunParameters(path), startTime, outfile, self)
            tooltip = "Profiling report for " + os.path.basename(path) + " at " + startTime
            self.em.showProfileReport(widget, tooltip)
        except Exception as exc:
            logging.error(str(exc))
        finally:
            QApplication.restoreOverrideCursor()
            if os.path.exists(outfile):
                os.unlink(outfile)

    def _onFloatingRenderer(self, action=None):
        """Triggered when the renderer type button is triggered"""
        del action  # unused argument
        self.settings["floatingRenderer"] = not self.settings["floatingRenderer"]

        if self.floatingRendererButton.isChecked():
            # Need to make the renderer floating
            self.__detachedRenderer.show()
        else:
            # Need to get back to the embedded renderer
            self.__detachedRenderer.hide()

    def setFocusToFloatingRenderer(self):
        """Raises the window up if it is shown and passes focus"""
        if not self.__detachedRenderer.isHidden():
            self.__detachedRenderer.raise_()
            self.__detachedRenderer.activateWindow()

    def __registerSearchProviders(self):
        """Registers all the search providers"""
        GlobalData().registerSearchProvider(FindInFilesSearchProvider())
        GlobalData().registerSearchProvider(VultureSearchProvider())
        GlobalData().registerSearchProvider(OccurrencesSearchProvider())
