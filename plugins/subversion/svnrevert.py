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

" SVN revert functionality "

import logging, os.path
from .svnstrconvert import notifyActionToString


class SVNRevertMixin:

    def __init__( self ):
        return

    def fileRevert( self ):
        path = str( self.fileParentMenu.menuAction().data().toString() )
        self.__svnRevert( path, False )
        return

    def dirRevert( self ):
        path = str( self.dirParentMenu.menuAction().data().toString() )
        self.__svnRevert( path, True )
        return

    def bufferRevert( self ):
        path = self.ide.currentEditorWidget.getFileName()
        self.__svnRevert( path, False )
        return

    def __svnRevert( self, path, recursively ):
        " Adds the given path to the repository "
        client = self.getSVNClient( self.getSettings() )

        pathList = []
        def notifyCallback( event, paths = pathList ):
            if event[ 'path' ]:
                path = event[ 'path' ]
                if os.path.isdir( path ) and not path.endswith( os.path.sep ):
                    path += os.path.sep
                action = notifyActionToString( event[ 'action' ] )
                if action:
                    logging.info( action + " " + path )
                    paths.append( path )
            return

        try:
            client.callback_notify = notifyCallback
            client.revert( path, recurse = recursively )

            if pathList:
                logging.info( "Finished" )
        except Exception as excpt:
            logging.error( str( excpt ) )

        for revertedPath in pathList:
            self.notifyPathChanged( revertedPath )
        return



