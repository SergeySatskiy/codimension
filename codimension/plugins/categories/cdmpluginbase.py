# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2017  Sergey Satskiy sergey.satskiy@gmail.com
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

"""Base class for all codimension plugins"""

import logging
from yapsy.IPlugin import IPlugin
from ui.qt import QObject, pyqtSignal
from utils.settings import SETTINGS_DIR


class CDMPluginBase(IPlugin, QObject):

    """Base class for all codimension plugin categories"""

    pluginLogMessage = pyqtSignal(int, str)

    def __init__(self):
        IPlugin.__init__(self)
        QObject.__init__(self)

        self.ide = IDEAccess(self)

    def activate(self, ideSettings, ideGlobalData):
        """Activates the plugin.

        Also saves references to the IDE settings and global data
        """
        IPlugin.activate(self)
        self.ide.activate(ideSettings, ideGlobalData)

    def deactivate(self):
        """Deactivates the plugin.

        Also clears references to the IDE settings and global data
        """
        self.ide.deactivate()
        IPlugin.deactivate(self)

    def getConfigFunction(self):
        """A plugin may provide a function for configuring it.

        If a plugin does not require any config parameters then None
        should be returned.
        By default no configuring is required.
        """
        return None


class ViewAndToolbar():

    """Incapsulates access to a certain view widget inside a side panel"""

    def __init__(self, widget, toolbar):
        self.widget = widget
        self.toolbar = toolbar


class SidePanel():

    """Incapsulates access to a side panel widget and its toolbar"""

    def __init__(self, widget):
        self.widget = widget
        self.views = {}       # view name (string) -> ViewAndToolbar instance


