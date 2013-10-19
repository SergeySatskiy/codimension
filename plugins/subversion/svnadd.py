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

""" Performs SVN add command """

import logging
import pysvn
from svnstrconvert import notifyActionToString


class SVNAddMixin:

    def __init__( self ):
        return

    def fileAddToRepository( self ):
        " Called when add for a file is requested "
        path = str( self.fileParentMenu.menuAction().data().toString() )
        self.__svnAdd( path, False )
        return

    def dirAddToRepository( self ):
        " Called when add for a directory is requested "
        path = str( self.dirParentMenu.menuAction().data().toString() )
        self.__svnAdd( path, False )
        return

    def dirAddToRepositoryRecursively( self ):
        " Called when add for a directory recursively is requested "
        path = str( self.dirParentMenu.menuAction().data().toString() )
        self.__svnAdd( path, True )
        return

    def bufferAddToRepository( self ):
        " Called when add for a buffer is requested "
        path = self.ide.currentEditorWidget.getFileName()
        self.__svnAdd( path, False )
        return

    def __svnAdd( self, path, recursively ):
        " Adds the given path to the repository "
        client = self.getSVNClient( self.getSettings() )
        doSVNAdd( self, client, path, recursively )
        return



def doSVNAdd( plugin, client, path, recursively ):
    " Does SVN add "
    pathList = []
    def notifyCallback( event, paths = pathList ):
        if path in event:
            if event[ 'path' ]:
                action = notifyActionToString( event[ 'action' ] )
                if action:
                    logging.info( action + " " + event[ 'path' ] )
                    paths.append( event[ 'path' ] )
        return

    try:
        client.callback_notify = notifyCallback
        if recursively:
            # This is a dir. It could be under VCS or not
            dirStatus = plugin.getLocalStatus( path )
            if dirStatus == plugin.NOT_UNDER_VCS:
                client.add( path, recurse = True )
            else:
                # Need to build the list manually
                statuses = plugin.getLocalStatus( path, pysvn.depth.infinity )
                if type( statuses ) != list:
                    logging.error( "Error checking local SVN statuses for " + path )
                    return

                pathsToAdd = []
                for item in statuses:
                    if item[ 1 ] == plugin.NOT_UNDER_VCS:
                        pathsToAdd.append( item[ 0 ] )

                if not pathsToAdd:
                    logging.info( "No paths to add for " + path )
                    return

                client.add( pathsToAdd )
        else:
            # It is a single file
            client.add( path )

        if pathList:
            logging.info( "Added" )
    except Exception, excpt:
        logging.error( str( excpt ) )

    for addedPath in pathList:
        plugin.notifyPathChanged( addedPath )
    return
