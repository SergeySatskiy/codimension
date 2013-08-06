#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010  Sergey Satskiy sergey.satskiy@gmail.com
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
# $Id$
#

""" Base class for all codimension plugins """

from yapsy.IPlugin import IPlugin
from PyQt4.QtCore import QObject

from utils.settings import settingsDir


class CDMPluginBase( IPlugin, QObject ):
    " Base class for all codimension plugin categories "

    def __init__( self ):
        IPlugin.__init__( self )
        QObject.__init__( self )

        self.ide = IDEAccess()
        return

    def activate( self, ideSettings, ideGlobalData ):
        """ Activates the plugin and saves references to
            the IDE settings and global data """
        IPlugin.activate( self )
        self.ide.activate( ideSettings, ideGlobalData )
        return

    def deactivate( self ):
        """ Deactivates the plugin and clears references to
            the IDE settings and global data """
        self.ide.deactivate()
        IPlugin.deactivate( self )
        return

    def getConfigFunction( self ):
        """ The plugin can provide a function which will be called when the
            user requests plugin configuring.
            If a plugin does not require any config parameters then None
            should be returned.
            By default no configuring is required.
        """
        return None


class SidePanel():
    " Incapsulates access to a side panel widget and its toolbar "

    def __init__( self, widget = None, toolbar = None ):
        self.widget = widget
        self.secondaryWidget = None
        self.toolbar = toolbar
        return



