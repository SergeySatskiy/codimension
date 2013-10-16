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


def doSVNAdd( plugin, client, path, recursively ):
    " Does SVN add "
    pathList = []
    def notifyCallback( event, paths = pathList ):
        if event[ 'action' ] == pysvn.wc_notify_action.add:
            paths.append( event[ 'path' ] )
            logging.info( "Adding '" + event[ 'path' ] +
                          "' to SVN repository..." )
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
    except Exception, excpt:
        logging.error( str( excpt ) )

    for addedPath in pathList:
        plugin.notifyPathChanged( addedPath )
    return
