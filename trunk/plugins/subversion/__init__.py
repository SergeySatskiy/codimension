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
from threading import Lock
from copy import deepcopy
import pysvn
from plugins.categories.vcsiface import VersionControlSystemInterface
from menus import ( populateMainMenu, populateFileContextMenu,
                    populateDirectoryContextMenu, populateBufferContextMenu )
from configdlg import ( SVNPluginConfigDialog, saveSVNSettings, getSettings,
                        AUTH_PASSWD, STATUS_LOCAL_ONLY )
from svnindicators import ( IND_ADDED, IND_ERROR, IND_DELETED, IND_IGNORED,
                            IND_MERGED,
                            IND_DESCRIPTION )



class SubversionPlugin( VersionControlSystemInterface ):
    """ Codimension subversion plugin """

    def __init__( self ):
        VersionControlSystemInterface.__init__( self )

        self.projectSettings = None
        self.ideWideSettings = None
        self.__settingsLock = Lock()
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
        print "SVN Plugin activated"
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
            self.__settingsLock.acquire()
            if self.ideWideSettings != dlg.ideWideSettings:
                self.ideWideSettings = dlg.ideWideSettings
                saveSVNSettings( self.ideWideSettings,
                                 self.__getIDEConfigFile() )
            if self.projectSettings is not None:
                if self.projectSettings != dlg.projectSettings:
                    self.projectSettings = dlg.projectSettings
                    saveSVNSettings( self.projectSettings,
                                     self.__getProjectConfigFile() )
            self.__settingsLock.release()
        return

    def __onProjectChanged( self, what ):
        " Triggers when a project has changed "
        if what != self.ide.project.CompleteProject:
            return

        if self.ide.project.isLoaded():
            self.__settingsLock.acquire()
            self.projectSettings = getSettings( self.__getProjectConfigFile() )
            self.__settingsLock.release()
        else:
            self.__settingsLock.acquire()
            self.projectSettings = None
            self.__settingsLock.release()
        return

    def getCustomIndicators( self ):
        " Provides custom indicators if needed "
        return IND_DESCRIPTION

    def getSettings( self ):
        " Thread safe settings copy "
        if self.ide.project.isLoaded():
            self.__settingsLock.acquire()
            settings = deepcopy( self.projectSettings )
            self.__settingsLock.release()
            return settings

        self.__settingsLock.acquire()
        settings = deepcopy( self.ideWideSettings )
        self.__settingsLock.release()
        return settings

    def getSVNClient( self, settings ):
        " Creates the SVN client object "
        client = pysvn.Client()
        client.exception_style = 1   # In order to get error codes

        if settings.authKind == AUTH_PASSWD:
            client.set_default_username( settings.userName )
            client.set_default_password( settings.password )
        return client

    @staticmethod
    def __convertSVNStatus( status ):
        " Converts the status between the SVN and the plugin supported values "
        if status.text_status == pysvn.wc_status_kind.added:
            return IND_ADDED
        if status.text_status == pysvn.wc_status_kind.deleted:
            return IND_DELETED
        if status.text_status == pysvn.wc_status_kind.ignored:
            return IND_IGNORED
        if status.text_status == pysvn.wc_status_kind.merged:
            return IND_MERGED
        if status.text_status == pysvn.wc_status_kind.modified:
            return 0
        if status.text_status == pysvn.wc_status_kind.normal:
            return 0
        if status.text_status == pysvn.wc_status_kind.replaced:
            return 0
        if status.text_status == pysvn.wc_status_kind.conflicted:
            return 0
        if status.text_status == pysvn.wc_status_kind.external:
            return 0
        if status.text_status == pysvn.wc_status_kind.incomplete:
            return 0
        if status.text_status == pysvn.wc_status_kind.missing:
            return 0
        if status.text_status == pysvn.wc_status_kind.none:
            return 0
        if status.text_status == pysvn.wc_status_kind.obstructed:
            return 0
        if status.text_status == pysvn.wc_status_kind.unversioned:
            return 0

        return 0

    def getStatus( self, path, flag ):
        " Provides VCS statuses for the path "
        settings = self.getSettings()
        client = self.getSVNClient( settings )

        clientUpdate = settings.statusKind != STATUS_LOCAL_ONLY
        if flag == self.REQUEST_RECURSIVE:
            clientRecurse = True
            clientGetAll = True
        elif flag == self.REQUEST_ITEM_ONLY:
            clientRecurse = False
            clientGetAll = False
        else:
            clientRecurse = False
            clientGetAll = True

        try:
            statusList = client.status( path, recurse = clientRecurse,
                                        get_all = clientGetAll,
                                        update = clientUpdate )
            result = []
            for status in statusList:
                result.append( (status.path.replace( path, "" ),
                               self.__convertSVNStatus( status ), None) )
            return result
        except pysvn.ClientError, exc:
            errorCode = exc.args[ 1 ]
            if errorCode == pysvn.svn_err.wc_not_working_copy:
                return ( ("", self.NOT_UNDER_VCS, None), )
            message = exc.args[ 0 ]
            return ( ("", IND_ERROR, message), )
        except Exception, exc:
            return ( ("", IND_ERROR, "Error: " + str( exc )), )
        except:
            return ( ("", IND_ERROR, "Unknown error"), )