class IDEAccess( object ):
    " Incapsulates access to the various IDE parts "

    def __init__( self ):
        # The members below are initialized after
        # the 'activate' method is called
        self.settings = None
        self.globalData = None
        self.__sidePanels = None
        return

    def activate( self, ideSettings, ideGlobalData ):
        " Saves references to the IDE settings and global data "
        self.settings = ideSettings
        self.globalData = ideGlobalData
        return

    def deactivate( self ):
        " Resets the references to the IDE settings and global data "
        self.settings = None
        self.globalData = None
        return

    def showStatusBarMessage( self, message, timeout = 10000 ):
        """ Shows a temporary status bar message, default for 10sec """
        self.statusBar.showMessage( message, timeout )
        return

    @property
    def application( self ):
        """ Reference to the codimension application.
            See details in src/ui/application.py """
        if self.globalData is None:
            raise Exception( "Plugin is not active" )
        return self.globalData.application

    @property
    def mainWindow( self ):
        """ Reference to the application main window.
            See details in src/ui/mainwindow.py """
        if self.globalData is None:
            raise Exception( "Plugin is not active" )
        return self.globalData.mainWindow

    @property
    def skin( self ):
        """ Reference to the current skin.
            See details in src/utils/skin.py """
        if self.globalData is None:
            raise Exception( "Plugin is not active" )
        return self.globalData.skin

    @property
    def project( self ):
        """ Reference to the current project.
            See details in src/utils/project.py
            Note: an object is provided even if there is no project loaded.
                  To check if a project is loaded use
                  getProject().isLoaded()
        """
        if self.globalData is None:
            raise Exception( "Plugin is not active" )
        return self.globalData.project

    @property
    def settingsDir( self ):
        """ The directory where the IDE setting files are stored.
            The directory is individual for each user and it is usually
            ~/.codimension/
        """
        return settingsDir

    @property
    def projectSettingsDir( self ):
        """ The directory where settings specific for the current
            project are stored. If there is no project loaded at the time of
            calling then None is returned.
            The directory is individual for each user/project and it is usually
            ~/.codimension/<project UUID>
        """
        if self.project.isLoaded():
            return self.project.userProjectDir
        return None

    @property
    def mainMenu( self ):
        " Reference to the codimension main menu bar (QMenuBar) "
        return self.mainWindow.menuBar()

    @property
    def statusBar( self ):
        " Reference to the codimension main window status bar (QStatusBar) "
        return self.mainWindow.statusBar()

    @property
    def mainToolbar( self ):
        " Reference to the main window toolbar (QToolBar) "
        return self.mainWindow.getToolbar()

    @property
    def editorsManager( self ):
        """ Reference to the editors manager (it derives QTabWidget)
            See details in src/ui/editorsmanager.py
        """
        return self.mainWindow.editorsManagerWidget.editorsManager

    @property
    def currentEditorWidget( self ):
        """ Reference to the current main area widget.
            Note: the widget could be of various types e.g. pixmap viewer, html viewer,
                  text editor etc. All of them derive from MainWindowTabWidgetBase (see
                  details in src/ui/mainwindowtabwidgetbase.py)
                  The getCurrentEditorWidget().getType() call provides the current widget type.
                  The known widget types are described in src/ui/mainwindowtabwidgetbase.py
                  Depending on the widget type various functionality is avalable. See the
                  certain widget implementation files:
                  PlainTextEditor     src/editor/texteditor.py
                  PictureViewer       src/ui/pixmapwidget.py
                  HTMLViewer          src/ui/htmltabwidget.py
                  GeneratedDiagram    src/diagram/importsdgmgraphics.py
                  ProfileViewer       src/profiling/profwidget.py
                  DisassemblerViewer  src/profiling/disasmwidget.py
        """
        return self.editorsManager.currentWidget()

    @property
    def sidePanels( self ):
        """ Reference to a side panel widget and its toolbar map, i.e. a plugin class
            can use the following code:
            self.sidePanels[ "project" ].widget
            self.sidePanels[ "project" ].toolbar
            A side panel is identified by its string identifier.

            Supported panel names are (case sensitive):
            project, fileSystem, recentFiles, recentProjects,
            classes, functions, globals, log, pylint, pymetrics,
            search, contextHelp, diff, fileOutline, debugVariables,
            debugStack, debugThreads, exceptions, ignoredExceptions,
            breakpoints.
        """
        if self.__sidePanels is None:
            self.__initializeSidePanels()
        return self.__sidePanels

    def __initializeSidePanels( self ):
        " Initializes the side panels map "
        self.__sidePanels = {}
        self.__sidePanels[ "project" ] = \
                SidePanel( self.mainWindow.projectViewer.projectTreeView,
                           self.mainWindow.projectViewer.getProjectToolbar() )
        self.__sidePanels[ "fileSystem" ] = \
                SidePanel( self.mainWindow.projectViewer.filesystemView,
                           self.mainWindow.projectViewer.getFileSystemToolbar() )
        self.__sidePanels[ "recentFiles" ] = \
                SidePanel( self.mainWindow.recentProjectsViewer.recentFilesView,
                           self.mainWindow.recentProjectsViewer.getRecentFilesToolbar() )
        self.__sidePanels[ "recentProjects" ] = \
                SidePanel( self.mainWindow.recentProjectsViewer.projectsView,
                           self.mainWindow.recentProjectsViewer.getRecentProjectsToolbar() )
        self.__sidePanels[ "classes" ] = \
                SidePanel( self.mainWindow.classesViewer.clViewer,
                           self.mainWindow.classesViewer.toolbar )
        self.__sidePanels[ "functions" ] = \
                SidePanel( self.mainWindow.functionsViewer.funcViewer,
                           self.mainWindow.functionsViewer.toolbar )
        self.__sidePanels[ "globals" ] = \
                SidePanel( self.mainWindow.globalsViewer.globalsViewer,
                           self.mainWindow.globalsViewer.toolbar )
        self.__sidePanels[ "log" ] = \
                SidePanel( self.mainWindow.logViewer.messages,
                           self.mainWindow.logViewer.toolbar )
        self.__sidePanels[ "pylint" ] = \
                SidePanel( self.mainWindow.pylintViewer.bodyWidget,
                           self.mainWindow.pylintViewer.toolbar )
        self.__sidePanels[ "pymetrics" ] = \
                SidePanel( self.mainWindow.pymetricsViewer.getTotalResultsWidget(),
                           self.mainWindow.pymetricsViewer.toolbar )
        self.__sidePanels[ "pymetrics"].secondaryWidget = \
                self.mainWindow.pymetricsViewer.getMcCabeResultsWidget()
        self.__sidePanels[ "search" ] = \
                SidePanel( self.mainWindow.findInFilesViewer.getResultsTree(),
                           self.mainWindow.findInFilesViewer.toolbar )
        self.__sidePanels[ "contextHelp" ] = \
                SidePanel( self.mainWindow.tagHelpViewer.widget,
                           self.mainWindow.tagHelpViewer.toolbar )
        self.__sidePanels[ "diff" ] = \
                SidePanel()
        self.__sidePanels[ "fileOutline" ] = \
                SidePanel()
        self.__sidePanels[ "debugVariables" ] = \
                SidePanel()
        self.__sidePanels[ "debugStack" ] = \
                SidePanel()
        self.__sidePanels[ "debugThreads" ] = \
                SidePanel()
        self.__sidePanels[ "exceptions" ] = \
                SidePanel()
        self.__sidePanels[ "ignoredExceptions" ] = \
                SidePanel()
        self.__sidePanels[ "breakpoints" ] = \
                SidePanel()
        return