class IDEAccess():

    """Incapsulates access to the various IDE parts"""

    def __init__(self, parent):
        # The members below are initialized after
        # the 'activate' method is called
        self.settings = None
        self.globalData = None
        self.__sidePanels = None
        self.__parent = parent

    def activate(self, ideSettings, ideGlobalData):
        """Saves references to the IDE settings and global data"""
        self.settings = ideSettings
        self.globalData = ideGlobalData

    def deactivate(self):
        """Resets the references to the IDE settings and global data"""
        self.settings = None
        self.globalData = None

    def showStatusBarMessage(self, message, timeout=10000):
        """Shows a temporary status bar message (default for 10sec)"""
        self.mainWindow.showStatusBarMessage(message, timeout)

    def clearStatusBarMessage(self):
        """Clears a temporary status bar message"""
        self.mainWindow.clearStatusBarMessage()

    @property
    def application(self):
        """Reference to the codimension application.

        See details in src/ui/application.py
        """
        if self.globalData is None:
            raise Exception("Plugin is not active")
        return self.globalData.application

    @property
    def mainWindow(self):
        """Reference to the application main window.
           See details in src/ui/mainwindow.py"""
        if self.globalData is None:
            raise Exception("Plugin is not active")
        return self.globalData.mainWindow

    @property
    def skin(self):
        """Reference to the current skin.

        See details in src/utils/skin.py
        """
        if self.globalData is None:
            raise Exception("Plugin is not active")
        return self.globalData.skin

    @property
    def project(self):
        """Reference to the current project.

        See details in src/utils/project.py
        Note: an object is provided even if there is no project loaded.
              To check if a project is loaded use
              getProject().isLoaded()
        """
        if self.globalData is None:
            raise Exception("Plugin is not active")
        return self.globalData.project

    @property
    def settingsDir(self):
        """The directory where the IDE setting files are stored.

        The directory is individual for each user and it is usually
        ~/.codimension3/
        """
        return SETTINGS_DIR

    @property
    def projectSettingsDir(self):
        """The directory where settings specific for the current
           project are stored. If there is no project loaded at the time of
           calling then None is returned.
           The directory is individual for each user/project and it is usually
           ~/.codimension3/<project UUID>"""
        if self.project.isLoaded():
            return self.project.userProjectDir
        return None

    @property
    def mainMenu(self):
        """Reference to the codimension main menu bar (QMenuBar)"""
        return self.mainWindow.menuBar()

    @property
    def statusBar(self):
        """Reference to the codimension main window status bar (QStatusBar)"""
        return self.mainWindow.statusBar()

    @property
    def mainToolbar(self):
        """Reference to the main window toolbar (QToolBar)"""
        return self.mainWindow.getToolbar()

    @property
    def editorsManager(self):
        """Reference to the editors manager (it derives QTabWidget)

        See details in src/ui/editorsmanager.py
        """
        return self.mainWindow.editorsManagerWidget.editorsManager

    @property
    def currentEditorWidget(self):
        """Reference to the current main area widget.

        Note: the widget could be of various types e.g. pixmap viewer,
              html viewer, text editor etc. All of them derive from
              MainWindowTabWidgetBase (see details in
              src/ui/mainwindowtabwidgetbase.py)
              The getCurrentEditorWidget().getType() call provides the
              current widget type.
              The known widget types are described in
              src/ui/mainwindowtabwidgetbase.py
              Depending on the widget type various functionality is
              avalable. See the certain widget implementation files:
              PlainTextEditor     src/editor/texteditor.py
              PictureViewer       src/ui/pixmapwidget.py
              HTMLViewer          src/ui/htmltabwidget.py
              GeneratedDiagram    src/diagram/importsdgmgraphics.py
              ProfileViewer       src/profiling/profwidget.py
        """
        return self.editorsManager.currentWidget()

    @property
    def sidePanels(self):
        """Reference to a side panel widget map.

        I.e. a plugin class can use e.g. the following code:
        self.sidePanels[ "project" ].widget
        A side panel is identified by its string identifier.

        Supported panel names are (case sensitive):
        project, recent, classes, functions, globals, log, pylint,
        pymetrics, search, contextHelp, diff, debuger,
        exceptions, breakpoints.

        Each side panel contains one or more views with thier toolbars. To
        get access to them a plugin class can use e.g. the following code:
        self.sidePanels[ "recent" ].views[ "files" ].widget
        self.sidePanels[ "recent" ].views[ "files" ].toolbar
        The names of views depend on the side panel.
        """
        if self.__sidePanels is None:
            self.__initializeSidePanels()
        return self.__sidePanels

    def __initializeSidePanels(self):
        """Initializes the side panels map"""
        self.__sidePanels = {}

        # Project
        projectPanel = SidePanel(self.mainWindow.projectViewer)
        projectPanel.views["project"] = ViewAndToolbar(
            projectPanel.widget.projectTreeView,
            projectPanel.widget.getProjectToolbar())
        projectPanel.views["fileSystem"] = ViewAndToolbar(
            projectPanel.widget.filesystemView,
            projectPanel.widget.getFileSystemToolbar())
        self.__sidePanels["project"] = projectPanel

        # Recent
        recentPanel = SidePanel(self.mainWindow.recentProjectsViewer)
        recentPanel.views["files"] = ViewAndToolbar(
            recentPanel.widget.recentFilesView,
            recentPanel.widget.getRecentFilesToolbar())
        recentPanel.views["projects"] = ViewAndToolbar(
            recentPanel.widget.projectsView,
            recentPanel.widget.getRecentProjectsToolbar())
        self.__sidePanels["recent"] = recentPanel

        # Classes
        classesPanel = SidePanel(self.mainWindow.classesViewer)
        classesPanel.views["classes"] = ViewAndToolbar(
            classesPanel.widget.clViewer,
            classesPanel.widget.toolbar)
        self.__sidePanels["classes"] = classesPanel

        # Functions
        funcPanel = SidePanel(self.mainWindow.functionsViewer)
        funcPanel.views["functions"] = ViewAndToolbar(
            funcPanel.widget.funcViewer,
            funcPanel.widget.toolbar)
        self.__sidePanels["functions"] = funcPanel

        # Globals
        globPanel = SidePanel(self.mainWindow.globalsViewer)
        globPanel.views["globals"] = ViewAndToolbar(
            globPanel.widget.globalsViewer,
            globPanel.widget.toolbar)
        self.__sidePanels["globals"] = globPanel

        # Log
        logPanel = SidePanel(self.mainWindow.logViewer)
        logPanel.views["log"] = ViewAndToolbar(
            logPanel.widget.messages,
            logPanel.widget.toolbar)
        self.__sidePanels["log"] = logPanel

        # Pylint
        lintPanel = SidePanel(self.mainWindow.pylintViewer)
        lintPanel.views["pylint"] = ViewAndToolbar(
            lintPanel.widget.bodyWidget,
            lintPanel.widget.toolbar)
        self.__sidePanels["pylint"] = lintPanel

        # Pymetrics
        metricsPanel = SidePanel(self.mainWindow.pymetricsViewer)
        metricsPanel.views["total"] = ViewAndToolbar(
            metricsPanel.widget.getTotalResultsWidget(),
            metricsPanel.widget.toolbar)
        metricsPanel.views["mccabe"] = ViewAndToolbar(
            metricsPanel.widget.getMcCabeResultsWidget(),
            metricsPanel.widget.toolbar)
        self.__sidePanels["pymetrics"] = metricsPanel

        # Search
        searchPanel = SidePanel(self.mainWindow.findInFilesViewer)
        searchPanel.views["search"] = ViewAndToolbar(
            searchPanel.widget.getResultsTree(),
            searchPanel.widget.toolbar)
        self.__sidePanels["search"] = searchPanel

        # Context help
        ctxHelpPanel = SidePanel(self.mainWindow.tagHelpViewer)
        ctxHelpPanel.views["contextHelp"] = ViewAndToolbar(
            ctxHelpPanel.widget.widget,
            ctxHelpPanel.widget.toolbar)
        self.__sidePanels["contextHelp"] = ctxHelpPanel

        # Diff
        diffPanel = SidePanel(self.mainWindow.diffViewer)
        diffPanel.views["diff"] = ViewAndToolbar(
            diffPanel.widget.viewer,
            diffPanel.widget.toolbar)
        self.__sidePanels["diff"] = diffPanel

        # Debugger
        dbgPanel = SidePanel(self.mainWindow.debuggerContext)
        dbgPanel.views["variables"] = ViewAndToolbar(
            dbgPanel.widget.variablesViewer,
            None)
        dbgPanel.views["stack"] = ViewAndToolbar(
            dbgPanel.widget.stackViewer,
            None)
        dbgPanel.views["threads"] = ViewAndToolbar(
            dbgPanel.widget.threadsViewer,
            None)
        self.__sidePanels["debugger"] = dbgPanel

        # Exceptions
        excptPanel = SidePanel(self.mainWindow.debuggerExceptions)
        excptPanel.views["exceptions"] = ViewAndToolbar(
            excptPanel.widget.clientExcptViewer.exceptionsList,
            excptPanel.widget.clientExcptViewer.toolbar)
        excptPanel.views["ignoredExceptions"] = ViewAndToolbar(
            excptPanel.widget.ignoredExcptViewer.exceptionsList,
            excptPanel.widget.ignoredExcptViewer.toolbar)
        self.__sidePanels["exceptions"] = excptPanel

        # Breakpoints
        bpointPanel = SidePanel(self.mainWindow.debuggerBreakWatchPoints)
        bpointPanel.views["breakpoints"] = ViewAndToolbar(
            bpointPanel.widget.breakPointViewer.bpointsList,
            bpointPanel.widget.breakPointViewer.toolbar)
        self.__sidePanels["breakpoints"] = bpointPanel

    def sendLogMessage(self, level, msg, *args):
        """Sends a log message asynchronously.

        The method could be used safely from a non-GUI thread.

        level => integer, one of those found in logging:
                          logging.CRITICAL
                          logging.ERROR
                          logging.WARNING
                          logging.INFO
                          logging.DEBUG
        msg => message
        args => message arguments to be substituted (mgs % args)
        """
        try:
            self.__parent.pluginLogMessage.emit(level, msg % args)
        except Exception as exc:
            self.__parent.pluginLogMessage.emit(
                logging.ERROR,
                "Error sending a plugin log message. Error: " + str(exc))
