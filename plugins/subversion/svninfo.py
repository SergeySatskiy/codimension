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

" Codimension SVN plugin INFO command implementation "

import pysvn, os.path, logging
from svnstrconvert import ( nodeKindToString, scheduleToString,
                            timestampToString, statusToString, rawStatusToString )
from svnindicators import IND_ERROR
from PyQt4.QtCore import Qt
from PyQt4.QtGui import QApplication, QCursor


class SVNInfoMixin:

    def __init__( self ):
        return

    def fileInfo( self ):
        " Called when info requested for a file via context menu "
        path = str( self.fileParentMenu.menuAction().data().toString() )
        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
        try:
            self.__svnInfo( path )
        except Exception as exc:
            logging.error( str( exc ) )
        QApplication.restoreOverrideCursor()
        return

    def dirInfo( self ):
        " Called when info requested for a directory via context menu "
        path = str( self.dirParentMenu.menuAction().data().toString() )
        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
        try:
            self.__svnInfo( path )
        except Exception as exc:
            logging.error( str( exc ) )
        QApplication.restoreOverrideCursor()
        return

    def bufferInfo( self ):
        " Called when info requested for a buffer "
        path = self.ide.currentEditorWidget.getFileName()
        if not os.path.isabs( path ):
            logging.info( "SVN info is not applicable for never saved buffer" )
            return

        QApplication.setOverrideCursor( QCursor( Qt.WaitCursor ) )
        try:
            self.__svnInfo( path )
        except Exception as exc:
            logging.error( str( exc ) )
        QApplication.restoreOverrideCursor()
        return

    def getLocalStatusObject( self, client, path ):
        " Provides quick local SVN status for the item itself "
        try:
            statusList = client.status( path, update = False,
                                        depth = pysvn.depth.empty )
            if len( statusList ) != 1:
                return None
            return statusList[ 0 ]
        except:
            return None

    def getServerStatusObject( self, client, path ):
        " Provides SVN server status for the item itself "
        try:
            statusList = client.status( path, update = True,
                                        depth = pysvn.depth.empty )
            if len( statusList ) != 1:
                statusList = client.status( path, update = True,
                                            depth = pysvn.depth.unknown )
                if len( statusList ) != 1:
                    return None
            return statusList[ 0 ]
        except:
            return None

    def getServerInfoObject( self, client, info ):
        " Returns the server revision "
        repRevision = pysvn.Revision( pysvn.opt_revision_kind.head )
        try:
            entries = client.info2( info.URL, repRevision, recurse = False )
            if len( entries ) != 1:
                return None
            itemPath, info = entries[ 0 ]
            return info
        except:
            return None
        return None

    @staticmethod
    def __getLockInfo( lockInfo ):
        " Provides lock info as a list of strings "
        info = []
        if 'owner' in lockInfo:
            if lockInfo[ 'owner' ]:
                info.append( "Owner: " + lockInfo[ 'owner' ] )
            else:
                info.append( "Owner: Unknown" )
        if 'creation_date' in lockInfo:
            if lockInfo[ 'creation_date' ]:
                info.append( "Creation date: " +
                             timestampToString( lockInfo[ 'creation_date' ] ) )
            else:
                info.append( "Creation date: Unknown" )
        if 'expiration_date' in lockInfo:
            if lockInfo[ 'expiration_date' ]:
                info.append( "Expiration date: " +
                             timestampToString( lockInfo[ 'expiration_date' ] ) )
            else:
                info.append( "Expiration date: Unknown" )
        if 'token' in lockInfo:
            if lockInfo[ 'token' ]:
                info.append( "Token: " + lockInfo[ 'token' ] )
            else:
                info.append( "Token: None" )
        if 'comment' in lockInfo:
            if lockInfo[ 'comment' ]:
                info.append( "Comment: " +  lockInfo[ 'comment' ] )
            else:
                info.append( "Comment: None" )
        return info

    def __lastCommitMessage( self, client, serverInfoObject ):
        " Provides the server last commit message "
        revStart = pysvn.Revision( pysvn.opt_revision_kind.number,
                                   serverInfoObject.last_changed_rev.number )
        revEnd = pysvn.Revision( pysvn.opt_revision_kind.number,
                                 serverInfoObject.last_changed_rev.number )

        try:
            return client.log( serverInfoObject.URL, revStart, revEnd,
                               limit = 1 )[ 0 ].message
        except Exception:
            return "Could not get last change log message"

    def __lastCommitProperties( self, client, serverInfoObject ):
        " Provides the server properties "
        rev = pysvn.Revision( pysvn.opt_revision_kind.number,
                              serverInfoObject.last_changed_rev.number )
        try:
            propList = client.proplist( serverInfoObject.URL, rev,
                                        recurse = False )
            if len( propList ) != 1:
                return None
            return propList[ 0 ][ 1 ]
        except:
            return None

    def __localProperties( self, client, path ):
        " Provides the local copy properties "
        try:
            propList = client.proplist( path )
            if len( propList ) != 1:
                return None
            return propList[ 0 ][ 1 ]
        except:
            return None

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

        # Local info throws exceptions if something is broken
        itemPath, localInfoObject = getSVNInfo( client, path )
        serverInfoObject = self.getServerInfoObject( client, localInfoObject )
        serverProperties = self.__lastCommitProperties( client, serverInfoObject )
        localStatusObject = self.getLocalStatusObject( client, itemPath )
        localProperties = self.__localProperties( client, itemPath )

        message = "\nServer Info:"
        if serverInfoObject is None:
            message += "\n    Error getting server info"
        else:
            message += "\n    Last commit:"
            message += "\n        Revision: " + str( serverInfoObject.last_changed_rev.number )
            message += "\n        Timestamp: " + timestampToString( serverInfoObject.last_changed_date )
            message += "\n        Author: " + str( serverInfoObject.last_changed_author )
            message += "\n        Message: " + str( self.__lastCommitMessage( client, serverInfoObject ) )
            message += "\n    Properties:"
            if serverProperties is None:
                message += "\n        Error getting server properties"
            else:
                if len( serverProperties ) == 0:
                    message += "\n        No properties"
                else:
                    for key in serverProperties.keys():
                        message += "\n        " + key + ": " + serverProperties[ key ]
            if serverInfoObject.lock is None:
                message += "\n    Locked: False"
            else:
                message += "\n    Locked: True"
                for line in self.__getLockInfo( serverInfoObject.lock ):
                    message += "\n        " + line
            message += "\n    Node:"
            message += "\n        URL: " + serverInfoObject.URL
            message += "\n        Repository root URL: " + serverInfoObject.repos_root_URL
            message += "\n        Repository UUID: " + serverInfoObject.repos_UUID
            message += "\n        Kind: " + nodeKindToString( serverInfoObject.kind )

        message += "\nLocal Info:"
        if localInfoObject is None:
            message += "\n    Error getting local info"
        else:
            message += "\n    Status:"
            message += "\n        Content: " + rawStatusToString( localStatusObject.text_status )
            message += "\n        Properties: " + rawStatusToString( localStatusObject.prop_status )
            message += "\n    Checkout:"
            message += "\n        Revision: " + str( localInfoObject.last_changed_rev.number )
            message += "\n        Timestamp: " + timestampToString( localInfoObject.last_changed_date )
            message += "\n        Author: " + str( localInfoObject.last_changed_author )
            message += "\n    Properties:"
            if localProperties is None:
                message += "\n        Error getting local properties"
            else:
                if len( localProperties ) == 0:
                    message += "\n        No properties"
                else:
                    for key in localProperties.keys():
                        message += "\n        " + key + ": " + localProperties[ key ]
            if localInfoObject.lock is None:
                message += "\n    Locked: False"
            else:
                message += "\n    Locked: True"
                for line in self.__getLockInfo( localInfoObject.lock ):
                    message += "\n        " + line
            message += "\n    Node:"
            message += "\n        Path: " + itemPath
            message += "\n        Copied: " + str( bool( localStatusObject.is_copied ) )
            message += "\n        Switched: " + str( bool( localStatusObject.is_switched ) )
            message += "\n        Schedule: " + scheduleToString( localInfoObject.wc_info.schedule )

        logging.info( message )
        client = None
        return

def getSVNInfo( client, path, repRevision = None, pegRevision = None ):
    " Provides info for the given path "
    if repRevision is None:
        repRevision = pysvn.Revision( pysvn.opt_revision_kind.unspecified )
    if pegRevision is None:
        pegRevision = pysvn.Revision( pysvn.opt_revision_kind.unspecified )

    try:
        entries = client.info2( path, repRevision, pegRevision,
                                recurse = False )
        if len( entries ) != 1:
            raise Exception( "Unexpected number of entries for the path. "
                             "Expected 1, received " + str( len( entries ) ) )
        itemPath, info = entries[ 0 ]
        return itemPath, info
    except pysvn.ClientError as exc:
        errorCode = exc.args[ 1 ][ 0 ][ 1 ]
        if errorCode in [ pysvn.svn_err.wc_not_working_copy,
                          pysvn.svn_err.wc_path_not_found ]:
            raise Exception( "Not under SVN control" )
        message = exc.args[ 0 ]
        raise Exception( message )
