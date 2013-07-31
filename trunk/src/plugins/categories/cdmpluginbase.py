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
        " Activates the plugin "
        IPlugin.activate( self )

        self.ideSettings = ideSettings
        self.ideGlobalData = ideGlobalData
        return

    def deactivate( self ):
        " Deactivates the plugin "
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
        " Provides a reference to the codimension application "
        if self.ideGlobalData is None:
            raise Exception( "Plugin is not active" )
        return self.ideGlobalData.application

    def getMainWindow( self ):
        " Provides a reference to the application main window "
        if self.ideGlobalData is None:
            raise Exception( "Plugin is not active" )
        return self.ideGlobalData.mainWindow

    def getSkin( self ):
        " Provides a reference to the current skin "
        if self.ideGlobalData is None:
            raise Exception( "Plugin is not active" )
        return self.ideGlobalData.skin

    def getProject( self ):
        """ Provides a reference to the current project.
            Note: an object is provided even if there is no project loaded.
                  To check if a project is loaded use
                  getProject().isLoaded()
        """
        if self.ideGlobalData is None:
            raise Exception( "Plugin is not active" )
        return self.ideGlobalData.project

    def getIDESettingsDir( self ):
        " Provides the directory where the IDE settings files are stored "
        return settingsDir

    def getProjectSettingsDir( self ):
        """ Provides the directory where settings specific for the current
            project are stored. If there is no project loaded then None is
            returned.
            The directory is individual for each user.
        """
        project = self.getProject()
        if project.isLoaded():
            return project.userProjectDir
        return None

    def getMainMenu( self ):
        " Provides a reference to the codimension main menu bar (QMenuBar) "
        return self.getMainWindow().menuBar()

    def getStatusBar( self ):
        " Provides a reference to the codimension main window status bar "
        return self.getMainWindow().statusBar()

    def getMainToolbar( self ):
        " Provides a reference to the main window toolbar "
        pass

    def getEditorsManager( self ):
        pass

    def getCurrentEditorWidget( self ):
        pass


