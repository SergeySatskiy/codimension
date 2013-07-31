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

        # The members below are initialized after
        # the 'activate' method is called
        self.ideSettings = None
        self.ideGlobalData = None
        return

    def activate( self, ideSettings, ideGlobalData ):
        """ Activates the plugin and saves references to
            the IDE settings and global data """
        IPlugin.activate( self )

        self.ideSettings = ideSettings
        self.ideGlobalData = ideGlobalData
        return

    def deactivate( self ):
        """ Deactivates the plugin and clears references to
            the IDE settings and global data """
        self.ideSettings = None
        self.ideGlobalData = None

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

    def getApplication( self ):
        """ Provides a reference to the codimension application.
            See details in src/ui/application.py """
        if self.ideGlobalData is None:
            raise Exception( "Plugin is not active" )
        return self.ideGlobalData.application

    def getMainWindow( self ):
        """ Provides a reference to the application main window.
            See details in src/ui/mainwindow.py """
        if self.ideGlobalData is None:
            raise Exception( "Plugin is not active" )
        return self.ideGlobalData.mainWindow

    def getSkin( self ):
        """ Provides a reference to the current skin.
            See details in src/utils/skin.py """
        if self.ideGlobalData is None:
            raise Exception( "Plugin is not active" )
        return self.ideGlobalData.skin

    def getProject( self ):
        """ Provides a reference to the current project.
            See details in src/utils/project.py
            Note: an object is provided even if there is no project loaded.
                  To check if a project is loaded use
                  getProject().isLoaded()
        """
        if self.ideGlobalData is None:
            raise Exception( "Plugin is not active" )
        return self.ideGlobalData.project

    def getIDESettingsDir( self ):
        """ Provides the directory where the IDE setting files are stored.
            The directory is individual for each user and it is usually
            ~/.codimension/
        """
        return settingsDir

    def getProjectSettingsDir( self ):
        """ Provides the directory where settings specific for the current
            project are stored. If there is no project loaded at the time of
            calling then None is returned.
            The directory is individual for each user/project and it is usually
            ~/.codimension/<project UUID>
        """
        project = self.getProject()
        if project.isLoaded():
            return project.userProjectDir
        return None

    def getMainMenu( self ):
        " Provides a reference to the codimension main menu bar (QMenuBar) "
        return self.getMainWindow().menuBar()

    def getStatusBar( self ):
        " Provides a reference to the codimension main window status bar (QStatusBar) "
        return self.getMainWindow().statusBar()

    def getMainToolbar( self ):
        " Provides a reference to the main window toolbar (QToolBar) "
        return self.getMainWindow().getToolbar()

    def getEditorsManager( self ):
        """ Provides a reference to the editors manager (it derives QTabWidget)
            See details in src/ui/editorsmanager.py
        """
        return self.getMainWindow().editorsManagerWidget.editorsManager

    def getCurrentEditorWidget( self ):
        """ Provides a reference to the current widget.
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
        return self.getEditorsManager().currentWidget()


