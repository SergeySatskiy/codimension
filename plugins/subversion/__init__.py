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


from PyQt4.QtCore import SIGNAL, QMutex
from PyQt4.QtGui import QDialog
from copy import deepcopy
import pysvn
import os.path
import logging
from plugins.categories.vcsiface import VersionControlSystemInterface
from svnmenus import ( populateMainMenu, populateFileContextMenu,
                       populateDirectoryContextMenu, populateBufferContextMenu,
                       fileContextMenuAboutToShow, mainMenuAboutToShow,
                       directoryContextMenuAboutToShow, bufferContextMenuAboutToshow )
from svnconfigdlg import ( SVNPluginConfigDialog, saveSVNSettings, getSettings,
                           AUTH_PASSWD, STATUS_LOCAL_ONLY )
from svnindicators import ( IND_ADDED, IND_ERROR, IND_DELETED, IND_IGNORED,
                            IND_MERGED, IND_MODIFIED_LR, IND_MODIFIED_L,
                            IND_MODIFIED_R, IND_UPTODATE, IND_REPLACED,
                            IND_CONFLICTED, IND_EXTERNAL, IND_INCOMPLETE,
                            IND_MISSING, IND_OBSTRUCTED, IND_UNKNOWN,
                            IND_DESCRIPTION )
from svninfo import getSVNInfo
from svnupdate import doSVNUpdate
from svnannotate import doSVNAnnotate
from svnstrconvert import statusToString



