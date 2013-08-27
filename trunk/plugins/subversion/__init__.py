#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010  Sergey Satskiy <sergey.satskiy@gmail.com>
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

" Codimension SVN plugin implementation "


from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QDialog
from plugins.categories.vcsiface import VersionControlSystemInterface
from menus import ( populateMainMenu, populateFileContextMenu,
                    populateDirectoryContextMenu, populateBufferContextMenu )
from configdlg import SVNPluginConfigDialog, saveSVNSettings, getSettings



class SubversionPlugin( VersionControlSystemInterface ):
    """ Codimension subversion plugin """

    def __init__( self ):
        VersionControlSystemInterface.__init__( self )

        self.projectSettings = None
        self.ideWideSettings = None
        return

    @staticmethod
    def isIDEVersionCompatible( ideVersion ):
        " SVN Plugin is compatible with any IDE version "
        return True

    @staticmethod
    def getVCSName():
        """ Should provide the specific version control name, e.g. SVN """
        return "SVN"

    def activate( self, ideSettings, ideGlobalData ):
        " Called when the plugin is activated "
        VersionControlSystemInterface.activate( self, ideSettings,
                                                      ideGlobalData )

        # Read the settings
        self.ideWideSettings = getSettings( self.__getIDEConfigFile() )
        if self.ide.project.isLoaded():
            self.projectSettings = getSettings( self.__getProjectConfigFile() )
        self.connect( self.ide.project, SIGNAL( 'projectChanged' ),
                      self.__onProjectChanged )
        return

    def deactivate( self ):
        " Called when the plugin is deactivated "
        self.disconnect( self.ide.project, SIGNAL( 'projectChanged' ),
                         self.__onProjectChanged )

        self.projectSettings = None
        self.ideWideSettings = None

        VersionControlSystemInterface.deactivate( self )
        return

    def getConfigFunction( self ):
        " SVN plugin requires configuring "
        return self.configure

    def populateMainMenu( self, parentMenu ):
        " Called to build main menu "
        populateMainMenu( self, parentMenu )
        return

    def populateFileContextMenu( self, parentMenu ):
        " Called to build a file context menu in the project and FS browsers "
        populateFileContextMenu( self, parentMenu )
        return

    def populateDirectoryContextMenu( self, parentMenu ):
        " Called to build a dir context menu in the project and FS browsers "
        populateDirectoryContextMenu( self, parentMenu )
        return

    def populateBufferContextMenu( self, parentMenu ):
        " Called to build a buffer context menu "
        populateBufferContextMenu( self, parentMenu )
        return

    def __getIDEConfigFile( self ):
        " Provides a name of the IDE wide config file "
        return self.ide.settingsDir + "svn.plugin.conf"

    def __getProjectConfigFile( self ):
        " Provides a name of the project config file "
        return self.ide.projectSettingsDir + "svn.plugin.conf"

    def configure( self ):
        " Configures the SVN plugin "
        dlg = SVNPluginConfigDialog( self.ideWideSettings,
                                     self.projectSettings )
        if dlg.exec_() == QDialog.Accepted:
            # Save the settings if they have changed
            if self.ideWideSettings != dlg.ideWideSettings:
                self.ideWideSettings = dlg.ideWideSettings
                saveSVNSettings( self.ideWideSettings,
                                 self.__getIDEConfigFile() )
            if self.projectSettings is not None:
                if self.projectSettings != dlg.projectSettings:
                    self.projectSettings = dlg.projectSettings
                    saveSVNSettings( self.projectSettings,
                                     self.__getProjectConfigFile() )
        return

    def __onProjectChanged( self, what ):
        " Triggers when a project has changed "
        if what != self.ide.project.CompleteProject:
            return

        if self.ide.project.isLoaded():
            self.projectSettings = getSettings( self.__getProjectConfigFile() )
        else:
            self.projectSettings = None
        return
