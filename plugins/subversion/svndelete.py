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

" SVN Delete functionality "

import logging, os.path
from svnstrconvert import notifyActionToString
from PyQt4.QtGui import QMessageBox


class SVNDeleteMixin:

    def __init__( self ):
        return

    def fileDelete( self ):
        path = str( self.fileParentMenu.menuAction().data().toString() )
        self.__svnDelete( path )
        return

    def dirDelete( self ):
        path = str( self.dirParentMenu.menuAction().data().toString() )
        self.__svnDelete( path )
        return

    def bufferDelete( self ):
        path = self.ide.currentEditorWidget.getFileName()
        self.__svnDelete( path )
        return

    def __svnDelete( self, path ):

        res = QMessageBox.warning( None, "Deleting from SVN",
                    "You are about to delete <b>" + path +
                    "</b> from SVN and from the disk.\nAre you sure?",
                           QMessageBox.StandardButtons(
                                QMessageBox.Cancel | QMessageBox.Yes ),
                           QMessageBox.Cancel )
        if res != QMessageBox.Yes:
            return

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
            client.remove( path )

            if pathList:
                logging.info( "Finished" )
        except Exception as excpt:
            logging.error( str( excpt ) )

        for revertedPath in pathList:
            self.notifyPathChanged( revertedPath )
        return