class SubversionPlugin( VersionControlSystemInterface ):
    """ Codimension subversion plugin """

    def __init__( self ):
        VersionControlSystemInterface.__init__( self )

        self.projectSettings = None
        self.ideWideSettings = None
        self.__settingsLock = QMutex()

        self.fileParentMenu = None
        self.dirParentMenu = None
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
            self.__settingsLock.lock()
            if self.ideWideSettings != dlg.ideWideSettings:
                self.ideWideSettings = dlg.ideWideSettings
                saveSVNSettings( self.ideWideSettings,
                                 self.__getIDEConfigFile() )
            if self.projectSettings is not None:
                if self.projectSettings != dlg.projectSettings:
                    self.projectSettings = dlg.projectSettings
                    saveSVNSettings( self.projectSettings,
                                     self.__getProjectConfigFile() )
            self.__settingsLock.unlock()
        return

    def __onProjectChanged( self, what ):
        " Triggers when a project has changed "
        if what != self.ide.project.CompleteProject:
            return

        if self.ide.project.isLoaded():
            self.__settingsLock.lock()
            self.projectSettings = getSettings( self.__getProjectConfigFile() )
            self.__settingsLock.unlock()
        else:
            self.__settingsLock.lock()
            self.projectSettings = None
            self.__settingsLock.unlock()
        return

    def getCustomIndicators( self ):
        " Provides custom indicators if needed "
        return IND_DESCRIPTION

    def getSettings( self ):
        " Thread safe settings copy "
        if self.ide.project.isLoaded():
            self.__settingsLock.lock()
            settings = deepcopy( self.projectSettings )
            self.__settingsLock.unlock()
            return settings

        self.__settingsLock.lock()
        settings = deepcopy( self.ideWideSettings )
        self.__settingsLock.unlock()
        return settings

    def getSVNClient( self, settings ):
        " Creates the SVN client object "
        client = pysvn.Client()
        client.exception_style = 1   # In order to get error codes

        if settings.authKind == AUTH_PASSWD:
            client.set_default_username( settings.userName )
            client.set_default_password( settings.password )
        return client

    def __convertSVNStatus( self, status ):
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
            if status.repos_text_status == pysvn.wc_status_kind.modified:
                return IND_MODIFIED_LR
            return IND_MODIFIED_L
        if status.text_status == pysvn.wc_status_kind.normal:
            if status.repos_text_status == pysvn.wc_status_kind.modified:
                return IND_MODIFIED_R
            return IND_UPTODATE
        if status.text_status == pysvn.wc_status_kind.replaced:
            return IND_REPLACED
        if status.text_status == pysvn.wc_status_kind.conflicted:
            return IND_CONFLICTED
        if status.text_status == pysvn.wc_status_kind.external:
            return IND_EXTERNAL
        if status.text_status == pysvn.wc_status_kind.incomplete:
            return IND_INCOMPLETE
        if status.text_status == pysvn.wc_status_kind.missing:
            return IND_MISSING
        if status.text_status == pysvn.wc_status_kind.none:
            return self.NOT_UNDER_VCS
        if status.text_status == pysvn.wc_status_kind.obstructed:
            return IND_OBSTRUCTED
        if status.text_status == pysvn.wc_status_kind.unversioned:
            return self.NOT_UNDER_VCS

        return IND_UNKNOWN

    def getStatus( self, path, flag ):
        " Provides VCS statuses for the path "
        settings = self.getSettings()
        client = self.getSVNClient( settings )

        clientUpdate = settings.statusKind != STATUS_LOCAL_ONLY
        if flag == self.REQUEST_RECURSIVE:
            clientDepth = pysvn.depth.infinity
        elif flag == self.REQUEST_ITEM_ONLY:
            # Heck! By some reasons if depth empty AND update is True
            # the request returns nothing
            if path.endswith( os.path.sep ):
                clientDepth = pysvn.depth.empty
            else:
                clientDepth = pysvn.depth.unknown
        else:
            clientDepth = pysvn.depth.files

        try:
            statusList = client.status( path, update = clientUpdate,
                                        depth = clientDepth )
            result = []
            for status in statusList:
                reportPath = status.path
                if not status.path.endswith( os.path.sep ):
                    if status.entry is None:
                        if os.path.isdir( status.path ):
                            reportPath += os.path.sep
                    elif status.entry.kind == pysvn.node_kind.dir:
                        reportPath += os.path.sep

                result.append( (reportPath.replace( path, "" ),
                                self.__convertSVNStatus( status ),
                                None) )
            client = None
            return result
        except pysvn.ClientError, exc:
            errorCode = exc.args[ 1 ][ 0 ][ 1 ]
            if errorCode == pysvn.svn_err.wc_not_working_copy:
                client = None
                return ( ("", self.NOT_UNDER_VCS, None), )
            message = exc.args[ 0 ]
            client = None
            return ( ("", IND_ERROR, message), )
        except Exception, exc:
            client = None
            return ( ("", IND_ERROR, "Error: " + str( exc )), )
        except:
            client = None
            return ( ("", IND_ERROR, "Unknown error"), )

    def getLocalStatus( self, path ):
        " Provides quick local SVN status for the item itself "
        client = self.getSVNClient( self.getSettings() )
        try:
            statusList = client.status( path, update = False,
                                        depth = pysvn.depth.empty )
            if len( statusList ) != 1:
                return IND_ERROR
            return self.__convertSVNStatus( statusList[ 0 ] )
        except pysvn.ClientError, exc:
            errorCode = exc.args[ 1 ][ 0 ][ 1 ]
            if errorCode == pysvn.svn_err.wc_not_working_copy:
                return self.NOT_UNDER_VCS
            message = exc.args[ 0 ]
            print message
            return IND_ERROR
        except Exception, exc:
            print str(exc)
            return IND_ERROR
        except:
            return IND_ERROR

    def fileInfo( self ):
        " Called when info requested for a file via context menu "
        path = str( self.fileParentMenu.menuAction().data().toString() )
        self.__svnInfo( path )
        return

    def dirInfo( self ):
        " Called when info requested for a directory via context menu "
        path = str( self.dirParentMenu.menuAction().data().toString() )
        self.__svnInfo( path )
        return

    def bufferInfo( self ):
        " Called when info requested for a buffer "
        path = self.ide.currentEditorWidget.getFileName()
        if not os.path.isabs( path ):
            logging.info( "SVN info is not applicable for never saved buffer" )
            return
        self.__svnInfo( path )
        return

    def __svnInfo( self, path ):
        " Implementation of the info command for a file "
        status = self.getLocalStatus( path )
        if status == IND_ERROR:
            logging.error( "Error getting status of " + path )
            return
        if status == self.NOT_UNDER_VCS:
            logging.info( "Status: " + statusToString( status ) )
            return

        client = self.getSVNClient( self.getSettings() )
        info = getSVNInfo( client, path )
        message = "\n    Status: " + statusToString( status )
        for item in info:
            message = message + "\n    " + item[ 0 ] + ": " + item[ 1 ]
        logging.info( message )
        client = None
        return

    def fileUpdate( self ):
        " Called when update for a file is requested "
        path = str( self.fileParentMenu.menuAction().data().toString() )
        self.__svnUpdate( path, False )
        return

    def dirUpdate( self ):
        " Called when update for a directory is requested "
        path = str( self.dirParentMenu.menuAction().data().toString() )
        self.__svnUpdate( path, True )
        return

    def bufferUpdate( self ):
        " Called when update for a buffer is requested "
        path = self.ide.currentEditorWidget.getFileName()
        if not os.path.isabs( path ):
            logging.info( "SVN update is not applicable for never saved buffer" )
            return
        self.__svnUpdate( path, False )
        return

    def __svnUpdate( self, path, recursively ):
        " Does SVN update "
        client = self.getSVNClient( self.getSettings() )
        doSVNUpdate( client, path, recursively )
        return

    def fileAnnotate( self ):
        " Called when annotate for a file is requested "
        path = str( self.fileParentMenu.menuAction().data().toString() )
        self.__svnAnnotate( path )
        return

    def bufferAnnotate( self ):
        " Called when annotate for a buffer is requested "
        path = self.ide.currentEditorWidget.getFileName()
        if not os.path.isabs( path ):
            logging.info( "SVN annotate is not "
                          "applicable for never saved buffer" )
            return
        self.__svnAnnotate( path )
        return

    def __svnAnnotate( self, path ):
        " Does SVN annotate "
        client = self.getSVNClient( self.getSettings() )
        fullText, revisionPerLine, revisionsInfo = doSVNAnnotate( client, path )
        if fullText is not None and revisionPerLine is not None and \
            revisionsInfo is not None:
            self.ide.editorsManager.showAnnotated( path, fullText,
                                                   revisionPerLine,
                                                   revisionsInfo )
        return


    # Menu dispatching

    def onMainMenuAboutToShow( self ):
        mainMenuAboutToShow( self )
        return

    def onFileContextMenuAboutToShow( self ):
        fileContextMenuAboutToShow( self )
        return

    def onDirectoryContextMenuAboutToShow( self ):
        directoryContextMenuAboutToShow( self )
        return

    def onBufferContextMenuAboutToshow( self ):
        bufferContextMenuAboutToshow( self )
        return
